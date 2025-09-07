"""
Anatomical preprocessing including skull stripping and brain mirroring
for hemispherectomy patients
"""
import os
import subprocess
import numpy as np
import nibabel as nib
from nilearn import image
import hemi_config as config

def skull_strip_anatomical(subject_id):
    """
    Perform skull stripping on anatomical image using FSL BET
    """
    print(f"Skull stripping anatomical data for {subject_id}")
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    
    # Find T1w file
    anat_file = f"{sub_dir}/anat/{subject_id}_ses-01_T1w.nii.gz"
    brain_file = f"{sub_dir}/anat/{subject_id}_ses-01_T1w_brain.nii.gz"
    mask_file = f"{sub_dir}/anat/{subject_id}_ses-01_T1w_brain_mask.nii.gz"
    
    if not os.path.exists(anat_file):
        print(f"  Error: Anatomical file not found: {anat_file}")
        return False
    
    if os.path.exists(brain_file):
        print(f"  Brain-extracted file already exists: {brain_file}")
        return True
    
    try:
        # Run FSL BET for skull stripping
        cmd = f"bet {anat_file} {brain_file} -R -B -m"
        subprocess.run(cmd.split(), check=True)
        print(f"  Successfully skull stripped: {brain_file}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"  Error during skull stripping: {e}")
        return False

def create_mirror_brain(subject_id):
    """
    Create mirrored brain for hemispherectomy patient registration
    """
    print(f"Creating mirrored brain for {subject_id}")
    
    # Get subject info
    subject_info = config.SUBJECTS[subject_id]
    intact_hemi = subject_info['intact_hemi']
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    
    # Input files
    brain_file = f"{sub_dir}/anat/{subject_id}_ses-01_T1w_brain.nii.gz"
    mask_file = f"{sub_dir}/anat/{subject_id}_ses-01_T1w_brain_mask.nii.gz"
    
    # Output files
    mirrored_file = f"{sub_dir}/anat/{subject_id}_ses-01_T1w_brain_mirrored.nii.gz"
    hemi_mask_file = f"{sub_dir}/anat/{subject_id}_ses-01_T1w_brain_mask_{intact_hemi}.nii.gz"
    
    if not os.path.exists(brain_file) or not os.path.exists(mask_file):
        print(f"  Error: Required files not found for {subject_id}")
        return False
    
    if os.path.exists(mirrored_file):
        print(f"  Mirrored brain already exists: {mirrored_file}")
        return True
    
    try:
        # Load anatomical data
        anat_img = image.load_img(brain_file)
        mask_img = image.load_img(mask_file)
        
        anat_data = anat_img.get_fdata()
        mask_data = mask_img.get_fdata()
        affine = anat_img.affine
        
        # Find midpoint of image
        mid_x = anat_data.shape[0] // 2
        
        # Create hemisphere mask
        hemi_mask = mask_data.copy()
        hemi_mask[hemi_mask > 0] = 1
        
        # Create mirrored brain
        anat_mirrored = anat_data.copy()
        anat_flipped = np.flip(anat_data, axis=0)  # Flip along x-axis
        
        if intact_hemi.lower() == 'left':
            # Keep left hemisphere, replace right with flipped left
            hemi_mask[mid_x:, :, :] = 0  # Mask out right hemisphere
            anat_mirrored[mid_x:, :, :] = anat_flipped[mid_x:, :, :]
        else:
            # Keep right hemisphere, replace left with flipped right
            hemi_mask[:mid_x, :, :] = 0  # Mask out left hemisphere
            anat_mirrored[:mid_x, :, :] = anat_flipped[:mid_x, :, :]
        
        # Save mirrored brain
        mirrored_img = nib.Nifti1Image(anat_mirrored, affine)
        nib.save(mirrored_img, mirrored_file)
        
        # Save hemisphere mask
        hemi_mask_img = nib.Nifti1Image(hemi_mask, affine)
        nib.save(hemi_mask_img, hemi_mask_file)
        
        print(f"  Successfully created mirrored brain: {mirrored_file}")
        print(f"  Created hemisphere mask: {hemi_mask_file}")
        return True
        
    except Exception as e:
        print(f"  Error creating mirrored brain: {e}")
        return False

def create_hemisphere_masks(subject_id):
    """
    Create left and right hemisphere masks for controls (if needed)
    """
    print(f"Creating hemisphere masks for {subject_id}")
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    mask_file = f"{sub_dir}/anat/{subject_id}_ses-01_T1w_brain_mask.nii.gz"
    
    if not os.path.exists(mask_file):
        print(f"  Error: Brain mask not found: {mask_file}")
        return False
    
    try:
        # Load brain mask
        mask_img = image.load_img(mask_file)
        mask_data = mask_img.get_fdata()
        affine = mask_img.affine
        
        # Find midpoint
        mid_x = mask_data.shape[0] // 2
        
        # Create hemisphere masks
        for hemi in ['left', 'right']:
            hemi_mask = mask_data.copy()
            hemi_mask[hemi_mask > 0] = 1
            
            if hemi == 'left':
                hemi_mask[mid_x:, :, :] = 0
            else:
                hemi_mask[:mid_x, :, :] = 0
            
            # Save hemisphere mask
            hemi_mask_file = f"{sub_dir}/anat/{subject_id}_ses-01_T1w_brain_mask_{hemi}.nii.gz"
            hemi_mask_img = nib.Nifti1Image(hemi_mask, affine)
            nib.save(hemi_mask_img, hemi_mask_file)
        
        print(f"  Created hemisphere masks for {subject_id}")
        return True
        
    except Exception as e:
        print(f"  Error creating hemisphere masks: {e}")
        return False

def process_anatomical_data(subject_id):
    """
    Complete anatomical preprocessing for a subject
    """
    print(f"\nProcessing anatomical data for {subject_id}")
    
    # Step 1: Skull strip
    if not skull_strip_anatomical(subject_id):
        return False
    
    # Step 2: Create hemisphere-specific processing
    subject_info = config.SUBJECTS[subject_id]
    if subject_info['group'] == 'patient':
        # For patients: create mirrored brain
        return create_mirror_brain(subject_id)
    else:
        # For controls: create hemisphere masks
        return create_hemisphere_masks(subject_id)

def main():
    """
    Run anatomical preprocessing for all subjects
    """
    print("Starting anatomical preprocessing...")
    
    for subject_id in config.SUBJECTS.keys():
        success = process_anatomical_data(subject_id)
        if not success:
            print(f"  Warning: Anatomical preprocessing failed for {subject_id}")
    
    print("Anatomical preprocessing complete!")

if __name__ == "__main__":
    main()
