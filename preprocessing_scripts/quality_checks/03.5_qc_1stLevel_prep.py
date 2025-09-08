#!/usr/bin/env python3
"""
Verify everything is ready before submitting FEAT jobs
"""

import os
import subprocess
from glob import glob

# Project parameters (same as submit_jobs.py)
data_dir = '/lab_data/behrmannlab/claire/long_pt'
raw_data_dir = '/lab_data/behrmannlab/hemi/Raw'
task = 'loc'
runs = ['01', '02', '03']

subject_sessions = {
    'sub-004': ['02', '03', '05', '06'],  # UD
    'sub-007': ['03', '04'],             # TC  
    'sub-021': ['01', '02', '03']        # OT
}

print("🔍 VERIFYING SETUP FOR FEAT SUBMISSION")
print("=" * 50)

# 1. Check if scripts exist
print("\n1. Checking required scripts...")
required_scripts = [
    'submit_jobs.py',
    'firstlevel_registration.py'
]

for script in required_scripts:
    if os.path.exists(script):
        print(f"   ✓ {script}")
    else:
        print(f"   ✗ {script} - MISSING!")

# 2. Check if slurm output directory exists
print("\n2. Checking slurm output directory...")
if os.path.exists('slurm_out'):
    print("   ✓ slurm_out/ directory exists")
else:
    print("   ⚠️  slurm_out/ directory missing - will be created")
    os.makedirs('slurm_out', exist_ok=True)
    print("   ✓ slurm_out/ directory created")

# 3. Check FSF files
print("\n3. Checking FSF files...")
total_fsf = 0
missing_fsf = []

for sub, sessions in subject_sessions.items():
    for ses in sessions:
        for run in runs:
            fsf_file = f'{data_dir}/{sub}/ses-{ses}/derivatives/fsl/{task}/run-{run}/1stLevel.fsf'
            if os.path.exists(fsf_file):
                total_fsf += 1
            else:
                missing_fsf.append(f"{sub}/ses-{ses}/run-{run}")

print(f"   ✓ Found {total_fsf} FSF files")
if missing_fsf:
    print(f"   ⚠️  Missing FSF files for: {', '.join(missing_fsf)}")

# 4. Check raw data (functional and timing files)
print("\n4. Checking raw data...")
missing_func = []
missing_timing = []

for sub, sessions in subject_sessions.items():
    for ses in sessions:
        for run in runs:
            # Check functional data
            func_file = f'{raw_data_dir}/{sub}/ses-{ses}/func/{sub}_ses-{ses}_task-{task}_run-{run}_bold.nii.gz'
            if not os.path.exists(func_file):
                missing_func.append(f"{sub}/ses-{ses}/run-{run}")
            
            # Check timing files
            if sub == 'sub-007' and ses == '03':
                # Special case: timing files in ses-04
                timing_file = f'{raw_data_dir}/{sub}/ses-04/func/{sub}_ses-04_task-{task}_run-{run}_events.tsv'
            else:
                timing_file = f'{raw_data_dir}/{sub}/ses-{ses}/func/{sub}_ses-{ses}_task-{task}_run-{run}_events.tsv'
            
            if not os.path.exists(timing_file):
                missing_timing.append(f"{sub}/ses-{ses}/run-{run}")

if not missing_func:
    print("   ✓ All functional data files found")
else:
    print(f"   ✗ Missing functional data: {', '.join(missing_func)}")

if not missing_timing:
    print("   ✓ All timing files found")
else:
    print(f"   ✗ Missing timing files: {', '.join(missing_timing)}")

# 5. Check FSL and conda environment
print("\n5. Checking FSL and environment...")
try:
    result = subprocess.run(['which', 'feat'], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"   ✓ FEAT found at: {result.stdout.strip()}")
    else:
        print("   ⚠️  FEAT not found - make sure FSL is loaded")
except:
    print("   ⚠️  Could not check FEAT - make sure FSL is loaded")

# 6. Test one FSF file
print("\n6. Testing one FSF file...")
test_fsf = None
for sub, sessions in subject_sessions.items():
    for ses in sessions:
        for run in runs:
            fsf_file = f'{data_dir}/{sub}/ses-{ses}/derivatives/fsl/{task}/run-{run}/1stLevel.fsf'
            if os.path.exists(fsf_file):
                test_fsf = fsf_file
                print(f"   📄 Test FSF: {test_fsf}")
                break
        if test_fsf:
            break
    if test_fsf:
        break

if test_fsf:
    print(f"\n   To test FEAT manually, run:")
    print(f"   feat {test_fsf}")
    print(f"   (This will create output in the same directory)")

# Summary
print("\n" + "=" * 50)
print("📋 SUMMARY")
print("=" * 50)

total_expected = sum(len(sessions) * len(runs) for sessions in subject_sessions.values())
ready_jobs = total_fsf - len(missing_func) - len(missing_timing)

print(f"Expected jobs: {total_expected}")
print(f"FSF files ready: {total_fsf}")
print(f"Jobs ready to run: {ready_jobs}")

if ready_jobs == total_expected:
    print("\n🎉 ALL CHECKS PASSED! Ready to submit jobs.")
    print("\nTo submit jobs:")
    print("1. python submit_jobs.py")
elif ready_jobs > 0:
    print(f"\n⚠️  {ready_jobs}/{total_expected} jobs ready to run")
    print("Some jobs will be skipped due to missing files")
    print("\nTo submit available jobs:")
    print("1. python submit_jobs.py")
else:
    print("\n❌ NO JOBS READY - Fix missing files first")

print(f"\nTo monitor jobs after submission:")
print(f"- Check status: squeue -u $USER")
print(f"- Check logs: ls slurm_out/")