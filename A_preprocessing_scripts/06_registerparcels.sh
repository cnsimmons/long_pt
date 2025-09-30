#!/bin/bash
# Register Harvard-Oxford fusiform parcels to subject native space (ses-01)

# Paths
MNI_BRAIN="/opt/fsl/6.0.3/data/standard/MNI152_T1_2mm_brain.nii.gz"
ATLAS_DIR="/opt/fsl/6.0.3/data/atlases/HarvardOxford"
BASE_DIR="/user_data/csimmon2/long_pt"

# Subject info with intact hemisphere
declare -A INTACT_HEMI
INTACT_HEMI["sub-004"]="left"
INTACT_HEMI["sub-007"]="right"  # UD
INTACT_HEMI["sub-021"]="left"

for subject in sub-004 sub-007 sub-021; do
    echo "Processing ${subject}..."
    
    # Paths for this subject
    anat_dir="${BASE_DIR}/${subject}/ses-01/anat"
    roi_dir="${BASE_DIR}/${subject}/ses-01/ROIs"
    mkdir -p ${roi_dir}
    
    # Subject's ses-01 brain
    subj_brain="${anat_dir}/${subject}_ses-01_T1w_brain.nii.gz"
    
    # Create transformation: MNI → subject ses-01 native space
    flirt -in ${MNI_BRAIN} \
          -ref ${subj_brain} \
          -omat ${anat_dir}/mni2ses01.mat \
          -bins 256 -cost corratio \
          -searchrx -90 90 -searchry -90 90 -searchrz -90 90 \
          -dof 12
    
    # Get intact hemisphere
    hemi=${INTACT_HEMI[${subject}]}
    
    # Extract fusiform from Harvard-Oxford atlas
    # Left fusiform is index 9, Right fusiform is index 48 in cortical atlas
    if [ "$hemi" == "left" ]; then
        atlas_idx=9
        hemi_label="l"
    else
        atlas_idx=48
        hemi_label="r"
    fi
    
    # Register fusiform parcel to subject space
    flirt -in ${ATLAS_DIR}/HarvardOxford-cort-maxprob-thr25-2mm.nii.gz \
          -ref ${subj_brain} \
          -out ${roi_dir}/${hemi_label}fusiform_registered.nii.gz \
          -applyxfm -init ${anat_dir}/mni2ses01.mat \
          -interp nearestneighbour
    
    # Threshold to get only fusiform (value = atlas_idx)
    fslmaths ${roi_dir}/${hemi_label}fusiform_registered.nii.gz \
             -thr ${atlas_idx} -uthr ${atlas_idx} -bin \
             ${roi_dir}/${hemi_label}fusiform_mask.nii.gz
    
    echo "  Created ${hemi_label} fusiform mask for ${subject}"
done

echo "Registration complete!"