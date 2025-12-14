#!/bin/bash
#SBATCH --job-name=searchlight
#SBATCH --output=/user_data/csimmon2/git_repos/long_pt/B_analyses/searchlight_decoding/logs/%x_%A_%a.out
#SBATCH --error=/user_data/csimmon2/git_repos/long_pt/B_analyses/searchlight_decoding/logs/%x_%A_%a.err
#SBATCH --time=4:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=4
#SBATCH --array=0-5

# ============================================================================
# Searchlight Decoding - SLURM Array Job
# ============================================================================
# 
# Runs searchlight decoding for all OTC patients
# Array indices map to subjects
#
# Usage:
#   sbatch submit_searchlight.sh              # All subjects
#   sbatch --array=0 submit_searchlight.sh    # Just sub-004
#
# ============================================================================

# Subjects array
SUBJECTS=(sub-004 sub-008 sub-010 sub-017 sub-021 sub-079)

# Get subject for this array task
SUB=${SUBJECTS[$SLURM_ARRAY_TASK_ID]}

echo "============================================"
echo "Job ID: $SLURM_JOB_ID"
echo "Array Task ID: $SLURM_ARRAY_TASK_ID"
echo "Subject: $SUB"
echo "Start time: $(date)"
echo "============================================"

# Activate conda environment
source ~/anaconda3/etc/profile.d/conda.sh
conda activate brainiak_env

# Create log directory if needed
mkdir -p /user_data/csimmon2/git_repos/long_pt/B_analyses/searchlight_decoding/logs

# Run the analysis
python /user_data/csimmon2/git_repos/long_pt/B_analyses/05_searchlight_decoding/searchlight_decoding_cluster.py \
    --sub $SUB \
    --all-cats \
    --cross-session

echo "============================================"
echo "End time: $(date)"
echo "============================================"