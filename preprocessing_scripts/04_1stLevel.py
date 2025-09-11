## adapted from Vlad's script

#!/usr/bin/env python3
"""
Register each 1stlevel to anat in a parallelized manner
Adapted for long_pt project
"""

import numpy as np
import pandas as pd
import subprocess
import os
import sys

# Get command line arguments
sub = sys.argv[1]  # e.g., 'sub-004'
ses = sys.argv[2]  # e.g., '02'

# Project parameters
data_dir = '/user_data/csimmon2/long_pt'
task = 'loc'
runs = ['01', '02', '03', '04', '05']  # Updated to include more runs if applicable

# Subject and session directories
sub_dir = f'{data_dir}/{sub}/ses-{ses}'
anat = f'{sub_dir}/anat/{sub}_ses-{ses}_T1w_brain.nii.gz'

print(f"Processing {sub} ses-{ses}")

for run in runs:
    print(f"  {sub} {task} run-{run}")
    
    # Paths for this run
    run_dir = f'{sub_dir}/derivatives/fsl/{task}/run-{run}/1stLevel.feat'
    filtered_func = f'{run_dir}/filtered_func_data.nii.gz'
    out_func = f'{run_dir}/filtered_func_data_reg.nii.gz'
    
    # Check if run exists and hasn't been processed yet
    if os.path.exists(filtered_func):
        if not os.path.exists(out_func):
            # Register filtered functional data to anatomical space
            bash_cmd = f'flirt -in {filtered_func} -ref {anat} -out {out_func} -applyxfm -init {run_dir}/reg/example_func2standard.mat -interp trilinear'
            print(f"    Running: {bash_cmd}")
            
            try:
                subprocess.run(bash_cmd.split(), check=True)
                print(f"    ✓ Successfully registered run-{run}")
            except subprocess.CalledProcessError as e:
                print(f"    ✗ Error registering run-{run}: {e}")
        else:
            print(f"    ✓ run-{run} already registered (output exists)")
    else:
        print(f"    ✗ run-{run} filtered_func_data.nii.gz does not exist - FEAT may not have completed")

print(f"Finished processing {sub} ses-{ses}")