#!/usr/bin/env python3
"""
Simple VOTC ROI Creation and Registration
==========================================
Creates VOTC ROIs from FreeSurfer parcellation and registers to FSL space.

Requirements: Python with nibabel, FSL commands (flirt, fslmaths, fslstats)
"""

import os
import subprocess
import nibabel as nib
import numpy as np
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path('/user_data/csimmon2/long_pt')
FS_DIR = Path('/lab_data/behrmannlab/hemi/FS')

SUBJECTS = {
    'sub-004': 'left',
    'sub-007': 'left', 
    'sub-021': 'right'
}

# Destrieux labels (empirically verified)
LH_FUSIFORM = 11121
LH_OTS = 11160

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def process_subject(subject, hemi):
    """Process one subject: extract ROI and register to FSL space"""
    
    print(f"\n{'='*60}")
    print(f"Processing {subject}")
    print(f"{'='*60}")
    
    # Setup paths
    roi_dir = BASE_DIR / subject / 'ses-01' / 'ROIs'
    roi_dir.mkdir(parents=True, exist_ok=True)
    
    anat_dir = BASE_DIR / subject / 'ses-01' / 'anat'
    fsl_brain = anat_dir / f'{subject}_ses-01_T1w_brain.nii.gz'
    
    fs_aparc = FS_DIR / f'{subject}_ses-01' / 'mri' / 'aparc.a2009s+aseg.mgz'
    fs_brain = FS_DIR / f'{subject}_ses-01' / 'mri' / 'brain.mgz'
    
    # Temp files
    temp_votc = roi_dir / 'temp_votc_fs.nii.gz'
    temp_brain = roi_dir / 'temp_brain_fs.nii.gz'
    
    # Output
    hemi_label = 'l' if hemi == 'left' else 'r'
    output_mask = roi_dir / f'{hemi_label}_VOTC_FG_OTS_mask.nii.gz'
    transform_file = anat_dir / 'fs2ses01.mat'
    
    # ------------------------------------------------------------------------
    # Step 1: Load FreeSurfer aparc and extract VOTC parcels
    # ------------------------------------------------------------------------
    print("\nStep 1: Extracting VOTC parcels from FreeSurfer aparc...")
    
    aparc = nib.load(fs_aparc)
    aparc_data = aparc.get_fdata()
    
    # Create mask
    mask = np.zeros_like(aparc_data)
    if hemi == 'left':
        mask[aparc_data == LH_FUSIFORM] = 1
        mask[aparc_data == LH_OTS] = 1
    else:
        mask[aparc_data == 12121] = 1  # RH fusiform
        mask[aparc_data == 12160] = 1  # RH OTS
    
    n_voxels_fs = int(np.sum(mask))
    print(f"  VOTC mask: {n_voxels_fs} voxels in FreeSurfer space")
    
    # Save as NIfTI
    mask_img = nib.Nifti1Image(mask.astype(np.float32), aparc.affine, aparc.header)
    nib.save(mask_img, temp_votc)
    print(f"  Saved: {temp_votc}")
    
    # ------------------------------------------------------------------------
    # Step 2: Convert FreeSurfer brain for registration
    # ------------------------------------------------------------------------
    print("\nStep 2: Converting FreeSurfer brain...")
    
    brain = nib.load(fs_brain)
    brain_nii = nib.Nifti1Image(brain.get_fdata(), brain.affine, brain.header)
    nib.save(brain_nii, temp_brain)
    print(f"  Saved: {temp_brain}")
    
    # ------------------------------------------------------------------------
    # Step 3: Register FreeSurfer → FSL (compute transformation)
    # ------------------------------------------------------------------------
    print("\nStep 3: Computing registration...")
    
    if not transform_file.exists():
        print("  Running FLIRT...")
        cmd = [
            'flirt',
            '-in', str(temp_brain),
            '-ref', str(fsl_brain),
            '-omat', str(transform_file),
            '-dof', '6',
            '-cost', 'corratio'
        ]
        subprocess.run(cmd, check=True)
        print(f"  Saved: {transform_file}")
    else:
        print(f"  Using existing: {transform_file}")
    
    # ------------------------------------------------------------------------
    # Step 4: Apply transformation to VOTC mask
    # ------------------------------------------------------------------------
    print("\nStep 4: Applying transformation to mask...")
    
    cmd = [
        'flirt',
        '-in', str(temp_votc),
        '-ref', str(fsl_brain),
        '-out', str(output_mask),
        '-applyxfm',
        '-init', str(transform_file),
        '-interp', 'nearestneighbour'
    ]
    subprocess.run(cmd, check=True)
    
    # ------------------------------------------------------------------------
    # Step 5: Verify and clean up
    # ------------------------------------------------------------------------
    print("\nStep 5: Verification...")
    
    result = subprocess.run(
        ['fslstats', str(output_mask), '-V'],
        capture_output=True,
        text=True,
        check=True
    )
    n_voxels_fsl = result.stdout.split()[0]
    
    print(f"  Output: {output_mask}")
    print(f"  Voxels: {n_voxels_fsl}")
    
    # Clean up temp files
    temp_votc.unlink(missing_ok=True)
    temp_brain.unlink(missing_ok=True)
    
    print(f"\n✓ {subject} complete!")
    
    return output_mask, n_voxels_fsl

# ============================================================================
# RUN FOR ALL SUBJECTS
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("VOTC ROI Creation and Registration")
    print("="*60)
    
    results = {}
    
    for subject, hemi in SUBJECTS.items():
        try:
            output_mask, n_voxels = process_subject(subject, hemi)
            results[subject] = {'mask': output_mask, 'voxels': n_voxels}
        except Exception as e:
            print(f"\n✗ Error processing {subject}: {e}")
            results[subject] = {'mask': None, 'voxels': None}
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for subject, info in results.items():
        if info['mask']:
            print(f"  ✓ {subject}: {info['mask']} ({info['voxels']} voxels)")
        else:
            print(f"  ✗ {subject}: FAILED")
    
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("1. Verify ROIs in FSLeyes")
    print("2. Update extraction script to use: l_VOTC_FG_OTS_mask.nii.gz")
    print("3. Run your contrast extraction pipeline")
    print("="*60 + "\n")