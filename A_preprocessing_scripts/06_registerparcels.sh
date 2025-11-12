#!/bin/bash
# Register Harvard-Oxford ventral temporal parcels (CSV-driven, all subjects)

FSLDIR="/opt/fsl/6.0.3"
ATLAS="${FSLDIR}/data/atlases/HarvardOxford/HarvardOxford-cort-prob-2mm.nii.gz"
MNI_BRAIN="${FSLDIR}/data/standard/MNI152_T1_2mm_brain.nii.gz"
BASE_DIR="/user_data/csimmon2/long_pt"
CSV_FILE="/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv"

SKIP_SUBS=("004" "021" "108")
INDICES=(37 38 39)  # Fusiform parcels

declare -A SESSION_START
SESSION_START["010"]=2
SESSION_START["018"]=2
SESSION_START["068"]=2

should_skip() {
    for skip in "${SKIP_SUBS[@]}"; do
        [[ "$1" == "$skip" ]] && return 0
    done
    return 1
}

tail -n +2 "$CSV_FILE" | while IFS=',' read -r sub dob age1 age2 age3 age4 age5 group sex surgery_side intact_hemi rest; do
    subject=$(echo "$sub" | sed 's/sub-//')
    should_skip "$subject" && continue
    
    first_ses=$(printf "%02d" ${SESSION_START[$subject]:-1})
    anat_dir="${BASE_DIR}/sub-${subject}/ses-${first_ses}/anat"
    roi_dir="${BASE_DIR}/sub-${subject}/ses-${first_ses}/ROIs"
    subject_anat="${anat_dir}/sub-${subject}_ses-${first_ses}_T1w_brain.nii.gz"
    
    [ ! -f "$subject_anat" ] && continue
    
    echo "Processing sub-${subject} (${intact_hemi})..."
    
    mkdir -p ${roi_dir}
    temp_dir="${roi_dir}/temp"
    mkdir -p ${temp_dir}
    
    # Extract and combine parcels
    for idx in "${INDICES[@]}"; do
        fslroi ${ATLAS} ${temp_dir}/parcel_${idx}.nii.gz ${idx} 1
    done
    
    fslmaths ${temp_dir}/parcel_${INDICES[0]}.nii.gz ${temp_dir}/combined.nii.gz
    for idx in "${INDICES[@]:1}"; do
        fslmaths ${temp_dir}/combined.nii.gz -max ${temp_dir}/parcel_${idx}.nii.gz ${temp_dir}/combined.nii.gz
    done
    
    fslmaths ${temp_dir}/combined.nii.gz -thr 25 -bin ${temp_dir}/ventral_temporal_bilateral.nii.gz
    
    # Create hemisphere masks
    fslmaths ${MNI_BRAIN} -mul 0 -add 1 -roi 0 45 0 -1 0 -1 0 -1 ${temp_dir}/left_hemi.nii.gz
    fslmaths ${MNI_BRAIN} -mul 0 -add 1 -roi 46 45 0 -1 0 -1 0 -1 ${temp_dir}/right_hemi.nii.gz
    
    # Apply hemisphere mask based on group
    if [ "$intact_hemi" == "control" ]; then
        # Bilateral for controls
        cp ${temp_dir}/ventral_temporal_bilateral.nii.gz ${temp_dir}/ventral_temporal_mni.nii.gz
        hemi_label="bilateral"
    elif [ "$intact_hemi" == "left" ]; then
        fslmaths ${temp_dir}/ventral_temporal_bilateral.nii.gz -mul ${temp_dir}/left_hemi.nii.gz ${temp_dir}/ventral_temporal_mni.nii.gz
        hemi_label="l"
    else
        fslmaths ${temp_dir}/ventral_temporal_bilateral.nii.gz -mul ${temp_dir}/right_hemi.nii.gz ${temp_dir}/ventral_temporal_mni.nii.gz
        hemi_label="r"
    fi
    
    # MNI to subject transformation
    if [ ! -f "${anat_dir}/mni2ses${first_ses}.mat" ]; then
        flirt -in ${MNI_BRAIN} -ref ${subject_anat} -omat ${anat_dir}/mni2ses${first_ses}.mat \
              -bins 256 -cost corratio -searchrx -90 90 -searchry -90 90 -searchrz -90 90 -dof 12
    fi
    
    # Register to subject
    flirt -in ${temp_dir}/ventral_temporal_mni.nii.gz -ref ${subject_anat} \
          -out ${roi_dir}/${hemi_label}_ventral_temporal_mask.nii.gz \
          -applyxfm -init ${anat_dir}/mni2ses${first_ses}.mat -interp nearestneighbour
    
    rm -rf ${temp_dir}
    
    nvoxels=$(fslstats ${roi_dir}/${hemi_label}_ventral_temporal_mask.nii.gz -V | awk '{print $1}')
    echo "  Created ${hemi_label} mask: ${nvoxels} voxels"
done