#!/usr/bin/env python3
"""
Diagnostic script to check registration between T1w and functional data
This is CRITICAL - misalignment invalidates all ROI analyses
"""

import nibabel as nib
import numpy as np
from nilearn import plotting, image
import matplotlib.pyplot as plt

def check_registration(subject, session):
    """
    Check if T1w_brain aligns with functional zstat maps
    """
    
    print(f"\n{'='*70}")
    print(f"REGISTRATION CHECK: {subject} session {session}")
    print(f"{'='*70}\n")
    
    # Define paths - adjust these to your actual structure
    anat_path = f'/user_data/csimmon2/long_pt/derivatives/fmriprep/{subject}/ses-{session}/anat/{subject}_ses-{session}_space-T1w_desc-preproc_T1w.nii.gz'
    
    # Try to find a functional zstat
    # Common FSL output locations:
    possible_zstat_paths = [
        f'/user_data/csimmon2/long_pt/analyses/{subject}/ses-{session}.feat/stats/zstat1.nii.gz',
        f'/user_data/csimmon2/long_pt/derivatives/{subject}/ses-{session}/func/zstat1.nii.gz',
        f'/user_data/csimmon2/long_pt/analyses/highlevel/{subject}_ses-{session}_zstat1.nii.gz',
    ]
    
    # Also check for the FGOTS ROI mask
    roi_path = f'/user_data/csimmon2/long_pt/masks/{subject}_FGOTS_mask.nii.gz'
    
    print("1. Checking file dimensions and affines:\n")
    
    # Load anatomical
    try:
        anat_img = nib.load(anat_path)
        print(f"✓ Anatomical T1w:")
        print(f"  Path: {anat_path}")
        print(f"  Shape: {anat_img.shape}")
        print(f"  Affine:\n{anat_img.affine}\n")
        print(f"  Voxel size: {anat_img.header.get_zooms()}")
    except:
        print(f"✗ Could not load anatomical: {anat_path}")
        anat_img = None
    
    # Try to load functional zstat
    zstat_img = None
    for zpath in possible_zstat_paths:
        try:
            zstat_img = nib.load(zpath)
            print(f"✓ Functional zstat:")
            print(f"  Path: {zpath}")
            print(f"  Shape: {zstat_img.shape}")
            print(f"  Affine:\n{zstat_img.affine}\n")
            print(f"  Voxel size: {zstat_img.header.get_zooms()}")
            break
        except:
            continue
    
    if zstat_img is None:
        print("✗ Could not find any zstat files. Checked:")
        for p in possible_zstat_paths:
            print(f"    {p}")
    
    # Load ROI if exists
    try:
        roi_img = nib.load(roi_path)
        print(f"\n✓ ROI mask (FGOTS):")
        print(f"  Path: {roi_path}")
        print(f"  Shape: {roi_img.shape}")
        print(f"  Affine:\n{roi_img.affine}\n")
        print(f"  Voxel size: {roi_img.header.get_zooms()}")
        print(f"  Non-zero voxels: {np.sum(roi_img.get_fdata() > 0)}")
    except:
        print(f"\n✗ Could not load ROI: {roi_path}")
        roi_img = None
    
    # Check alignment
    print("\n2. Checking if images are in same space:\n")
    
    if anat_img and zstat_img:
        # Check if shapes match
        if anat_img.shape[:3] == zstat_img.shape[:3]:
            print("✓ Shapes MATCH - same dimensions")
        else:
            print("✗ Shapes DIFFER - images in different spaces!")
            print(f"  Anatomical: {anat_img.shape}")
            print(f"  Functional: {zstat_img.shape}")
        
        # Check if affines match (within tolerance)
        affine_diff = np.abs(anat_img.affine - zstat_img.affine).max()
        if affine_diff < 0.01:
            print("✓ Affines MATCH - same coordinate system")
        else:
            print("✗ Affines DIFFER - coordinate systems don't match!")
            print(f"  Max difference: {affine_diff:.6f}")
    
    if anat_img and roi_img:
        if anat_img.shape[:3] == roi_img.shape[:3]:
            print("✓ ROI and anatomical shapes MATCH")
        else:
            print("✗ ROI and anatomical shapes DIFFER!")
            print(f"  Anatomical: {anat_img.shape}")
            print(f"  ROI: {roi_img.shape}")
        
        affine_diff = np.abs(anat_img.affine - roi_img.affine).max()
        if affine_diff < 0.01:
            print("✓ ROI and anatomical affines MATCH")
        else:
            print("✗ ROI and anatomical affines DIFFER!")
            print(f"  Max difference: {affine_diff:.6f}")
    
    # Create overlay visualization if we have both images
    if anat_img and zstat_img:
        print("\n3. Creating overlay visualization...\n")
        
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        
        # If images are in different spaces, try to resample
        if anat_img.shape[:3] != zstat_img.shape[:3]:
            print("⚠ Images in different spaces - attempting to resample functional to anatomical...")
            try:
                from nilearn.image import resample_to_img
                zstat_resampled = resample_to_img(zstat_img, anat_img)
                print("✓ Resampling successful")
            except Exception as e:
                print(f"✗ Resampling failed: {e}")
                zstat_resampled = zstat_img
        else:
            zstat_resampled = zstat_img
        
        # Plot anatomical
        plotting.plot_anat(anat_img, title='Anatomical T1w', 
                          axes=axes[0, 0], display_mode='x', cut_coords=1)
        plotting.plot_anat(anat_img, title='Anatomical T1w', 
                          axes=axes[0, 1], display_mode='y', cut_coords=1)
        plotting.plot_anat(anat_img, title='Anatomical T1w', 
                          axes=axes[0, 2], display_mode='z', cut_coords=1)
        
        # Plot overlay
        plotting.plot_stat_map(zstat_resampled, bg_img=anat_img, 
                              title='Functional on Anatomical',
                              axes=axes[1, 0], display_mode='x', cut_coords=1,
                              threshold=2.3, cmap='hot')
        plotting.plot_stat_map(zstat_resampled, bg_img=anat_img,
                              title='Functional on Anatomical', 
                              axes=axes[1, 1], display_mode='y', cut_coords=1,
                              threshold=2.3, cmap='hot')
        plotting.plot_stat_map(zstat_resampled, bg_img=anat_img,
                              title='Functional on Anatomical',
                              axes=axes[1, 2], display_mode='z', cut_coords=1,
                              threshold=2.3, cmap='hot')
        
        plt.tight_layout()
        output_path = f'/user_data/csimmon2/long_pt/analyses/registration_check_{subject}_ses{session}.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"✓ Saved visualization: {output_path}")
        plt.show()
    
    return anat_img, zstat_img, roi_img


def find_transformation_matrix(subject, session):
    """
    Look for FSL transformation matrices
    """
    print(f"\n4. Looking for registration/transformation files:\n")
    
    import os
    import glob
    
    # Common locations for FSL registration files
    search_paths = [
        f'/user_data/csimmon2/long_pt/analyses/{subject}/ses-{session}.feat/reg/',
        f'/user_data/csimmon2/long_pt/derivatives/fmriprep/{subject}/ses-{session}/func/',
        f'/user_data/csimmon2/long_pt/derivatives/{subject}/ses-{session}/transforms/',
    ]
    
    for search_path in search_paths:
        if os.path.exists(search_path):
            print(f"✓ Found directory: {search_path}")
            
            # Look for transformation files
            mat_files = glob.glob(os.path.join(search_path, '*.mat'))
            nii_files = glob.glob(os.path.join(search_path, '*highres*.nii*'))
            
            if mat_files:
                print(f"  Transformation matrices found:")
                for f in mat_files:
                    print(f"    - {os.path.basename(f)}")
            
            if nii_files:
                print(f"  Registered images found:")
                for f in nii_files:
                    print(f"    - {os.path.basename(f)}")
        else:
            print(f"✗ Directory not found: {search_path}")


# ============================================================================
# RUN CHECKS
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("CRITICAL REGISTRATION DIAGNOSTIC")
    print("Checking alignment between anatomical and functional data")
    print("="*70)
    
    # Check one subject/session
    subject = 'sub-004'
    session = '01'
    
    print("\nAdjust the paths in this script to match your directory structure!")
    print("Key paths to check:")
    print("  1. T1w anatomical image")
    print("  2. Functional zstat maps")
    print("  3. ROI masks")
    print("  4. Transformation matrices (.mat files)")
    
    anat, zstat, roi = check_registration(subject, session)
    find_transformation_matrix(subject, session)
    
    print("\n" + "="*70)
    print("DIAGNOSIS SUMMARY")
    print("="*70)
    
    print("\nWhat to look for:")
    print("  ✗ Different shapes = Images in different spaces (BIG PROBLEM)")
    print("  ✗ Different affines = Wrong coordinate system (BIG PROBLEM)")
    print("  ✓ Same shapes + affines = Likely correct (but check overlay)")
    
    print("\nIf misaligned, you need to:")
    print("  1. Find the correct transformation matrices")
    print("  2. Transform ROI to functional space (or vice versa)")
    print("  3. Re-extract all statistics")
    
    print("\n⚠ Until registration is confirmed, all current analyses are suspect!")