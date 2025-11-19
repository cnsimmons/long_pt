#!/bin/bash
# Extract parcels for controls 018 and 068 (session 2 start)
set -e

echo "============================================================"
echo "CONTROLS 018/068 PARCEL EXTRACTION (SESSION 2)"
echo "============================================================"

# Process both control subjects
for SUBJECT in "sub-018" "sub-068"; do
    
    FIRST_SES="02"  # These subjects start at session 2
    
    echo ""
    echo "Processing: $SUBJECT (BOTH hemispheres, ses-$FIRST_SES)"
    
    # Paths
    FS_APARC="/lab_data/behrmannlab/hemi/FS/${SUBJECT}_ses-${FIRST_SES}/mri/aparc+aseg.mgz"
    OUTPUT_DIR="/user_data/csimmon2/long_pt/$SUBJECT/ses-$FIRST_SES/ROIs"
    TEMP_DK="/tmp/dk_native_${SUBJECT}.nii.gz"
    
    mkdir -p "$OUTPUT_DIR"
    
    if [ ! -f "$FS_APARC" ]; then
        echo "❌ FreeSurfer data not found: $FS_APARC"
        continue
    fi
    
    echo "✅ FreeSurfer data found: $FS_APARC"
    
    # Convert FreeSurfer data
    echo "Converting FreeSurfer DK parcellation..."
    mri_convert "$FS_APARC" "$TEMP_DK" --out_orientation LAS
    echo "✓ Conversion complete"
    
    # Extract BOTH hemisphere parcels (controls need both)
    python3 << EOF
import nibabel as nib
import numpy as np

dk_img = nib.load('$TEMP_DK')
dk_data = dk_img.get_fdata()

print(f"DK atlas shape: {dk_data.shape}")

# Extract BOTH hemisphere parcels for controls
parcels = {
    # LEFT hemisphere
    'l_fusiform': 1007, 'l_lateraloccipital': 1011, 'l_parahippocampal': 1016,
    'l_inferiortemporal': 1009, 'l_middletemporal': 1015, 'l_lingual': 1013,
    'l_isthmuscingulate': 1010,
    # RIGHT hemisphere  
    'r_fusiform': 2007, 'r_lateraloccipital': 2011, 'r_parahippocampal': 2016,
    'r_inferiortemporal': 2009, 'r_middletemporal': 2015, 'r_lingual': 2013,
    'r_isthmuscingulate': 2010
}

print("Extracting BOTH hemisphere parcels:")

for name, label in parcels.items():
    mask = dk_data == label
    n_voxels = int(np.sum(mask))
    
    if n_voxels > 0:
        mask_img = nib.Nifti1Image(mask.astype(float), dk_img.affine)
        nib.save(mask_img, f'$OUTPUT_DIR/{name}_mask.nii.gz')
        
        coords = np.where(mask)
        if len(coords[0]) > 0:
            center = nib.affines.apply_affine(dk_img.affine, [np.mean(coords[i]) for i in range(3)])
            expected_left = name.startswith('l_')
            is_left_side = center[0] < 0
            
            if expected_left == is_left_side:
                status = "✓"
            else:
                status = "⚠️"
        else:
            status = "?"
            center = [0, 0, 0]
        
        print(f"  {status} {name}: {n_voxels:4d} voxels at ({center[0]:5.1f}, {center[1]:5.1f}, {center[2]:5.1f})")
    else:
        print(f"  ❌ {name}: Not found")
EOF
    
    rm -f "$TEMP_DK"
    
done

echo ""
echo "============================================================"
echo "CONTROLS 018/068 EXTRACTION COMPLETE"
echo "============================================================"
echo "Next: Create bilateral searchmasks for these controls"