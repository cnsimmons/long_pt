#!/usr/bin/env python3
"""
Submit FSL FEAT jobs for long_pt project
Adapted from hemispace project - Vlad's script
Creates and submits SLURM jobs for:
- FEAT first level analysis
- Registration to anatomical space
- High level analysis
Requires FSL and a conda environment named 'fmri' with necessary packages
Make sure to adjust paths and parameters as needed
"""

import subprocess
from glob import glob
import os
import time
import pandas as pd

# Job parameters
job_name = 'long_pt_feat'
mem = 24
run_time = "1-00:00:00"
pause_crit = 12  # Number of jobs before pausing
pause_time = 5   # Minutes to pause

# Project parameters
data_dir = '/lab_data/behrmannlab/claire/long_pt'
task = 'loc'
runs = ['01', '02', '03']

# Subject and session mapping
# Skip ses-01 for sub-004 and sub-007 since they're already processed
subject_sessions = {
    'sub-004': ['02', '03', '05', '06'],  # UD
    'sub-007': ['03', '04'],             # TC  
    'sub-021': ['01', '02', '03']        # OT
}

# Job control flags
run_1stlevel = True      # Run FEAT first level
run_registration = False # Run registration to anatomical space
run_highlevel = False    # Run high level analysis (set to True later when needed)

def setup_sbatch(job_name, script_name):
    """Create SLURM sbatch script content"""
    sbatch_setup = f"""#!/bin/bash -l
# Job name
#SBATCH --job-name={job_name}
#SBATCH --mail-type=ALL
#SBATCH --mail-user=csimmon2@andrew.cmu.edu

# Submit job to cpu queue                
#SBATCH -p cpu
#SBATCH --cpus-per-task=1
#SBATCH --gres=gpu:0
#SBATCH --exclude=mind-0-15,mind-0-14,mind-0-16

# Job memory request
#SBATCH --mem={mem}gb

# Time limit days-hrs:min:sec
#SBATCH --time {run_time}

# Standard output and error log
#SBATCH --output=slurm_out/{job_name}.out

# Load modules and activate environment
module load fsl-6.0.3
conda activate fmri

{script_name}
"""
    return sbatch_setup

def create_job(job_name, job_cmd):
    """Create and submit a SLURM job"""
    print(f"Submitting job: {job_name}")
    print(f"Command: {job_cmd}")
    
    # Create temporary script file
    script_file = f"{job_name}.sh"
    with open(script_file, "w") as f:
        f.write(setup_sbatch(job_name, job_cmd))
    
    # Submit job
    try:
        result = subprocess.run(['sbatch', script_file], check=True, capture_output=True, text=True)
        print(f"  ✓ Job submitted: {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Error submitting job: {e}")
    
    # Clean up script file
    os.remove(script_file)

# Create output directory for slurm logs
os.makedirs('slurm_out', exist_ok=True)

# Job submission loop
n_jobs = 0

for sub, sessions in subject_sessions.items():
    for ses in sessions:
        sub_dir = f"{data_dir}/{sub}/ses-{ses}"
        
        if run_1stlevel:
            # Submit FEAT first level jobs
            task_dir = f'{sub_dir}/derivatives/fsl/{task}'
            
            for run in runs:
                fsf_file = f'{task_dir}/run-{run}/1stLevel.fsf'
                
                # Check if FSF file exists
                if os.path.exists(fsf_file):
                    job_name_full = f'{sub}_ses{ses}_{task}_run{run}_feat'
                    job_cmd = f'feat {fsf_file}'
                    create_job(job_name_full, job_cmd)
                    n_jobs += 1
                else:
                    print(f"⚠️  FSF file not found: {fsf_file}")
        
        if run_registration:
            # Submit registration jobs (only if FEAT output exists)
            feat_dirs = glob(f'{sub_dir}/derivatives/fsl/{task}/run-*/1stLevel.feat')
            
            if feat_dirs:  # Only submit if there are FEAT outputs
                job_name_full = f'{sub}_ses{ses}_registration'
                job_cmd = f'python firstlevel_registration.py {sub} {ses}'
                create_job(job_name_full, job_cmd)
                n_jobs += 1
        
        if run_highlevel:
            # Submit high level analysis jobs
            high_fsf = f'{sub_dir}/derivatives/fsl/{task}/HighLevel.fsf'
            
            if os.path.exists(high_fsf):
                job_name_full = f'{sub}_ses{ses}_{task}_highlevel'
                job_cmd = f'feat {high_fsf}'
                create_job(job_name_full, job_cmd)
                n_jobs += 1
            else:
                print(f"⚠️  High level FSF file not found: {high_fsf}")
        
        # Pause if we've submitted too many jobs
        if n_jobs >= pause_crit:
            print(f"\n🛑 Pausing for {pause_time} minutes after submitting {n_jobs} jobs...")
            time.sleep(pause_time * 60)
            n_jobs = 0

print(f"\n✅ Finished submitting all jobs!")
print(f"Total jobs submitted: {n_jobs}")
print("\nTo check job status: squeue -u $USER")
print("To check job details: scontrol show job <job_id>")
print("To cancel jobs: scancel <job_id> or scancel -u $USER")