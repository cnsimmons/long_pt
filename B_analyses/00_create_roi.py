#!/usr/bin/env python3
"""
VOTC ROI Creation: Individual Desikan-Killiany parcels
"""

import subprocess
import nibabel as nib
import numpy as np
from pathlib import Path

BASE_DIR = Path('/user_data/csimmon2/long_pt')
FS_DIR = Path('/lab_data/behrmannlab/hemi/FS')

SUBJECTS = {
    'sub-004': 'left',
    'sub-021': 'right'
}

# Desikan-Killiany labels
PARCELS = {
    'left': {
        'fusiform': 1007,
        'lateraloccipital': 1011,
        'parahippocampal': 1016,
        'inferiortemporal': 1009,
        'middletemporal': 1015
    },
    'right': {
        'fusiform': 2007,
        'lateraloccipital': 2011,
        'parahippocampal': 2016,
        'inferiortemporal': 2009,
        'middletemporal': 2015
    }
}

def create_individual_parcels(subject, hemi):
    """Create individual parcel masks"""
    
    print(f"\n{'='*60}")
    print(f"{subject} ({hemi} hemisphere)")
    print(f"{'='*60}")
    
    # Paths
    roi_dir = BASE_DIR / subject / 'ses-01' / 'ROIs'
    anat_dir = BASE_DIR / subject / 'ses-01' / 'anat'
    fsl_brain = anat_dir / f'{subject}_ses-01_T1w_brain.nii.gz'
    
    fs_aparc = FS_DIR / f'{subject}_ses-01' / 'mri' / 'aparc+aseg.mgz'
    fs_brain = FS_DIR / f'{subject}_ses-01' / 'mri' / 'brain.mgz'
    
    hemi_prefix = 'l' if hemi == 'left' else 'r'
    transform_file = anat_dir / 'fs2ses01.mat'
    
    # Load aparc
    aparc = nib.load(fs_aparc)
    aparc_data = aparc.get_fdata()
    
    # Check/create registration
    if not transform_file.exists():
        print("Computing registration...")
        temp_brain = roi_dir / 'temp_brain_fs.nii.gz'
        brain = nib.load(fs_brain)
        nib.save(nib.Nifti1Image(brain.get_fdata(), brain.affine), temp_brain)
        
        subprocess.run([
            'flirt', '-in', str(temp_brain), '-ref', str(fsl_brain),
            '-omat', str(transform_file), '-dof', '6', '-cost', 'corratio'
        ], check=True)
        temp_brain.unlink()
    
    created_masks = {}
    
    # Create each parcel
    for parcel_name, label in PARCELS[hemi].items():
        print(f"\nProcessing {parcel_name}...")
        
        # Create mask
        mask = np.zeros_like(aparc_data)
        mask[aparc_data == label] = 1
        n_vox_fs = int(np.sum(mask))
        print(f"  FreeSurfer space: {n_vox_fs} voxels")
        
        if n_vox_fs == 0:
            print(f"  ⚠️  Empty mask, skipping")
            continue
        
        # Save temp
        temp_file = roi_dir / f'temp_{parcel_name}_fs.nii.gz'
        nib.save(nib.Nifti1Image(mask.astype(np.float32), aparc.affine), temp_file)
        
        # Transform to subject space
        output_file = roi_dir / f'{hemi_prefix}_{parcel_name}_mask.nii.gz'
        subprocess.run([
            'flirt', '-in', str(temp_file), '-ref', str(fsl_brain),
            '-out', str(output_file), '-applyxfm', '-init', str(transform_file),
            '-interp', 'nearestneighbour'
        ], check=True)
        
        # Get final voxel count
        result = subprocess.run(['fslstats', str(output_file), '-V'], 
                              capture_output=True, text=True, check=True)
        n_vox = result.stdout.split()[0]
        print(f"  Subject space: {n_vox} voxels")
        print(f"  ✓ Saved: {output_file.name}")
        
        created_masks[parcel_name] = output_file
        temp_file.unlink()
    
    return created_masks

if __name__ == "__main__":
    print("Creating individual Desikan-Killiany parcels for VOTC")
    
    all_results = {}
    for subject, hemi in SUBJECTS.items():
        try:
            masks = create_individual_parcels(subject, hemi)
            all_results[subject] = masks
        except Exception as e:
            print(f"❌ Error processing {subject}: {e}")
            all_results[subject] = {}
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for subject, masks in all_results.items():
        print(f"\n{subject}:")
        for name, path in masks.items():
            print(f"  ✓ {name}")