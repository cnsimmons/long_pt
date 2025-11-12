#!/usr/bin/env python3
"""Check completeness of all preprocessing steps"""
import pandas as pd
from pathlib import Path

BASE_DIR = Path('/user_data/csimmon2/long_pt')
CSV_FILE = Path('/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv')
SESSION_START = {'sub-010': 2, 'sub-018': 2, 'sub-068': 2}
SKIP_SUBS = ['sub-004', 'sub-007', 'sub-021', 'sub-108']

df = pd.read_csv(CSV_FILE)

checks = {
    'timing': [],
    'confounds': [],
    'skull_strip': [],
    'registration': [],
    'fsf_files': [],
    'feat_complete': []
}

for _, row in df.iterrows():
    sub = row['sub']
    if sub in SKIP_SUBS:
        continue
    
    session_count = sum(1 for col in ['age_1', 'age_2', 'age_3', 'age_4', 'age_5'] 
                       if pd.notna(row[col]) and row[col] != '')
    start_ses = SESSION_START.get(sub, 1)
    
    for i in range(session_count):
        ses = f"{(start_ses + i):02d}"
        
        # Check timing files
        timing_dir = BASE_DIR / sub / f'ses-{ses}' / 'timing'
        if not list(timing_dir.glob('catloc_*.txt')):
            checks['timing'].append(f"{sub} ses-{ses}")
        
        # Check skull strip
        brain = BASE_DIR / sub / f'ses-{ses}' / 'anat' / f'{sub}_ses-{ses}_T1w_brain.nii.gz'
        if not brain.exists():
            checks['skull_strip'].append(f"{sub} ses-{ses}")
        
        # Check registration
        reg_mat = BASE_DIR / sub / f'ses-{ses}' / 'anat' / 'anat2stand.mat'
        if not reg_mat.exists():
            checks['registration'].append(f"{sub} ses-{ses}")
        
        # Check runs
        task_dir = BASE_DIR / sub / f'ses-{ses}' / 'derivatives' / 'fsl' / 'loc'
        for run_dir in sorted(task_dir.glob('run-*')):
            run = run_dir.name.split('-')[1]
            
            # Check confounds
            spike = run_dir / f'{sub}_ses-{ses}_task-loc_run-{run}_bold_spikes.txt'
            if not spike.exists():
                checks['confounds'].append(f"{sub} ses-{ses} run-{run}")
            
            # Check FSF
            fsf = run_dir / '1stLevel.fsf'
            if not fsf.exists():
                checks['fsf_files'].append(f"{sub} ses-{ses} run-{run}")
            
            # Check FEAT completion
            feat_dir = run_dir / '1stLevel.feat'
            filtered_func = feat_dir / 'filtered_func_data.nii.gz'
            if not filtered_func.exists():
                checks['feat_complete'].append(f"{sub} ses-{ses} run-{run}")

for step, missing in checks.items():
    if missing:
        print(f"\n{step.upper()} - Missing {len(missing)}:")
        for m in missing[:5]:
            print(f"  {m}")
        if len(missing) > 5:
            print(f"  ... and {len(missing)-5} more")
    else:
        print(f"\n{step.upper()} - All complete ✓")