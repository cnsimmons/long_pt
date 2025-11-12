#!/bin/bash
# Register Harvard-Oxford atlas to subject space (CSV-driven)

BASE_DIR="/user_data/csimmon2/long_pt"
CSV_FILE="/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv"
FSLDIR="${FSLDIR:-/usr/local/fsl}"
ATLAS="${FSLDIR}/data/atlases/HarvardOxford/HarvardOxford-cort-maxprob-thr25-2mm.nii.gz"
MNI_TEMPLATE="${FSLDIR}/data/standard/MNI152_T1_2mm_brain.nii.gz"

SKIP_SUBS=("004" "021" "108")

declare -A SESSION_START
SESSION_START["010"]=2
SESSION_START["018"]=2

should_skip() {
    for skip in "${SKIP_SUBS[@]}"; do
        [[ "$1" == "$skip" ]] && return 0
    done
    return 1
}

echo "======================================"
echo "Registering Harvard-Oxford Atlas"
echo "======================================"

[ ! -f "${ATLAS}" ] && echo "ERROR: Atlas not found" && exit 1
[ ! -f "${MNI_TEMPLATE}" ] && echo "ERROR: MNI template not found" && exit 1

tail -n +2 "$CSV_FILE" | while IFS=',' read -r sub dob age1 age2 age3 age4 age5 group sex surgery_side intact_hemi rest; do
    subject=$(echo "$sub" | sed 's/sub-//')
    should_skip "$subject" && continue
    [[ "$intact_hemi" == "control" ]] && continue
    
    first_ses=$(printf "%02d" ${SESSION_START[$subject]:-1})
    anat_dir="${BASE_DIR}/sub-${subject}/ses-${first_ses}/anat"
    subject_anat="${anat_dir}/sub-${subject}_ses-${first_ses}_T1w_brain.nii.gz"
    
    [ ! -f "$subject_anat" ] && echo "  Skipping sub-${subject}: no anatomy" && continue
    
    echo "Processing sub-${subject}..."
    
    mni2subj_mat="${anat_dir}/mni2sub-${subject}_ses-${first_ses}.mat"
    atlas_output="${anat_dir}/HarvardOxford_cort_maxprob_sub-${subject}_ses-${first_ses}.nii.gz"
    
    if [ ! -f "${mni2subj_mat}" ]; then
        echo "  Step 1: Registering MNI to subject..."
        flirt -in "${MNI_TEMPLATE}" -ref "${subject_anat}" \
              -out "${anat_dir}/mni_in_subjspace_sub-${subject}_ses-${first_ses}.nii.gz" \
              -omat "${mni2subj_mat}" \
              -bins 256 -cost corratio \
              -searchrx -90 90 -searchry -90 90 -searchrz -90 90 -dof 12
        [ $? -eq 0 ] && echo "    ✓ Transform created" || echo "    ✗ Failed"
    else
        echo "  ✓ Transform exists"
    fi
    
    if [ ! -f "${atlas_output}" ]; then
        echo "  Step 2: Transforming atlas..."
        flirt -in "${ATLAS}" -ref "${subject_anat}" -out "${atlas_output}" \
              -init "${mni2subj_mat}" -applyxfm -interp nearestneighbour
        [ $? -eq 0 ] && echo "    ✓ Atlas created" || echo "    ✗ Failed"
    else
        echo "  ✓ Atlas exists"
    fi
    
    echo ""
done

echo "======================================"
echo "Complete!"
echo "======================================"