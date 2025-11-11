#!/bin/bash
#
# Create FEAT .fsf files for long_pt project (CSV-driven)
# DO not run without correcting templateFSF!
#

# Configuration
dataDir='/user_data/csimmon2/long_pt'
rawDataDir='/lab_data/behrmannlab/hemi/Raw'
CSV_FILE='/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv'

# Template configuration
templateFSF="/user_data/csimmon2/long_pt/sub-004/ses-01/derivatives/fsl/loc/run-01/1stLevel.feat/design.fsf"
templateSub="004"
templateSes="01"
templateRun="01"

# Subjects to skip (already processed)
SKIP_SUBS=("004" "007" "021" '108')

# Special session mappings
declare -A SESSION_START
SESSION_START["010"]=2
SESSION_START["018"]=2

echo "Using template: $templateFSF"
echo ""

# Function to check if subject should be skipped
should_skip() {
    local sub="$1"
    for skip in "${SKIP_SUBS[@]}"; do
        if [[ "$sub" == "$skip" ]]; then
            return 0
        fi
    done
    return 1
}

# Function to get starting session for a subject
get_session_start() {
    local sub="$1"
    echo "${SESSION_START[$sub]:-1}"
}

# Function to check if required files exist
check_files_exist() {
    local sub="$1"
    local ses="$2"
    local run="$3"
    
    # Check functional data (in Raw)
    local funcData="$rawDataDir/sub-${sub}/ses-${ses}/func/sub-${sub}_ses-${ses}_task-loc_run-${run}_bold.nii.gz"
    if [ ! -f "$funcData" ]; then
        return 1
    fi
    
    # Check timing files (in long_pt as covs)
    local covsDir="$dataDir/sub-${sub}/ses-${ses}/timing"
    if [ ! -d "$covsDir" ]; then
        return 1
    fi
    
    for condition in Face House Object Word Scramble; do
        local timing_file="$covsDir/catloc_${sub}_run-${run}_${condition}.txt"
        if [ ! -f "$timing_file" ]; then
            return 1
        fi
    done
    
    # Check structural image (in long_pt)
    local structImage="$dataDir/sub-${sub}/ses-${ses}/anat/sub-${sub}_ses-${ses}_T1w_brain.nii.gz"
    if [ ! -f "$structImage" ]; then
        echo "      WARNING: Structural image not found: $structImage"
        return 1
    fi
    
    return 0
}

# Function to create FSF file
create_fsf() {
    local sub="$1"
    local ses="$2"
    local run="$3"
    
    local outputDir="$dataDir/sub-${sub}/ses-${ses}/derivatives/fsl/loc/run-${run}"
    local fsfFile="$outputDir/1stLevel.fsf"
    
    # Create output directory
    mkdir -p "$outputDir"
    
    # Remove existing FSF to avoid duplicates
    [ -f "$fsfFile" ] && rm "$fsfFile"
    
    # Copy template
    cp "$templateFSF" "$fsfFile"
    
    # Update paths with proper template variable substitution
    sed -i "s/sub-${templateSub}/sub-${sub}/g" "$fsfFile"
    sed -i "s/${templateSub}/${sub}/g" "$fsfFile"
    sed -i "s/ses-${templateSes}/ses-${ses}/g" "$fsfFile"
    sed -i "s/run-${templateRun}/run-${run}/g" "$fsfFile"
    sed -i "s/run${templateRun}/run${run}/g" "$fsfFile"
    sed -i "s/Run${templateRun}/Run${run}/g" "$fsfFile"
    
    # Update functional data path (from Raw)
    local funcData="$rawDataDir/sub-${sub}/ses-${ses}/func/sub-${sub}_ses-${ses}_task-loc_run-${run}_bold.nii.gz"
    sed -i "s|set feat_files(1) \".*\"|set feat_files(1) \"$funcData\"|g" "$fsfFile"
    
    # Update timing file paths (from long_pt covs dir)
    local covsDir="$dataDir/sub-${sub}/ses-${ses}/timing"
    sed -i "s|set fmri(custom1) \".*\"|set fmri(custom1) \"$covsDir/catloc_${sub}_run-${run}_Face.txt\"|g" "$fsfFile"
    sed -i "s|set fmri(custom2) \".*\"|set fmri(custom2) \"$covsDir/catloc_${sub}_run-${run}_House.txt\"|g" "$fsfFile"
    sed -i "s|set fmri(custom3) \".*\"|set fmri(custom3) \"$covsDir/catloc_${sub}_run-${run}_Object.txt\"|g" "$fsfFile"
    sed -i "s|set fmri(custom4) \".*\"|set fmri(custom4) \"$covsDir/catloc_${sub}_run-${run}_Word.txt\"|g" "$fsfFile"
    sed -i "s|set fmri(custom5) \".*\"|set fmri(custom5) \"$covsDir/catloc_${sub}_run-${run}_Scramble.txt\"|g" "$fsfFile"
    
    # Update structural image path
    local structImage="$dataDir/sub-${sub}/ses-${ses}/anat/sub-${sub}_ses-${ses}_T1w_brain.nii.gz"
    sed -i "s|set highres_files(1) \".*\"|set highres_files(1) \"$structImage\"|g" "$fsfFile"
    
    # Update standard space template paths
    sed -i "s|/lab_data/behrmannlab/vlad/hemispace|$dataDir|g" "$fsfFile"
    
    # Handle T1w vs T1w_brain
    sed -i "s|T1w\.nii\.gz|T1w_brain.nii.gz|g" "$fsfFile"
    
    # Update output directory
    sed -i "s|set fmri(outputdir) \".*\"|set fmri(outputdir) \"$outputDir/1stLevel\"|g" "$fsfFile"
    
    echo "      Created: $fsfFile"
}

# Main processing loop
echo "Processing subjects with data validation (CSV-driven)..."
echo ""

tail -n +2 "$CSV_FILE" | while IFS=',' read -r sub rest; do
    subject=$(echo "$sub" | sed 's/sub-//')
    
    if should_skip "$subject"; then
        echo "SKIP: sub-${subject} (already processed)"
        continue
    fi
    
    echo "=== Processing sub-${subject} ==="
    
    # Count sessions from CSV
    IFS=',' read -ra fields <<< "$rest"
    session_count=0
    for i in {1..5}; do
        if [[ -n "${fields[$i]}" && "${fields[$i]}" != " " ]]; then
            ((session_count++))
        fi
    done
    
    start_ses=$(get_session_start "$subject")
    
    for ((i=0; i<session_count; i++)); do
        ses_num=$((start_ses + i))
        ses=$(printf "%02d" $ses_num)
        
        echo "  Session ${ses}:"
        
        # Auto-detect runs from filesystem
        func_dir="$rawDataDir/sub-${subject}/ses-${ses}/func"
        
        if [ ! -d "$func_dir" ]; then
            echo "    SKIP: No func directory"
            continue
        fi
        
        for bold_file in "$func_dir"/sub-${subject}_ses-${ses}_task-loc_run-*_bold.nii.gz; do
            [ ! -f "$bold_file" ] && continue
            
            run=$(basename "$bold_file" | sed -n 's/.*run-\([0-9]*\)_bold.nii.gz/\1/p')
            
            echo "    Run ${run}:"
            if check_files_exist "$subject" "$ses" "$run"; then
                create_fsf "$subject" "$ses" "$run"
            else
                echo "      SKIPPING - missing required files"
            fi
        done
    done
    
    echo ""
done

echo "FSF file creation complete!"
echo ""
echo "Created FSF files:"
find "$dataDir" -name "1stLevel.fsf" -path "*/derivatives/fsl/loc/run-*" | wc -l
echo ""
echo "Clean any failed FEAT directories before re-running:"
echo "find $dataDir -name '1stLevel.feat' -type d | xargs rm -rf"