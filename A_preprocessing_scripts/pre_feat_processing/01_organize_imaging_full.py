#!/usr/bin/env python3
"""
Setup directory structure for long_pt hemispherectomy patients (CSV-driven)
Keeps raw data in place, only creates processed derivatives directories.
"""
import os
import pandas as pd

# Configuration
RAW_DIR = '/lab_data/behrmannlab/hemi/Raw'
PROCESSED_DIR = '/user_data/csimmon2/long_pt'
CSV_FILE = '/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv'
TASK = 'loc'

# Subjects to skip (already processed)
SKIP_SUBS = ['sub-004', 'sub-007', 'sub-021', 'sub-108']

# Special session mappings
SESSION_START = {
    'sub-010': 2,
    'sub-018': 2,
    'sub-068': 2
}

def get_sessions_for_subject(row):
    """Count non-empty age columns to determine session count"""
    age_cols = ['age_1', 'age_2', 'age_3', 'age_4', 'age_5']
    return sum(1 for col in age_cols if pd.notna(row[col]) and row[col] != '')

def get_runs_for_session(subject_id, session_num):
    """Auto-detect runs from filesystem"""
    ses = f"{session_num:02d}"
    func_dir = f"{RAW_DIR}/{subject_id}/ses-{ses}/func"
    
    if not os.path.exists(func_dir):
        return []
    
    # Find all bold files for this session
    import glob
    bold_files = glob.glob(f"{func_dir}/{subject_id}_ses-{ses}_task-{TASK}_run-*_bold.nii.gz")
    
    # Extract run numbers
    runs = []
    for f in bold_files:
        run_str = f.split('run-')[1].split('_')[0]
        runs.append(int(run_str))
    
    return sorted(runs)

def create_directory_structure(subject_id, session_nums):
    """Create processed directory structure for a subject"""
    print(f"  Creating structure for {subject_id}")
    
    for session_num in session_nums:
        session_dir = f'{PROCESSED_DIR}/{subject_id}/ses-{session_num:02d}'
        
        # Get runs for this session
        runs = get_runs_for_session(subject_id, session_num)
        
        if not runs:
            print(f"    WARNING: No runs found for session {session_num}")
            continue
        
        print(f"    Session {session_num}: {len(runs)} runs")
        
        # Create main directories
        directories = [
            f'{session_dir}/timing',
            f'{session_dir}/anat',
            f'{session_dir}/derivatives',
            f'{session_dir}/derivatives/fsl',
            f'{session_dir}/derivatives/fsl/{TASK}',
            f'{session_dir}/derivatives/qc'
        ]
        
        # Create run-specific directories
        for run in runs:
            directories.append(f'{session_dir}/derivatives/fsl/{TASK}/run-{run:02d}')
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

def main():
    """Setup processing structure for all subjects"""
    print("Setting up long_pt processing structure (CSV-driven)...")
    print(f"Processed data location: {PROCESSED_DIR}\n")
    
    # Read CSV
    df = pd.read_csv(CSV_FILE)
    
    # Create main processed directory
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    # Process each subject
    for _, row in df.iterrows():
        subject_id = row['sub']
        
        if subject_id in SKIP_SUBS:
            print(f"SKIP: {subject_id} (already processed)")
            continue
        
        print(f"\nSetting up {subject_id}...")
        
        # Count sessions
        session_count = get_sessions_for_subject(row)
        
        # Get starting session
        start_ses = SESSION_START.get(subject_id, 1)
        
        # Generate session numbers
        session_nums = [start_ses + i for i in range(session_count)]
        
        print(f"  {session_count} sessions (starting from session {start_ses})")
        
        # Create structure
        create_directory_structure(subject_id, session_nums)
    
    print(f"\n{'='*50}")
    print("Directory setup complete!")

if __name__ == "__main__":
    main()