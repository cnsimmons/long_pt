"""
Registration module for hemispherectomy patients
Registers mirrored brains to MNI space and creates transformation matrices
"""
import os
import subprocess
import hemi_config as config

def register_anatomical_to_mni(subject_id):
    """
    Register anatomical image to MNI space using mirrored brain for patients
    """
    print(f"Registering {subject_id} anatomical to MNI space")
    
    subject_info = config.SUBJECTS[subject_id]
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    anat_dir = f"{sub_dir}/anat"
    
    # Input files
    original_brain = f"{anat_dir}/{subject_id}_ses-01_T1w_brain.nii.gz"
    
    if subject_info['group'] == 'patient':
        # For patients: use mirrored brain for registration
        registration_brain = f"{anat_dir}/{subject_id}_ses-01_T1w_brain_mirrored.nii.gz"
    else:
        # For controls: use original brain
        registration_brain = original_brain
    
    # Output files
    transform_matrix = f"{anat_dir}/anat2stand.mat"
    inverse_matrix = f"{anat_dir}/mni2anat.mat"
    registered_brain = f"{anat_dir}/{subject_id}_ses-01_T1w_brain_stand.nii.gz"
    
    # Check if files exist
    if not os.path.exists(registration_brain):
        print(f"  Error: Registration brain not found: {registration_brain}")
        return False
    
    if os.path.exists(transform_matrix):
        print(f"  Registration already complete for {subject_id}")
        return True
    
    try:
        # Step 1: Create transformation matrix (mirrored/original brain -> MNI)
        print(f"  Creating transformation matrix...")
        cmd = [
            'flirt',
            '-in', registration_brain,
            '-ref', config.MNI_BRAIN,
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
        print(f"  Applying transformation to original brain...")
        cmd = [
            'flirt',
            '-in', original_brain,
            '-ref', config.MNI_BRAIN,
            '-out', registered_brain,
            '-applyxfm',
            '-init', transform_matrix,
            '-interp', 'trilinear'
        ]
        subprocess.run(cmd, check=True)
        
        # Step 3: Create inverse transformation matrix (MNI -> anatomical)
        print(f"  Creating inverse transformation matrix...")
        cmd = [
            'flirt',
            '-in', config.MNI_BRAIN,
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
        
        print(f"  Successfully registered {subject_id} to MNI space")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"  Error during registration: {e}")
        return False

def register_rois_to_subject(subject_id):
    """
    Register ROI parcels from MNI space to subject space
    """
    print(f"Registering ROIs to {subject_id} space")
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    anat_dir = f"{sub_dir}/anat"
    roi_dir = f"{sub_dir}/derivatives/rois"
    
    # Create ROI directory
    os.makedirs(f"{roi_dir}/parcels", exist_ok=True)
    
    # Input files
    inverse_matrix = f"{anat_dir}/mni2anat.mat"
    reference_brain = f"{anat_dir}/{subject_id}_ses-01_T1w_brain.nii.gz"
    
    if not os.path.exists(inverse_matrix):
        print(f"  Error: Inverse transformation matrix not found: {inverse_matrix}")
        return False
    
    if not os.path.exists(reference_brain):
        print(f"  Error: Reference brain not found: {reference_brain}")
        return False
    
    # Register each ROI
    for roi_name in config.ROI_PARCELS:
        roi_mni = f"{config.PARCEL_DIR}/{roi_name}.nii.gz"
        roi_subject = f"{roi_dir}/parcels/{roi_name}.nii.gz"
        
        if not os.path.exists(roi_mni):
            print(f"    Warning: ROI not found in MNI space: {roi_mni}")
            continue
        
        if os.path.exists(roi_subject):
            print(f"    ROI already registered: {roi_name}")
            continue
        
        try:
            # Register ROI to subject space
            cmd = [
                'flirt',
                '-in', roi_mni,
                '-ref', reference_brain,
                '-out', roi_subject,
                '-applyxfm',
                '-init', inverse_matrix,
                '-interp', 'trilinear'
            ]
            subprocess.run(cmd, check=True)
            
            # Binarize the ROI
            cmd = ['fslmaths', roi_subject, '-bin', roi_subject]
            subprocess.run(cmd, check=True)
            
            print(f"    Successfully registered ROI: {roi_name}")
            
        except subprocess.CalledProcessError as e:
            print(f"    Error registering ROI {roi_name}: {e}")
    
    return True

def check_registration_quality(subject_id):
    """
    Basic check of registration quality
    """
    print(f"Checking registration quality for {subject_id}")
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    anat_dir = f"{sub_dir}/anat"
    
    registered_brain = f"{anat_dir}/{subject_id}_ses-01_T1w_brain_stand.nii.gz"
    
    if not os.path.exists(registered_brain):
        print(f"  Error: Registered brain not found: {registered_brain}")
        return False
    
    # You could add more sophisticated checks here, such as:
    # - Computing overlap metrics
    # - Visual inspection commands
    # - Checking for proper brain coverage
    
    print(f"  Registration files created successfully")
    print(f"  Manual inspection recommended: {registered_brain}")
    return True

def process_registration(subject_id):
    """
    Complete registration pipeline for a subject
    """
    print(f"\nProcessing registration for {subject_id}")
    
    # Step 1: Register anatomical to MNI
    if not register_anatomical_to_mni(subject_id):
        return False
    
    # Step 2: Register ROIs to subject space
    if not register_rois_to_subject(subject_id):
        print(f"  Warning: ROI registration had issues for {subject_id}")
    
    # Step 3: Check registration quality
    return check_registration_quality(subject_id)

def main():
    """
    Run registration for all subjects
    """
    print("Starting registration pipeline...")
    
    for subject_id in config.SUBJECTS.keys():
        success = process_registration(subject_id)
        if not success:
            print(f"  Warning: Registration failed for {subject_id}")
    
    print("Registration pipeline complete!")

if __name__ == "__main__":
    main()
