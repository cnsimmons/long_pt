#!/usr/bin/env python3
"""
Process high-level outputs in first-session space (CSV-driven)
"""
import numpy as np
import pandas as pd
import subprocess
import os
import sys

sub = sys.argv[1]
ses = sys.argv[2]

data_dir = '/user_data/csimmon2/long_pt'
CSV_FILE = '/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv'
task = 'loc'

SESSION_START = {'sub-010': 2, 'sub-018': 2}

first_ses = SESSION_START.get(sub, 1)
first_ses_str = f"{first_ses:02d}"
ses01_ref = f'{data_dir}/{sub}/ses-{first_ses_str}/anat/{sub}_ses-{first_ses_str}_T1w_brain.nii.gz'

cope_info = {f'cope{i}': i for i in range(1, 15)}

sub_dir = f'{data_dir}/{sub}/ses-{ses}'
print(f"Processing high-level outputs for {sub} ses-{ses} in first-session space")

if not os.path.exists(ses01_ref):
    print(f"⚠️  First-session anatomy not found: {ses01_ref}")
    sys.exit(1)

if ses == first_ses_str:
    print(f"  Session {first_ses_str}: Maps already in correct space, no registration needed")
    need_registration = False
else:
    anat_transform = f'{sub_dir}/anat/anat2ses{first_ses_str}.mat'
    if os.path.exists(anat_transform):
        print(f"  Found transformation matrix: {anat_transform}")
        need_registration = True
    else:
        print(f"⚠️  No transformation matrix found: {anat_transform}")
        need_registration = False

highlevel_dir = f'{sub_dir}/derivatives/fsl/{task}/HighLevel.gfeat'

for contrast_name, cope_num in cope_info.items():
    print(f"  Processing {contrast_name} (cope{cope_num})")
    
    cope_dir = f'{highlevel_dir}/cope{cope_num}.feat'
    zstat_file = f'{cope_dir}/stats/zstat1.nii.gz'
    cope_file = f'{cope_dir}/stats/cope1.nii.gz'
    zstat_ses01 = f'{cope_dir}/stats/zstat1_ses{first_ses_str}.nii.gz'
    cope_ses01 = f'{cope_dir}/stats/cope1_ses{first_ses_str}.nii.gz'
    
    # Process zstat
    if os.path.exists(zstat_file):
        if need_registration and not os.path.exists(zstat_ses01):
            bash_cmd = f'flirt -in {zstat_file} -ref {ses01_ref} -out {zstat_ses01} -applyxfm -init {anat_transform} -interp trilinear'
            try:
                subprocess.run(bash_cmd.split(), check=True)
                print(f"    ✓ Successfully registered zstat")
            except subprocess.CalledProcessError as e:
                print(f"    ✗ Error registering zstat: {e}")
        elif not need_registration and not os.path.exists(zstat_ses01):
            os.symlink(os.path.abspath(zstat_file), zstat_ses01)
            print(f"    ✓ Linked zstat")
        else:
            print(f"    ✓ zstat already processed")
    else:
        print(f"    ⚠️  zstat file not found")
    
    # Process cope
    if os.path.exists(cope_file):
        if need_registration and not os.path.exists(cope_ses01):
            bash_cmd = f'flirt -in {cope_file} -ref {ses01_ref} -out {cope_ses01} -applyxfm -init {anat_transform} -interp trilinear'
            try:
                subprocess.run(bash_cmd.split(), check=True)
                print(f"    ✓ Successfully registered cope")
            except subprocess.CalledProcessError as e:
                print(f"    ✗ Error registering cope: {e}")
        elif not need_registration and not os.path.exists(cope_ses01):
            os.symlink(os.path.abspath(cope_file), cope_ses01)
            print(f"    ✓ Linked cope")
        else:
            print(f"    ✓ cope already processed")
    else:
        print(f"    ⚠️  cope file not found")

print(f"Finished processing {sub} ses-{ses}")

# Summary
processed_zstats = sum(1 for _, cope_num in cope_info.items() 
                      if os.path.exists(f'{highlevel_dir}/cope{cope_num}.feat/stats/zstat1_ses{first_ses_str}.nii.gz'))
processed_copes = sum(1 for _, cope_num in cope_info.items() 
                     if os.path.exists(f'{highlevel_dir}/cope{cope_num}.feat/stats/cope1_ses{first_ses_str}.nii.gz'))

print(f"\nSummary:")
print(f"  Processed zstats: {processed_zstats}/{len(cope_info)}")
print(f"  Processed copes: {processed_copes}/{len(cope_info)}")
print(f"  Reference: {ses01_ref}")