#!/usr/bin/env python3
"""
Register zstat files to anatomical space for all subjects/sessions
Adapted for long_pt project
"""

import numpy as np
import pandas as pd
import subprocess
import os

# Project parameters
data_dir = '/user_data/csimmon2/long_pt'

# Subject and session configuration
subjects_sessions = {
    'sub-004': {'sessions': ['01', '02', '03', '05', '06', '07'], 'runs': ['01', '02', '03']},
    'sub-007': {'sessions': ['01', '03', '04', '05'], 'runs': ['01', '02', '03']},  # ses-03/04 have only 2 runs
    'sub-021': {'sessions': ['01', '02', '03'], 'runs': ['01', '02', '03']}
}

# Zstats to register (based on your contrasts)
zstats = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]  # All contrasts

for sub, config in subjects_sessions.items():
    for ses in config['sessions']:
        sub_dir = f'{data_dir}/{sub}/ses-{ses}'
        anat = f'{sub_dir}/anat/{sub}_ses-{ses}_T1w_brain.nii.gz'
        
        # Determine runs for this session
        if sub == 'sub-007' and ses in ['03', '04']:
            runs = ['01', '02']
        else:
            runs = config['runs']
        
        for run in runs:
            print(f"{sub} ses-{ses} run-{run}")
            run_dir = f'{sub_dir}/derivatives/fsl/loc/run-{run}/1stLevel.feat'
            
            # Check if reg_standard/stats exists, create if not
            reg_stats_dir = f'{run_dir}/reg_standard/stats'
            os.makedirs(reg_stats_dir, exist_ok=True)
            
            for zstat in zstats:
                zstat_func = f'{run_dir}/stats/zstat{zstat}.nii.gz'
                zstat_out = f'{reg_stats_dir}/zstat{zstat}.nii.gz'
                
                # Skip if already exists
                if os.path.exists(zstat_out):
                    print(f"  zstat{zstat} already registered, skipping")
                    continue
                
                if os.path.exists(zstat_func):
                    bash_cmd = f'flirt -in {zstat_func} -ref {anat} -out {zstat_out} -applyxfm -init {run_dir}/reg/example_func2highres.mat -interp trilinear'
                    try:
                        subprocess.run(bash_cmd.split(), check=True)
                        print(f"  ✓ Registered zstat{zstat}")
                    except subprocess.CalledProcessError as e:
                        print(f"  ✗ Error registering zstat{zstat}: {e}")
                else:
                    print(f"  ⚠ zstat{zstat}.nii.gz not found")

print("\nZstat registration complete!")