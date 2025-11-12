#!/bin/bash
# Register Harvard-Oxford ventral temporal parcels to subject native space (CSV-driven)

FSLDIR="/opt/fsl/6.0.3"
ATLAS="${FSLDIR}/data/atlases/HarvardOxford/HarvardOxford-cort-prob-2mm.nii.gz"
MNI_BRAIN="${FSLDIR}/data/standard/MNI152_T1_2mm_brain.nii.gz"
BASE_DIR="/user_data/csimmon2/long_pt"
CSV_FILE="/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv"

SKIP_SUBS=("004" "007" "021" "108")
INDICES=(37 38 39)

declare -A SESSION_START
SESSION_START["010"]=2
SESSION_START["018"]=2

should_skip() {
    local sub="$1"
    for skip in "${SKIP_SUBS[@]}"; do
        [[ "$sub" == "$skip" ]] && return 0
    done
    return 1
}

get_first_session() {
    local sub="$1"
    echo "${SESSION_START[$sub]:-1}"
}

tail -n +2 "$CSV_FILE" | while IFS=',' read -r sub dob age1 age2 age3 age4 age5 group sex surgery_side intact_hemi rest; do
    subject=$(echo "$sub" | sed 's/sub-//')
    
    should_skip "$subject" && continue
    
    # Skip controls (no intact_hemi)
    [[ "$intact_hemi" == "control" ]] && continue
    
    first_ses=$(get_first_session "$subject")
    ses=$(printf "%02d" $first_ses)
    
    echo "Processing sub-${subject} (intact: ${intact_hemi})..."
    
    anat_dir="${BASE_DIR}/sub-${subject}/ses-${ses}/anat"
    roi_dir="${BASE_DIR}/sub-${subject}/ses-${ses}/ROIs"
    subj_brain="${anat_dir}/sub-${subject}_ses-${ses}_T1w_brain.nii.gz"
    
    [ ! -f "$subj_brain" ] && echo "  Skipping: no brain" && continue
    
    mkdir -p ${roi_dir}
    temp_dir="${roi_dir}/temp"
    mkdir -p ${temp_dir}
    
    # Extract and combine parcels
    echo "  Extracting parcels..."
    for idx in "${INDICES[@]}"; do
        fslroi ${ATLAS} ${temp_dir}/parcel_${idx}.nii.gz ${idx} 1
    done
    
    fslmaths ${temp_dir}/parcel_${INDICES[0]}.nii.gz ${temp_dir}/combined.nii.gz
    for idx in "${INDICES[@]:1}"; do
        fslmaths ${temp_dir}/combined.nii.gz -max ${temp_dir}/parcel_${idx}.nii.gz ${temp_dir}/combined.nii.gz
    done
    
    fslmaths ${temp_dir}/combined.nii.gz -thr 25 -bin ${temp_dir}/ventral_temporal_bilateral.nii.gz
    
    # Hemisphere masks
    fslmaths ${MNI_BRAIN} -mul 0 -add 1 -roi 0 45 0 -1 0 -1 0 -1 ${temp_dir}/left_hemi.nii.gz
    fslmaths ${MNI_BRAIN} -mul 0 -add 1 -roi 46 45 0 -1 0 -1 0 -1 ${temp_dir}/right_hemi.nii.gz
    
    # Apply hemisphere mask
    if [ "$intact_hemi" == "left" ]; then
        fslmaths ${temp_dir}/ventral_temporal_bilateral.nii.gz -mul ${temp_dir}/left_hemi.nii.gz ${temp_dir}/ventral_temporal_mni.nii.gz
        hemi_label="l"
    else
        fslmaths ${temp_dir}/ventral_temporal_bilateral.nii.gz -mul ${temp_dir}/right_hemi.nii.gz ${temp_dir}/ventral_temporal_mni.nii.gz
        hemi_label="r"
    fi
    
    # MNI to ses transformation
    if [ ! -f "${anat_dir}/mni2ses${ses}.mat" ]; then
        flirt -in ${MNI_BRAIN} -ref ${subj_brain} -omat ${anat_dir}/mni2ses${ses}.mat \
              -bins 256 -cost corratio -searchrx -90 90 -searchry -90 90 -searchrz -90 90 -dof 12
    fi
    
    # Register to subject
    flirt -in ${temp_dir}/ventral_temporal_mni.nii.gz -ref ${subj_brain} \
          -out ${roi_dir}/${hemi_label}_ventral_temporal_mask.nii.gz \
          -applyxfm -init ${anat_dir}/mni2ses${ses}.mat -interp nearestneighbour
    
    rm -rf ${temp_dir}
    
    nvoxels=$(fslstats ${roi_dir}/${hemi_label}_ventral_temporal_mask.nii.gz -V | awk '{print $1}')
    echo "  Created ${hemi_label} mask: ${nvoxels} voxels"
done