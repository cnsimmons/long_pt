#!/bin/bash
#
# run_prefeat_steps.sh
#
# This script runs preprocessing steps *before* launching the main FEAT (1stLevel.fsf) analysis.
#
# 1. Skull-strips the anatomical (OPTIONAL - FEAT can do this).
# 2. Generates motion outlier "spike" confound files using fsl_motion_outliers.
#
# Must be run *after* setup_long_pt_structure.py and *before* running the 1stLevel.fsf.
#

# --- Configuration ---
# Load FSL
module load fsl-6.0.3

# Set main project directories
# (Using directories from your Python script for consistency)
RAW_DIR='/lab_data/behrmannlab/hemi/Raw'
PROCESSED_DIR='/user_data/csimmon2/long_pt'

# Define subjects, sessions, and tasks to process
# (Update this to match your actual study subjects)
declare -A SUBJECTS_SESSIONS
SUBJECTS_SESSIONS=(
    ["sub-004"]="1 2 3 5 6"
    ["sub-007"]="1 3 4"
    ["sub-021"]="1 2 3"
)

TASKS=("loc") # Add other tasks like "toolloc" if needed
RUNS=("01" "02" "03")

# --- Main Loop ---

echo "Starting Pre-FEAT processing..."

for subject_id in "${!SUBJECTS_SESSIONS[@]}"; do
    echo "=== Processing ${subject_id} ==="
    
    for session_num in ${SUBJECTS_SESSIONS[$subject_id]}; do
        ses=$(printf "%02d" $session_num) # Zero-pad session number
        echo "  --- Session ${ses} ---"

        subj_dir_raw="${RAW_DIR}/${subject_id}/ses-${ses}"
        subj_dir_processed="${PROCESSED_DIR}/${subject_id}/ses-${ses}"
        
        # Check if processed directory exists (created by Python script)
        if [ ! -d "$subj_dir_processed" ]; then
            echo "    SKIP: Processed directory not found: $subj_dir_processed"
            continue
        fi

        # --- 1. Anatomical Skull-Stripping (Optional) ---
        #
        # **RECOMMENDATION:** FEAT (your 1stLevel.fsf) typically runs 'bet' automatically.
        # Running it here is redundant *unless* you specifically tell FEAT
        # to use the pre-made brain-extracted image.
        #
        # If you want to run it here, uncomment the lines below.
        #
        # echo "    Running BET (Skull-stripping)..."
        # T1_RAW="${subj_dir_raw}/anat/${subject_id}_ses-${ses}_T1w.nii.gz"
        # T1_BRAIN="${subj_dir_processed}/anat/${subject_id}_ses-${ses}_T1w_brain.nii.gz" # Saving to processed dir
        # 
        # if [ -f "$T1_RAW" ]; then
        #     mkdir -p "${subj_dir_processed}/anat"
        #     bet "$T1_RAW" "$T1_BRAIN" -R -B
        # else
        #     echo "    WARNING: T1w file not found: $T1_RAW"
        # fi


        # --- 2. Generate Motion Outliers (Spikes) ---
        echo "    Generating motion outliers (spikes)..."
        
        for task in "${TASKS[@]}"; do
            for run in "${RUNS[@]}"; do
                
                # Define input (raw) and output (processed) files
                func_raw_file="${subj_dir_raw}/func/${subject_id}_ses-${ses}_task-${task}_run-${run}_bold.nii.gz"
                
                # Output directory for spikes
                # Note: Your Python script creates /timing for 3-col files.
                # Your sample script puts spikes in derivatives/fsl/TASK/run-XX/
                # Let's stick to that.
                out_dir="${subj_dir_processed}/derivatives/fsl/${task}/run-${run}"
                out_spike_file="${out_dir}/${subject_id}_ses-${ses}_task-${task}_run-${run}_bold_spikes.txt"

                if [ ! -f "$func_raw_file" ]; then
                    echo "      SKIP: Func file not found: $func_raw_file"
                    continue
                fi
                
                # Ensure output directory exists
                mkdir -p "$out_dir"
                
                echo "      Processing: ${task} run-${run}"
                fsl_motion_outliers -i "$func_raw_file" -o "$out_spike_file" --dummy=0
                
                if [ -s "$out_spike_file" ]; then
                    echo "        -> Created spikes file: $(basename $out_spike_file)"
                else
                    echo "        -> No outliers found. Empty spikes file created."
                fi

            done # end run
        done # end task
    done # end session
done # end subject

echo "==========================="
echo "Pre-FEAT processing complete."
echo "Next steps:"
echo "1. Manually add the generated _spikes.txt files to your 1stLevel.fsf design (Stats -> Confound EVs)."
echo "2. Run your 1stLevel.fsf analysis."