## N.P. ses 1 for 004 & 007 subjects has been run for PTOC, this script will create .fsf for the other sessions
## previously known as the ChangeOut file

#!/bin/bash
#
# ChangeOut script for long_pt project - adapted from your original
# Takes working FSF template and propagates to all needed sessions/runs

#!/bin/bash
#
# Create FEAT .fsf files for long_pt project
# Generates first-level analysis files for all subjects/sessions/runs
#

# Configuration
dataDir='/user_data/csimmon2/long_pt'
rawDataDir='/lab_data/behrmannlab/hemi/Raw'

# Template configuration
templateSub="007"
templateSes="01" 
templateRun="03"
templateFSF="$dataDir/sub-${templateSub}/ses-${templateSes}/derivatives/fsl/loc/run-${templateRun}/1stLevel.fsf"

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
    
    # Check structural image (in processed directory)
    local structImage="$dataDir/sub-${sub}/ses-${ses}/anat/sub-${sub}_ses-${ses}_T1w_brain.nii.gz"
    if [ ! -f "$structImage" ]; then
        echo "      Missing structural image: $structImage"
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
    
    # Update structural image path (point to processed anat directory)
    local structImage="$dataDir/sub-${sub}/ses-${ses}/anat/sub-${sub}_ses-${ses}_T1w_brain.nii.gz"
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

# sub-004 (UD): Need ses-02, 03, 05, 06 (already have ses-01)
echo "Processing sub-004 (UD)..."
for ses in "02" "03" "05" "06"; do
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

# sub-007 (TC): Need ses-03, 04 (already have ses-01)  
echo ""
echo "Processing sub-007 (TC)..."
for ses in "03" "04"; do
    echo "  Session ${ses}:"
    
    for run in "${runs[@]}"; do
        echo "    Run ${run}:"
        
        # Special case: ses-03 uses timing from ses-04, but may not have functional data for all runs
        if [[ "$ses" == "03" ]]; then
            # For ses-03, check if functional data exists first
            funcData="$rawDataDir/sub-007/ses-${ses}/func/sub-007_ses-${ses}_task-loc_run-${run}_bold.nii.gz"
            if [ ! -f "$funcData" ]; then
                echo "      SKIPPING - no functional data for ses-03 run-${run}"
                continue
            fi
        fi
        
        if ! check_files_exist "007" "$ses" "$run"; then
            echo "      SKIPPING - missing required files"
            continue
        fi
        
        create_fsf "007" "$ses" "$run"
    done
done

# sub-021 (OT): Need ses-01, 02, 03 (all new)
echo ""
echo "Processing sub-021 (OT)..."
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
echo "feat $dataDir/sub-004/ses-02/derivatives/fsl/loc/run-01/1stLevel.fsf"
echo ""
echo "To run all analyses, use the batch submission script." 