
### created to confirm functional scan conversion to neurological

# 1. Count converted files
find /user_data/csimmon2/long_pt -name "*bold.nii.gz" -type f | wc -l

# 2. Check orientations (sample each subject)
for sub in 004 007 021; do
    echo "sub-${sub}:"
    func=$(find /user_data/csimmon2/long_pt/sub-${sub} -name "*bold.nii.gz" | head -1)
    anat=$(find /user_data/csimmon2/long_pt/sub-${sub} -name "*T1w_brain.nii.gz" | head -1)
    echo "  Functional: $(fslorient -getorient $func)"
    echo "  Anatomical: $(fslorient -getorient $anat)"
done

# 3. Compare one file before/after
echo "Raw (should be RADIOLOGICAL):"
fslorient -getorient /lab_data/behrmannlab/hemi/Raw/sub-004/ses-01/func/sub-004_ses-01_task-loc_run-01_bold.nii.gz
echo "Converted (should be NEUROLOGICAL):"
fslorient -getorient /user_data/csimmon2/long_pt/sub-004/ses-01/func/sub-004_ses-01_task-loc_run-01_bold.nii.gz