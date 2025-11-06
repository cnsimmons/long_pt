# README!!!! This is not typically part of my pipeline - I don't know if this is just because of the data collection
#!/bin/bash
#
# Convert functional data from RADIOLOGICAL to NEUROLOGICAL orientation
# Copies from Raw to processed directory and fixes orientation
#

rawDir='/lab_data/behrmannlab/hemi/Raw'
procDir='/user_data/csimmon2/long_pt'

echo "Converting functional data orientation..."
echo "From: RADIOLOGICAL (Raw)"
echo "To: NEUROLOGICAL (processed)"
echo ""

# Function to convert functional data
convert_functional() {
    local sub="$1"
    local ses="$2"
    local run="$3"
    
    # Create output directory
    mkdir -p "${procDir}/sub-${sub}/ses-${ses}/func"
    
    # Define paths
    local input="${rawDir}/sub-${sub}/ses-${ses}/func/sub-${sub}_ses-${ses}_task-loc_run-${run}_bold.nii.gz"
    local output="${procDir}/sub-${sub}/ses-${ses}/func/sub-${sub}_ses-${ses}_task-loc_run-${run}_bold.nii.gz"
    
    # Check if input exists
    if [ ! -f "$input" ]; then
        echo "    WARNING: Input file not found: $input"
        return 1
    fi
    
    # Check if already converted
    if [ -f "$output" ]; then
        local current_orient=$(fslorient -getorient "$output")
        if [ "$current_orient" == "NEUROLOGICAL" ]; then
            echo "    ✓ Already converted: run-${run}"
            return 0
        fi
    fi
    
    # Copy file
    cp "$input" "$output"
    
    # Verify orientation before swap
    local orient_before=$(fslorient -getorient "$output")
    
    # Swap orientation
    fslorient -swaporient "$output"
    
    # Verify orientation after swap
    local orient_after=$(fslorient -getorient "$output")
    
    echo "    ✓ Converted run-${run}: ${orient_before} → ${orient_after}"
    
    if [ "$orient_after" != "NEUROLOGICAL" ]; then
        echo "    ERROR: Orientation conversion failed!"
        return 1
    fi
    
    return 0
}

# UD (sub-004): sessions 01,02,03,05,06
echo "UD (sub-004):"
for ses in 01 02 03 05 06 07; do
    echo "  Session ${ses}:"
    for run in 01 02 03; do
        convert_functional "004" "$ses" "$run"
    done
done

# OT (sub-007): sessions 01,03,04,05
echo ""
echo "OT (sub-007):"
for ses in 01 03 04 05; do
    echo "  Session ${ses}:"
    
    # ses-03 and ses-04 only have 2 runs
    if [[ "$ses" == "03" ]] || [[ "$ses" == "04" ]]; then
        for run in 01 02; do
            convert_functional "007" "$ses" "$run"
        done
    else
        for run in 01 02 03; do
            convert_functional "007" "$ses" "$run"
        done
    fi
done

# TC (sub-021): sessions 01,02,03
echo ""
echo "TC (sub-021):"
for ses in 01 02 03; do
    echo "  Session ${ses}:"
    for run in 01 02 03; do
        convert_functional "021" "$ses" "$run"
    done
done

echo ""
echo "Conversion complete!"
echo ""
echo "Verification - checking orientation of converted files:"
for sub in 004 007 021; do
    echo "sub-${sub}:"
    first_file=$(find "${procDir}/sub-${sub}" -name "*bold.nii.gz" -type f | head -1)
    if [ -f "$first_file" ]; then
        fslorient -getorient "$first_file"
    fi
done