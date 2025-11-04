#!/usr/bin/env python3
"""
Setup directory structure for long_pt hemispherectomy patients
Keeps raw data in place, only creates processed derivatives directories.
This script DOES NOT convert timing files.
"""
import os
from glob import glob

# Configuration
RAW_DIR = '/lab_data/behrmannlab/hemi/Raw'
PROCESSED_DIR = '/user_data/csimmon2/long_pt'

# This structure allows you to specify exactly which runs
# to process for each subject's session.
SUBJECTS_SESSIONS_RUNS = {
    'sub-004': {
        1: [1, 2, 3],
        2: [1, 2, 3],
        3: [1, 2, 3],
        5: [1, 2, 3],
        6: [1, 2, 3]
    },
    'sub-007': {
        1: [1, 2, 3],
        3: [1, 2],  # Special case: Only runs 1 and 2 are available
        4: [1, 2, 3]
    },
    'sub-021': {
        1: [1, 2, 3],
        2: [1, 2, 3],
        3: [1, 2, 3]
    }
}

TASK = 'loc' # This is used to create the task-specific directory

def create_directory_structure(subject_id):
    """
    Create processed directory structure for a subject.
    """
    print(f"  Creating directory structure for {subject_id}")
    
    if subject_id not in SUBJECTS_SESSIONS_RUNS:
        print(f"    Error: {subject_id} not in config.")
        return

    sessions_runs = SUBJECTS_SESSIONS_RUNS[subject_id]
    
    for session, runs in sessions_runs.items():
        session_dir = f'{PROCESSED_DIR}/{subject_id}/ses-{session:02d}'
        
        # Create main directories
        directories = [
            f'{session_dir}/timing', # For Script 2's output
            f'{session_dir}/anat',   # For BET output (if used)
            f'{session_dir}/derivatives',
            f'{session_dir}/derivatives/fsl',
            f'{session_dir}/derivatives/fsl/{TASK}',
            f'{session_dir}/derivatives/qc'
        ]
        
        # Create run-specific directories
        for run in runs:
            # This is where confound files and .fsf designs will go
            directories.append(f'{session_dir}/derivatives/fsl/{TASK}/run-{run:02d}')
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    print(f"    Created processed directory structure")

def main():
    """
    Setup processing structure for all subjects
    """
    print("Setting up long_pt processing structure...")
    print(f"Processed data location: {PROCESSED_DIR}")
    print(f"Subjects: {list(SUBJECTS_SESSIONS_RUNS.keys())}")
    
    # Create main processed directory
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    # Setup each subject
    for subject_id in SUBJECTS_SESSIONS_RUNS.keys():
        print(f"\nSetting up {subject_id}...")
        create_directory_structure(subject_id)
    
    print(f"\nDirectory setup complete!")
    print("Next step: Run your Bash script to convert timing files.")

if __name__ == "__main__":
    main()