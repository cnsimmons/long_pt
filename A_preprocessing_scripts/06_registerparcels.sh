#!/bin/bash
# Register Harvard-Oxford ventral temporal parcels to subject native space - CORRECTED

FSLDIR="/opt/fsl/6.0.3"
ATLAS="${FSLDIR}/data/atlases/HarvardOxford/HarvardOxford-cort-prob-2mm.nii.gz"
MNI_BRAIN="${FSLDIR}/data/standard/MNI152_T1_2mm_brain.nii.gz"
BASE_DIR="/user_data/csimmon2/long_pt"

# Bilateral ventral temporal indices
INDICES=(37 38 39)  # Posterior fusiform, occipital fusiform, occipital fusiform gyrus

# Subject info with intact hemisphere
declare -A INTACT_HEMI
INTACT_HEMI["sub-004"]="left"
INTACT_HEMI["sub-007"]="left"   # CORRECTED: sub-007 has RIGHT resection, LEFT intact
INTACT_HEMI["sub-021"]="left"

for subject in sub-004 sub-007 sub-021; do
    echo "Processing ${subject}..."
    
    anat_dir="${BASE_DIR}/${subject}/ses-01/anat"
    roi_dir="${BASE_DIR}/${subject}/ses-01/ROIs"
    mkdir -p ${roi_dir}
    
    subj_brain="${anat_dir}/${subject}_ses-01_T1w_brain.nii.gz"
    hemi=${INTACT_HEMI[${subject}]}
    temp_dir="${roi_dir}/temp"
    mkdir -p ${temp_dir}
    
    # Extract and combine parcels
    echo "  Extracting ventral temporal parcels..."
    for idx in "${INDICES[@]}"; do
        fslroi ${ATLAS} ${temp_dir}/parcel_${idx}.nii.gz ${idx} 1
    done
    
    # Combine parcels
    fslmaths ${temp_dir}/parcel_${INDICES[0]}.nii.gz ${temp_dir}/combined.nii.gz
    for idx in "${INDICES[@]:1}"; do
        fslmaths ${temp_dir}/combined.nii.gz -max ${temp_dir}/parcel_${idx}.nii.gz ${temp_dir}/combined.nii.gz
    done
    
    # Threshold and binarize
    fslmaths ${temp_dir}/combined.nii.gz -thr 25 -bin ${temp_dir}/ventral_temporal_bilateral.nii.gz
    
    # Create hemisphere masks in MNI space
    # X dimension is 91 voxels, center at voxel 45 (0-indexed 44)
    fslmaths ${MNI_BRAIN} -mul 0 -add 1 -roi 0 45 0 -1 0 -1 0 -1 ${temp_dir}/left_hemi.nii.gz
    fslmaths ${MNI_BRAIN} -mul 0 -add 1 -roi 46 45 0 -1 0 -1 0 -1 ${temp_dir}/right_hemi.nii.gz
    
    # Apply hemisphere mask
    if [ "$hemi" == "left" ]; then
        fslmaths ${temp_dir}/ventral_temporal_bilateral.nii.gz -mul ${temp_dir}/left_hemi.nii.gz ${temp_dir}/ventral_temporal_mni.nii.gz
        hemi_label="l"
    else
        fslmaths ${temp_dir}/ventral_temporal_bilateral.nii.gz -mul ${temp_dir}/right_hemi.nii.gz ${temp_dir}/ventral_temporal_mni.nii.gz
        hemi_label="r"
    fi
    
    # Create MNI to ses-01 transformation
    if [ ! -f "${anat_dir}/mni2ses01.mat" ]; then
        flirt -in ${MNI_BRAIN} -ref ${subj_brain} \
              -omat ${anat_dir}/mni2ses01.mat \
              -bins 256 -cost corratio \
              -searchrx -90 90 -searchry -90 90 -searchrz -90 90 \
              -dof 12
    fi
    
    # Register to subject space
    flirt -in ${temp_dir}/ventral_temporal_mni.nii.gz \
          -ref ${subj_brain} \
          -out ${roi_dir}/${hemi_label}_ventral_temporal_mask.nii.gz \
          -applyxfm -init ${anat_dir}/mni2ses01.mat \
          -interp nearestneighbour
    
    # Clean up
    rm -rf ${temp_dir}
    
    # Count voxels
    nvoxels=$(fslstats ${roi_dir}/${hemi_label}_ventral_temporal_mask.nii.gz -V | awk '{print $1}')
    echo "  Created ${hemi_label} ventral temporal mask: ${nvoxels} voxels"
done

echo "Done!"