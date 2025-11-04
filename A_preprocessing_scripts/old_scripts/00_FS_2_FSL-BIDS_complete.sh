#!/bin/bash
# Corrected timing file conversion for Figure 5 longitudinal analysis
# TEST VERSION - Only processing sub-007 ses-03
# Handles all available sessions with proper patient mappings
# Modified to use processed directory for sub-007 ses-03

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
        # Special case: UD ses-03 originally used ses-04 events (no longer needed since we have .prt conversions)
        local events_session="$session"
        if [[ "$subject" == "007" && "$session" == "04" ]]; then
            events_session="04"
        fi
        
        events_file="$RAW_DIR/sub-${subject}/ses-${events_session}/func/sub-${subject}_ses-${events_session}_task-loc_run-${run}_events.tsv"
    fi
    
    covs_dir="$PROCESSED_DIR/sub-${subject}/ses-${session}/covs"
    
    if [ ! -f "$events_file" ]; then
        echo "    SKIP: $events_file not found"
        return 1
    fi
    
    mkdir -p "$covs_dir"
    echo "    Converting run-${run} (from $(basename $(dirname $events_file)))..."
    
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

echo "Starting timing file conversion TEST..."
echo "==========================================="
echo "TEST MODE: Only processing sub-007 ses-03"
echo "NOTE: sub-007 ses-03 uses converted .prt files from processed directory"
echo ""

# # TC (sub-004): Process ses-01,02,03,05,06,07 (skip ses-04 no func)
# echo "=== Processing TC (sub-004) ==="
# tc_sessions=("01" "02" "03" "05" "06" "07")
# tc_runs=("01" "02" "03")  # Use first 3 runs for consistency
# 
# for ses in "${tc_sessions[@]}"; do
#     echo "  Session ${ses}:"
#     session_success=0
#     
#     for run in "${tc_runs[@]}"; do
#         if convert_for_subject "004" "$ses" "$run"; then
#             ((session_success++))
#         fi
#     done
#     
#     echo "    Session summary: $session_success/3 runs successful"
# done

echo ""
echo "=== Processing UD (sub-007) ses-03 ONLY ==="
# UD (sub-007): Process ONLY ses-03
# ses-03 uses converted .prt files (only runs 01,02 available)
ses="03"
echo "  Session ${ses}:"
session_success=0

ud_runs=("01" "02")
echo "    NOTE: Only runs 01-02 available (converted from .prt files)"

for run in "${ud_runs[@]}"; do
    if convert_for_subject "007" "$ses" "$run"; then
        ((session_success++))
    fi
done

echo "    Session summary: $session_success/${#ud_runs[@]} runs successful"

# echo ""
# echo "=== Processing OT (sub-021) ==="
# # OT (sub-021): Process all sessions (complete data)
# ot_sessions=("01" "02" "03")
# ot_runs=("01" "02" "03")
# 
# for ses in "${ot_sessions[@]}"; do
#     echo "  Session ${ses}:"
#     session_success=0
#     
#     for run in "${ot_runs[@]}"; do
#         if convert_for_subject "021" "$ses" "$run"; then
#             ((session_success++))
#         fi
#     done
#     
#     echo "    Session summary: $session_success/3 runs successful"
# done

echo ""
echo "=========================================="
echo "TEST conversion complete!"
echo ""
echo "Processed: sub-007 ses-03 (2 runs)"
echo ""
echo "Check output in: /user_data/csimmon2/long_pt/sub-007/ses-03/covs/"
echo ""
echo "If successful, uncomment other subjects to run full conversion"