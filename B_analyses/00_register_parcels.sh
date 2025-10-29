#!/bin/bash
# Register Julian parcels to subject anatomy

set -e

MNI_PARCEL_DIR="/user_data/csimmon2/git_repos/long_pt/roiParcels/julian_parcels"
BASE_DIR="/user_data/csimmon2/long_pt"
MNI_REF="/opt/fsl/6.0.3/data/standard/MNI152_T1_2mm_brain.nii.gz"

# Julian parcels (already L/R split)
PARCELS="lFFA rFFA lLO rLO lOFA rOFA lPFS rPFS lPPA rPPA lOPA rOPA"

for SUBJ in sub-004 sub-007 sub-021; do
    echo "============================================================"
    echo "${SUBJ}"
    echo "============================================================"
    
    ANAT_DIR="${BASE_DIR}/${SUBJ}/ses-01/anat"
    ROI_OUT_DIR="${BASE_DIR}/${SUBJ}/ses-01/derivatives/rois/parcels"
    mkdir -p ${ROI_OUT_DIR}
    
    ORIGINAL_ANAT="${ANAT_DIR}/${SUBJ}_ses-01_T1w_brain.nii.gz"
    MIRRORED_ANAT="${ANAT_DIR}/${SUBJ}_ses-01_T1w_brain_mirrored.nii.gz"
    MATRIX_FILE="${ANAT_DIR}/mni2anat.mat"
    
    # Create matrix once
    echo "Creating transformation matrix..."
    flirt -in ${MNI_REF} -ref ${MIRRORED_ANAT} -omat ${MATRIX_FILE} \
          -bins 256 -cost corratio -searchrx -90 90 -searchry -90 90 \
          -searchrz -90 90 -dof 12
    
    # Register each parcel
    for ROI in ${PARCELS}; do
        MNI_PARCEL="${MNI_PARCEL_DIR}/${ROI}.nii.gz"
        
        if [ ! -f "${MNI_PARCEL}" ]; then
            echo "  ${ROI}: NOT FOUND"
            continue
        fi
        
        OUTPUT="${ROI_OUT_DIR}/${ROI}.nii.gz"
        
        # Register and binarize
        flirt -in ${MNI_PARCEL} -ref ${ORIGINAL_ANAT} -out ${OUTPUT} \
              -applyxfm -init ${MATRIX_FILE} -interp trilinear
        fslmaths ${OUTPUT} -bin ${OUTPUT}
        
        # Report voxels
        VOX=$(fslstats ${OUTPUT} -V | awk '{print $1}')
        echo "  ${ROI}: ${VOX} voxels"
    done
    echo ""
done

echo "============================================================"
echo "COMPLETE"
echo "============================================================"