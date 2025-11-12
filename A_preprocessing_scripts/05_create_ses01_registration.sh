#!/bin/bash
# Create first-session registration matrices (CSV-driven)

dataDir='/user_data/csimmon2/long_pt'
CSV_FILE='/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv'

SKIP_SUBS=("004" "007" "021" "108")

declare -A SESSION_START
SESSION_START["010"]=2
SESSION_START["018"]=2

should_skip() {
    local sub="$1"
    for skip in "${SKIP_SUBS[@]}"; do
        [[ "$sub" == "$skip" ]] && return 0
    done
    return 1
}

get_first_session() {
    local sub="$1"
    echo "${SESSION_START[$sub]:-1}"
}

tail -n +2 "$CSV_FILE" | while IFS=',' read -r sub rest; do
    subject=$(echo "$sub" | sed 's/sub-//')
    
    should_skip "$subject" && continue
    
    first_ses=$(get_first_session "$subject")
    ref_anat="$dataDir/sub-${subject}/ses-$(printf "%02d" $first_ses)/anat/sub-${subject}_ses-$(printf "%02d" $first_ses)_T1w_brain.nii.gz"
    
    [ ! -f "$ref_anat" ] && continue
    
    echo "=== sub-${subject} (reference: ses-$(printf "%02d" $first_ses)) ==="
    
    for ses_dir in $dataDir/sub-${subject}/ses-*/; do
        ses=$(basename "$ses_dir" | sed 's/ses-//')
        ses_num=$((10#$ses))
        
        [ $ses_num -eq $first_ses ] && continue
        
        input_anat="$dataDir/sub-${subject}/ses-${ses}/anat/sub-${subject}_ses-${ses}_T1w_brain.nii.gz"
        output_mat="$dataDir/sub-${subject}/ses-${ses}/anat/anat2ses$(printf "%02d" $first_ses).mat"
        
        if [ -f "$input_anat" ]; then
            echo "  Creating ses-${ses} -> ses-$(printf "%02d" $first_ses) matrix"
            flirt -in "$input_anat" -ref "$ref_anat" -omat "$output_mat"
        fi
    done
done