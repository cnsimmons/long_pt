#!/bin/bash
# ------------------------------------------------------------------------
# FSL Script to Register MNI Parcels to Patient Anatomical Space
#
# This script ensures that for a patient (using a mirrored brain to avoid
# lesion bias), the correct reference image is used for both:
# 1. Creating the transformation matrix (MNI -> Mirrored Brain).
# 2. Applying the transformation (MNI Parcel -> Original Brain).
# ------------------------------------------------------------------------

# Exit immediately if any command fails
set -e

# --- 1. CONFIGURATION ---
# IMPORTANT: Paths are updated to match your specific execution environment.
SUBJ="sub-004"
ROI_NAME="LO" # CHANGED from 'rLO' to 'LO' based on file name in error log
GROUP="patient" # Set to "control" or "patient"

# Source Directory: Full path to the directory containing the MNI parcel file (LO.nii.gz)
MNI_PARCEL_DIR="/user_data/csimmon2/git_repos/long_pt/roiParcels"
# Subject Anatomical Directory (anat)
ANAT_DIR="/user_data/csimmon2/long_pt/${SUBJ}/ses-01/anat"
# Derivatives Directory: Output location for the registered ROIs
ROI_OUT_DIR="/user_data/csimmon2/long_pt/${SUBJ}/ses-01/derivatives/rois/parcels"

# FSL standard MNI template used for registration reference
# UPDATED PATH: Using the user-specified local MNI file.
MNI_REF="/user_data/csimmon2/git_repos/long_pt/roiParcels/MNI152_T1_2mm_brain.nii.gz"

# Define the subject's brain files
ORIGINAL_ANAT="${ANAT_DIR}/${SUBJ}_ses-01_T1w_brain.nii.gz"
MIRRORED_ANAT="${ANAT_DIR}/${SUBJ}_ses-01_T1w_brain_mirrored.nii.gz"
MNI_INPUT_PARCEL="${MNI_PARCEL_DIR}/${ROI_NAME}.nii.gz"
OUTPUT_PARCEL="${ROI_OUT_DIR}/${ROI_NAME}_in_subj.nii.gz"
MATRIX_FILE="${ANAT_DIR}/mni2anat.mat"

# Create output directory if it doesn't exist
mkdir -p ${ROI_OUT_DIR}

echo "--- Starting Registration for ${SUBJ} (${ROI_NAME}) ---"

# --- 2. VALIDATION (NEW STEP) ---
if [ ! -f "$MNI_REF" ]; then
    echo "FATAL ERROR: MNI Reference file not found at $MNI_REF"
    echo "Please ensure the path is correct."
    exit 1
fi

if [ ! -f "$ORIGINAL_ANAT" ]; then
    echo "FATAL ERROR: Subject anatomical brain file not found at $ORIGINAL_ANAT"
    exit 1
fi

if [ ! -f "$MNI_INPUT_PARCEL" ]; then
    echo "FATAL ERROR: Input MNI parcel file not found at $MNI_INPUT_PARCEL"
    exit 1
fi


# --- 3. STAGE 1: CREATE THE TRANSFORMATION MATRIX (MNI -> ANATOMY) ---

# The reference image for matrix calculation depends on the subject group.
if [ "$GROUP" == "patient" ]; then
    # For patients, use the mirrored brain as the target reference
    TARGET_ANAT="${MIRRORED_ANAT}"
    # Also check if the mirrored file exists, as it's critical for patient processing
    if [ ! -f "$TARGET_ANAT" ]; then
        echo "FATAL ERROR: Mirrored anatomical brain file not found at $TARGET_ANAT"
        echo "This file must be created before running parcel registration for patients."
        exit 1
    fi
    echo "Patient detected. Using MIRRORED brain for matrix calculation."
elif [ "$GROUP" == "control" ]; then
    # For controls, use the original brain as the target reference
    TARGET_ANAT="${ORIGINAL_ANAT}"
    echo "Control detected. Using ORIGINAL brain for matrix calculation."
else
    echo "Error: GROUP must be 'patient' or 'control'."
    exit 1
fi

echo "STAGE 1: Creating/Verifying ${MATRIX_FILE} using target ${TARGET_ANAT}"
# This FLIRT step computes the transformation matrix (MNI -> ANAT/MIRROR)
# The '-in' and '-ref' are swapped compared to the 'anat2stand' call,
# ensuring the matrix transforms the MNI parcel into the subject's space.
flirt -in ${MNI_REF} \
      -ref ${TARGET_ANAT} \
      -omat ${MATRIX_FILE} \
      -bins 256 -cost corratio -searchrx -90 90 -searchry -90 90 -searchrz -90 90 -dof 12
echo "Matrix creation complete."


# --- 4. STAGE 2: APPLY MATRIX TO PARCEL (MNI PARCEL -> ORIGINAL ANATOMY) ---

# The reference image for the final parcel output MUST be the ORIGINAL anatomical brain.
echo "STAGE 2: Resampling parcel ${ROI_NAME} into ${ORIGINAL_ANAT} space."

# This FLIRT step applies the matrix to the parcel.
flirt -in ${MNI_INPUT_PARCEL} \
      -ref ${ORIGINAL_ANAT} \
      -out ${OUTPUT_PARCEL} \
      -applyxfm -init ${MATRIX_FILE} \
      -interp trilinear
echo "FLIRT resampling complete. Output: ${OUTPUT_PARCEL}"

# --- 5. STAGE 3: BINARIZE THE RESAMPLED PARCEL ---

# Binarize to ensure the final ROI consists only of 0s and 1s,
# compensating for "fuzzy" values introduced by trilinear interpolation.
echo "STAGE 3: Binarizing the final parcel."
fslmaths ${OUTPUT_PARCEL} -bin ${OUTPUT_PARCEL}

echo "--- Registration and Binarization Complete! ---"
