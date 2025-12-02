# Quick fix: Run the timing conversion manually for sub-079 ses-02
'''
RAW_DIR='/lab_data/behrmannlab/hemi/Raw'
PROCESSED_DIR='/user_data/csimmon2/long_pt'
TASK="loc"
subject="079"
session_num=2
ses="02"

# Create output directory (using 'timing' to match the conversion script)
timing_dir="$PROCESSED_DIR/sub-${subject}/ses-${ses}/timing"
mkdir -p "$timing_dir"

echo "Converting sub-079 ses-02 timing files..."

# Convert all 3 runs
for run_num in 1 2 3; do
    run=$(printf "%02d" $run_num)
    events_file="$RAW_DIR/sub-${subject}/ses-${ses}/func/sub-${subject}_ses-${ses}_task-${TASK}_run-${run}_events.tsv"
    
    echo "  Processing run-${run}..."
    
    for condition in Face House Object Word Scramble; do
        output_file="$timing_dir/catloc_${subject}_run-${run}_${condition}.txt"
        awk -v cond="$condition" 'BEGIN{FS="\t"} NR>1 && $3==cond {print $1, $2, 1}' "$events_file" > "$output_file"
        
        if [ -s "$output_file" ]; then
            echo "    ✓ Created: catloc_${subject}_run-${run}_${condition}.txt"
        else
            echo "    ✗ Failed: catloc_${subject}_run-${run}_${condition}.txt"
            rm -f "$output_file"
        fi
    done
done

echo ""
echo "Checking results:"
ls -lh "$timing_dir"
'''

# After running this script, remember to verify the output files in the timing directory.

# Create FSF files for sub-079 ses-02 only

dataDir='/user_data/csimmon2/long_pt'
rawDataDir='/lab_data/behrmannlab/hemi/Raw'
templateFSF="/user_data/csimmon2/long_pt/sub-004/ses-01/derivatives/fsl/loc/run-01/1stLevel.feat/design.fsf"

sub="079"
ses="02"

for run in "01" "02" "03"; do
    echo "Creating FSF for run-${run}..."
    
    outputDir="$dataDir/sub-${sub}/ses-${ses}/derivatives/fsl/loc/run-${run}"
    fsfFile="$outputDir/1stLevel.fsf"
    
    mkdir -p "$outputDir"
    cp "$templateFSF" "$fsfFile"
    
    # Replace subject/session/run
    sed -i "s/sub-004/sub-${sub}/g" "$fsfFile"
    sed -i "s/004/${sub}/g" "$fsfFile"
    sed -i "s/ses-01/ses-${ses}/g" "$fsfFile"
    sed -i "s/run-01/run-${run}/g" "$fsfFile"
    sed -i "s/run01/run${run}/g" "$fsfFile"
    
    # Update paths
    funcData="$rawDataDir/sub-${sub}/ses-${ses}/func/sub-${sub}_ses-${ses}_task-loc_run-${run}_bold.nii.gz"
    sed -i "s|set feat_files(1) \".*\"|set feat_files(1) \"$funcData\"|g" "$fsfFile"
    
    covsDir="$dataDir/sub-${sub}/ses-${ses}/covs"
    sed -i "s|set fmri(custom1) \".*\"|set fmri(custom1) \"$covsDir/catloc_${sub}_run-${run}_Face.txt\"|g" "$fsfFile"
    sed -i "s|set fmri(custom2) \".*\"|set fmri(custom2) \"$covsDir/catloc_${sub}_run-${run}_House.txt\"|g" "$fsfFile"
    sed -i "s|set fmri(custom3) \".*\"|set fmri(custom3) \"$covsDir/catloc_${sub}_run-${run}_Object.txt\"|g" "$fsfFile"
    sed -i "s|set fmri(custom4) \".*\"|set fmri(custom4) \"$covsDir/catloc_${sub}_run-${run}_Word.txt\"|g" "$fsfFile"
    sed -i "s|set fmri(custom5) \".*\"|set fmri(custom5) \"$covsDir/catloc_${sub}_run-${run}_Scramble.txt\"|g" "$fsfFile"
    
    structImage="$dataDir/sub-${sub}/ses-${ses}/anat/sub-${sub}_ses-${ses}_T1w_brain.nii.gz"
    sed -i "s|set highres_files(1) \".*\"|set highres_files(1) \"$structImage\"|g" "$fsfFile"
    
    sed -i "s|/lab_data/behrmannlab/vlad/hemispace|$dataDir|g" "$fsfFile"
    sed -i "s|T1w\.nii\.gz|T1w_brain.nii.gz|g" "$fsfFile"
    sed -i "s|set fmri(outputdir) \".*\"|set fmri(outputdir) \"$outputDir/1stLevel\"|g" "$fsfFile"
    
    echo "  ✓ Created: $fsfFile"
done

echo ""
echo "Verifying FSF files..."
ls -lh /user_data/csimmon2/long_pt/sub-079/ses-02/derivatives/fsl/loc/run-*/1stLevel.fsf