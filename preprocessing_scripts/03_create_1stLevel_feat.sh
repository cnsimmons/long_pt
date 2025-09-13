#!/bin/bash
#
# Create FEAT .fsf files for long_pt project
# Corrected version with proper template variable handling
#

# Configuration
dataDir='/user_data/csimmon2/long_pt'
rawDataDir='/lab_data/behrmannlab/hemi/Raw'

# Template configuration
templateFSF="/lab_data/behrmannlab/vlad/ptoc/sub-004/ses-01/derivatives/fsl/loc/run-01/1stLevel.fsf"
templateSub="004"
templateSes="01"
templateRun="01"

# Check template exists
if [ ! -f "$templateFSF" ]; then
    echo "ERROR: Template FSF not found: $templateFSF"
    exit 1
fi

echo "Using template: $templateFSF"
echo ""

# Function to check if required files exist
check_files_exist() {
    local sub="$1"
    local ses="$2"
    local run="$3"
    
    # Check functional data
    local funcData="$rawDataDir/sub-${sub}/ses-${ses}/func/sub-${sub}_ses-${ses}_task-loc_run-${run}_bold.nii.gz"
    if [ ! -f "$funcData" ]; then
        return 1
    fi
    
    # Check timing files
    local covsDir="$dataDir/sub-${sub}/ses-${ses}/covs"
    if [ ! -d "$covsDir" ]; then
        return 1
    fi
    
    for condition in Face House Object Word Scramble; do
        local timing_file="$covsDir/catloc_${sub}_run-${run}_${condition}.txt"
        if [ ! -f "$timing_file" ]; then
            return 1
        fi
    done
    
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
    
    # Update functional data path
    local funcData="$rawDataDir/sub-${sub}/ses-${ses}/func/sub-${sub}_ses-${ses}_task-loc_run-${run}_bold.nii.gz"
    sed -i "s|set feat_files(1) \".*\"|set feat_files(1) \"$funcData\"|g" "$fsfFile"
    
    # Update timing file paths
    local covsDir="$dataDir/sub-${sub}/ses-${ses}/covs"
    sed -i "s|set fmri(custom1) \".*\"|set fmri(custom1) \"$covsDir/catloc_${sub}_run-${run}_Face.txt\"|g" "$fsfFile"
    sed -i "s|set fmri(custom2) \".*\"|set fmri(custom2) \"$covsDir/catloc_${sub}_run-${run}_House.txt\"|g" "$fsfFile"
    sed -i "s|set fmri(custom3) \".*\"|set fmri(custom3) \"$covsDir/catloc_${sub}_run-${run}_Object.txt\"|g" "$fsfFile"
    sed -i "s|set fmri(custom4) \".*\"|set fmri(custom4) \"$covsDir/catloc_${sub}_run-${run}_Word.txt\"|g" "$fsfFile"
    sed -i "s|set fmri(custom5) \".*\"|set fmri(custom5) \"$covsDir/catloc_${sub}_run-${run}_Scramble.txt\"|g" "$fsfFile"
    
    # Update structural image path
    local structImage="$rawDataDir/sub-${sub}/ses-${ses}/anat/sub-${sub}_ses-${ses}_T1w.nii.gz"
    sed -i "s|set highres_files(1) \".*\"|set highres_files(1) \"$structImage\"|g" "$fsfFile"
    
    # Update output directory
    sed -i "s|set fmri(outputdir) \".*\"|set fmri(outputdir) \"$outputDir/1stLevel\"|g" "$fsfFile"
    
    echo "      Created: $fsfFile"
}

# Subject and session configuration
runs=("01" "02" "03")

echo "Processing subjects with data validation..."

# TC (sub-004): sessions 01,02,03,05,06,07
echo "TC (sub-004):"
for ses in "01" "02" "03" "05" "06" "07"; do
    echo "  Session ${ses}:"
    for run in "${runs[@]}"; do
        echo "    Run ${run}:"
        if check_files_exist "004" "$ses" "$run"; then
            create_fsf "004" "$ses" "$run"
        else
            echo "      SKIPPING - missing required files"
        fi
    done
done

# UD (sub-007): sessions 01,03,04,05
echo ""
echo "UD (sub-007):"
for ses in "01" "03" "04" "05"; do
    echo "  Session ${ses}:"
    for run in "${runs[@]}"; do
        echo "    Run ${run}:"
        
        # ses-03 and ses-04 only have 2 runs
        if [[ ("$ses" == "03" || "$ses" == "04") && "$run" == "03" ]]; then
            echo "      SKIPPING - run-03 not available for ses-${ses}"
            continue
        fi
        
        if check_files_exist "007" "$ses" "$run"; then
            create_fsf "007" "$ses" "$run"
        else
            echo "      SKIPPING - missing required files"
        fi
    done
done

# OT (sub-021): sessions 01,02,03
echo ""
echo "OT (sub-021):"
for ses in "01" "02" "03"; do
    echo "  Session ${ses}:"
    for run in "${runs[@]}"; do
        echo "    Run ${run}:"
        if check_files_exist "021" "$ses" "$run"; then
            create_fsf "021" "$ses" "$run"
        else
            echo "      SKIPPING - missing required files"
        fi
    done
done

echo ""
echo "FSF file creation complete!"
echo ""
echo "Created FSF files:"
find "$dataDir" -name "1stLevel.fsf" -path "*/derivatives/fsl/loc/run-*" | wc -l
echo ""
echo "Clean any failed FEAT directories before re-running:"
echo "find $dataDir -name '1stLevel.feat' -type d | xargs rm -rf"ba