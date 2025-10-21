#!/usr/bin/env python3
"""
Use nibabel's BrainVoyager support to properly convert VOI files
"""

import nibabel as nib
import numpy as np

# Unfortunately nibabel doesn't directly support VOI files yet
# But we can use the coordinate system info from BrainVoyager documentation

def bv_to_world_coords(bv_coords, frame_dim=256):
    """
    Convert BrainVoyager voxel coordinates to world/scanner coordinates
    
    BrainVoyager uses origin at upper-frontal-right corner [0,0,0]
    Center is at [128,128,128] for 256^3 volume
    World coordinates are RAS+ (Right-Anterior-Superior)
    """
    # BrainVoyager coordinate system has origin at corner
    # Need to center and flip axes to get to RAS+
    world = bv_coords.copy().astype(float)
    
    # Center coordinates (BV center is at frame_dim/2)
    center = frame_dim / 2.0
    world = world - center
    
    # BrainVoyager to RAS+: need to flip X (make it right-to-left becomes left-to-right)
    world[:, 0] = -world[:, 0]
    
    return world

def world_to_fsl_voxels(world_coords, fsl_img):
    """Convert world coordinates to FSL voxel indices"""
    # Get inverse affine to go from world to voxels
    inv_affine = np.linalg.inv(fsl_img.affine)
    
    # Add homogeneous coordinate
    world_hom = np.hstack([world_coords, np.ones((len(world_coords), 1))])
    
    # Transform to FSL voxel space
    voxels = (inv_affine @ world_hom.T).T[:, :3]
    
    return voxels

def convert_voi_with_proper_transform(voi_path, voi_name, ref_nifti_path, output_path):
    """Convert VOI using proper coordinate transformations"""
    
    # Parse VOI file
    with open(voi_path, 'r') as f:
        lines = f.readlines()
    
    # Extract BrainVoyager coordinates
    bv_coords = []
    for i, line in enumerate(lines):
        if voi_name in line and 'NameOfVOI' in line:
            for j in range(i, min(i+10, len(lines))):
                if 'NrOfVoxels:' in lines[j]:
                    n_vox = int(lines[j].split(':')[1].strip())
                    for k in range(j+1, j+1+n_vox):
                        parts = lines[k].strip().split()
                        if len(parts) == 3:
                            bv_coords.append([int(p) for p in parts])
                    break
            break
    
    bv_coords = np.array(bv_coords)
    print(f"{voi_name}: {len(bv_coords)} BrainVoyager coordinates")
    
    # Convert BV coords to world coordinates
    world_coords = bv_to_world_coords(bv_coords, frame_dim=256)
    print(f"  Converted to world coordinates")
    
    # Load FSL reference image
    fsl_img = nib.load(ref_nifti_path)
    
    # Convert world coords to FSL voxel indices
    fsl_voxels = world_to_fsl_voxels(world_coords, fsl_img)
    
    # Round and filter to in-bounds
    fsl_voxels_int = np.round(fsl_voxels).astype(int)
    mask_inbounds = (
        (fsl_voxels_int[:, 0] >= 0) & (fsl_voxels_int[:, 0] < fsl_img.shape[0]) &
        (fsl_voxels_int[:, 1] >= 0) & (fsl_voxels_int[:, 1] < fsl_img.shape[1]) &
        (fsl_voxels_int[:, 2] >= 0) & (fsl_voxels_int[:, 2] < fsl_img.shape[2])
    )
    
    fsl_voxels_valid = fsl_voxels_int[mask_inbounds]
    print(f"  {len(fsl_voxels_valid)} voxels in bounds")
    
    # Create mask
    mask = np.zeros(fsl_img.shape, dtype=np.uint8)
    for vox in fsl_voxels_valid:
        mask[vox[0], vox[1], vox[2]] = 1
    
    # Save
    mask_img = nib.Nifti1Image(mask, fsl_img.affine, fsl_img.header)
    nib.save(mask_img, output_path)
    print(f"  Saved to {output_path}\n")

# Convert both subjects
convert_voi_with_proper_transform(
    '/user_data/csimmon2/long_pt/roi_files/UD_Anat_ROIs_Native_2023.voi',
    'FGOTS2',
    '/lab_data/behrmannlab/hemi/Raw/sub-004/ses-01/anat/sub-004_ses-01_T1w.nii.gz',
    '/user_data/csimmon2/long_pt/sub-004/ses-01/ROIs/l_FGOTS_liu_proper.nii.gz'
)

convert_voi_with_proper_transform(
    '/user_data/csimmon2/long_pt/roi_files/TC_Anat_ROIs_VolumeSpace_2023.voi',
    'Anat_FG_OTS_7307',
    '/lab_data/behrmannlab/hemi/Raw/sub-021/ses-01/anat/sub-021_ses-01_T1w.nii.gz',
    '/user_data/csimmon2/long_pt/sub-021/ses-01/ROIs/r_FGOTS_liu_proper.nii.gz'
)