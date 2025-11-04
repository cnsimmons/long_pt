#!/bin/bash
# Timing file conversion for sub-007 ses-03 ONLY
# Uses converted .prt files from processed directory

RAW_DIR='/lab_data/behrmannlab/hemi/Raw'
PROCESSED_DIR='/user_data/csimmon2/long_pt'

convert_for_subject() {
    local subject="$1" 
    local session="$2" 
    local run="$3"
    
    # Special case: UD ses-03 uses events from processed directory (converted from .prt)
    if [[ "$subject" == "007" && "$session" == "03" ]]; then
        events_file="$PROCESSED_DIR/sub-${subject}/ses-${session}/func/sub-${subject}_ses-${session}_task-loc_run-${run}_events.tsv"
    else
        events_file="$RAW_DIR/sub-${subject}/ses-${events_session}/func/sub-${subject}_ses-${events_session}_task-loc_run-${run}_events.tsv"
    fi
    
    covs_dir="$PROCESSED_DIR/sub-${subject}/ses-${session}/covs"
    
    if [ ! -f "$events_file" ]; then
        echo "    SKIP: $events_file not found"
        return 1
    fi
    
    mkdir -p "$covs_dir"
    echo "    Converting run-${run}..."
    
    local success=0
    for condition in Face House Object Word Scramble; do
        output_file="$covs_dir/catloc_${subject}_run-${run}_${condition}.txt"
        awk -v cond="$condition" 'NR>1 && $3==cond {print $1, $2, 1}' "$events_file" > "$output_file"
        
        if [ -s "$output_file" ]; then
            ((success++))
        else
            echo "      WARNING: Empty $condition file"
        fi
    done
    
    echo "      Created $success/5 condition files"
    return 0
}

echo "Converting timing files for sub-007 ses-03..."
echo "==========================================="

ses="03"
echo "  Session ${ses}:"
session_success=0

for run in "01" "02"; do
    echo "    Run ${run}:"
    if convert_for_subject "007" "$ses" "$run"; then
        ((session_success++))
    fi
done

echo "    Session summary: $session_success/2 runs successful"
echo ""
echo "Conversion complete!"
echo "Output directory: $PROCESSED_DIR/sub-007/ses-03/covs/"