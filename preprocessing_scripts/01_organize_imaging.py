"""
Setup directory structure and timing files for long_pt hemispherectomy patients
Keeps raw data in place, only creates processed derivatives and timing files
"""
import os
import pandas as pd
import numpy as np
from glob import glob

# Configuration
RAW_DIR = '/lab_data/behrmannlab/hemi/Raw'
PROCESSED_DIR = '/lab_data/behrmannlab/claire/long_pt'

# Subject and session configuration
SUBJECTS_SESSIONS = {
    'sub-004': [1, 2, 3, 5, 6],
    'sub-007': [1, 3, 4], 
    'sub-021': [1, 2, 3]
}

RUNS = [1, 2, 3]
TASK = 'loc'
CONDITIONS = ['Face', 'House', 'Object', 'Word', 'Scramble']

def check_raw_data_exists(subject_id, session, run=None):
    """
    Check if raw data exists for subject/session/run
    """
    session_dir = f'{RAW_DIR}/{subject_id}/ses-{session:02d}'
    
    if not os.path.exists(session_dir):
        return False, f"Session directory missing: {session_dir}"
    
    # Check anatomical
    anat_files = glob(f'{session_dir}/anat/*T1w*.nii.gz')
    if not anat_files:
        return False, f"No T1w files in {session_dir}/anat"
    
    # Check functional if run specified
    if run is not None:
        func_file = f'{session_dir}/func/{subject_id}_ses-{session:02d}_task-{TASK}_run-{run:02d}_bold.nii.gz'
        events_file = f'{session_dir}/func/{subject_id}_ses-{session:02d}_task-{TASK}_run-{run:02d}_events.tsv'
        
        if not os.path.exists(func_file):
            return False, f"Functional file missing: {func_file}"
        if not os.path.exists(events_file):
            return False, f"Events file missing: {events_file}"
    
    return True, "OK"

def create_directory_structure(subject_id):
    """
    Create processed directory structure (but don't copy raw data)
    """
    print(f"  Creating directory structure for {subject_id}")
    
    sessions = SUBJECTS_SESSIONS[subject_id]
    
    for session in sessions:
        session_dir = f'{PROCESSED_DIR}/{subject_id}/ses-{session:02d}'
        
        # Create main directories
        directories = [
            f'{session_dir}/timing',
            f'{session_dir}/derivatives',
            f'{session_dir}/derivatives/fsl',
            f'{session_dir}/derivatives/fsl/{TASK}',
            f'{session_dir}/derivatives/qc'
        ]
        
        # Create run-specific directories
        for run in RUNS:
            directories.append(f'{session_dir}/derivatives/fsl/{TASK}/run-{run:02d}')
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    print(f"    Created processed directory structure")

def convert_timing_files(subject_id, session, run):
    """
    Convert timing files from raw .tsv to processed FSL 3-column format
    """
    print(f"  Converting timing files for {subject_id} ses-{session:02d} run-{run:02d}")
    
    # Source (raw data location)
    events_file = f'{RAW_DIR}/{subject_id}/ses-{session:02d}/func/{subject_id}_ses-{session:02d}_task-{TASK}_run-{run:02d}_events.tsv'
    
    # Target (processed location)
    target_timing_dir = f'{PROCESSED_DIR}/{subject_id}/ses-{session:02d}/timing'
    
    if not os.path.exists(events_file):
        print(f"    Warning: Events file not found: {events_file}")
        return False
    
    try:
        # Read events file
        events = pd.read_csv(events_file, sep='\t')
        
        # Check for required columns
        if 'trial_type' not in events.columns:
            if 'block_type' in events.columns:
                events['trial_type'] = events['block_type']
            else:
                print(f"    Error: No trial_type or block_type column found")
                return False
        
        # Convert each condition to FSL 3-column format
        conditions_found = []
        for condition in CONDITIONS:
            cond_events = events[events['trial_type'] == condition]
            
            if len(cond_events) > 0:
                # Create 3-column format: onset, duration, amplitude
                timing_data = pd.DataFrame({
                    'onset': cond_events['onset'],
                    'duration': cond_events['duration'],
                    'amplitude': np.ones(len(cond_events))
                })
                
                # Save timing file (matches format expected by .fsf files)
                timing_file = f'{target_timing_dir}/catloc_{subject_id[-3:]}_run-{run:02d}_{condition}.txt'
                timing_data.to_csv(timing_file, sep='\t', header=False, index=False)
                conditions_found.append(condition)
        
        print(f"    Created timing files for: {conditions_found}")
        return len(conditions_found) == len(CONDITIONS)
        
    except Exception as e:
        print(f"    Error converting timing files: {e}")
        return False

def create_path_reference_file(subject_id):
    """
    Create a reference file with paths to raw data for easy access
    """
    sessions = SUBJECTS_SESSIONS[subject_id]
    
    ref_file = f'{PROCESSED_DIR}/{subject_id}/raw_data_paths.txt'
    
    with open(ref_file, 'w') as f:
        f.write(f"Raw data paths for {subject_id}\n")
        f.write("=" * 40 + "\n\n")
        
        for session in sessions:
            f.write(f"Session {session}:\n")
            f.write(f"  Anatomical: {RAW_DIR}/{subject_id}/ses-{session:02d}/anat/\n")
            f.write(f"  Functional: {RAW_DIR}/{subject_id}/ses-{session:02d}/func/\n")
            
            for run in RUNS:
                func_file = f"{RAW_DIR}/{subject_id}/ses-{session:02d}/func/{subject_id}_ses-{session:02d}_task-{TASK}_run-{run:02d}_bold.nii.gz"
                f.write(f"    Run {run}: {func_file}\n")
            f.write("\n")

def setup_subject(subject_id):
    """
    Setup processing structure for one subject
    """
    print(f"\nSetting up {subject_id}")
    
    if subject_id not in SUBJECTS_SESSIONS:
        print(f"  Error: {subject_id} not in configured subjects")
        return False
    
    sessions = SUBJECTS_SESSIONS[subject_id]
    
    # Check raw data exists
    missing_data = []
    for session in sessions:
        for run in RUNS:
            exists, msg = check_raw_data_exists(subject_id, session, run)
            if not exists:
                missing_data.append(f"  ses-{session:02d} run-{run:02d}: {msg}")
    
    if missing_data:
        print("  Missing raw data:")
        for item in missing_data:
            print(item)
        print("  Continuing with available data...")
    
    # Create directory structure
    create_directory_structure(subject_id)
    
    # Convert timing files
    timing_success = 0
    total_runs = 0
    
    for session in sessions:
        for run in RUNS:
            exists, _ = check_raw_data_exists(subject_id, session, run)
            if exists:
                total_runs += 1
                if convert_timing_files(subject_id, session, run):
                    timing_success += 1
    
    # Create reference file
    create_path_reference_file(subject_id)
    
    print(f"  Summary: {timing_success}/{total_runs} timing conversions successful")
    return timing_success > 0

def check_setup_completeness():
    """
    Check what has been set up successfully
    """
    print("\nChecking setup completeness...")
    
    for subject_id, sessions in SUBJECTS_SESSIONS.items():
        print(f"\n{subject_id}:")
        
        for session in sessions:
            session_dir = f'{PROCESSED_DIR}/{subject_id}/ses-{session:02d}'
            
            # Check if directories exist
            dirs_exist = os.path.exists(f'{session_dir}/derivatives/fsl/{TASK}')
            
            # Check timing files
            timing_files = glob(f'{session_dir}/timing/catloc_{subject_id[-3:]}_run-*_*.txt')
            expected_timing = len(RUNS) * len(CONDITIONS)
            
            # Check raw data availability
            raw_available = 0
            for run in RUNS:
                exists, _ = check_raw_data_exists(subject_id, session, run)
                if exists:
                    raw_available += 1
            
            status = "✓" if dirs_exist else "✗"
            print(f"  ses-{session:02d}: Dirs {status}, Timing {len(timing_files)}/{expected_timing}, Raw data {raw_available}/{len(RUNS)} runs")

def main():
    """
    Setup processing structure for all subjects
    """
    print("Setting up long_pt processing structure...")
    print(f"Raw data location: {RAW_DIR}")
    print(f"Processed data location: {PROCESSED_DIR}")
    print(f"Subjects: {list(SUBJECTS_SESSIONS.keys())}")
    
    # Create main processed directory
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    # Setup each subject
    for subject_id in SUBJECTS_SESSIONS.keys():
        setup_subject(subject_id)
    
    # Check completeness
    check_setup_completeness()
    
    print(f"\nSetup complete!")
    print("Next steps:")
    print("1. Run brain mirroring/anatomical preprocessing")
    print("2. Generate .fsf files pointing to raw data locations")
    print("3. Run FEAT analyses")

if __name__ == "__main__":
    main()