"""
Data organization and timing file conversion for hemispherectomy patients
"""
import os
import shutil
import pandas as pd
import numpy as np
from glob import glob
import hemi_config as config

def organize_subject_data(subject_id):
    """
    Copy and organize data for a single subject
    """
    print(f"Organizing data for {subject_id}")
    
    # Create subject directories
    sub_processed_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    os.makedirs(f"{sub_processed_dir}/anat", exist_ok=True)
    os.makedirs(f"{sub_processed_dir}/func", exist_ok=True)
    os.makedirs(f"{sub_processed_dir}/derivatives", exist_ok=True)
    os.makedirs(f"{sub_processed_dir}/timing", exist_ok=True)
    
    # Define source directories
    sub_raw_dir = f"{config.RAW_DATA_DIR}/{subject_id}/ses-01"
    
    # Copy anatomical data
    anat_files = glob(f"{sub_raw_dir}/anat/*T1w*.nii.gz")
    if anat_files:
        for anat_file in anat_files:
            filename = os.path.basename(anat_file)
            shutil.copy(anat_file, f"{sub_processed_dir}/anat/{filename}")
        print(f"  Copied anatomical data")
    else:
        print(f"  Warning: No anatomical data found for {subject_id}")
    
    # Copy functional data
    for run in config.RUNS:
        func_file = f"{sub_raw_dir}/func/{subject_id}_ses-01_task-{config.TASK}_run-0{run}_bold.nii.gz"
        if os.path.exists(func_file):
            shutil.copy(func_file, f"{sub_processed_dir}/func/")
            print(f"  Copied functional data for run {run}")
        else:
            print(f"  Warning: No functional data found for {subject_id} run {run}")
    
    # Convert timing files
    convert_timing_files(subject_id, sub_raw_dir, sub_processed_dir)

def convert_timing_files(subject_id, raw_dir, processed_dir):
    """
    Convert FSL 3-column timing files to GLMSingle design matrices
    """
    print(f"  Converting timing files for {subject_id}")
    
    for run in config.RUNS:
        events_file = f"{raw_dir}/func/{subject_id}_ses-01_task-{config.TASK}_run-0{run}_events.tsv"
        
        if os.path.exists(events_file):
            # Read events file
            events = pd.read_csv(events_file, sep='\t')
            
            # Create FSL-style timing files for each condition
            for condition in config.CONDITIONS:
                cond_events = events[events['trial_type'] == condition]
                if len(cond_events) > 0:
                    # Create 3-column format (onset, duration, amplitude)
                    timing_data = pd.DataFrame({
                        'onset': cond_events['onset'],
                        'duration': cond_events['duration'], 
                        'amplitude': np.ones(len(cond_events))
                    })
                    
                    # Save timing file
                    timing_file = f"{processed_dir}/timing/{config.TASK}_{subject_id}_run-0{run}_{condition}.txt"
                    timing_data.to_csv(timing_file, sep='\t', header=False, index=False)
            
            print(f"    Converted timing files for run {run}")
        else:
            print(f"    Warning: No events file found for {subject_id} run {run}")

def create_design_matrices(subject_id, n_vols):
    """
    Create GLMSingle-compatible design matrices from timing files
    """
    print(f"Creating design matrices for {subject_id}")
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    design_matrices = []
    
    for run in config.RUNS:
        # Initialize design matrix for this run
        design_matrix = np.zeros((n_vols, len(config.CONDITIONS)))
        
        for i, condition in enumerate(config.CONDITIONS):
            timing_file = f"{sub_dir}/timing/{config.TASK}_{subject_id}_run-0{run}_{condition}.txt"
            
            if os.path.exists(timing_file):
                timing_data = pd.read_csv(timing_file, sep='\t', header=None)
                timing_data.columns = ['onset', 'duration', 'amplitude']
                
                # Convert to TR units
                onset_trs = (timing_data['onset'] / config.TR).astype(int)
                duration_trs = (timing_data['duration'] / config.TR).astype(int)
                
                # Fill design matrix (block design)
                for onset, duration in zip(onset_trs, duration_trs):
                    end_tr = min(onset + duration, n_vols)
                    design_matrix[onset:end_tr, i] = 1
        
        design_matrices.append(design_matrix)
        
        # Save design matrix
        np.save(f"{sub_dir}/timing/design_matrix_run-0{run}.npy", design_matrix)
    
    print(f"  Created {len(design_matrices)} design matrices")
    return design_matrices

def main():
    """
    Run data organization for all subjects
    """
    print("Starting data organization...")
    
    for subject_id in config.SUBJECTS.keys():
        organize_subject_data(subject_id)
    
    print("Data organization complete!")

if __name__ == "__main__":
    main()
