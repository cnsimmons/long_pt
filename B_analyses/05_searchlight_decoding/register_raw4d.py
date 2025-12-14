import os
import subprocess
from glob import glob

# CONFIGURATION
# Add all your subjects here
SUBJECTS = ['sub-004', 'sub-008'] 
BASE_DIR = '/user_data/csimmon2/long_pt'
FIRST_SES = '01' 

for sub in SUBJECTS:
    print(f"Processing {sub}...")
    
    # 1. Get the transformation matrix you likely already used for RSA
    # This aligns Ses-02 Anat -> Ses-01 Anat
    anat_transform = f"{BASE_DIR}/{sub}/ses-02/anat/anat2ses{FIRST_SES}.mat"
    
    # Check if the matrix exists
    if not os.path.exists(anat_transform):
        print(f"  Skipping {sub}: No anat2ses01.mat found.")
        continue

    # 2. Loop over functional runs
    runs = glob(f"{BASE_DIR}/{sub}/ses-02/derivatives/fsl/loc/run-*/1stLevel.feat")
    
    for run_dir in runs:
        # Inputs
        func_4d = f"{run_dir}/filtered_func_data.nii.gz"
        func2anat = f"{run_dir}/reg/example_func2highres.mat"
        
        # Outputs
        combined_mat = f"{run_dir}/reg/func2ses{FIRST_SES}.mat"
        output_4d = f"{run_dir}/filtered_func_data_reg_ses{FIRST_SES}.nii.gz" # <--- THIS IS THE FILE SEARCHLIGHT NEEDS
        
        # Check if output already exists
        if os.path.exists(output_4d):
            print(f"  Already exists: {output_4d}")
            continue

        print(f"  Registering 4D data: {os.path.basename(run_dir)}")

        # Step A: Chain the matrices (Func -> Ses2 Anat -> Ses1 Anat)
        # This is safer than your previous method because it includes the func->anat step
        cmd_concat = f"convert_xfm -omat {combined_mat} -concat {anat_transform} {func2anat}"
        try:
            subprocess.run(cmd_concat, shell=True, check=True)
            
            # Step B: Apply to 4D data using Session 1 Brain as reference
            ref_brain = f"{BASE_DIR}/{sub}/ses-{FIRST_SES}/anat/{sub}_ses-{FIRST_SES}_T1w_brain.nii.gz"
            
            cmd_apply = f"flirt -in {func_4d} -ref {ref_brain} -out {output_4d} -applyxfm -init {combined_mat} -interp trilinear"
            subprocess.run(cmd_apply, shell=True, check=True)
            
        except subprocess.CalledProcessError as e:
            print(f"  Error: {e}")

print("Done! Now update your Searchlight script to load 'filtered_func_data_reg_ses01.nii.gz'")