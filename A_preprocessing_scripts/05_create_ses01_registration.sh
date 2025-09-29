#!/bin/bash
# Create first-session registration matrices
dataDir='/user_data/csimmon2/long_pt'

for sub in "004" "007" "021"; do
    # Get first session anatomy as reference
    ref_anat="$dataDir/sub-${sub}/ses-01/anat/sub-${sub}_ses-01_T1w_brain.nii.gz"
    
    # Register all other sessions to ses-01
    for ses_dir in $dataDir/sub-${sub}/ses-*/; do
        ses=$(basename "$ses_dir" | cut -d'-' -f2)
        if [ "$ses" != "01" ]; then
            input_anat="$dataDir/sub-${sub}/ses-${ses}/anat/sub-${sub}_ses-${ses}_T1w_brain.nii.gz"
            output_mat="$dataDir/sub-${sub}/ses-${ses}/anat/anat2ses01.mat"
            
            if [ -f "$input_anat" ]; then
                echo "Creating $output_mat"
                flirt -in "$input_anat" -ref "$ref_anat" -omat "$output_mat"
            fi
        fi
    done
done