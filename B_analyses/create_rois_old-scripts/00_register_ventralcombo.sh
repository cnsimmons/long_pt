#!/bin/bash
# Register and properly split ventral_visual_cortex

MNI_PARCEL="/user_data/csimmon2/git_repos/long_pt/roiParcels/ventral_visual_cortex.nii.gz"
BASE_DIR="/user_data/csimmon2/long_pt"
MNI_REF="/opt/fsl/6.0.3/data/standard/MNI152_T1_2mm_brain.nii.gz"

# Create MNI hemisphere masks
L_MNI_MASK="/tmp/MNI_L_mask.nii.gz"
R_MNI_MASK="/tmp/MNI_R_mask.nii.gz"

fslmaths ${MNI_REF} -bin /tmp/MNI_temp.nii.gz
fslroi /tmp/MNI_temp.nii.gz ${L_MNI_MASK} 0 45 0 -1 0 -1
fslroi /tmp/MNI_temp.nii.gz ${R_MNI_MASK} 45 46 0 -1 0 -1

for SUBJ in sub-004 sub-007 sub-021; do
    echo "Processing ${SUBJ}..."
    
    ANAT_DIR="${BASE_DIR}/${SUBJ}/ses-01/anat"
    ROI_DIR="${BASE_DIR}/${SUBJ}/ses-01/ROIs"
    
    ORIGINAL_ANAT="${ANAT_DIR}/${SUBJ}_ses-01_T1w_brain.nii.gz"
    MIRRORED_ANAT="${ANAT_DIR}/${SUBJ}_ses-01_T1w_brain_mirrored.nii.gz"
    MATRIX_FILE="${ANAT_DIR}/mni2anat.mat"
    
    # Matrix
    flirt -in ${MNI_REF} -ref ${MIRRORED_ANAT} -omat ${MATRIX_FILE} \
          -bins 256 -cost corratio -dof 12 > /dev/null 2>&1
    
    # Register full parcel
    FULL_PARCEL="${ROI_DIR}/ventral_temp.nii.gz"
    flirt -in ${MNI_PARCEL} -ref ${ORIGINAL_ANAT} -out ${FULL_PARCEL} \
          -applyxfm -init ${MATRIX_FILE} -interp trilinear > /dev/null 2>&1
    fslmaths ${FULL_PARCEL} -bin ${FULL_PARCEL}
    
    # Register hemisphere masks
    L_SUBJ_MASK="${ROI_DIR}/L_hemi_temp.nii.gz"
    R_SUBJ_MASK="${ROI_DIR}/R_hemi_temp.nii.gz"
    
    flirt -in ${L_MNI_MASK} -ref ${ORIGINAL_ANAT} -out ${L_SUBJ_MASK} \
          -applyxfm -init ${MATRIX_FILE} -interp nearestneighbour > /dev/null 2>&1
    flirt -in ${R_MNI_MASK} -ref ${ORIGINAL_ANAT} -out ${R_SUBJ_MASK} \
          -applyxfm -init ${MATRIX_FILE} -interp nearestneighbour > /dev/null 2>&1
    
    # Split by hemisphere
    fslmaths ${FULL_PARCEL} -mul ${L_SUBJ_MASK} ${ROI_DIR}/l_ventral_julian.nii.gz
    fslmaths ${FULL_PARCEL} -mul ${R_SUBJ_MASK} ${ROI_DIR}/r_ventral_julian.nii.gz
    
    # Determine which to use
    if [ "$SUBJ" == "sub-021" ]; then
        HEMI="r"
    else
        HEMI="l"
    fi
    
    cp ${ROI_DIR}/${HEMI}_ventral_julian.nii.gz ${ROI_DIR}/${HEMI}_VOTC_FG_OTS_mask.nii.gz
    
    VOX=$(fslstats ${ROI_DIR}/${HEMI}_VOTC_FG_OTS_mask.nii.gz -V | awk '{print $1}')
    echo "  ${HEMI}_VOTC_FG_OTS_mask.nii.gz: ${VOX} voxels"
    
    # Cleanup
    rm ${FULL_PARCEL} ${L_SUBJ_MASK} ${R_SUBJ_MASK}
done