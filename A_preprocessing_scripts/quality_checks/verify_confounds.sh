#!/bin/bash
# verify_confounds.sh - CORRECTED filename

PROCESSED_DIR='/user_data/csimmon2/long_pt'
task='loc'
runs=("01" "02" "03")

echo "Verifying confound setup in FSF files..."
echo "========================================="

check_confounds() {
    local subject=$1
    local sessions=$2
    
    echo ""
    echo "${subject}:"
    
    for ses in $sessions; do
        for run in "${runs[@]}"; do
            if [[ "$subject" == "sub-007" && ("$ses" == "03" || "$ses" == "04") && "$run" == "03" ]]; then
                continue
            fi
            
            fsf_file="${PROCESSED_DIR}/${subject}/ses-${ses}/derivatives/fsl/${task}/run-${run}/1stLevel.fsf"
            
            if [ ! -f "$fsf_file" ]; then
                echo "  ses-${ses} run-${run}: ⚠️  FSF not found"
                continue
            fi
            
            confound_line=$(grep "set confoundev_files(1)" "$fsf_file")
            confound_path=$(echo "$confound_line" | sed 's/.*"\(.*\)".*/\1/')
            
            if [ -z "$confound_path" ]; then
                echo "  ses-${ses} run-${run}: ❌ No confound path in FSF"
                continue
            fi
            
            if [ -f "$confound_path" ]; then
                n_regressors=$(awk 'NF' "$confound_path" | wc -l)
                echo "  ses-${ses} run-${run}: ✓ ${n_regressors} regressors"
            else
                echo "  ses-${ses} run-${run}: ❌ File missing: $(basename $confound_path)"
            fi
        done
    done
}

check_confounds "sub-004" "01 02 03 05 06"
check_confounds "sub-007" "01 03 04 05"
check_confounds "sub-021" "01 02 03"

echo ""
echo "Verification complete!"