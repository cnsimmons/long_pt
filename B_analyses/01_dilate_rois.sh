#!/bin/bash
# Dilate all ROI masks

BASE_DIR="/user_data/csimmon2/long_pt"

for SUBJ in sub-004 sub-007 sub-021; do
    echo "Dilating ${SUBJ}..."
    
    ROI_DIR="${BASE_DIR}/${SUBJ}/ses-01/ROIs"
    
    # Dilate fusiform
    if [ "$SUBJ" == "sub-021" ]; then
        HEMI="r"
    else
        HEMI="l"
    fi
    
    fslmaths ${ROI_DIR}/${HEMI}_fusiform_mask.nii.gz -dilM \
             ${ROI_DIR}/${HEMI}_fusiform_mask_dilated.nii.gz
    
    fslmaths ${ROI_DIR}/${HEMI}_LO_PPA_mask.nii.gz -dilM \
             ${ROI_DIR}/${HEMI}_LO_PPA_mask_dilated.nii.gz
    
    # Check sizes
    echo "  Fusiform:"
    fslstats ${ROI_DIR}/${HEMI}_fusiform_mask_dilated.nii.gz -V
    echo "  LO+PPA:"
    fslstats ${ROI_DIR}/${HEMI}_LO_PPA_mask_dilated.nii.gz -V
done

# Dilation options:
#-dilM              # 1 iteration (~1mm)
#-dilM -dilM        # 2 iterations (~2-3mm)
#-dilM -dilM -dilM  # 3 iterations (~3-5mm)