#!/bin/bash
# extract_confounds.sh (CSV-driven version)

module load fsl-6.0.3

RAW_DIR='/lab_data/behrmannlab/hemi/Raw'
PROCESSED_DIR='/user_data/csimmon2/long_pt'
CSV_FILE='/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv'
TASK='loc'

# Subjects to skip (already processed)
SKIP_SUBS=("004" "007" "021" '108')
# SKIP_SUBS=("004" "007" "021" '108' "008" "009" "010" "011" "012" "013" "014" "015" "016" "019" "020" "022" "023" "024" "025" "026" "027" "028" "029" "030" "031" "032" "033" "034" "035" "036" "037" "038" "039" "040" "041" "042" "043" "044" "045" "046" "047" "048" "049" "050" "051" "052" "053" "054" "055" "056" "057" "058" "059" "060" "061" "062" "063" "064" "065" "066" "067" "068" "069" "070" "071" "072" "073" "074" "075" "076" "077" "078" "079" "080" "081" "082" "083" "084" "085" "086" "087" "088" "089" "090" "091" "092" "093" "094"  )


# Special session mappings
declare -A SESSION_START
SESSION_START["010"]=2
SESSION_START["018"]=2

should_skip() {
    local sub="$1"
    for skip in "${SKIP_SUBS[@]}"; do
        if [[ "$sub" == "$skip" ]]; then
            return 0
        fi
    done
    return 1
}

get_session_start() {
    local sub="$1"
    echo "${SESSION_START[$sub]:-1}"
}

extract_confounds_for_run() {
    local subject="$1"
    local session_num="$2"
    local run_num="$3"
    
    local ses=$(printf "%02d" $session_num)
    local run=$(printf "%02d" $run_num)
    
    func_raw_file="${RAW_DIR}/sub-${subject}/ses-${ses}/func/sub-${subject}_ses-${ses}_task-${TASK}_run-${run}_bold.nii.gz"
    out_dir="${PROCESSED_DIR}/sub-${subject}/ses-${ses}/derivatives/fsl/${TASK}/run-${run}"
    out_spike_file="${out_dir}/sub-${subject}_ses-${ses}_task-${TASK}_run-${run}_bold_spikes.txt"
    
    if [ ! -f "$func_raw_file" ]; then
        echo "    SKIP Run ${run} (file not found)"
        return 1
    fi
    
    echo "    Processing Run ${run}..."
    mkdir -p "$out_dir"
    fsl_motion_outliers -i "$func_raw_file" -o "$out_spike_file" --fd --thresh=0.5 --dummy=0
}

echo "Starting confound extraction (CSV-driven)..."
echo "============================================="

tail -n +2 "$CSV_FILE" | while IFS=',' read -r sub rest; do
    subject=$(echo "$sub" | sed 's/sub-//')
    
    if should_skip "$subject"; then
        echo "SKIP: sub-${subject} (already processed)"
        continue
    fi
    
    echo
    echo "=== Processing sub-${subject} ==="
    
    IFS=',' read -ra fields <<< "$rest"
    
    session_count=0
    for i in {1..5}; do
        if [[ -n "${fields[$i]}" && "${fields[$i]}" != " " ]]; then
            ((session_count++))
        fi
    done
    
    start_ses=$(get_session_start "$subject")
    echo "  Detected $session_count sessions (starting from session $start_ses)"
    
    for ((i=0; i<session_count; i++)); do
        ses_num=$((start_ses + i))
        ses=$(printf "%02d" $ses_num)
        echo "  --- Session ${ses_num} ---"
        
        func_dir="${RAW_DIR}/sub-${subject}/ses-${ses}/func"
        
        if [ ! -d "$func_dir" ]; then
            echo "    SKIP: No func directory"
            continue
        fi
        
        run_count=0
        for bold_file in "$func_dir"/sub-${subject}_ses-${ses}_task-${TASK}_run-*_bold.nii.gz; do
            [ ! -f "$bold_file" ] && continue
            
            run=$(basename "$bold_file" | sed -n 's/.*run-\([0-9]*\)_bold.nii.gz/\1/p')
            run_num=$((10#$run))
            
            extract_confounds_for_run "$subject" "$ses_num" "$run_num"
            ((run_count++))
        done
        
        if [ $run_count -eq 0 ]; then
            echo "    SKIP: No runs found"
        fi
    done
done

echo
echo "============================================="
echo "Confound extraction complete!"