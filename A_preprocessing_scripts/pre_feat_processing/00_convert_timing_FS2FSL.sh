#!/bin/bash
#
# convert_all_timing_files.sh
#
# Converts BIDS .tsv event files into FSL-compatible 3-column .txt files.
# This script handles all subjects and includes the special case for
# sub-007 ses-03 (which uses .prt-converted files from the processed dir).
#

RAW_DIR='/lab_data/behrmannlab/hemi/Raw'
PROCESSED_DIR='/user_data/csimmon2/long_pt'

# --- Data Structure ---
# Replicating the logic from the Python script to define subjects, sessions, and runs
declare -A SUB_SESSIONS_RUNS
SUB_SESSIONS_RUNS["004"]="1:1,2,3 2:1,2,3 3:1,2,3 5:1,2,3 6:1,2,3"
SUB_SESSIONS_RUNS["007"]="1:1,2,3 3:1,2 4:1,2,3" # sub-007 ses-03 has only 2 runs
SUB_SESSIONS_RUNS["021"]="1:1,2,3 2:1,2,3 3:1,2,3"
# ---

# Function to convert files for a single run
convert_for_subject_run() {
    local subject="$1" 
    local session_num="$2" 
    local run_num="$3"
    local task="loc"
    
    local ses=$(printf "%02d" $session_num)
    local run=$(printf "%02d" $run_num)
    
    # Special case: sub-007 ses-03 uses events from processed directory
    if [[ "$subject" == "007" && "$ses" == "03" ]]; then
        events_file="$PROCESSED_DIR/sub-${subject}/ses-${ses}/func/sub-${subject}_ses-${ses}_task-${task}_run-${run}_events.tsv"
        echo "    INFO: Using special-case file: $events_file"
    else
        # Standard case: Use raw directory
        events_file="$RAW_DIR/sub-${subject}/ses-${ses}/func/sub-${subject}_ses-${ses}_task-${task}_run-${run}_events.tsv"
    fi
    
    # Output directory (created by Python script)
    local timing_dir="$PROCESSED_DIR/sub-${subject}/ses-${ses}/timing"
    
    if [ ! -f "$events_file" ]; then
        echo "    SKIP: Events file not found: $events_file"
        return 1
    fi
    
    echo "    Converting ses-${ses} run-${run}..."
    
    local success=0
    for condition in Face House Object Word Scramble; do
        output_file="$timing_dir/catloc_${subject}_run-${run}_${condition}.txt"
        
        # Use awk to find matching condition, skip header (NR>1), and print 3-col
        awk -v cond="$condition" 'BEGIN{FS="\t"} NR>1 && $3==cond {print $1, $2, 1}' "$events_file" > "$output_file"
        
        if [ -s "$output_file" ]; then
            ((success++))
        else
            # Remove empty file
            rm "$output_file"
        fi
    done
    
    echo "      Created $success/5 condition files"
    return 0
}

# --- Main Loop ---
echo "Starting timing file conversion for all subjects..."
echo "==================================================="

for sub in "${!SUB_SESSIONS_RUNS[@]}"; do
    echo
    echo "=== Processing sub-${sub} ==="
    
    # Read the session and run string (e.g., "1:1,2,3 2:1,2,3")
    IFS=' ' read -r -a sessions_def <<< "${SUB_SESSIONS_RUNS[$sub]}"
    
    for ses_def in "${sessions_def[@]}"; do
        # Get session number (e.g., "1")
        ses_num=$(echo "$ses_def" | cut -d: -f1)
        # Get run list (e.g., "1,2,3")
        run_list=$(echo "$ses_def" | cut -d: -f2)
        
        echo "  --- Session ${ses_num} ---"
        
        # Iterate over runs
        IFS=',' read -r -a runs <<< "$run_list"
        for run_num in "${runs[@]}"; do
            convert_for_subject_run "$sub" "$ses_num" "$run_num"
        done
    done
done

echo
echo "================================="
echo "Timing conversion complete."
echo "Next step: Run your Bash script to extract confounds."