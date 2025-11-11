#!/bin/bash
#
# convert_all_timing_files.sh (CSV-driven version with special session handling)
#

RAW_DIR='/lab_data/behrmannlab/hemi/Raw'
PROCESSED_DIR='/user_data/csimmon2/long_pt'
CSV_FILE='/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv'
TASK="loc"

# Subjects to skip (already processed)
SKIP_SUBS=("004" "007" "021" '108')

# Special session mappings (subjects that skip session 1)
declare -A SESSION_START
SESSION_START["010"]=2
SESSION_START["018"]=2

# Function to check if subject should be skipped
should_skip() {
    local sub="$1"
    for skip in "${SKIP_SUBS[@]}"; do
        if [[ "$sub" == "$skip" ]]; then
            return 0
        fi
    done
    return 1
}

# Function to get starting session for a subject
get_session_start() {
    local sub="$1"
    echo "${SESSION_START[$sub]:-1}"  # Default to 1 if not specified
}

# Function to convert files for a single run
convert_for_subject_run() {
    local subject="$1" 
    local session_num="$2" 
    local run_num="$3"
    
    local ses=$(printf "%02d" $session_num)
    local run=$(printf "%02d" $run_num)
    
    # Special case: sub-007 ses-03 uses events from processed directory
    if [[ "$subject" == "007" && "$ses" == "03" ]]; then
        events_file="$PROCESSED_DIR/sub-${subject}/ses-${ses}/func/sub-${subject}_ses-${ses}_task-${TASK}_run-${run}_events.tsv"
        echo "    INFO: Using special-case file: $events_file"
    else
        events_file="$RAW_DIR/sub-${subject}/ses-${ses}/func/sub-${subject}_ses-${ses}_task-${TASK}_run-${run}_events.tsv"
    fi
    
    local timing_dir="$PROCESSED_DIR/sub-${subject}/ses-${ses}/timing"
    mkdir -p "$timing_dir"
    
    if [ ! -f "$events_file" ]; then
        echo "    SKIP: Events file not found: $events_file"
        return 1
    fi
    
    echo "    Converting ses-${ses} run-${run}..."
    
    local success=0
    for condition in Face House Object Word Scramble; do
        output_file="$timing_dir/catloc_${subject}_run-${run}_${condition}.txt"
        
        awk -v cond="$condition" 'BEGIN{FS="\t"} NR>1 && $3==cond {print $1, $2, 1}' "$events_file" > "$output_file"
        
        if [ -s "$output_file" ]; then
            ((success++))
        else
            rm -f "$output_file"
        fi
    done
    
    echo "      Created $success/5 condition files"
    return 0
}

# --- Main Loop ---
echo "Starting timing file conversion (CSV-driven)..."
echo "==================================================="

# Read CSV and process each subject
tail -n +2 "$CSV_FILE" | while IFS=',' read -r sub rest; do
    # Extract subject number (e.g., "004" from "sub-004")
    subject=$(echo "$sub" | sed 's/sub-//')
    
    # Skip if in skip list
    if should_skip "$subject"; then
        echo "SKIP: sub-${subject} (already processed)"
        continue
    fi
    
    echo
    echo "=== Processing sub-${subject} ==="
    
    # Read the rest of the CSV line to count non-empty age columns
    IFS=',' read -ra fields <<< "$rest"
    # fields[0]=DOB, fields[1]=age_1, fields[2]=age_2, etc.
    
    # Count sessions based on non-empty age columns
    session_count=0
    for i in {1..5}; do
        if [[ -n "${fields[$i]}" && "${fields[$i]}" != " " ]]; then
            ((session_count++))
        fi
    done
    
    # Get starting session number
    start_ses=$(get_session_start "$subject")
    
    echo "  Detected $session_count sessions from CSV (starting from session $start_ses)"
    
    # Process each session
    for ((i=0; i<session_count; i++)); do
        ses_num=$((start_ses + i))
        ses=$(printf "%02d" $ses_num)
        echo "  --- Session ${ses_num} ---"
        
        # Auto-detect runs from filesystem
        func_dir="$RAW_DIR/sub-${subject}/ses-${ses}/func"
        
        # Check special case first
        if [[ "$subject" == "007" && "$ses" == "03" ]]; then
            func_dir="$PROCESSED_DIR/sub-${subject}/ses-${ses}/func"
        fi
        
        if [ ! -d "$func_dir" ]; then
            echo "    SKIP: No func directory found at $func_dir"
            continue
        fi
        
        # Find all runs
        run_count=0
        for events_file in "$func_dir"/sub-${subject}_ses-${ses}_task-${TASK}_run-*_events.tsv; do
            [ ! -f "$events_file" ] && continue
            
            run=$(basename "$events_file" | sed -n 's/.*run-\([0-9]*\)_events.tsv/\1/p')
            run_num=$((10#$run))
            
            convert_for_subject_run "$subject" "$ses_num" "$run_num"
            ((run_count++))
        done
        
        if [ $run_count -eq 0 ]; then
            echo "    SKIP: No runs found"
        fi
    done
done

echo
echo "================================="
echo "Timing conversion complete."