#!/bin/bash
# update_confound_paths.sh - Update confoundev_files paths in existing FSF files

PROCESSED_DIR='/user_data/csimmon2/long_pt'
task='loc'
runs=("01" "02" "03")

echo "Updating confound paths in FSF files..."
echo "========================================"

# UD (sub-004)
echo "UD (sub-004):"
for ses in "01" "02" "03" "05" "06"; do
    for run in "${runs[@]}"; do
        fsf_file="${PROCESSED_DIR}/sub-004/ses-${ses}/derivatives/fsl/${task}/run-${run}/1stLevel.fsf"
        confound_file="${PROCESSED_DIR}/sub-004/ses-${ses}/derivatives/fsl/${task}/run-${run}/sub-004_ses-${ses}_task-${task}_run-${run}_bold_spikes.txt"
        
        if [ ! -f "$fsf_file" ]; then
            continue
        fi
        
        echo "  Updating ses-${ses} run-${run}..."
        sed -i "s|set confoundev_files(1) \".*\"|set confoundev_files(1) \"${confound_file}\"|g" "$fsf_file"
    done
done

# OT (sub-007)
echo ""
echo "OT (sub-007):"
for ses in "01" "03" "04" "05"; do
    for run in "${runs[@]}"; do
        if [[ ("$ses" == "03" || "$ses" == "04") && "$run" == "03" ]]; then
            continue
        fi
        
        fsf_file="${PROCESSED_DIR}/sub-007/ses-${ses}/derivatives/fsl/${task}/run-${run}/1stLevel.fsf"
        confound_file="${PROCESSED_DIR}/sub-007/ses-${ses}/derivatives/fsl/${task}/run-${run}/sub-007_ses-${ses}_task-${task}_run-${run}_bold_spikes.txt"
        
        if [ ! -f "$fsf_file" ]; then
            continue
        fi
        
        echo "  Updating ses-${ses} run-${run}..."
        sed -i "s|set confoundev_files(1) \".*\"|set confoundev_files(1) \"${confound_file}\"|g" "$fsf_file"
    done
done

# TC (sub-021)
echo ""
echo "TC (sub-021):"
for ses in "01" "02" "03"; do
    for run in "${runs[@]}"; do
        fsf_file="${PROCESSED_DIR}/sub-021/ses-${ses}/derivatives/fsl/${task}/run-${run}/1stLevel.fsf"
        confound_file="${PROCESSED_DIR}/sub-021/ses-${ses}/derivatives/fsl/${task}/run-${run}/sub-021_ses-${ses}_task-${task}_run-${run}_bold_spikes.txt"
        
        if [ ! -f "$fsf_file" ]; then
            continue
        fi
        
        echo "  Updating ses-${ses} run-${run}..."
        sed -i "s|set confoundev_files(1) \".*\"|set confoundev_files(1) \"${confound_file}\"|g" "$fsf_file"
    done
done

echo ""
echo "Confound paths updated!"