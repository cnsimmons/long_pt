#!/usr/bin/env python3
"""

Necesary for registering anatomical parcels for functional rois || may no longer need

UNNECESSARY - should not need to run this script since I'm running job script FEAT.
Process high-level outputs in first-session space for long_pt project
UPDATED: Works with first-session registration instead of MNI registration

If HighLevel FEAT registered to MNI instead of ses-01, you'd need 09_highLevel.py to:

Take MNI-space outputs
Transform them to ses-01 space using anat2ses01.mat
Align all sessions to first session for consistent extraction

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

# First-session anatomy as reference (instead of MNI template)
ses01_ref = f'{data_dir}/{sub}/ses-01/anat/{sub}_ses-01_T1w_brain.nii.gz'

# Define cope numbers for different contrasts
# Updated to match the corrected HighLevel.fsf template (only group_mean)
# Fix - process all copes:
cope_info = {
    'cope1': 1,
    'cope2': 2,
    'cope3': 3,
    'cope4': 4,
    'cope5': 5,
    'cope6': 6,
    'cope7': 7,
    'cope8': 8,
    'cope9': 9,
    'cope10': 10,
    'cope11': 11,
    'cope12': 12,
    'cope13': 13,
    'cope14': 14,
}
# Subject and session directories
sub_dir = f'{data_dir}/{sub}/ses-{ses}'

print(f"Processing high-level outputs for {sub} ses-{ses} in first-session space")

# Check if first-session anatomy exists
if not os.path.exists(ses01_ref):
    print(f"⚠️  First-session anatomy not found: {ses01_ref}")
    print("   Make sure ses-01 anatomy exists for this subject")
    sys.exit(1)

# Check if we need to register to ses-01 space (for non-ses-01 sessions)
if ses == '01':
    print(f"  Session 01: Maps already in correct space, no registration needed")
    need_registration = False
else:
    # Check if transformation matrix exists
    anat_transform = f'{sub_dir}/anat/anat2ses01.mat'
    if os.path.exists(anat_transform):
        print(f"  Found transformation matrix: {anat_transform}")
        need_registration = True
    else:
        print(f"⚠️  No transformation matrix found: {anat_transform}")
        print("   High-level outputs should already be in first-session space")
        need_registration = False

# Process each cope
for contrast_name, cope_num in cope_info.items():
    print(f"  Processing {contrast_name} (cope{cope_num})")
    
    # Paths for this cope
    highlevel_dir = f'{sub_dir}/derivatives/fsl/{task}/HighLevel.gfeat'
    cope_dir = f'{highlevel_dir}/cope{cope_num}.feat'
    zstat_file = f'{cope_dir}/stats/zstat1.nii.gz'
    cope_file = f'{cope_dir}/stats/cope1.nii.gz'
    
    # Output files (ses01-registered versions)
    zstat_ses01 = f'{cope_dir}/stats/zstat1_ses01.nii.gz'
    cope_ses01 = f'{cope_dir}/stats/cope1_ses01.nii.gz'
    
    # Process zstat file
    if os.path.exists(zstat_file):
        if need_registration and not os.path.exists(zstat_ses01):
            # Register to first-session space
            bash_cmd = f'flirt -in {zstat_file} -ref {ses01_ref} -out {zstat_ses01} -applyxfm -init {anat_transform} -interp trilinear'
            print(f"    Running: {bash_cmd}")
            
            try:
                subprocess.run(bash_cmd.split(), check=True)
                print(f"    ✓ Successfully registered zstat to ses-01 space")
            except subprocess.CalledProcessError as e:
                print(f"    ✗ Error registering zstat: {e}")
        
        elif not need_registration:
            # Create symbolic link or copy (maps should already be in ses-01 space)
            if not os.path.exists(zstat_ses01):
                os.symlink(os.path.abspath(zstat_file), zstat_ses01)
                print(f"    ✓ Linked zstat (already in ses-01 space)")
            else:
                print(f"    ✓ zstat already processed")
        else:
            print(f"    ✓ zstat already registered to ses-01 space")
    else:
        print(f"    ⚠️  zstat file not found: {zstat_file}")
        print(f"       High-level FEAT may not have completed for {contrast_name}")

    # Process cope file
    if os.path.exists(cope_file):
        if need_registration and not os.path.exists(cope_ses01):
            # Register to first-session space
            bash_cmd = f'flirt -in {cope_file} -ref {ses01_ref} -out {cope_ses01} -applyxfm -init {anat_transform} -interp trilinear'
            print(f"    Running: {bash_cmd}")
            
            try:
                subprocess.run(bash_cmd.split(), check=True)
                print(f"    ✓ Successfully registered cope to ses-01 space")
            except subprocess.CalledProcessError as e:
                print(f"    ✗ Error registering cope: {e}")
        
        elif not need_registration:
            # Create symbolic link or copy (maps should already be in ses-01 space)
            if not os.path.exists(cope_ses01):
                os.symlink(os.path.abspath(cope_file), cope_ses01)
                print(f"    ✓ Linked cope (already in ses-01 space)")
            else:
                print(f"    ✓ cope already processed")
        else:
            print(f"    ✓ cope already registered to ses-01 space")
    else:
        print(f"    ⚠️  cope file not found: {cope_file}")

print(f"Finished processing high-level outputs for {sub} ses-{ses}")

# Summary
processed_zstats = []
processed_copes = []

for contrast_name, cope_num in cope_info.items():
    cope_dir = f'{highlevel_dir}/cope{cope_num}.feat'
    zstat_ses01 = f'{cope_dir}/stats/zstat1_ses01.nii.gz'
    cope_ses01 = f'{cope_dir}/stats/cope1_ses01.nii.gz'
    
    if os.path.exists(zstat_ses01):
        processed_zstats.append(contrast_name)
    if os.path.exists(cope_ses01):
        processed_copes.append(contrast_name)

print(f"\nSummary:")
print(f"  Processed zstats: {len(processed_zstats)}/{len(cope_info)} contrasts")
print(f"  Processed copes: {len(processed_copes)}/{len(cope_info)} contrasts")
print(f"  All outputs in first-session space: {ses01_ref}")

if processed_zstats:
    print(f"  Successfully processed zstats: {', '.join(processed_zstats)}")
if processed_copes:
    print(f"  Successfully processed copes: {', '.join(processed_copes)}")