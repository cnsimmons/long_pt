#!/usr/bin/env python3
"""
Extract Individual Desikan-Killiany Parcels for VOTC Analysis
Creates anatomical masks for each relevant DK parcel in subject native space
"""

import subprocess
import nibabel as nib
import numpy as np
from pathlib import Path

# Paths
BASE_DIR = Path('/user_data/csimmon2/long_pt')
FS_DIR = Path('/lab_data/behrmannlab/hemi/FS')

# Subjects and hemispheres
SUBJECTS = {
    'sub-004': 'left',
    'sub-021': 'right'
}

# Desikan-Killiany label values
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

def extract_parcels(subject_id, hemisphere):
    """Extract all DK parcels for one subject"""
    
    print(f"\n{'='*70}")
    print(f"{subject_id} ({hemisphere} hemisphere)")
    print(f"{'='*70}")
    
    # Setup paths
    roi_dir = BASE_DIR / subject_id / 'ses-01' / 'ROIs'
    roi_dir.mkdir(parents=True, exist_ok=True)
    
    anat_dir = BASE_DIR / subject_id / 'ses-01' / 'anat'
    fsl_brain = anat_dir / f'{subject_id}_ses-01_T1w_brain.nii.gz'
    
    fs_aparc = FS_DIR / f'{subject_id}_ses-01' / 'mri' / 'aparc+aseg.mgz'
    fs_brain = FS_DIR / f'{subject_id}_ses-01' / 'mri' / 'brain.mgz'
    
    hemi_prefix = 'l' if hemisphere == 'left' else 'r'
    transform_file = anat_dir / 'fs2ses01.mat'
    
    # Load FreeSurfer parcellation
    print("\nLoading FreeSurfer parcellation...")
    aparc_img = nib.load(fs_aparc)
    aparc_data = aparc_img.get_fdata()
    
    # Create/check registration
    if not transform_file.exists():
        print("Computing FreeSurfer → Subject space registration...")
        temp_brain = roi_dir / 'temp_fs_brain.nii.gz'
        brain_img = nib.load(fs_brain)
        nib.save(nib.Nifti1Image(brain_img.get_fdata(), brain_img.affine), temp_brain)
        
        subprocess.run([
            'flirt',
            '-in', str(temp_brain),
            '-ref', str(fsl_brain),
            '-omat', str(transform_file),
            '-dof', '6',
            '-cost', 'corratio'
        ], check=True)
        
        temp_brain.unlink()
        print(f"  ✓ Registration saved: {transform_file.name}")
    else:
        print(f"  ✓ Using existing registration: {transform_file.name}")
    
    # Extract each parcel
    print(f"\nExtracting parcels...")
    created_masks = {}
    
    for parcel_name, label_value in PARCELS[hemisphere].items():
        
        # Create binary mask
        mask_data = np.zeros_like(aparc_data, dtype=np.float32)
        mask_data[aparc_data == label_value] = 1
        n_voxels_fs = int(np.sum(mask_data))
        
        if n_voxels_fs == 0:
            print(f"  ⚠️  {parcel_name:<20s}: Empty in FreeSurfer space")
            continue
        
        print(f"  {parcel_name:<20s}: {n_voxels_fs:6d} voxels (FS space)", end='')
        
        # Save temporary file
        temp_file = roi_dir / f'temp_{parcel_name}_fs.nii.gz'
        mask_img = nib.Nifti1Image(mask_data, aparc_img.affine)
        nib.save(mask_img, temp_file)
        
        # Transform to subject space
        output_file = roi_dir / f'{hemi_prefix}_{parcel_name}_mask.nii.gz'
        
        subprocess.run([
            'flirt',
            '-in', str(temp_file),
            '-ref', str(fsl_brain),
            '-out', str(output_file),
            '-applyxfm',
            '-init', str(transform_file),
            '-interp', 'nearestneighbour'
        ], check=True, capture_output=True)
        
        # Get final voxel count
        result = subprocess.run(
            ['fslstats', str(output_file), '-V'],
            capture_output=True,
            text=True,
            check=True
        )
        n_voxels_subj = result.stdout.split()[0]
        
        print(f" → {n_voxels_subj:>6s} voxels (subject space)")
        
        # Cleanup
        temp_file.unlink()
        
        created_masks[parcel_name] = output_file
    
    return created_masks


def main():
    """Extract parcels for all subjects"""
    
    print("="*70)
    print("DESIKAN-KILLIANY PARCEL EXTRACTION")
    print("="*70)
    
    all_results = {}
    
    for subject_id, hemisphere in SUBJECTS.items():
        try:
            masks = extract_parcels(subject_id, hemisphere)
            all_results[subject_id] = masks
        except Exception as e:
            print(f"\n❌ Error processing {subject_id}: {e}")
            all_results[subject_id] = {}
    
    # Summary
    print(f"\n{'='*70}")
    print("EXTRACTION COMPLETE")
    print(f"{'='*70}")
    
    for subject_id, masks in all_results.items():
        hemi = 'L' if SUBJECTS[subject_id] == 'left' else 'R'
        print(f"\n{subject_id} ({hemi}H): {len(masks)} parcels created")
        for parcel_name in masks.keys():
            print(f"  ✓ {parcel_name}")
    
    print()


if __name__ == "__main__":
    main()