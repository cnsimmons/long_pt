#!/usr/bin/env python3
"""
VOTC ROI Creation: Fusiform (face-word) and LO+PPA (object-house)
"""

import os
import subprocess
import nibabel as nib
import numpy as np
from pathlib import Path

BASE_DIR = Path('/user_data/csimmon2/long_pt')
FS_DIR = Path('/lab_data/behrmannlab/hemi/FS')

SUBJECTS = {
    'sub-004': 'left',
    'sub-007': 'left', 
    'sub-021': 'right'
}

# Desikan-Killiany labels
LH_FUSIFORM = 1007
LH_LATERALOCCIPITAL = 1011
LH_PARAHIPPOCAMPAL = 1016

RH_FUSIFORM = 2007
RH_LATERALOCCIPITAL = 2011
RH_PARAHIPPOCAMPAL = 2016

def process_subject(subject, hemi):
    """Create two ROI masks: fusiform and LO+PPA"""
    
    print(f"\n{'='*60}")
    print(f"{subject} ({hemi} hemisphere)")
    print(f"{'='*60}")
    
    # Paths
    roi_dir = BASE_DIR / subject / 'ses-01' / 'ROIs'
    roi_dir.mkdir(parents=True, exist_ok=True)
    
    anat_dir = BASE_DIR / subject / 'ses-01' / 'anat'
    fsl_brain = anat_dir / f'{subject}_ses-01_T1w_brain.nii.gz'
    
    fs_aparc = FS_DIR / f'{subject}_ses-01' / 'mri' / 'aparc+aseg.mgz'
    fs_brain = FS_DIR / f'{subject}_ses-01' / 'mri' / 'brain.mgz'
    
    hemi_prefix = 'l' if hemi == 'left' else 'r'
    transform_file = anat_dir / 'fs2ses01.mat'
    
    # Select labels
    if hemi == 'left':
        fusiform_label = LH_FUSIFORM
        lo_label = LH_LATERALOCCIPITAL
        ppa_label = LH_PARAHIPPOCAMPAL
    else:
        fusiform_label = RH_FUSIFORM
        lo_label = RH_LATERALOCCIPITAL
        ppa_label = RH_PARAHIPPOCAMPAL
    
    # Load aparc
    aparc = nib.load(fs_aparc)
    aparc_data = aparc.get_fdata()
    
    # Create fusiform mask
    fusiform_mask = np.zeros_like(aparc_data)
    fusiform_mask[aparc_data == fusiform_label] = 1
    fusiform_vox = int(np.sum(fusiform_mask))
    
    # Create LO+PPA mask
    lo_ppa_mask = np.zeros_like(aparc_data)
    lo_ppa_mask[aparc_data == lo_label] = 1
    lo_ppa_mask[aparc_data == ppa_label] = 1
    lo_ppa_vox = int(np.sum(lo_ppa_mask))
    
    print(f"Fusiform: {fusiform_vox} voxels")
    print(f"LO+PPA: {lo_ppa_vox} voxels")
    
    # Save temp files
    temp_fusiform = roi_dir / 'temp_fusiform_fs.nii.gz'
    temp_lo_ppa = roi_dir / 'temp_lo_ppa_fs.nii.gz'
    temp_brain = roi_dir / 'temp_brain_fs.nii.gz'
    
    nib.save(nib.Nifti1Image(fusiform_mask.astype(np.float32), aparc.affine), temp_fusiform)
    nib.save(nib.Nifti1Image(lo_ppa_mask.astype(np.float32), aparc.affine), temp_lo_ppa)
    
    brain = nib.load(fs_brain)
    nib.save(nib.Nifti1Image(brain.get_fdata(), brain.affine), temp_brain)
    
    # Register if needed
    if not transform_file.exists():
        print("Computing registration...")
        subprocess.run([
            'flirt', '-in', str(temp_brain), '-ref', str(fsl_brain),
            '-omat', str(transform_file), '-dof', '6', '-cost', 'corratio'
        ], check=True)
    
    # Apply transformations
    fusiform_out = roi_dir / f'{hemi_prefix}_fusiform_mask.nii.gz'
    lo_ppa_out = roi_dir / f'{hemi_prefix}_LO_PPA_mask.nii.gz'
    
    for temp_mask, output in [(temp_fusiform, fusiform_out), (temp_lo_ppa, lo_ppa_out)]:
        subprocess.run([
            'flirt', '-in', str(temp_mask), '-ref', str(fsl_brain),
            '-out', str(output), '-applyxfm', '-init', str(transform_file),
            '-interp', 'nearestneighbour'
        ], check=True)
        
        result = subprocess.run(['fslstats', str(output), '-V'], 
                              capture_output=True, text=True, check=True)
        vox = result.stdout.split()[0]
        print(f"  → {output.name}: {vox} voxels")
    
    # Cleanup
    temp_fusiform.unlink(missing_ok=True)
    temp_lo_ppa.unlink(missing_ok=True)
    temp_brain.unlink(missing_ok=True)
    
    return fusiform_out, lo_ppa_out

if __name__ == "__main__":
    print("Creating category-specific ROIs")
    
    results = {}
    for subject, hemi in SUBJECTS.items():
        try:
            fusiform, lo_ppa = process_subject(subject, hemi)
            results[subject] = {'fusiform': fusiform, 'lo_ppa': lo_ppa}
        except Exception as e:
            print(f"Error: {e}")
            results[subject] = None
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for subject, masks in results.items():
        if masks:
            print(f"{subject}:")
            print(f"  Fusiform: {masks['fusiform'].name}")
            print(f"  LO+PPA: {masks['lo_ppa'].name}")