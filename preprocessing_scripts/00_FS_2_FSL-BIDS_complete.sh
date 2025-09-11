#!/bin/bash
# Corrected timing file conversion for Figure 5 longitudinal analysis
# Handles all available sessions with proper patient mappings

RAW_DIR='/lab_data/behrmannlab/hemi/Raw'
PROCESSED_DIR='/user_data/csimmon2/long_pt'

convert_for_subject() {
    local subject="$1" 
    local session="$2" 
    local run="$3"
    
    # Special case: UD ses-03 uses ses-04 events
    local events_session="$session"
    if [[ "$subject" == "007" && "$session" == "03" ]]; then
        events_session="04"
    fi
    
    events_file="$RAW_DIR/sub-${subject}/ses-${events_session}/func/sub-${subject}_ses-${events_session}_task-loc_run-${run}_events.tsv"
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

echo "Starting corrected timing file conversion..."
echo "==========================================="
echo "Patient mappings: TC=sub-004, UD=sub-007, OT=sub-021"
echo ""

# TC (sub-004): Process ses-01,02,03,05,06,07 (skip ses-04 no func)
echo "=== Processing TC (sub-004) ==="
tc_sessions=("01" "02" "03" "05" "06" "07")
tc_runs=("01" "02" "03")  # Use first 3 runs for consistency

for ses in "${tc_sessions[@]}"; do
    echo "  Session ${ses}:"
    session_success=0
    
    for run in "${tc_runs[@]}"; do
        if convert_for_subject "004" "$ses" "$run"; then
            ((session_success++))
        fi
    done
    
    echo "    Session summary: $session_success/3 runs successful"
done

echo ""
echo "=== Processing UD (sub-007) ==="
# UD (sub-007): Process ses-01,04,05 (skip ses-02 no func, ses-03 no events)
ud_sessions=("01" "03" "04" "05")
ud_runs=("01" "02" "03")

for ses in "${ud_sessions[@]}"; do
    echo "  Session ${ses}:"
    session_success=0
    
    for run in "${ud_runs[@]}"; do
        if convert_for_subject "007" "$ses" "$run"; then
            ((session_success++))
        fi
    done
    
    echo "    Session summary: $session_success/3 runs successful"
done

echo ""
echo "=== Processing OT (sub-021) ==="
# OT (sub-021): Process all sessions (complete data)
ot_sessions=("01" "02" "03")
ot_runs=("01" "02" "03")

for ses in "${ot_sessions[@]}"; do
    echo "  Session ${ses}:"
    session_success=0
    
    for run in "${ot_runs[@]}"; do
        if convert_for_subject "021" "$ses" "$run"; then
            ((session_success++))
        fi
    done
    
    echo "    Session summary: $session_success/3 runs successful"
done

echo ""
echo "=========================================="
echo "Conversion complete!"
echo ""
echo "Expected sessions for Figure 5:"
echo "- TC (sub-004): 6 sessions × 3 runs = 18 analyses"
echo "- UD (sub-007): 3 sessions × 3 runs = 9 analyses"  
echo "- OT (sub-021): 3 sessions × 3 runs = 9 analyses"
echo "- Total: 36 run-level analyses"
echo ""
echo "Next step: Create FSF files for session-level analysis"