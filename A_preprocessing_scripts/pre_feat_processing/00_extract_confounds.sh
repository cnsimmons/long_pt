#!/bin/bash
#
# extract_confounds.sh
#
# Runs pre-FEAT processing steps, primarily:
# 1. fsl_motion_outliers (to create spike regressors)
# 2. bet (optional, as FEAT can do this)
#

# --- Configuration ---
module load fsl-6.0.3

RAW_DIR='/lab_data/behrmannlab/hemi/Raw'
PROCESSED_DIR='/user_data/csimmon2/long_pt'

# Replicating the logic from the Python script
declare -A SUB_SESSIONS_RUNS
SUB_SESSIONS_RUNS["004"]="1:1,2,3 2:1,2,3 3:1,2,3 5:1,2,3 6:1,2,3"
SUB_SESSIONS_RUNS["007"]="1:1,2,3 3:1,2 4:1,2,3"
SUB_SESSIONS_RUNS["021"]="1:1,2,3 2:1,2,3 3:1,2,3"
# ---

echo "Starting confound extraction..."
echo "==============================="

for sub in "${!SUB_SESSIONS_RUNS[@]}"; do
    echo
    echo "=== Processing sub-${sub} ==="
    
    IFS=' ' read -r -a sessions_def <<< "${SUB_SESSIONS_RUNS[$sub]}"
    
    for ses_def in "${sessions_def[@]}"; do
        ses_num=$(echo "$ses_def" | cut -d: -f1)
        run_list=$(echo "$ses_def" | cut -d: -f2)
        
        local ses=$(printf "%02d" $ses_num)
        echo "  --- Session ${ses} ---"

        # --- Anatomical Skull-Stripping (Optional) ---
        # **RECOMMENDATION:** FEAT (your 1stLevel.fsf) runs 'bet' automatically.
        # Running it here is redundant *unless* you specifically tell FEAT
        # to use this pre-made brain. I recommend keeping this commented.
        #
        # echo "    Running BET (Skull-stripping)..."
        # T1_RAW="${RAW_DIR}/sub-${sub}/ses-${ses}/anat/sub-${sub}_ses-${ses}_T1w.nii.gz"
        # T1_BRAIN_DIR="${PROCESSED_DIR}/sub-${sub}/ses-${ses}/anat"
        #
        # if [ -f "$T1_RAW" ]; then
        #     bet "$T1_RAW" "${T1_BRAIN_DIR}/sub-${sub}_ses-${ses}_T1w_brain.nii.gz" -R -B
        # else
        #     echo "    WARNING: T1w file not found: $T1_RAW"
        # fi

        # --- Motion Outlier (Spike) Generation ---
        echo "    Generating motion outliers (spikes)..."
        
        IFS=',' read -r -a runs <<< "$run_list"
        for run_num in "${runs[@]}"; do
            local run=$(printf "%02d" $run_num)
            local task="loc"
            
            # Input file
            func_raw_file="${RAW_DIR}/sub-${sub}/ses-${ses}/func/sub-${sub}_ses-${ses}_task-${task}_run-${run}_bold.nii.gz"
            
            # Output directory (created by Python script)
            out_dir="${PROCESSED_DIR}/sub-${sub}/ses-${ses}/derivatives/fsl/${task}/run-${run}"
            out_spike_file="${out_dir}/sub-${sub}_ses-${ses}_task-${task}_run-${run}_bold_spikes.txt"

            if [ ! -f "$func_raw_file" ]; then
                echo "      SKIP: Func file not found: $func_raw_file"
                continue
            fi
            
            echo "      Processing run-${run}..."
            fsl_motion_outliers -i "$func_raw_file" -o "$out_spike_file" --dummy=0
            
            if [ -s "$out_spike_file" ]; then
                echo "        -> Created spikes file."
            else
                echo "        -> No outliers found. Empty spikes file created."
            fi
            
        done # end run
    done # end session
done # end subject

echo
echo "==========================="
echo "Confound extraction complete."
echo "Next step: Edit your .fsf file and run your analysis."