#!/usr/bin/env python3
"""
Brain mirroring and registration for long_pt hemispherectomy patients (CSV-driven)
Adapted from register_mirror.py script
"""
import os
import subprocess
import numpy as np
import pandas as pd
import nibabel as nib
from nilearn import image

# Configuration
RAW_DIR = '/lab_data/behrmannlab/hemi/Raw'
PROCESSED_DIR = '/user_data/csimmon2/long_pt'
CSV_FILE = '/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv'
MNI_BRAIN = '/opt/fsl/6.0.3/data/standard/MNI152_T1_2mm_brain.nii.gz'

# Subjects to skip (already processed)
SKIP_SUBS = ['sub-004', 'sub-007', 'sub-021', 'sub-108']

# Special session mappings
SESSION_START = {
    'sub-010': 2,
    'sub-018': 2
}

def get_sessions_for_subject(row):
    """Count non-empty age columns to determine session count"""
    age_cols = ['age_1', 'age_2', 'age_3', 'age_4', 'age_5']
    return sum(1 for col in age_cols if pd.notna(row[col]) and row[col] != '')

def skull_strip_anatomical(subject_id, session):
    """Perform skull stripping on anatomical image using FSL BET"""
    print(f"  Skull stripping {subject_id} ses-{session:02d}")
    
    anat_file = f'{RAW_DIR}/{subject_id}/ses-{session:02d}/anat/{subject_id}_ses-{session:02d}_T1w.nii.gz'
    processed_anat_dir = f'{PROCESSED_DIR}/{subject_id}/ses-{session:02d}/anat'
    os.makedirs(processed_anat_dir, exist_ok=True)
    
    brain_file = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain.nii.gz'
    
    if not os.path.exists(anat_file):
        print(f"    Error: Anatomical file not found")
        return False
    
    if os.path.exists(brain_file):
        print(f"    Brain-extracted file already exists")
        return True
    
    try:
        cmd = ['bet', anat_file, brain_file, '-R', '-B', '-m']
        subprocess.run(cmd, check=True)
        print(f"    Successfully skull stripped")
        return True
    except subprocess.CalledProcessError as e:
        print(f"    Error during skull stripping: {e}")
        return False

def create_mirror_brain(subject_id, session, intact_hemi):
    """Create mirrored brain for hemispherectomy patient registration"""
    print(f"  Creating mirrored brain (intact: {intact_hemi})")
    
    processed_anat_dir = f'{PROCESSED_DIR}/{subject_id}/ses-{session:02d}/anat'
    brain_file = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain.nii.gz'
    mask_file = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain_mask.nii.gz'
    mirrored_file = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain_mirrored.nii.gz'
    hemi_mask_file = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain_mask_{intact_hemi}.nii.gz'
    
    if not os.path.exists(brain_file) or not os.path.exists(mask_file):
        print(f"    Error: Required files not found")
        return False
    
    if os.path.exists(mirrored_file):
        print(f"    Mirrored brain already exists")
        return True
    
    try:
        anat_img = image.load_img(brain_file)
        mask_img = image.load_img(mask_file)
        anat_data = anat_img.get_fdata()
        mask_data = mask_img.get_fdata()
        affine = anat_img.affine
        
        mid_x = anat_data.shape[0] // 2
        hemi_mask = mask_data.copy()
        hemi_mask[hemi_mask > 0] = 1
        
        anat_mirrored = anat_data.copy()
        anat_flipped = np.flip(anat_data, axis=0)
        
        if intact_hemi.lower() == 'left':
            hemi_mask[mid_x:, :, :] = 0
            anat_mirrored[mid_x:, :, :] = anat_flipped[mid_x:, :, :]
        else:
            hemi_mask[:mid_x, :, :] = 0
            anat_mirrored[:mid_x, :, :] = anat_flipped[:mid_x, :, :]
        
        nib.save(nib.Nifti1Image(anat_mirrored, affine), mirrored_file)
        nib.save(nib.Nifti1Image(hemi_mask, affine), hemi_mask_file)
        
        print(f"    Successfully created mirrored brain")
        return True
    except Exception as e:
        print(f"    Error creating mirrored brain: {e}")
        return False

def register_to_mni(subject_id, session, is_patient):
    """Register anatomical image to MNI space"""
    print(f"  Registering to MNI space")
    
    processed_anat_dir = f'{PROCESSED_DIR}/{subject_id}/ses-{session:02d}/anat'
    original_brain = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain.nii.gz'
    
    if is_patient:
        registration_brain = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain_mirrored.nii.gz'
    else:
        registration_brain = original_brain
    
    transform_matrix = f'{processed_anat_dir}/anat2stand.mat'
    inverse_matrix = f'{processed_anat_dir}/mni2anat.mat'
    registered_brain = f'{processed_anat_dir}/{subject_id}_ses-{session:02d}_T1w_brain_stand.nii.gz'
    
    if not os.path.exists(registration_brain):
        print(f"    Error: Registration brain not found")
        return False
    
    if os.path.exists(transform_matrix):
        print(f"    Registration already complete")
        return True
    
    try:
        # Create transformation matrix
        print(f"    Creating transformation matrix...")
        subprocess.run([
            'flirt', '-in', registration_brain, '-ref', MNI_BRAIN,
            '-omat', transform_matrix, '-bins', '256', '-cost', 'corratio',
            '-searchrx', '-90', '90', '-searchry', '-90', '90',
            '-searchrz', '-90', '90', '-dof', '12'
        ], check=True)
        
        # Apply to original brain
        print(f"    Applying transformation...")
        subprocess.run([
            'flirt', '-in', original_brain, '-ref', MNI_BRAIN,
            '-out', registered_brain, '-applyxfm', '-init', transform_matrix,
            '-interp', 'trilinear'
        ], check=True)
        
        # Create inverse
        subprocess.run([
            'flirt', '-in', MNI_BRAIN, '-ref', registration_brain,
            '-omat', inverse_matrix, '-bins', '256', '-cost', 'corratio',
            '-searchrx', '-90', '90', '-searchry', '-90', '90',
            '-searchrz', '-90', '90', '-dof', '12'
        ], check=True)
        
        print(f"    Successfully registered")
        return True
    except subprocess.CalledProcessError as e:
        print(f"    Error during registration: {e}")
        return False

def process_subject_session(subject_id, session, is_patient, intact_hemi):
    """Complete anatomical processing for one subject/session"""
    print(f"\nProcessing {subject_id} ses-{session:02d}")
    
    if not skull_strip_anatomical(subject_id, session):
        return False
    
    if is_patient:
        if not create_mirror_brain(subject_id, session, intact_hemi):
            return False
    
    if not register_to_mni(subject_id, session, is_patient):
        return False
    
    return True

def main():
    """Run anatomical processing for all subjects"""
    print("Starting brain mirroring and anatomical registration (CSV-driven)...")
    
    df = pd.read_csv(CSV_FILE)
    total_sessions = 0
    successful_sessions = 0
    
    for _, row in df.iterrows():
        subject_id = row['sub']
        
        if subject_id in SKIP_SUBS:
            print(f"\nSKIP: {subject_id} (already processed)")
            continue
        
        session_count = get_sessions_for_subject(row)
        start_ses = SESSION_START.get(subject_id, 1)
        is_patient = row['patient'] == 1
        intact_hemi = row['intact_hemi']
        
        print(f"\n{'='*60}")
        print(f"{subject_id} ({session_count} sessions, intact: {intact_hemi})")
        print(f"{'='*60}")
        
        for i in range(session_count):
            session = start_ses + i
            total_sessions += 1
            
            anat_file = f'{RAW_DIR}/{subject_id}/ses-{session:02d}/anat/{subject_id}_ses-{session:02d}_T1w.nii.gz'
            if not os.path.exists(anat_file):
                print(f"\nSkipping {subject_id} ses-{session:02d}: Raw anatomical not found")
                continue
            
            if process_subject_session(subject_id, session, is_patient, intact_hemi):
                successful_sessions += 1
    
    print(f"\n{'='*60}")
    print(f"Sessions processed: {successful_sessions}/{total_sessions}")
    print("Anatomical processing complete!")

if __name__ == "__main__":
    main()