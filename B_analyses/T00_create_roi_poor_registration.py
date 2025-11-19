#!/usr/bin/env python3
"""
Extract Individual Desikan-Killiany Parcels for VOTC Analysis (CSV-driven)
"""

import subprocess
import nibabel as nib
import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR = Path('/user_data/csimmon2/long_pt')
FS_DIR = Path('/lab_data/behrmannlab/hemi/FS')
CSV_FILE = Path('/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv')

SKIP_SUBS = ['sub-004', 'sub-021', 'sub-108']
SESSION_START = {'sub-010': 2, 'sub-018': 2, 'sub-068': 2}

PARCELS = {
    'left': {
        'fusiform': 1007,
        'lateraloccipital': 1011,
        'parahippocampal': 1016,
        'inferiortemporal': 1009,
        'middletemporal': 1015,
        'lingual': 1013,
        'isthmuscingulate': 1010
    },
    'right': {
        'fusiform': 2007,
        'lateraloccipital': 2011,
        'parahippocampal': 2016,
        'inferiortemporal': 2009,
        'middletemporal': 2015,
        'lingual': 2013,
        'isthmuscingulate': 2010
    }
}

def extract_parcels(subject_id, hemisphere, first_ses):
    """Extract all DK parcels for one subject"""
    
    print(f"\n{'='*70}")
    print(f"{subject_id} ({hemisphere} hemisphere)")
    print(f"{'='*70}")
    
    roi_dir = BASE_DIR / subject_id / f'ses-{first_ses:02d}' / 'ROIs'
    roi_dir.mkdir(parents=True, exist_ok=True)
    
    anat_dir = BASE_DIR / subject_id / f'ses-{first_ses:02d}' / 'anat'
    fsl_brain = anat_dir / f'{subject_id}_ses-{first_ses:02d}_T1w_brain.nii.gz'
    
    fs_aparc = FS_DIR / f'{subject_id}_ses-{first_ses:02d}' / 'mri' / 'aparc+aseg.mgz'
    fs_brain = FS_DIR / f'{subject_id}_ses-{first_ses:02d}' / 'mri' / 'brain.mgz'
    
    if not fs_aparc.exists():
        print(f"  ⚠️  FreeSurfer data not found: {fs_aparc}")
        return {}
    
    hemi_prefix = 'l' if hemisphere == 'left' else 'r'
    transform_file = anat_dir / f'fs2ses{first_ses:02d}.mat'
    
    print("\nLoading FreeSurfer parcellation...")
    aparc_img = nib.load(fs_aparc)
    aparc_data = aparc_img.get_fdata()
    
    if not transform_file.exists():
        print("Computing FreeSurfer → Subject space registration...")
        temp_brain = roi_dir / 'temp_fs_brain.nii.gz'
        brain_img = nib.load(fs_brain)
        nib.save(nib.Nifti1Image(brain_img.get_fdata(), brain_img.affine), temp_brain)
        
        subprocess.run([
            'flirt', '-in', str(temp_brain), '-ref', str(fsl_brain),
            '-omat', str(transform_file), '-dof', '6', '-cost', 'corratio'
        ], check=True)
        
        temp_brain.unlink()
        print(f"  ✓ Registration saved")
    else:
        print(f"  ✓ Using existing registration")
    
    print(f"\nExtracting parcels...")
    created_masks = {}
    
    for parcel_name, label_value in PARCELS[hemisphere].items():
        mask_data = np.zeros_like(aparc_data, dtype=np.float32)
        mask_data[aparc_data == label_value] = 1
        n_voxels_fs = int(np.sum(mask_data))
        
        if n_voxels_fs == 0:
            print(f"  ⚠️  {parcel_name:<20s}: Empty in FS space")
            continue
        
        print(f"  {parcel_name:<20s}: {n_voxels_fs:6d} voxels (FS)", end='')
        
        temp_file = roi_dir / f'temp_{parcel_name}_fs.nii.gz'
        nib.save(nib.Nifti1Image(mask_data, aparc_img.affine), temp_file)
        
        output_file = roi_dir / f'{hemi_prefix}_{parcel_name}_mask.nii.gz'
        
        subprocess.run([
            'flirt', '-in', str(temp_file), '-ref', str(fsl_brain),
            '-out', str(output_file), '-applyxfm', '-init', str(transform_file),
            '-interp', 'nearestneighbour'
        ], check=True, capture_output=True)
        
        result = subprocess.run(
            ['fslstats', str(output_file), '-V'],
            capture_output=True, text=True, check=True
        )
        n_voxels_subj = result.stdout.split()[0]
        print(f" → {n_voxels_subj:>6s} voxels (subject)")
        
        temp_file.unlink()
        created_masks[parcel_name] = output_file
    
    return created_masks

def main():
    print("="*70)
    print("DESIKAN-KILLIANY PARCEL EXTRACTION")
    print("="*70)
    
    df = pd.read_csv(CSV_FILE)
    all_results = {}
    
    for _, row in df.iterrows():
        subject_id = row['sub']
        
        if subject_id in SKIP_SUBS:
            continue
        
        if row['patient'] != 1:
            continue
        
        hemisphere = row['intact_hemi']
        first_ses = SESSION_START.get(subject_id, 1)
        
        try:
            masks = extract_parcels(subject_id, hemisphere, first_ses)
            all_results[subject_id] = masks
        except Exception as e:
            print(f"\n❌ Error: {e}")
            all_results[subject_id] = {}
    
    print(f"\n{'='*70}")
    print("COMPLETE")
    print(f"{'='*70}")
    
    for subject_id, masks in all_results.items():
        print(f"\n{subject_id}: {len(masks)} parcels")
        for parcel_name in masks.keys():
            print(f"  ✓ {parcel_name}")

if __name__ == "__main__":
    main()