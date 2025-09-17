#!/usr/bin/env python3
"""
Register each HighLevel to ses01_ref space in a parallelized manner (that is register back to first session)
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
mni = '/opt/fsl/6.0.3/data/standard/MNI152_T1_2mm_brain.nii.gz'  # MNI template for analysis
ses01_ref = f'{data_dir}/{sub}/ses-01/anat/{sub}_ses-01_T1w_brain.nii.gz'

# Define cope numbers for different contrasts
# Updated to match the corrected HighLevel.fsf template (only group_mean)
cope_info = {
    'group_mean': 1,
}


cope_info = {
    'objects': 1,      # Objects vs baseline  
    'houses': 2,       # Houses vs baseline
    'objects_vs_houses': 3,  # Objects vs Houses competition
}

# Subject and session directories
sub_dir = f'{data_dir}/{sub}/ses-{ses}'
anat_transform = f'{sub_dir}/anat/anat2stand.mat'

print(f"Registering high-level outputs for {sub} ses-{ses}")

# Check if anatomical transformation matrix exists
if not os.path.exists(anat_transform):
    print(f"⚠️  Anatomical transformation matrix not found: {anat_transform}")
    print("   You may need to run FEAT with registration to standard space first")
    sys.exit(1)

# Process each cope
for contrast_name, cope_num in cope_info.items():
    print(f"  Processing {contrast_name} (cope{cope_num})")
    
    # Paths for this cope
    highlevel_dir = f'{sub_dir}/derivatives/fsl/{task}/HighLevel.gfeat'
    cope_dir = f'{highlevel_dir}/cope{cope_num}.feat'
    zstat_file = f'{cope_dir}/stats/zstat1.nii.gz'
    out_file = f'{cope_dir}/stats/zstat1_reg.nii.gz'
    
    # Check if high-level output exists
    if os.path.exists(zstat_file):
        if not os.path.exists(out_file):
            # Register zstat to ses01_ref space
            bash_cmd = f'flirt -in {zstat_file} -ref {ses01_ref} -out {out_file} -applyxfm -init {anat_transform} -interp trilinear'
            print(f"    Running: {bash_cmd}")
            
            try:
                subprocess.run(bash_cmd.split(), check=True)
                print(f"    ✓ Successfully registered {contrast_name}")
            except subprocess.CalledProcessError as e:
                print(f"    ✗ Error registering {contrast_name}: {e}")
        else:
            print(f"    ✓ {contrast_name} already registered (output exists)")
    else:
        print(f"    ⚠️  zstat file not found: {zstat_file}")
        print(f"       High-level FEAT may not have completed for {contrast_name}")

# Also register cope files if they exist
print(f"  Processing cope files...")
for contrast_name, cope_num in cope_info.items():
    cope_dir = f'{highlevel_dir}/cope{cope_num}.feat'
    cope_file = f'{cope_dir}/stats/cope1.nii.gz'
    out_cope_file = f'{cope_dir}/stats/cope1_reg.nii.gz'
    
    if os.path.exists(cope_file):
        if not os.path.exists(out_cope_file):
            bash_cmd = f'flirt -in {cope_file} -ref {ses01_ref} -out {out_cope_file} -applyxfm -init {anat_transform} -interp trilinear'
            print(f"    Running: {bash_cmd}")
            
            try:
                subprocess.run(bash_cmd.split(), check=True)
                print(f"    ✓ Successfully registered cope for {contrast_name}")
            except subprocess.CalledProcessError as e:
                print(f"    ✗ Error registering cope for {contrast_name}: {e}")
        else:
            print(f"    ✓ cope for {contrast_name} already registered")

print(f"Finished registering high-level outputs for {sub} ses-{ses}")

# Summary of what was processed
registered_zstats = []
registered_copes = []

for contrast_name, cope_num in cope_info.items():
    cope_dir = f'{highlevel_dir}/cope{cope_num}.feat'
    zstat_reg = f'{cope_dir}/stats/zstat1_reg.nii.gz'
    cope_reg = f'{cope_dir}/stats/cope1_reg.nii.gz'
    
    if os.path.exists(zstat_reg):
        registered_zstats.append(contrast_name)
    if os.path.exists(cope_reg):
        registered_copes.append(contrast_name)

print(f"\nSummary:")
print(f"  Registered zstats: {len(registered_zstats)}/{len(cope_info)} contrasts")
print(f"  Registered copes: {len(registered_copes)}/{len(cope_info)} contrasts")

if registered_zstats:
    print(f"  Successfully registered zstats: {', '.join(registered_zstats)}")
if registered_copes:
    print(f"  Successfully registered copes: {', '.join(registered_copes)}")