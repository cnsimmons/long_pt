#!/bin/bash
# Fixed CSV reading for the correct column structure

set -e

BASE_DIR="/user_data/csimmon2/long_pt"
FS_DIR="/lab_data/behrmannlab/hemi/FS"
CSV_FILE="/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv"

echo "============================================================"
echo "DIRECT DK PARCELLATION EXTRACTION (FIXED CSV READING)"
echo "============================================================"

# Read CSV with correct column positions
tail -n +2 "$CSV_FILE" | while IFS=',' read -r sub dob age1 age2 age3 age4 age5 group sex surgery_side intact_hemi loc otc scanner pre_post patient rest; do
    
    # Only process patients
    if [[ "$patient" != "1" ]]; then
        continue
    fi
    
    SUBJECT="$sub"
    HEMISPHERE="$intact_hemi"
    
    echo "Processing: $SUBJECT ($HEMISPHERE hemisphere, patient=$patient)"
    
    # Handle special session starts
    case "$SUBJECT" in
        "sub-010"|"sub-018"|"sub-068") FIRST_SES="02";;
        *) FIRST_SES="01";;
    esac
    
    echo ""
    echo "============================================================"
    echo "$SUBJECT ($HEMISPHERE hemisphere) - DIRECT METHOD"
    echo "============================================================"
    
    # Paths
    FS_APARC="$FS_DIR/${SUBJECT}_ses-${FIRST_SES}/mri/aparc+aseg.mgz"
    OUTPUT_DIR="$BASE_DIR/$SUBJECT/ses-$FIRST_SES/ROIs"
    TEMP_DK="/tmp/dk_native_${SUBJECT}.nii.gz"
    
    mkdir -p "$OUTPUT_DIR"
    
    if [ ! -f "$FS_APARC" ]; then
        echo "❌ FreeSurfer data not found: $FS_APARC"
        continue
    fi
    
    # Direct FreeSurfer conversion
    echo "Converting FreeSurfer DK parcellation..."
    mri_convert "$FS_APARC" "$TEMP_DK" --out_orientation LAS
    echo "✓ Conversion complete"
    
    # Extract parcels
    python3 << EOF
import nibabel as nib
import numpy as np

dk_img = nib.load('$TEMP_DK')
dk_data = dk_img.get_fdata()

print(f"DK atlas shape: {dk_data.shape}")

if '$HEMISPHERE' == 'left':
    parcels = {'l_fusiform': 1007, 'l_lateraloccipital': 1011, 'l_parahippocampal': 1016, 'l_inferiortemporal': 1009, 'l_middletemporal': 1015, 'l_lingual': 1013, 'l_isthmuscingulate': 1010}
else:
    parcels = {'r_fusiform': 2007, 'r_lateraloccipital': 2011, 'r_parahippocampal': 2016, 'r_inferiortemporal': 2009, 'r_middletemporal': 2015, 'r_lingual': 2013, 'r_isthmuscingulate': 2010}

for name, label in parcels.items():
    mask = dk_data == label
    n_voxels = int(np.sum(mask))
    
    if n_voxels > 0:
        mask_img = nib.Nifti1Image(mask.astype(float), dk_img.affine)
        nib.save(mask_img, f'$OUTPUT_DIR/{name}_mask.nii.gz')
        
        coords = np.where(mask)
        center = nib.affines.apply_affine(dk_img.affine, [np.mean(coords[i]) for i in range(3)])
        hemi_check = "✓" if (('$HEMISPHERE' == 'left' and center[0] < 0) or ('$HEMISPHERE' == 'right' and center[0] > 0)) else "❌"
        
        print(f"  {hemi_check} {name}: {n_voxels:4d} voxels at ({center[0]:5.1f}, {center[1]:5.1f}, {center[2]:5.1f})")
    else:
        print(f"  ⚠️  {name}: Not found")
EOF
    
    rm -f "$TEMP_DK"
    
done

echo ""
echo "============================================================"
echo "EXTRACTION COMPLETE"
echo "============================================================"