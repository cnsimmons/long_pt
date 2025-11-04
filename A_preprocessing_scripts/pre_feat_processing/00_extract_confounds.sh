#!/bin/bash
# extract_confounds.sh

module load fsl-6.0.3

RAW_DIR='/lab_data/behrmannlab/hemi/Raw'
PROCESSED_DIR='/user_data/csimmon2/long_pt'
task='loc'
runs=("01" "02" "03")

echo "Starting confound extraction..."

# UD (sub-004)
echo "UD (sub-004):"
for ses in "01" "02" "03" "05" "06"; do
    echo "  Session ${ses}:"
    for run in "${runs[@]}"; do
        func_raw_file="${RAW_DIR}/sub-004/ses-${ses}/func/sub-004_ses-${ses}_task-${task}_run-${run}_bold.nii.gz"
        out_dir="${PROCESSED_DIR}/sub-004/ses-${ses}/derivatives/fsl/${task}/run-${run}"
        out_spike_file="${out_dir}/sub-004_ses-${ses}_task-${task}_run-${run}_bold_spikes.txt"

        if [ ! -f "$func_raw_file" ]; then
            echo "    SKIP Run ${run}"
            continue
        fi
        
        echo "    Processing Run ${run}..."
        mkdir -p "$out_dir"
        fsl_motion_outliers -i "$func_raw_file" -o "$out_spike_file" --fd --thresh=0.5 --dummy=0
    done
done

# OT (sub-007)
echo ""
echo "OT (sub-007):"
for ses in "01" "03" "04" "05"; do
    echo "  Session ${ses}:"
    for run in "${runs[@]}"; do
        if [[ ("$ses" == "03" || "$ses" == "04") && "$run" == "03" ]]; then
            echo "    SKIP Run ${run}"
            continue
        fi

        func_raw_file="${RAW_DIR}/sub-007/ses-${ses}/func/sub-007_ses-${ses}_task-${task}_run-${run}_bold.nii.gz"
        out_dir="${PROCESSED_DIR}/sub-007/ses-${ses}/derivatives/fsl/${task}/run-${run}"
        out_spike_file="${out_dir}/sub-007_ses-${ses}_task-${task}_run-${run}_bold_spikes.txt"
        
        if [ ! -f "$func_raw_file" ]; then
            echo "    SKIP Run ${run}"
            continue
        fi

        echo "    Processing Run ${run}..."
        mkdir -p "$out_dir"
        fsl_motion_outliers -i "$func_raw_file" -o "$out_spike_file" --fd --thresh=0.5 --dummy=0
    done
done

# TC (sub-021)
echo ""
echo "TC (sub-021):"
for ses in "01" "02" "03"; do
    echo "  Session ${ses}:"
    for run in "${runs[@]}"; do
        func_raw_file="${RAW_DIR}/sub-021/ses-${ses}/func/sub-021_ses-${ses}_task-${task}_run-${run}_bold.nii.gz"
        out_dir="${PROCESSED_DIR}/sub-021/ses-${ses}/derivatives/fsl/${task}/run-${run}"
        out_spike_file="${out_dir}/sub-021_ses-${ses}_task-${task}_run-${run}_bold_spikes.txt"

        if [ ! -f "$func_raw_file" ]; then
            echo "    SKIP Run ${run}"
            continue
        fi
        
        echo "    Processing Run ${run}..."
        mkdir -p "$out_dir"
        fsl_motion_outliers -i "$func_raw_file" -o "$out_spike_file" --fd --thresh=0.5 --dummy=0
    done
done

echo ""
echo "Confound extraction complete!"