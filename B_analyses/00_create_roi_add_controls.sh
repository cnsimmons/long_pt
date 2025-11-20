# Fixed control parcel creation - BOTH hemispheres
echo "Creating BOTH hemisphere parcels for control subjects..."

while IFS=',' read -r subject_id dob age1 age2 age3 age4 age5 group sex surgery_side intact_hemi loc otc scanner pre_post patient rest; do
    
    # Only process controls this time (patient=0)
    if [[ "$patient" != "0" ]] || [[ "$subject_id" == "sub" ]]; then
        continue
    fi
    
    SUBJECT="$subject_id"
    FIRST_SES="01"
    
    echo "Processing control: $SUBJECT (creating BOTH hemispheres)"
    
    FS_APARC="/lab_data/behrmannlab/hemi/FS/${SUBJECT}_ses-${FIRST_SES}/mri/aparc+aseg.mgz"
    OUTPUT_DIR="/user_data/csimmon2/long_pt/$SUBJECT/ses-$FIRST_SES/ROIs"
    TEMP_DK="/tmp/dk_native_${SUBJECT}.nii.gz"
    
    mkdir -p "$OUTPUT_DIR"
    
    if [ ! -f "$FS_APARC" ]; then
        echo "❌ FreeSurfer data not found for $SUBJECT"
        continue
    fi
    
    echo "  Converting FreeSurfer DK parcellation..."
    mri_convert "$FS_APARC" "$TEMP_DK" --out_orientation LAS
    
    python3 << EOF
    
import nibabel as nib
import numpy as np

dk_img = nib.load('$TEMP_DK')
dk_data = dk_img.get_fdata()

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

for name, label in parcels.items():
    mask = dk_data == label
    n_voxels = int(np.sum(mask))
    
    if n_voxels > 0:
        mask_img = nib.Nifti1Image(mask.astype(float), dk_img.affine)
        nib.save(mask_img, f'$OUTPUT_DIR/{name}_mask.nii.gz')
        print(f"  ✓ {name}: {n_voxels} voxels")
    else:
        print(f"  ⚠️ {name}: 0 voxels")
EOF
    
    rm -f "$TEMP_DK"
    
done < /user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv

echo "✓ Control parcels (both hemispheres) created"