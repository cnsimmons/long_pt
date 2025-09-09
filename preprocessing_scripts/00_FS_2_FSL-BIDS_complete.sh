#!/bin/bash
# Convert all BIDS events to FSL timing files
# Complete version for all intended analyses

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

echo "Starting timing file conversion for all intended analyses..."
echo "============================================================"

# sub-004: sessions 02, 03, 05, 06 (4 sessions × 3 runs = 12 analyses)
echo ""
echo "=== Processing sub-004 (UD) ==="
for ses in "02" "03" "05" "06"; do
    echo "  Session ${ses}:"
    for run in "01" "02" "03"; do
        convert_for_subject "004" "$ses" "$run"
    done
done

# sub-007: sessions 03, 04 (2 sessions × 3 runs = 6 analyses)
echo ""
echo "=== Processing sub-007 (TC) ==="  
for ses in "03" "04"; do
    echo "  Session ${ses}:"
    for run in "01" "02" "03"; do
        convert_for_subject "007" "$ses" "$run"
    done
done

# sub-021: sessions 01, 02, 03 (3 sessions × 3 runs = 9 analyses)
echo ""
echo "=== Processing sub-021 (OT) ==="
for ses in "01" "02" "03"; do
    echo "  Session ${ses}:"
    for run in "01" "02" "03"; do
        convert_for_subject "021" "$ses" "$run"
    done
done

echo ""
echo "============================================================"
echo "Timing file conversion complete!"
echo ""
echo "Summary check:"
for sub in "004" "007" "021"; do
    echo "sub-${sub}:"
    sessions_dir="/lab_data/behrmannlab/claire/long_pt/sub-${sub}"
    
    if [ -d "$sessions_dir" ]; then
        for ses_dir in "$sessions_dir"/ses-*; do
            if [ -d "$ses_dir" ]; then
                ses=$(basename "$ses_dir")
                covs_dir="$ses_dir/covs"
                
                if [ -d "$covs_dir" ]; then
                    timing_count=$(ls "$covs_dir"/catloc_*.txt 2>/dev/null | wc -l)
                    echo "  $ses: $timing_count timing files"
                else
                    echo "  $ses: NO COVS DIRECTORY"
                fi
            fi
        done
    fi
done

echo ""
echo "Expected: 27 total analyses (sub-004: 12, sub-007: 6, sub-021: 9)"