#!/bin/bash
# register_ho_atlas.sh (CORRECTED)
# Register Harvard-Oxford atlas FROM MNI space TO subject ses-01 anatomical space

BASE_DIR="/user_data/csimmon2/long_pt"
FSLDIR="${FSLDIR:-/usr/local/fsl}"
ATLAS="${FSLDIR}/data/atlases/HarvardOxford/HarvardOxford-cort-maxprob-thr25-2mm.nii.gz"
MNI_TEMPLATE="${FSLDIR}/data/standard/MNI152_T1_2mm_brain.nii.gz"

echo "======================================"
echo "Registering Harvard-Oxford Atlas to Subject Space"
echo "======================================"
echo "Atlas: ${ATLAS}"
echo "MNI Template: ${MNI_TEMPLATE}"
echo ""

# Check files exist
if [ ! -f "${ATLAS}" ]; then
    echo "ERROR: Harvard-Oxford atlas not found at ${ATLAS}"
    exit 1
fi

if [ ! -f "${MNI_TEMPLATE}" ]; then
    echo "ERROR: MNI template not found at ${MNI_TEMPLATE}"
    exit 1
fi

# Process each subject
for sub in sub-004 sub-007 sub-021; do
    echo "Processing ${sub}..."
    
    ses="ses-01"
    anat_dir="${BASE_DIR}/${sub}/${ses}/anat"
    
    # Check anatomical exists
    subject_anat="${anat_dir}/${sub}_${ses}_T1w_brain.nii.gz"
    if [ ! -f "${subject_anat}" ]; then
        echo "  ERROR: Anatomical not found: ${subject_anat}"
        continue
    fi
    
    # Output paths
    mni2subj_mat="${anat_dir}/mni2${sub}_${ses}.mat"
    atlas_output="${anat_dir}/HarvardOxford_cort_maxprob_${sub}_${ses}.nii.gz"
    
    # Step 1: Register MNI template to subject anatomical
    if [ ! -f "${mni2subj_mat}" ]; then
        echo "  Step 1: Registering MNI template to subject anatomy..."
        flirt \
            -in "${MNI_TEMPLATE}" \
            -ref "${subject_anat}" \
            -out "${anat_dir}/mni_in_subjspace_${sub}_${ses}.nii.gz" \
            -omat "${mni2subj_mat}" \
            -bins 256 \
            -cost corratio \
            -searchrx -90 90 \
            -searchry -90 90 \
            -searchrz -90 90 \
            -dof 12
        
        if [ $? -eq 0 ]; then
            echo "    ✓ Created MNI-to-subject transform"
        else
            echo "    ✗ Failed to register MNI to subject"
            continue
        fi
    else
        echo "  ✓ MNI-to-subject transform exists"
    fi
    
    # Step 2: Apply transform to atlas
    if [ ! -f "${atlas_output}" ]; then
        echo "  Step 2: Applying transform to Harvard-Oxford atlas..."
        flirt \
            -in "${ATLAS}" \
            -ref "${subject_anat}" \
            -out "${atlas_output}" \
            -init "${mni2subj_mat}" \
            -applyxfm \
            -interp nearestneighbour
        
        if [ $? -eq 0 ]; then
            echo "    ✓ Created atlas in subject space: ${atlas_output}"
        else
            echo "    ✗ Failed to transform atlas"
            continue
        fi
    else
        echo "  ✓ Atlas already in subject space"
    fi
    
    echo ""
done

echo "======================================"
echo "Atlas registration complete!"
echo "======================================"
echo ""
echo "Verify registration quality by checking:"
echo "  - Atlas overlays correctly on subject anatomy"
echo "  - Ventral temporal regions align with anatomical landmarks"