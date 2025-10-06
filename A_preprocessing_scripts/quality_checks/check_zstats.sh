#!/bin/bash
# Check for zstat13 and zstat14 existence across all subjects/sessions

echo "Checking for zstat13 and zstat14 files..."
echo ""

for sub in sub-004 sub-007 sub-021; do
    echo "=== ${sub} ==="
    
    if [ "$sub" == "sub-004" ]; then
        sessions="01 02 03 05 06"
    elif [ "$sub" == "sub-007" ]; then
        sessions="01 03 04"
    else
        sessions="01 02 03"
    fi
    
    for ses in $sessions; do
        echo "  ses-${ses}:"
        
        if [ "$sub" == "sub-007" ] && [ "$ses" == "03" -o "$ses" == "04" ]; then
            runs="01 02"
        else
            runs="01 02 03"
        fi
        
        for run in $runs; do
            stats_dir="/user_data/csimmon2/long_pt/${sub}/ses-${ses}/derivatives/fsl/loc/run-${run}/1stLevel.feat/stats"
            
            if [ -f "${stats_dir}/zstat13.nii.gz" ] && [ -f "${stats_dir}/zstat14.nii.gz" ]; then
                echo "    run-${run}: ✓ both exist"
            elif [ -f "${stats_dir}/zstat13.nii.gz" ]; then
                echo "    run-${run}: ⚠ only zstat13 exists"
            elif [ -f "${stats_dir}/zstat14.nii.gz" ]; then
                echo "    run-${run}: ⚠ only zstat14 exists"
            else
                echo "    run-${run}: ✗ neither exist"
            fi
        done
    done
    echo ""
done