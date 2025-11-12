#!/usr/bin/env python3
"""
Submit FSL FEAT jobs for long_pt project (CSV-driven)
"""

import subprocess
from glob import glob
import os
import time
import pandas as pd

# Job parameters
job_name = 'long_pt_feat'
mem = 48
run_time = "1-00:00:00"
pause_crit = 12
pause_time = 5

# Project parameters
data_dir = '/user_data/csimmon2/long_pt'
raw_dir = '/lab_data/behrmannlab/hemi/Raw'
CSV_FILE = '/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv'
task = 'loc'

# Subjects to skip
SKIP_SUBS = ['sub-004', 'sub-021', 'sub-108']

# Special session mappings
SESSION_START = {
    'sub-010': 2,
    'sub-018': 2,
    'sub-068': 2
}

# Job control flags
run_1stlevel = False
run_registration = False
run_highlevel = True
run_mni_registration = False

def get_sessions_for_subject(row):
    """Count non-empty age columns"""
    age_cols = ['age_1', 'age_2', 'age_3', 'age_4', 'age_5']
    return sum(1 for col in age_cols if pd.notna(row[col]) and row[col] != '')

def get_runs_for_session(subject_id, ses):
    """Auto-detect runs from filesystem"""
    func_dir = f"{raw_dir}/{subject_id}/ses-{ses}/func"
    if not os.path.exists(func_dir):
        return []
    
    runs = []
    for bold in glob(f"{func_dir}/{subject_id}_ses-{ses}_task-{task}_run-*_bold.nii.gz"):
        run = os.path.basename(bold).split('run-')[1].split('_')[0]
        runs.append(run)
    return sorted(runs)

def setup_sbatch(job_name, script_name):
    """Create SLURM sbatch script"""
    return f"""#!/bin/bash -l
#SBATCH --job-name={job_name}
#SBATCH --mail-type=ALL
#SBATCH --mail-user=csimmon2@andrew.cmu.edu
#SBATCH -p cpu
#SBATCH --cpus-per-task=1
#SBATCH --gres=gpu:0
#SBATCH --mem={mem}gb
#SBATCH --time {run_time}
#SBATCH --output=slurm_out/{job_name}.out

module load fsl-6.0.3
conda activate fmri

{script_name}
"""

def create_job(job_name, job_cmd):
    """Create and submit SLURM job"""
    print(f"Submitting: {job_name}")
    
    script_file = f"{job_name}.sh"
    with open(script_file, "w") as f:
        f.write(setup_sbatch(job_name, job_cmd))
    
    try:
        result = subprocess.run(['sbatch', script_file], check=True, capture_output=True, text=True)
        print(f"  ✓ {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Error: {e.stderr}")
    
    if os.path.exists(script_file):
        os.remove(script_file)

# Main
os.makedirs('slurm_out', exist_ok=True)
df = pd.read_csv(CSV_FILE)
n_jobs = 0

for _, row in df.iterrows():
    sub = row['sub']
    
    if sub in SKIP_SUBS:
        print(f"SKIP: {sub}")
        continue
    
    session_count = get_sessions_for_subject(row)
    start_ses = SESSION_START.get(sub, 1)
    
    for i in range(session_count):
        ses_num = start_ses + i
        ses = f"{ses_num:02d}"
        sub_dir = f"{data_dir}/{sub}/ses-{ses}"
        
        # Get runs for this session
        runs = get_runs_for_session(sub, ses)
        
        if run_1stlevel:
            task_dir = f'{sub_dir}/derivatives/fsl/{task}'
            for run in runs:
                fsf_file = f'{task_dir}/run-{run}/1stLevel.fsf'
                
                if os.path.exists(fsf_file):
                    job_name_full = f'{sub}_ses{ses}_{task}_run{run}_feat'
                    create_job(job_name_full, f'feat {fsf_file}')
                    n_jobs += 1
                else:
                    print(f"⚠️  Missing: {fsf_file}")
        
        if run_registration:
            job_name_full = f'{sub}_ses{ses}_registration'
            create_job(job_name_full, f'python A_preprocessing_scripts/04_1stLevel.py {sub} {ses}')
            n_jobs += 1
        
        if run_highlevel:
            high_fsf = f'{sub_dir}/derivatives/fsl/{task}/HighLevel.fsf'
            if os.path.exists(high_fsf):
                job_name_full = f'{sub}_ses{ses}_{task}_highlevel'
                create_job(job_name_full, f'feat {high_fsf}')
                n_jobs += 1
        
        if run_mni_registration:
            job_name_full = f'{sub}_ses{ses}_mni_registration'
            create_job(job_name_full, f'python A_preprocessing_scripts/09_highLevel.py {sub} {ses}')
            n_jobs += 1
        
        if n_jobs >= pause_crit:
            print(f"\n🛑 Pausing {pause_time}min after {n_jobs} jobs...")
            time.sleep(pause_time * 60)
            n_jobs = 0

print(f"\n✅ Finished! Total: {n_jobs}")