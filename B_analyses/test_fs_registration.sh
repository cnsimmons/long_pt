#!/bin/bash
# Test FreeSurfer → FSL registration on sub-008
# If this works, we can apply to all subjects

SUBJECT="sub-008"
SESSION="01"

# Paths
BASE_DIR="/user_data/csimmon2/long_pt"
FS_DIR="/lab_data/behrmannlab/hemi/FS"
WORK_DIR="$BASE_DIR/${SUBJECT}/ses-${SESSION}/ROIs"
TEMP_DIR="$WORK_DIR/temp_registration"

# Input files
FS_BRAIN="$FS_DIR/${SUBJECT}_ses-${SESSION}/mri/brain.mgz"
FS_APARC="$FS_DIR/${SUBJECT}_ses-${SESSION}/mri/aparc+aseg.mgz"
FSL_BRAIN="$BASE_DIR/${SUBJECT}/ses-${SESSION}/anat/${SUBJECT}_ses-${SESSION}_T1w_brain.nii.gz"

echo "======================================"
echo "Testing FS→FSL Registration: $SUBJECT"
echo "======================================"

# Create temp directory
mkdir -p "$TEMP_DIR"

# Check files exist
if [ ! -f "$FS_BRAIN" ]; then
    echo "❌ FS brain not found: $FS_BRAIN"
    exit 1
fi

if [ ! -f "$FS_APARC" ]; then
    echo "❌ FS aparc not found: $FS_APARC"
    exit 1
fi

if [ ! -f "$FSL_BRAIN" ]; then
    echo "❌ FSL brain not found: $FSL_BRAIN"
    exit 1
fi

echo "✓ All input files found"

# Step 1: Convert .mgz to .nii.gz using Python
echo ""
echo "Step 1: Converting .mgz to .nii.gz..."

python3 << EOF
import nibabel as nib

# Load and convert FreeSurfer data
print("  Loading FS brain...")
fs_brain = nib.load('$FS_BRAIN')
brain_nii = nib.Nifti1Image(fs_brain.get_fdata(), fs_brain.affine)
nib.save(brain_nii, '$TEMP_DIR/fs_brain.nii.gz')

print("  Loading FS aparc...")
fs_aparc = nib.load('$FS_APARC')  
aparc_nii = nib.Nifti1Image(fs_aparc.get_fdata(), fs_aparc.affine)
nib.save(aparc_nii, '$TEMP_DIR/fs_aparc.nii.gz')

print("  Conversion complete")

# Print dimensions for verification
fsl_brain = nib.load('$FSL_BRAIN')
print(f"  FS brain: {brain_nii.shape}")
print(f"  FS aparc: {aparc_nii.shape}")
print(f"  FSL brain: {fsl_brain.shape}")
EOF

if [ $? -ne 0 ]; then
    echo "❌ Conversion failed"
    exit 1
fi

echo "✓ Conversion successful"

# Step 2: Register FS brain to FSL brain
echo ""
echo "Step 2: Computing registration..."

TRANSFORM="$WORK_DIR/fs2ses${SESSION}_test.mat"

flirt \
    -in "$TEMP_DIR/fs_brain.nii.gz" \
    -ref "$FSL_BRAIN" \
    -omat "$TRANSFORM" \
    -dof 6 \
    -cost corratio \
    -searchrx -180 180 \
    -searchry -180 180 \
    -searchrz -180 180

if [ $? -ne 0 ]; then
    echo "❌ Registration failed"
    exit 1
fi

echo "✓ Registration complete"

# Step 3: Apply transform to parcellation
echo ""
echo "Step 3: Applying transform to parcellation..."

flirt \
    -in "$TEMP_DIR/fs_aparc.nii.gz" \
    -ref "$FSL_BRAIN" \
    -out "$WORK_DIR/aparc_registered_test.nii.gz" \
    -init "$TRANSFORM" \
    -applyxfm \
    -interp nearestneighbour

if [ $? -ne 0 ]; then
    echo "❌ Transform application failed"
    exit 1
fi

echo "✓ Transform applied"

# Step 4: Extract fusiform for quick test
echo ""
echo "Step 4: Testing fusiform extraction..."

python3 << EOF
import nibabel as nib
import numpy as np

# Load registered parcellation
aparc = nib.load('$WORK_DIR/aparc_registered_test.nii.gz')
aparc_data = aparc.get_fdata()

# Extract left fusiform (label 1007)
fusiform_mask = aparc_data == 1007
n_voxels = np.sum(fusiform_mask)

print(f"  Left fusiform: {n_voxels} voxels")

if n_voxels > 0:
    # Save fusiform mask
    fusiform_img = nib.Nifti1Image(fusiform_mask.astype(float), aparc.affine)
    nib.save(fusiform_img, '$WORK_DIR/l_fusiform_test.nii.gz')
    
    # Get center of mass for sanity check
    coords = np.where(fusiform_mask)
    center = [np.mean(coords[i]) for i in range(3)]
    center_world = nib.affines.apply_affine(aparc.affine, center)
    
    print(f"  Center: ({center_world[0]:.1f}, {center_world[1]:.1f}, {center_world[2]:.1f})")
    print(f"  Expected for left: X < 0")
    
    if center_world[0] < 0:
        print("  ✓ Correct hemisphere!")
    else:
        print("  ❌ Wrong hemisphere")
        
else:
    print("  ❌ No fusiform found")
EOF

# Step 5: Check transformation matrix
echo ""
echo "Step 5: Checking transformation quality..."

python3 << EOF
import numpy as np

try:
    matrix = np.loadtxt('$TRANSFORM')
    identity_diff = np.abs(matrix[:3, :3] - np.eye(3)).max()
    
    print(f"  Transformation matrix:")
    print(f"    {matrix[0, :]}")
    print(f"    {matrix[1, :]}")
    print(f"    {matrix[2, :]}")
    
    if identity_diff < 0.1:
        print("  ✓ Near-identity (good alignment)")
    elif identity_diff < 0.5:
        print("  ~ Moderate transform")
    else:
        print("  ⚠ Large transform")
        
except:
    print("  ❌ Could not read transform")
EOF

# Cleanup
echo ""
echo "Cleaning up temporary files..."
rm -rf "$TEMP_DIR"

echo ""
echo "======================================"
echo "Test complete!"
echo "======================================"
echo "Check results in: $WORK_DIR/"
echo "  - aparc_registered_test.nii.gz"
echo "  - l_fusiform_test.nii.gz"
echo "  - fs2ses${SESSION}_test.mat"
echo ""
echo "If fusiform is in correct location and hemisphere,"
echo "we can apply this approach to all subjects."