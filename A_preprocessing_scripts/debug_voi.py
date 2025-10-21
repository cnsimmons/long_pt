#!/usr/bin/env python3
"""
Debug VOI coordinate issues
"""

import numpy as np
import nibabel as nib

def check_voi_coords(voi_path, target_voi_name, ref_img_path):
    """Check coordinate ranges and out-of-bounds issues"""
    
    # Parse VOI
    with open(voi_path, 'r') as f:
        lines = f.readlines()
    
    coords = []
    reading = False
    for i, line in enumerate(lines):
        if target_voi_name in line and 'NameOfVOI' in line:
            # Find NrOfVoxels
            for j in range(i, min(i+10, len(lines))):
                if 'NrOfVoxels:' in lines[j]:
                    n_vox = int(lines[j].split(':')[1].strip())
                    # Read coordinates
                    for k in range(j+1, j+1+n_vox):
                        parts = lines[k].strip().split()
                        if len(parts) == 3:
                            coords.append([int(parts[0]), int(parts[1]), int(parts[2])])
                    break
            break
    
    coords = np.array(coords)
    print(f"\n{target_voi_name}:")
    print(f"  Coordinates in VOI file: {len(coords)}")
    print(f"  Unique coordinates: {len(np.unique(coords, axis=0))}")
    print(f"  Coordinate ranges:")
    print(f"    X: {coords[:,0].min()} to {coords[:,0].max()}")
    print(f"    Y: {coords[:,1].min()} to {coords[:,1].max()}")
    print(f"    Z: {coords[:,2].min()} to {coords[:,2].max()}")
    
    # Check reference image
    ref_img = nib.load(ref_img_path)
    print(f"  Reference image dimensions: {ref_img.shape}")
    
    # Check how many coords are in bounds
    in_bounds = 0
    out_bounds = 0
    for coord in coords:
        if (0 <= coord[0] < ref_img.shape[0] and 
            0 <= coord[1] < ref_img.shape[1] and 
            0 <= coord[2] < ref_img.shape[2]):
            in_bounds += 1
        else:
            out_bounds += 1
    
    print(f"  In bounds: {in_bounds}")
    print(f"  Out of bounds: {out_bounds}")

# Check both VOI files
check_voi_coords('/user_data/csimmon2/long_pt/roi_files/UD_Anat_ROIs_Native_2023.voi', 
                 'FGOTS2',
                 '/lab_data/behrmannlab/hemi/Raw/sub-004/ses-01/anat/sub-004_ses-01_T1w.nii.gz')

check_voi_coords('/user_data/csimmon2/long_pt/roi_files/TC_Anat_ROIs_VolumeSpace_2023.voi',
                 'Anat_FG_OTS_7307',
                 '/lab_data/behrmannlab/hemi/Raw/sub-021/ses-01/anat/sub-021_ses-01_T1w.nii.gz')