#!/bin/bash
# Convert all BIDS events to FSL timing files

convert_for_subject() {
    local subject="$1"
    local session="$2" 
    local run="$3"
    
    # Handle special case for TC ses-03 timing files
    local timing_session="$session"
    if [[ "$subject" == "007" && "$session" == "03" ]]; then
        timing_session="04"
    fi
    
    events_file="/lab_data/behrmannlab/hemi/Raw/sub-${subject}/ses-${timing_session}/func/sub-${subject}_ses-${timing_session}_task-loc_run-${run}_events.tsv"
    covs_dir="/lab_data/behrmannlab/claire/long_pt/sub-${subject}/ses-${session}/covs"
    
    if [ ! -f "$events_file" ]; then
        echo "SKIP: $events_file not found"
        return
    fi
    
    mkdir -p "$covs_dir"
    echo "Converting sub-${subject}/ses-${session}/run-${run}..."
    
    # Check the events file format first
    echo "Events file header:"
    head -1 "$events_file"
    echo "Sample data:"
    head -5 "$events_file" | tail -4
    
    for condition in Face House Object Word Scramble; do
        output_file="$covs_dir/catloc_${subject}_run-${run}_${condition}.txt"
        awk -v cond="$condition" 'NR>1 && $3==cond {print $1, $2, 1}' "$events_file" > "$output_file"
        
        # Check if timing file was created and has content
        if [ -s "$output_file" ]; then
            echo "  Created: $output_file ($(wc -l < "$output_file") events)"
        else
            echo "  WARNING: Empty or missing: $output_file"
        fi
    done
}

# Test with one subject first
convert_for_subject "007" "01" "03"