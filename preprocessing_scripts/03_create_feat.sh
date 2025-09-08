## N.P. ses 1 for 004 & 007 subjects has been run for PTOC, this script will create .fsf for the other sessions
## previously known as the ChangeOut file
## N.P. ses 1 for 004 & 007 subjects has been run for PTOC, this script will create .fsf for the other sessions
## previously known as the ChangeOut file

#!/bin/bash
#
# ChangeOut script for long_pt project - adapted from your original
# Takes working FSF template and propagates to all needed sessions/runs
#

# Template configuration (using your working FSF)
ogSub="007"
ogSes="01" 
ogRun="03"
dataDir='/lab_data/behrmannlab/claire/long_pt'

# Template FSF location
ogDir="$dataDir/sub-${ogSub}/ses-${ogSes}/derivatives/fsl"
templateFSF="$ogDir/loc/run-${ogRun}/1stLevel.fsf"

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
    
    # Raw data is in the hemi/Raw directory
    local rawDataDir="/lab_data/behrmannlab/hemi/Raw"
    
    # Define paths to check in raw data location
    local funcData="$rawDataDir/sub-${sub}/ses-${ses}/func/sub-${sub}_ses-${ses}_task-loc_run-${run}_bold.nii.gz"
    local timingDir="$rawDataDir/sub-${sub}/ses-${ses}/func"
    
    # Special case: sub-007 ses-03 timing files are actually in ses-04
    if [[ "$sub" == "007" && "$ses" == "03" ]]; then
        timingDir="$rawDataDir/sub-${sub}/ses-04/func"
    fi
    
    # Check if functional data exists
    if [ ! -f "$funcData" ]; then
        echo "      Missing functional data: $funcData"
        return 1
    fi
    
    # Check if timing directory exists
    if [ ! -d "$timingDir" ]; then
        echo "      Missing timing directory: $timingDir"
        return 1
    fi
    
    # Check for timing files (BIDS format: sub-XXX_ses-XX_task-loc_run-XX_events.tsv)
    local timingFilePattern
    if [[ "$sub" == "007" && "$ses" == "03" ]]; then
        timingFilePattern="sub-${sub}_ses-04_task-loc_run-${run}_events.tsv"
    else
        timingFilePattern="sub-${sub}_ses-${ses}_task-loc_run-${run}_events.tsv"
    fi
    
    local timingFiles=$(find "$timingDir" -name "$timingFilePattern" 2>/dev/null | wc -l)
    if [ "$timingFiles" -eq 0 ]; then
        echo "      Missing timing files for run ${run} in: $timingDir"
        echo "      Looking for: $timingFilePattern"
        return 1
    fi
    
    return 0
}

# Runs to process
runs=("01" "02" "03")
cond="loc"

###############################
# SUBJECTS AND SESSIONS TO PROCESS
###############################

# sub-004 (UD): Need ses-02, 03, 05, 06 (already have ses-01)
echo "Processing sub-004 (UD)..."
for ses in "02" "03" "05" "06"; do
    subjDir="$dataDir/sub-004/ses-${ses}/derivatives/fsl"
    runDir="$subjDir/${cond}"
    
    echo "  Session ${ses}:"
    
    for r in "${runs[@]}"; do
        echo "    Run ${r}:"
        
        # Check if required files exist
        if ! check_files_exist "004" "$ses" "$r"; then
            echo "      SKIPPING - missing required files"
            continue
        fi
        
        # Create run directory
        mkdir -p "$runDir/run-${r}"
        
        # Copy FSF from template
        cp "$templateFSF" "$runDir/run-${r}/1stLevel.fsf"
        
        # Replace subject
        sed -i "s/sub-${ogSub}/sub-004/g" "$runDir/run-${r}/1stLevel.fsf"
        sed -i "s/${ogSub}/004/g" "$runDir/run-${r}/1stLevel.fsf"
        
        # Replace session
        sed -i "s/ses-${ogSes}/ses-${ses}/g" "$runDir/run-${r}/1stLevel.fsf"
        
        # Replace run
        sed -i "s/run-${ogRun}/run-${r}/g" "$runDir/run-${r}/1stLevel.fsf"
        sed -i "s/run${ogRun}/run${r}/g" "$runDir/run-${r}/1stLevel.fsf"
        sed -i "s/Run${ogRun}/Run${r}/g" "$runDir/run-${r}/1stLevel.fsf"
        
        echo "      Created ✓"
    done
done

# sub-007 (TC): Need ses-03, 04 (already have ses-01)  
echo ""
echo "Processing sub-007 (TC)..."
for ses in "03" "04"; do
    subjDir="$dataDir/sub-007/ses-${ses}/derivatives/fsl"
    runDir="$subjDir/${cond}"
    
    echo "  Session ${ses}:"
    
    for r in "${runs[@]}"; do
        echo "    Run ${r}:"
        
        # Check if required files exist
        if ! check_files_exist "007" "$ses" "$r"; then
            echo "      SKIPPING - missing required files"
            continue
        fi
        
        # Create run directory
        mkdir -p "$runDir/run-${r}"
        
        # Copy FSF from template
        cp "$templateFSF" "$runDir/run-${r}/1stLevel.fsf"
        
        # Replace session
        sed -i "s/ses-${ogSes}/ses-${ses}/g" "$runDir/run-${r}/1stLevel.fsf"
        
        # Replace run
        sed -i "s/run-${ogRun}/run-${r}/g" "$runDir/run-${r}/1stLevel.fsf"
        sed -i "s/run${ogRun}/run${r}/g" "$runDir/run-${r}/1stLevel.fsf"
        sed -i "s/Run${ogRun}/Run${r}/g" "$runDir/run-${r}/1stLevel.fsf"
        
        # Special case: Handle timing file paths for ses-03 (timing files are in ses-04)
        if [[ "$ses" == "03" ]]; then
            sed -i "s|/timing/loc_007_run-${r}_|/ses-04/loc_007_run-${r}_|g" "$runDir/run-${r}/1stLevel.fsf"
            sed -i "s|/ses-03/ses-04/|/ses-04/|g" "$runDir/run-${r}/1stLevel.fsf"
        fi
        
        echo "      Created ✓"
    done
done

# sub-021 (OT): Need ses-01, 02, 03 (all new)
echo ""
echo "Processing sub-021 (OT)..."
for ses in "01" "02" "03"; do
    subjDir="$dataDir/sub-021/ses-${ses}/derivatives/fsl"
    runDir="$subjDir/${cond}"
    
    echo "  Session ${ses}:"
    
    for r in "${runs[@]}"; do
        echo "    Run ${r}:"
        
        # Check if required files exist
        if ! check_files_exist "021" "$ses" "$r"; then
            echo "      SKIPPING - missing required files"
            continue
        fi
        
        # Create run directory
        mkdir -p "$runDir/run-${r}"
        
        # Copy FSF from template
        cp "$templateFSF" "$runDir/run-${r}/1stLevel.fsf"
        
        # Replace subject
        sed -i "s/sub-${ogSub}/sub-021/g" "$runDir/run-${r}/1stLevel.fsf"
        sed -i "s/${ogSub}/021/g" "$runDir/run-${r}/1stLevel.fsf"
        
        # Replace session
        sed -i "s/ses-${ogSes}/ses-${ses}/g" "$runDir/run-${r}/1stLevel.fsf"
        
        # Replace run
        sed -i "s/run-${ogRun}/run-${r}/g" "$runDir/run-${r}/1stLevel.fsf"
        sed -i "s/run${ogRun}/run${r}/g" "$runDir/run-${r}/1stLevel.fsf"
        sed -i "s/Run${ogRun}/Run${r}/g" "$runDir/run-${r}/1stLevel.fsf"
        
        echo "      Created ✓"
    done
done

echo ""
echo "=========================================="
echo "FSF files created! Ready for FEAT submission."
echo ""
echo "To test one FSF:"
echo "feat $dataDir/sub-004/ses-02/derivatives/fsl/loc/run-01/1stLevel.fsf"