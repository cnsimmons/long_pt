#!/bin/bash
#SBATCH --job-name=SL_decode
#SBATCH --output=logs/sl_%A_%a.out
#SBATCH --error=logs/sl_%A_%a.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --array=0-24

# 1. Activate Environment
source ~/.bashrc
conda activate fmri 

# 2. Define Subjects (FULL LIST)
subjects=(
    "sub-004" "sub-007" "sub-008" "sub-010" "sub-017" "sub-018" 
    "sub-021" "sub-045" "sub-047" "sub-049" "sub-070" 
    "sub-072" "sub-073" "sub-079" "sub-081" "sub-086" 
    "sub-108" "sub-022" "sub-025" "sub-027" "sub-052" 
    "sub-058" "sub-062" "sub-064" "sub-068"
)

sub=${subjects[$SLURM_ARRAY_TASK_ID]}

echo "------------------------------------------------"
echo "Job ID: $SLURM_JOB_ID"
echo "Processing Subject: $sub"
echo "------------------------------------------------"

# 3. Run Searchlight
# The python script now internally handles the sub-007 gap
python B_analyses/05_searchlight_decoding/searchlight_decoding_cluster.py \
    --sub $sub \
    --all-cats \
    --cross-session