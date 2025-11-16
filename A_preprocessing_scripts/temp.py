# Check if the flirt registration is the problem
import subprocess

subject = 'sub-008'  # Known bad case
fs_brain = f'/lab_data/behrmannlab/hemi/FS/{subject}_ses-01/mri/brain.mgz'
subj_brain = f'/user_data/csimmon2/long_pt/{subject}/ses-01/anat/{subject}_ses-01_T1w_brain.nii.gz'

# Test registration with verbose output
cmd = ['flirt', '-in', fs_brain, '-ref', subj_brain, '-omat', 'test_registration.mat', 
       '-dof', '6', '-cost', 'corratio', '-v']

result = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)