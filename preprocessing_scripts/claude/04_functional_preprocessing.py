"""
Functional preprocessing for hemispherectomy patients
Includes motion correction, outlier detection, and basic preprocessing
"""
import os
import subprocess
import numpy as np
import nibabel as nib
from nilearn import image
import hemi_config as config

def detect_motion_outliers(subject_id):
    """
    Detect motion outliers using FSL motion outliers
    """
    print(f"Detecting motion outliers for {subject_id}")
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    fsl_dir = f"{sub_dir}/derivatives/fsl/{config.TASK}"
    
    # Create FSL directories
    os.makedirs(fsl_dir, exist_ok=True)
    
    for run in config.RUNS:
        print(f"  Processing run {run}")
        
        # Input functional file
        func_file = f"{sub_dir}/func/{subject_id}_ses-01_task-{config.TASK}_run-0{run}_bold.nii.gz"
        
        if not os.path.exists(func_file):
            print(f"    Warning: Functional file not found: {func_file}")
            continue
        
        # Create run directory
        run_dir = f"{fsl_dir}/run-0{run}"
        os.makedirs(run_dir, exist_ok=True)
        
        # Output files
        outliers_file = f"{run_dir}/{subject_id}_ses-01_task-{config.TASK}_run-0{run}_outliers.txt"
        outliers_plot = f"{run_dir}/{subject_id}_ses-01_task-{config.TASK}_run-0{run}_outliers.png"
        
        if os.path.exists(outliers_file):
            print(f"    Motion outliers already detected for run {run}")
            continue
        
        try:
            # Run FSL motion outliers
            cmd = [
                'fsl_motion_outliers',
                '-i', func_file,
                '-o', outliers_file,
                '-p', outliers_plot,
                '--dummy=0'
            ]
            subprocess.run(cmd, check=True)
            print(f"    Successfully detected motion outliers for run {run}")
            
        except subprocess.CalledProcessError as e:
            print(f"    Error detecting motion outliers for run {run}: {e}")

def get_functional_info(subject_id):
    """
    Get basic information about functional data (number of volumes, etc.)
    """
    print(f"Getting functional data info for {subject_id}")
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    func_info = {}
    
    for run in config.RUNS:
        func_file = f"{sub_dir}/func/{subject_id}_ses-01_task-{config.TASK}_run-0{run}_bold.nii.gz"
        
        if os.path.exists(func_file):
            try:
                img = nib.load(func_file)
                n_vols = img.shape[3] if len(img.shape) == 4 else 1
                func_info[f"run_{run}"] = {
                    'n_volumes': n_vols,
                    'shape': img.shape,
                    'file': func_file
                }
                print(f"  Run {run}: {n_vols} volumes, shape: {img.shape}")
                
            except Exception as e:
                print(f"  Error reading functional file for run {run}: {e}")
                func_info[f"run_{run}"] = None
        else:
            print(f"  Warning: Functional file not found for run {run}")
            func_info[f"run_{run}"] = None
    
    return func_info

def basic_functional_qc(subject_id):
    """
    Basic quality control checks for functional data
    """
    print(f"Running basic QC for {subject_id}")
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    
    qc_results = {
        'subject_id': subject_id,
        'runs_found': [],
        'volumes_per_run': {},
        'outliers_detected': {}
    }
    
    for run in config.RUNS:
        func_file = f"{sub_dir}/func/{subject_id}_ses-01_task-{config.TASK}_run-0{run}_bold.nii.gz"
        outliers_file = f"{sub_dir}/derivatives/fsl/{config.TASK}/run-0{run}/{subject_id}_ses-01_task-{config.TASK}_run-0{run}_outliers.txt"
        
        if os.path.exists(func_file):
            qc_results['runs_found'].append(run)
            
            # Get number of volumes
            try:
                img = nib.load(func_file)
                n_vols = img.shape[3] if len(img.shape) == 4 else 1
                qc_results['volumes_per_run'][run] = n_vols
            except:
                qc_results['volumes_per_run'][run] = 'Error'
            
            # Check for outliers
            if os.path.exists(outliers_file):
                try:
                    with open(outliers_file, 'r') as f:
                        outlier_lines = f.readlines()
                    qc_results['outliers_detected'][run] = len(outlier_lines)
                except:
                    qc_results['outliers_detected'][run] = 'Error'
            else:
                qc_results['outliers_detected'][run] = 0
    
    # Print QC summary
    print(f"  QC Summary for {subject_id}:")
    print(f"    Runs found: {qc_results['runs_found']}")
    print(f"    Volumes per run: {qc_results['volumes_per_run']}")
    print(f"    Outliers detected: {qc_results['outliers_detected']}")
    
    return qc_results

def load_functional_data(subject_id):
    """
    Load functional data for GLMSingle analysis
    """
    print(f"Loading functional data for {subject_id}")
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    functional_data = []
    
    for run in config.RUNS:
        func_file = f"{sub_dir}/func/{subject_id}_ses-01_task-{config.TASK}_run-0{run}_bold.nii.gz"
        
        if os.path.exists(func_file):
            try:
                img = image.load_img(func_file)
                data = img.get_fdata()
                functional_data.append(data)
                print(f"  Loaded run {run}: shape {data.shape}")
                
            except Exception as e:
                print(f"  Error loading functional data for run {run}: {e}")
                return None
        else:
            print(f"  Error: Functional file not found for run {run}")
            return None
    
    if len(functional_data) != len(config.RUNS):
        print(f"  Warning: Expected {len(config.RUNS)} runs, but loaded {len(functional_data)}")
    
    return functional_data

def create_functional_mask(subject_id):
    """
    Create a basic functional mask from the first run
    """
    print(f"Creating functional mask for {subject_id}")
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    
    # Use first run to create mask
    func_file = f"{sub_dir}/func/{subject_id}_ses-01_task-{config.TASK}_run-01_bold.nii.gz"
    mask_file = f"{sub_dir}/derivatives/func_mask.nii.gz"
    
    if os.path.exists(mask_file):
        print(f"  Functional mask already exists: {mask_file}")
        return True
    
    if not os.path.exists(func_file):
        print(f"  Error: First functional run not found: {func_file}")
        return False
    
    try:
        # Create mask using FSL
        cmd = ['fslmaths', func_file, '-Tmean', '-bin', mask_file]
        subprocess.run(cmd, check=True)
        print(f"  Successfully created functional mask: {mask_file}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"  Error creating functional mask: {e}")
        return False

def process_functional_data(subject_id):
    """
    Complete functional preprocessing for a subject
    """
    print(f"\nProcessing functional data for {subject_id}")
    
    # Step 1: Get functional data info
    func_info = get_functional_info(subject_id)
    
    # Step 2: Detect motion outliers
    detect_motion_outliers(subject_id)
    
    # Step 3: Create functional mask
    create_functional_mask(subject_id)
    
    # Step 4: Run QC checks
    qc_results = basic_functional_qc(subject_id)
    
    return func_info, qc_results

def main():
    """
    Run functional preprocessing for all subjects
    """
    print("Starting functional preprocessing...")
    
    all_qc_results = []
    
    for subject_id in config.SUBJECTS.keys():
        func_info, qc_results = process_functional_data(subject_id)
        all_qc_results.append(qc_results)
    
    # Print summary
    print("\nFunctional preprocessing summary:")
    for qc in all_qc_results:
        print(f"  {qc['subject_id']}: {len(qc['runs_found'])} runs, outliers: {qc['outliers_detected']}")
    
    print("Functional preprocessing complete!")

if __name__ == "__main__":
    main()
