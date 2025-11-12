#!/usr/bin/env python3
"""
Register each 1stlevel to anat
"""
import numpy as np
import pandas as pd
import subprocess
import os
import sys
from glob import glob

# Get command line arguments
sub = sys.argv[1]  # e.g., 'sub-004'
ses = sys.argv[2]  # e.g., '02'

# Project parameters
data_dir = '/user_data/csimmon2/long_pt'
raw_dir = '/lab_data/behrmannlab/hemi/Raw'
task = 'loc'

# Auto-detect runs from filesystem
sub_dir = f'{data_dir}/{sub}/ses-{ses}'
task_dir = f'{sub_dir}/derivatives/fsl/{task}'

runs = []
for feat_dir in glob(f'{task_dir}/run-*/1stLevel.feat'):
    run = feat_dir.split('run-')[1].split('/')[0]
    runs.append(run)
runs = sorted(runs)

print(f"Processing {sub} ses-{ses}")
print(f"Found runs: {runs}")

anat = f'{sub_dir}/anat/{sub}_ses-{ses}_T1w_brain.nii.gz'

for run in runs:
    print(f"  {sub} {task} run-{run}")
    
    run_dir = f'{sub_dir}/derivatives/fsl/{task}/run-{run}/1stLevel.feat'
    filtered_func = f'{run_dir}/filtered_func_data.nii.gz'
    out_func = f'{run_dir}/filtered_func_data_reg.nii.gz'
    
    if os.path.exists(filtered_func):
        if not os.path.exists(out_func):
            bash_cmd = f'flirt -in {filtered_func} -ref {anat} -out {out_func} -applyxfm -init {run_dir}/reg/example_func2standard.mat -interp trilinear'
            print(f"    Running: {bash_cmd}")
            
            try:
                subprocess.run(bash_cmd.split(), check=True)
                print(f"    ✓ Successfully registered")
            except subprocess.CalledProcessError as e:
                print(f"    ✗ Error: {e}")
        else:
            print(f"    ✓ Already registered")
    else:
        print(f"    ✗ filtered_func_data.nii.gz missing")

print(f"Finished {sub} ses-{ses}")