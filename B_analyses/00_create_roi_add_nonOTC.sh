#!/bin/bash
# Add resected hemisphere parcels for nonOTC patients only
set -e

CSV_FILE="/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv"

echo "============================================================"
echo "ADDING RESECTED HEMISPHERE PARCELS FOR nonOTC PATIENTS"
echo "============================================================"

# Process only nonOTC patients from CSV
tail -n +2 "$CSV_FILE" | while IFS=',' read -r subject_id dob age1 age2 age3 age4 age5 group sex surgery_side intact_hemi loc otc scanner pre_post patient rest; do
    
    # Skip header row
    if [[ "$subject_id" == "sub" ]]; then
        continue
    fi
    
    # Only process nonOTC patients
    if [[ "$group" != "nonOTC" ]] || [[ "$patient" != "1" ]]; then
        continue
    fi
    
    SUBJECT="$subject_id"
    
    # Handle special session starts
    case "$SUBJECT" in
        "sub-010"|"sub-018"|"sub-068") FIRST_SES="02";;
        *) FIRST_SES="01";;
    esac
    
    echo "🔄 nonOTC $SUBJECT: Adding RESECTED $surgery_side hemisphere"
    
    FS_APARC="/lab_data/behrmannlab/hemi/FS/${SUBJECT}_ses-${FIRST_SES}/mri/aparc+aseg.mgz"
    OUTPUT_DIR="/user_data/csimmon2/long_pt/$SUBJECT/ses-$FIRST_SES/ROIs"
    TEMP_DK="/tmp/dk_native_${SUBJECT}.nii.gz"
    
    mkdir -p "$OUTPUT_DIR"
    
    if [ ! -f "$FS_APARC" ]; then
        echo "❌ FreeSurfer data not found for $SUBJECT"
        continue
    fi
    
    # Determine resected hemisphere
    if [[ "$surgery_side" == "left" ]]; then
        RESECTED_HEMI="l"
    elif [[ "$surgery_side" == "right" ]]; then
        RESECTED_HEMI="r"
    else
        echo "⚠️ Unknown surgery side: $surgery_side, skipping"
        continue
    fi
    
    # Check if resected hemisphere parcels already exist
    SAMPLE_PARCEL="$OUTPUT_DIR/${RESECTED_HEMI}_fusiform_mask.nii.gz"
    if [[ -f "$SAMPLE_PARCEL" ]]; then
        echo "  ✅ Resected hemisphere parcels already exist, skipping"
        continue
    fi
    
    # Convert FreeSurfer data
    echo "  Converting FreeSurfer DK parcellation..."
    mri_convert "$FS_APARC" "$TEMP_DK" --out_orientation LAS
    
    # Extract only the resected hemisphere parcels
    python3 << EOF
import nibabel as nib
import numpy as np

dk_img = nib.load('$TEMP_DK')
dk_data = dk_img.get_fdata()

resected_hemi = '$RESECTED_HEMI'

# Define parcels for the resected hemisphere
if resected_hemi == 'l':
    parcels = {
        'l_fusiform': 1007, 'l_lateraloccipital': 1011, 'l_parahippocampal': 1016,
        'l_inferiortemporal': 1009, 'l_middletemporal': 1015, 'l_lingual': 1013,
        'l_isthmuscingulate': 1010
    }
else:  # right hemisphere
    parcels = {
        'r_fusiform': 2007, 'r_lateraloccipital': 2011, 'r_parahippocampal': 2016,
        'r_inferiortemporal': 2009, 'r_middletemporal': 2015, 'r_lingual': 2013,
        'r_isthmuscingulate': 2010
    }

print(f"  Extracting {resected_hemi.upper()} hemisphere parcels (resected)")

# Extract the resected hemisphere parcels
for name, label in parcels.items():
    mask = dk_data == label
    n_voxels = int(np.sum(mask))
    
    if n_voxels > 0:
        output_file = f'$OUTPUT_DIR/{name}_mask.nii.gz'
        
        mask_img = nib.Nifti1Image(mask.astype(float), dk_img.affine)
        nib.save(mask_img, output_file)
        
        # Verify placement
        coords = np.where(mask)
        if len(coords[0]) > 0:
            center = nib.affines.apply_affine(dk_img.affine, [np.mean(coords[i]) for i in range(3)])
            expected_left = name.startswith('l_')
            is_left_side = center[0] < 0
            
            status = "✓" if expected_left == is_left_side else "⚠️"
        else:
            status = "?"
            center = [0, 0, 0]
        
        print(f"    {status} {name}: {n_voxels:4d} voxels at ({center[0]:5.1f}, {center[1]:5.1f}, {center[2]:5.1f})")
    else:
        print(f"    ❌ {name}: 0 voxels")
EOF
    
    rm -f "$TEMP_DK"
    echo ""
    
done

echo "============================================================"
echo "✅ RESECTED HEMISPHERE EXTRACTION COMPLETE"
echo "============================================================"
echo "Added resected hemisphere parcels for nonOTC patients"
echo "Ready to create bilateral searchmasks and expand dataset"