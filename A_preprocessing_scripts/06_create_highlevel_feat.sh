#!/bin/bash
# Create high-level FSF files for session-level analysis
# UPDATED: Uses first-session registration instead of MNI space

dataDir='/user_data/csimmon2/long_pt'
templateFSF="/lab_data/behrmannlab/vlad/ptoc/sub-004/ses-01/derivatives/fsl/loc/HighLevel.fsf"

# Check template exists
if [ ! -f "$templateFSF" ]; then
    echo "ERROR: Template high-level FSF not found: $templateFSF"
    exit 1
fi

create_highlevel_fsf() {
    local sub="$1"
    local ses="$2"
    local runs=("${!3}")
    
    echo "  Creating high-level FSF for ses-${ses}"
    
    session_dir="$dataDir/sub-${sub}/ses-${ses}"
    fsf_file="$session_dir/derivatives/fsl/loc/HighLevel.fsf"
    
    mkdir -p "$(dirname "$fsf_file")"
    
    # Copy template
    cp "$templateFSF" "$fsf_file"
    
    # Update paths and session info
    sed -i "s|/lab_data/behrmannlab/vlad/ptoc|$dataDir|g" "$fsf_file"
    sed -i "s/sub-004/sub-${sub}/g" "$fsf_file"
    sed -i "s/ses-01/ses-${ses}/g" "$fsf_file"
    
    # CRITICAL: Update standard space registration to use first-session anatomy instead of MNI
    ses01_anat="$dataDir/sub-${sub}/ses-01/anat/sub-${sub}_ses-01_T1w_brain.nii.gz"
    sed -i "s|set fmri(regstandard) \".*\"|set fmri(regstandard) \"$ses01_anat\"|g" "$fsf_file"
    
    # Also update any other MNI template references to first-session space
    sed -i "s|/opt/fsl/.*/MNI152.*brain|$ses01_anat|g" "$fsf_file"
    sed -i "s|/usr/share/fsl/.*/MNI152.*brain|$ses01_anat|g" "$fsf_file"
    
    # Update number of inputs
    local num_runs=${#runs[@]}
    sed -i "s/set fmri(multiple) 3/set fmri(multiple) $num_runs/g" "$fsf_file"
    sed -i "s/set fmri(npts) 3/set fmri(npts) $num_runs/g" "$fsf_file"
    
    # Update FEAT directory paths
    for i in "${!runs[@]}"; do
        run_num=$((i + 1))
        run="${runs[i]}"
        feat_dir="$session_dir/derivatives/fsl/loc/run-${run}/1stLevel.feat"
        sed -i "s|set feat_files($run_num) \".*\"|set feat_files($run_num) \"$feat_dir\"|g" "$fsf_file"
    done
    
    # Remove extra feat_files if fewer runs
    if [ $num_runs -lt 3 ]; then
        for ((i=num_runs+1; i<=3; i++)); do
            sed -i "/set feat_files($i)/d" "$fsf_file"
        done
    fi
    
    echo "    Created: $fsf_file"
    echo "    Using first-session anatomy: $ses01_anat"
}

echo "Creating high-level FSF files for first-session registration..."

# TC (sub-004)
echo "TC (sub-004):"
for ses in "01" "02" "03" "05" "06" "07"; do
    runs=("01" "02" "03")
    create_highlevel_fsf "004" "$ses" runs[@]
done

# UD (sub-007)
echo "UD (sub-007):"
for ses in "01" "05"; do
    runs=("01" "02" "03")
    create_highlevel_fsf "007" "$ses" runs[@]
done

# UD ses-03: 2 runs only
runs=("01" "02")
create_highlevel_fsf "007" "03" runs[@]

# UD ses-04: 2 runs only
runs=("01" "02")
create_highlevel_fsf "007" "04" runs[@]

# OT (sub-021)
echo "OT (sub-021):"
for ses in "01" "02" "03"; do
    runs=("01" "02" "03")
    create_highlevel_fsf "021" "$ses" runs[@]
done

echo ""
echo "High-level FSF files created for first-session registration!"
echo "All analyses will be registered to ses-01 anatomy instead of MNI space"
echo ""
echo "Next steps:"
echo "1. Run high-level FEAT with updated FSF files"
echo "2. Update 06_highLevel.py script for first-session registration"