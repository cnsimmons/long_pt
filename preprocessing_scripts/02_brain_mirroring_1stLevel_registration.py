"""
Brain mirroring and registration for long_pt hemispherectomy patients
Adapted from register_mirror.py script
"""
import os
import subprocess
import numpy as np
import pandas as pd
import nibabel as nib
from nilearn import image
from glob import glob

# Configuration
RAW_DIR = '/lab_data/behrmannlab/hemi/Raw'
PROCESSED_DIR = '/lab_data/behrmannlab/claire/long_pt'

# Subject configuration with intact hemispheres
SUBJECTS_INFO = {
    'sub-004': {
        'sessions': [1, 2, 3, 5, 6],
        'intact_hemi': 'left',
        'group': 'patient'
    },
    'sub-007': {
        'sessions': [1, 2],
        'intact_hemi': 'right',
        'group': 'patient'
    },
    'sub-021': {
        'sessions': [1, 3, 4],
        'intact_hemi': 'left',
        'group': 'patient'
    }
}

# FSL paths
MNI_BRAIN = '/opt/fsl/6.0.3/data/standard/MNI152_T1_2mm_brain.nii.gz'

def skull_strip_anatomical(subject_id, session):
    """
    Perform skull stripping on anatomical image using FSL BET
    """
    print(f"  Skull stripping {subject_id} ses-{session:02d}")
    
    # Raw anatomical file
    anat_file = f'{RAW_DIR}/{subject_id}/ses-{session:02d}/anat/{subject_id}_ses-{session:02d}_T1w.nii.gz'
    
    # Output files in processed directory
    processed_anat_dir = f'{PROCESSED_DIR}/{subject_id}/ses-{session:02d}/anat'
    os.makedirs(processed_anat_dir, exist_ok=True)
    
    brain_file = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain.nii.gz'
    mask_file = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain_mask.nii.gz'
    
    if not os.path.exists(anat_file):
        print(f"    Error: Anatomical file not found: {anat_file}")
        return False
    
    if os.path.exists(brain_file):
        print(f"    Brain-extracted file already exists")
        return True
    
    try:
        # Run FSL BET for skull stripping
        cmd = ['bet', anat_file, brain_file, '-R', '-B', '-m']
        subprocess.run(cmd, check=True)
        print(f"    Successfully skull stripped anatomical")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"    Error during skull stripping: {e}")
        return False

def create_mirror_brain(subject_id, session, intact_hemi):
    """
    Create mirrored brain for hemispherectomy patient registration
    Adapted from original register_mirror.py
    """
    print(f"  Creating mirrored brain for {subject_id} ses-{session:02d} (intact: {intact_hemi})")
    
    processed_anat_dir = f'{PROCESSED_DIR}/{subject_id}/ses-{session:02d}/anat'
    
    # Input files
    brain_file = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain.nii.gz'
    mask_file = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain_mask.nii.gz'
    
    # Output files
    mirrored_file = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain_mirrored.nii.gz'
    hemi_mask_file = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain_mask_{intact_hemi}.nii.gz'
    
    if not os.path.exists(brain_file) or not os.path.exists(mask_file):
        print(f"    Error: Required files not found for {subject_id} ses-{session:02d}")
        return False
    
    if os.path.exists(mirrored_file):
        print(f"    Mirrored brain already exists")
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
        
        print(f"    Successfully created mirrored brain")
        return True
        
    except Exception as e:
        print(f"    Error creating mirrored brain: {e}")
        return False

def register_to_mni(subject_id, session, group):
    """
    Register anatomical image to MNI space using mirrored brain for patients
    Adapted from original register_mirror.py
    """
    print(f"  Registering {subject_id} ses-{session:02d} to MNI space")
    
    processed_anat_dir = f'{PROCESSED_DIR}/{subject_id}/ses-{session:02d}/anat'
    
    # Input files
    original_brain = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain.nii.gz'
    
    if group == 'patient':
        # For patients: use mirrored brain for registration
        registration_brain = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain_mirrored.nii.gz'
    else:
        # For controls: use original brain
        registration_brain = original_brain
    
    # Output files
    transform_matrix = f'{processed_anat_dir}/anat2stand.mat'
    inverse_matrix = f'{processed_anat_dir}/mni2anat.mat'
    registered_brain = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain_stand.nii.gz'
    
    # Check if files exist
    if not os.path.exists(registration_brain):
        print(f"    Error: Registration brain not found: {registration_brain}")
        return False
    
    if os.path.exists(transform_matrix):
        print(f"    Registration already complete")
        return True
    
    try:
        # Step 1: Create transformation matrix (mirrored/original brain -> MNI)
        print(f"    Creating transformation matrix...")
        cmd = [
            'flirt',
            '-in', registration_brain,
            '-ref', MNI_BRAIN,
            '-omat', transform_matrix,
            '-bins', '256',
            '-cost', 'corratio',
            '-searchrx', '-90', '90',
            '-searchry', '-90', '90', 
            '-searchrz', '-90', '90',
            '-dof', '12'
        ]
        subprocess.run(cmd, check=True)
        
        # Step 2: Apply transformation to original brain (not mirrored)
        print(f"    Applying transformation to original brain...")
        cmd = [
            'flirt',
            '-in', original_brain,
            '-ref', MNI_BRAIN,
            '-out', registered_brain,
            '-applyxfm',
            '-init', transform_matrix,
            '-interp', 'trilinear'
        ]
        subprocess.run(cmd, check=True)
        
        # Step 3: Create inverse transformation matrix (MNI -> anatomical)
        print(f"    Creating inverse transformation matrix...")
        cmd = [
            'flirt',
            '-in', MNI_BRAIN,
            '-ref', registration_brain,
            '-omat', inverse_matrix,
            '-bins', '256',
            '-cost', 'corratio',
            '-searchrx', '-90', '90',
            '-searchry', '-90', '90',
            '-searchrz', '-90', '90',
            '-dof', '12'
        ]
        subprocess.run(cmd, check=True)
        
        print(f"    Successfully registered to MNI space")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"    Error during registration: {e}")
        return False

def process_subject_session(subject_id, session, subject_info):
    """
    Complete anatomical processing for one subject/session
    """
    print(f"\nProcessing {subject_id} ses-{session:02d}")
    
    # Step 1: Skull strip
    if not skull_strip_anatomical(subject_id, session):
        print(f"  Failed skull stripping for {subject_id} ses-{session:02d}")
        return False
    
    # Step 2: Create mirrored brain (for patients only)
    if subject_info['group'] == 'patient':
        if not create_mirror_brain(subject_id, session, subject_info['intact_hemi']):
            print(f"  Failed brain mirroring for {subject_id} ses-{session:02d}")
            return False
    
    # Step 3: Register to MNI
    if not register_to_mni(subject_id, session, subject_info['group']):
        print(f"  Failed MNI registration for {subject_id} ses-{session:02d}")
        return False
    
    return True

def check_anatomical_completeness():
    """
    Check completion status of anatomical processing
    """
    print("\nChecking anatomical processing completeness...")
    
    for subject_id, subject_info in SUBJECTS_INFO.items():
        print(f"\n{subject_id} ({subject_info['intact_hemi']} intact):")
        
        for session in subject_info['sessions']:
            processed_anat_dir = f'{PROCESSED_DIR}/{subject_id}/ses-{session:02d}/anat'
            
            # Check skull stripping
            brain_file = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain.nii.gz'
            skull_strip = "✓" if os.path.exists(brain_file) else "✗"
            
            # Check mirroring (patients only)
            if subject_info['group'] == 'patient':
                mirrored_file = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain_mirrored.nii.gz'
                mirroring = "✓" if os.path.exists(mirrored_file) else "✗"
            else:
                mirroring = "N/A"
            
            # Check registration
            transform_file = f'{processed_anat_dir}/anat2stand.mat'
            registration = "✓" if os.path.exists(transform_file) else "✗"
            
            print(f"  ses-{session:02d}: Skull strip {skull_strip}, Mirroring {mirroring}, Registration {registration}")

def main():
    """
    Run anatomical processing for all subjects
    """
    print("Starting brain mirroring and anatomical registration...")
    print(f"Processing subjects: {list(SUBJECTS_INFO.keys())}")
    
    total_sessions = 0
    successful_sessions = 0
    
    for subject_id, subject_info in SUBJECTS_INFO.items():
        print(f"\n{'='*60}")
        print(f"Processing {subject_id} (intact hemisphere: {subject_info['intact_hemi']})")
        print(f"{'='*60}")
        
        for session in subject_info['sessions']:
            total_sessions += 1
            
            # Check if raw anatomical data exists
            anat_file = f'{RAW_DIR}/{subject_id}/ses-{session:02d}/anat/{subject_id}_ses-{session:02d}_T1w.nii.gz'
            if not os.path.exists(anat_file):
                print(f"\nSkipping {subject_id} ses-{session:02d}: Raw anatomical not found")
                continue
            
            if process_subject_session(subject_id, session, subject_info):
                successful_sessions += 1
    
    print(f"\n{'='*60}")
    print(f"ANATOMICAL PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"Sessions processed: {successful_sessions}/{total_sessions}")
    
    # Check completeness
    check_anatomical_completeness()
    
    print("\nAnatomical processing complete!")
    print("Next step: Generate .fsf files and run FEAT analyses")

if __name__ == "__main__":
    main()