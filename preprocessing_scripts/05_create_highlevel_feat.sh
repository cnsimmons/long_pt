#!/bin/bash
# Create high-level FSF files for session-level analysis

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
    
    # Add Face vs Word contrast (key for Figure 5)
    cat >> "$fsf_file" << EOF

# Additional contrasts for Figure 5
set fmri(ncon_real) 4

# Face vs Word contrast
set fmri(conpic_real.2) 1
set fmri(conname_real.2) "face_vs_word"
set fmri(con_real2.1) 1

# Word vs Face contrast  
set fmri(conpic_real.3) 1
set fmri(conname_real.3) "word_vs_face"
set fmri(con_real3.1) 1

# Objects vs Houses contrast
set fmri(conpic_real.4) 1
set fmri(conname_real.4) "objects_vs_houses"
set fmri(con_real4.1) 1
EOF
    
    echo "    Created: $fsf_file"
}

echo "Creating high-level FSF files..."

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

# UD ses-04: 2 runs only
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

echo "High-level FSF files created!"