import nibabel as nib
import os

base = '/user_data/csimmon2/long_pt'
subject = 'sub-007'
session = '01'

print("="*70)
print("CHECKING WHICH ANATOMICAL SPACE FUNCTIONAL DATA IS IN")
print("="*70)

# Check what files exist
anat_files = {
    'native': f'{base}/{subject}/ses-{session}/anat/{subject}_ses-{session}_T1w_brain.nii.gz',
    'standard': f'{base}/{subject}/ses-{session}/anat/{subject}_ses-{session}_T1w_brain_stand.nii.gz'
}

print("\nAnatomical files:")
for name, path in anat_files.items():
    exists = os.path.exists(path)
    if exists:
        img = nib.load(path)
        print(f"  {name}: {img.shape} - EXISTS")
    else:
        print(f"  {name}: NOT FOUND")

# Check HighLevel registration
highlevel_dir = f'{base}/{subject}/ses-{session}/derivatives/fsl/loc/HighLevel.gfeat'
reg_dir = f'{highlevel_dir}/reg'

print(f"\nHighLevel registration directory:")
if os.path.exists(reg_dir):
    reg_files = os.listdir(reg_dir)
    print(f"  Files: {reg_files}")
    
    # Check what the example_func is registered to
    if 'standard.nii.gz' in reg_files:
        standard = nib.load(f'{reg_dir}/standard.nii.gz')
        print(f"\n  standard.nii.gz shape: {standard.shape}")
        
    if 'highres.nii.gz' in reg_files:
        highres = nib.load(f'{reg_dir}/highres.nii.gz')
        print(f"  highres.nii.gz shape: {highres.shape}")
else:
    print("  Registration directory not found")

# Check the actual zstat space
zstat = nib.load(f'{highlevel_dir}/cope13.feat/stats/zstat1.nii.gz')
print(f"\nZstat shape: {zstat.shape}")

# Compare to both anatomicals
if os.path.exists(anat_files['native']):
    native = nib.load(anat_files['native'])
    print(f"Native T1 shape: {native.shape}")
    
if os.path.exists(anat_files['standard']):
    standard_anat = nib.load(anat_files['standard'])
    print(f"Standard T1 shape: {standard_anat.shape}")

print("\n" + "="*70)
print("QUESTION: Which T1 space are the zstats registered to?")
print("="*70)