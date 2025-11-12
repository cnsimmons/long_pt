#!/usr/bin/env python3
"""
Register zstat files to anatomical space (CSV-driven)
"""
import numpy as np
import pandas as pd
import subprocess
import os
from glob import glob

data_dir = '/user_data/csimmon2/long_pt'
CSV_FILE = '/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv'
SKIP_SUBS = ['sub-004', 'sub-007', 'sub-021', 'sub-108']
SESSION_START = {'sub-010': 2, 'sub-018': 2}
zstats = list(range(1, 15))  # 1-14

def get_sessions_for_subject(row):
    age_cols = ['age_1', 'age_2', 'age_3', 'age_4', 'age_5']
    return sum(1 for col in age_cols if pd.notna(row[col]) and row[col] != '')

def get_runs(sub, ses):
    """Auto-detect runs from completed FEAT dirs"""
    task_dir = f'{data_dir}/{sub}/ses-{ses}/derivatives/fsl/loc'
    runs = []
    for feat_dir in glob(f'{task_dir}/run-*/1stLevel.feat'):
        run = feat_dir.split('run-')[1].split('/')[0]
        runs.append(run)
    return sorted(runs)

df = pd.read_csv(CSV_FILE)

for _, row in df.iterrows():
    sub = row['sub']
    
    if sub in SKIP_SUBS:
        continue
    
    session_count = get_sessions_for_subject(row)
    start_ses = SESSION_START.get(sub, 1)
    first_ses = f"{start_ses:02d}"
    
    # Reference anatomy (first session)
    ref_anat = f'{data_dir}/{sub}/ses-{first_ses}/anat/{sub}_ses-{first_ses}_T1w_brain.nii.gz'
    
    if not os.path.exists(ref_anat):
        continue
    
    for i in range(session_count):
        ses = f"{(start_ses + i):02d}"
        runs = get_runs(sub, ses)
        
        for run in runs:
            print(f"{sub} ses-{ses} run-{run}")
            run_dir = f'{data_dir}/{sub}/ses-{ses}/derivatives/fsl/loc/run-{run}/1stLevel.feat'
            reg_stats_dir = f'{run_dir}/reg_standard/stats'
            os.makedirs(reg_stats_dir, exist_ok=True)
            
            for zstat in zstats:
                zstat_func = f'{run_dir}/stats/zstat{zstat}.nii.gz'
                zstat_out = f'{reg_stats_dir}/zstat{zstat}.nii.gz'
                
                if os.path.exists(zstat_out):
                    continue
                
                if os.path.exists(zstat_func):
                    bash_cmd = f'flirt -in {zstat_func} -ref {ref_anat} -out {zstat_out} -applyxfm -init {run_dir}/reg/example_func2highres.mat -interp trilinear'
                    try:
                        subprocess.run(bash_cmd.split(), check=True)
                        print(f"  ✓ zstat{zstat}")
                    except subprocess.CalledProcessError as e:
                        print(f"  ✗ zstat{zstat}: {e}")

print("Complete!")