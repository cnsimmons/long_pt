#!/bin/bash
#SBATCH --job-name=reg_4d
#SBATCH --output=logs/reg_%A_%a.out
#SBATCH --error=logs/reg_%A_%a.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --time=06:00:00
#SBATCH --array=0-8

# Define the list of subjects to process
subjects=(
    "sub-086" "sub-022" "sub-025" "sub-027" "sub-052" 
    "sub-058" "sub-062" "sub-064" "sub-068"
)

# Get the subject ID for this specific array task
sub=${subjects[$SLURM_ARRAY_TASK_ID]}

echo "------------------------------------------------"
echo "Job ID: $SLURM_JOB_ID"
echo "Array Task ID: $SLURM_ARRAY_TASK_ID"
echo "Processing Subject: $sub"
echo "------------------------------------------------"

# Activate your environment
source ~/.bashrc
conda activate fmri  

# Run the python script for this single subject
python B_analyses/05_searchlight_decoding/register_raw2_4d.py $sub