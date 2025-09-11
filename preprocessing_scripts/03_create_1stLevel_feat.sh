#!/bin/bash
#
# Create FEAT .fsf files for long_pt project
# Generates first-level analysis files for all subjects/sessions/runs
#

# Configuration
dataDir='/user_data/csimmon2/long_pt'
rawDataDir='/lab_data/behrmannlab/hemi/Raw'

# Template configuration
templateFSF="/lab_data/behrmannlab/vlad/ptoc/sub-004/ses-01/derivatives/fsl/loc/run-01/1stLevel.fsf"

# Check template exists
if [ ! -f "$templateFSF" ]; then
    echo "ERROR: Template FSF not found: $templateFSF"
    echo "Looking for templates in other locations..."
    # Try alternative template locations
    for alt_template in "$dataDir/sub-004/ses-01/derivatives/fsl/loc/run-01/1stLevel.fsf" \
                       "$dataDir/sub-007/ses-01/derivatives/fsl/loc/run-01/1stLevel.fsf"; do
        if [ -f "$alt_template" ]; then
            templateFSF="$alt_template"
            echo "Using alternative template: $templateFSF"
            break
        fi
    done
    
    if [ ! -f "$templateFSF" ]; then
        echo "No template FSF found. Please run preprocessing first."
        exit 1
    fi
fi

echo "Using template: $templateFSF"
echo ""

# Function to check if required files exist
check_files_exist() {
    local sub="$1"
    local ses="$2"
    local run="$3"
    
    # Check functional data (in Raw directory)
    local funcData="$rawDataDir/sub-${sub}/ses-${ses}/func/sub-${sub}_ses-${ses}_task-loc_run-${run}_bold.nii.gz"
    if [ ! -f "$funcData" ]; then
        echo "      Missing functional data: $funcData"
        return 1
    fi
    
    # Check timing files (in processed directory)
    local covsDir="$dataDir/sub-${sub}/ses-${ses}/covs"
    if [ ! -d "$covsDir" ]; then
        echo "      Missing covs directory: $covsDir"
        return 1
    fi
    
    local missing_timing=0
    for condition in Face House Object Word Scramble; do
        local timing_file="$covsDir/catloc_${sub}_run-${run}_${condition}.txt"
        if [ ! -f "$timing_file" ]; then
            echo "      Missing timing file: $timing_file"
            missing_timing=1
        fi
    done
    
    if [ $missing_timing -eq 1 ]; then
        return 1
    fi
    
    return 0
}

# Function to create FSF file
create_fsf() {
    local sub="$1"
    local ses="$2"
    local run="$3"
    
    # Paths
    local outputDir="$dataDir/sub-${sub}/ses-${ses}/derivatives/fsl/loc/run-${run}"
    local fsfFile="$outputDir/1stLevel.fsf"
    
    # Create output directory
    mkdir -p "$outputDir"
    
    # Copy template
    cp "$templateFSF" "$fsfFile"
    
    # Update subject ID
    sed -i "s/sub-${templateSub}/sub-${sub}/g" "$fsfFile"
    sed -i "s/${templateSub}/${sub}/g" "$fsfFile"
    
    # Update session
    sed -i "s/ses-${templateSes}/ses-${ses}/g" "$fsfFile"
    
    # Update run
    sed -i "s/run-${templateRun}/run-${run}/g" "$fsfFile"
    sed -i "s/run${templateRun}/run${run}/g" "$fsfFile"
    sed -i "s/Run${templateRun}/Run${run}/g" "$fsfFile"
    
    # Update functional data path (point to Raw directory)
    local funcData="$rawDataDir/sub-${sub}/ses-${ses}/func/sub-${sub}_ses-${ses}_task-loc_run-${run}_bold.nii.gz"
    sed -i "s|set feat_files(1) \".*\"|set feat_files(1) \"$funcData\"|g" "$fsfFile"
    
    # Update timing file paths (point to processed covs directory)
    local covsDir="$dataDir/sub-${sub}/ses-${ses}/covs"
    sed -i "s|set fmri(custom1) \".*\"|set fmri(custom1) \"$covsDir/catloc_${sub}_run-${run}_Face.txt\"|g" "$fsfFile"
    sed -i "s|set fmri(custom2) \".*\"|set fmri(custom2) \"$covsDir/catloc_${sub}_run-${run}_House.txt\"|g" "$fsfFile"
    sed -i "s|set fmri(custom3) \".*\"|set fmri(custom3) \"$covsDir/catloc_${sub}_run-${run}_Object.txt\"|g" "$fsfFile"
    sed -i "s|set fmri(custom4) \".*\"|set fmri(custom4) \"$covsDir/catloc_${sub}_run-${run}_Word.txt\"|g" "$fsfFile"
    sed -i "s|set fmri(custom5) \".*\"|set fmri(custom5) \"$covsDir/catloc_${sub}_run-${run}_Scramble.txt\"|g" "$fsfFile"
    
    # Update structural image path - try both raw and processed locations
    local structImage="$rawDataDir/sub-${sub}/ses-${ses}/anat/sub-${sub}_ses-${ses}_T1w.nii.gz"
    if [ ! -f "$structImage" ]; then
        structImage="$dataDir/sub-${sub}/ses-${ses}/anat/sub-${sub}_ses-${ses}_T1w_brain.nii.gz"
    fi
    sed -i "s|set highres_files(1) \".*\"|set highres_files(1) \"$structImage\"|g" "$fsfFile"
    
    # Update output directory
    sed -i "s|set fmri(outputdir) \".*\"|set fmri(outputdir) \"$outputDir/1stLevel\"|g" "$fsfFile"
    
    echo "      Created ✓"
}

# Subject and session configuration
runs=("01" "02" "03")

###############################
# PROCESS EACH SUBJECT
###############################

# TC (sub-004): All 6 sessions
echo "Processing TC (sub-004)..."
for ses in "01" "02" "03" "05" "06" "07"; do
    echo "  Session ${ses}:"
    
    for run in "${runs[@]}"; do
        echo "    Run ${run}:"
        
        if ! check_files_exist "004" "$ses" "$run"; then
            echo "      SKIPPING - missing required files"
            continue
        fi
        
        create_fsf "004" "$ses" "$run"
    done
done

# UD (sub-007): Sessions 01, 04, 05
echo ""
echo "Processing UD (sub-007)..."
for ses in "01" "03" "04" "05"; do
    echo "  Session ${ses}:"
    
    for run in "${runs[@]}"; do
        echo "    Run ${run}:"
        
        # Special case: ses-04 only has 2 runs
        if [[ "$ses" == "04" && "$run" == "03" ]]; then
            echo "      SKIPPING - run-03 not available for ses-04"
            continue
        fi
        
        if ! check_files_exist "007" "$ses" "$run"; then
            echo "      SKIPPING - missing required files"
            continue
        fi
        
        create_fsf "007" "$ses" "$run"
    done
done

# OT (sub-021): All 3 sessions
echo ""
echo "Processing OT (sub-021)..."
for ses in "01" "02" "03"; do
    echo "  Session ${ses}:"
    
    for run in "${runs[@]}"; do
        echo "    Run ${run}:"
        
        if ! check_files_exist "021" "$ses" "$run"; then
            echo "      SKIPPING - missing required files"
            continue
        fi
        
        create_fsf "021" "$ses" "$run"
    done
done

echo ""
echo "=========================================="
echo "FSF file creation complete!"
echo ""
echo "Summary of created files:"
find "$dataDir" -name "1stLevel.fsf" -path "*/derivatives/fsl/loc/run-*" | sort

echo ""
echo "To test a single FSF file:"
echo "feat $dataDir/sub-004/ses-01/derivatives/fsl/loc/run-01/1stLevel.fsf"
echo ""
echo "To run all analyses, use the batch submission script."