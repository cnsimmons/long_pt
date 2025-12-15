import os
import subprocess
from glob import glob
import sys

BASE_DIR = '/user_data/csimmon2/long_pt'

# Start/Anchor sessions
# Default is '01', these are the exceptions
SESSION_START = {
    'sub-018': '02',
    'sub-068': '02',
    'sub-010': '02',
    # sub-007 is NOT here because it uses 01 as anchor, despite the gap
}

def register_subject(sub):
    print(f"--> Processing {sub}...")
    
    # 1. Determine Anchor Session
    anchor_ses = SESSION_START.get(sub, '01')
    ref_brain = f"{BASE_DIR}/{sub}/ses-{anchor_ses}/anat/{sub}_ses-{anchor_ses}_T1w_brain.nii.gz"
    
    if not os.path.exists(ref_brain):
        print(f"  CRITICAL: Anchor anatomy not found at {ref_brain}")
        sys.exit(1)

    # 2. Find sessions to process
    all_sessions = glob(f"{BASE_DIR}/{sub}/ses-*")
    
    for ses_path in sorted(all_sessions):
        ses_name = os.path.basename(ses_path).replace('ses-', '')
        
        # Skip anchor session
        if ses_name == anchor_ses: continue
            
        # For sub-007, this loop will naturally find '03' and '04' and register them to '01'
        # It will naturally skip '02' because the glob() won't find it.
            
        print(f"  Processing Session {ses_name} -> Anchor {anchor_ses}")
        
        anat_transform = f"{ses_path}/anat/anat2ses{anchor_ses}.mat"
        if not os.path.exists(anat_transform):
            print(f"  ⚠️  MISSING MATRIX: {anat_transform}")
            continue
            
        runs = glob(f"{ses_path}/derivatives/fsl/loc/run-*/1stLevel.feat")
        
        for run_dir in runs:
            run_name = os.path.basename(os.path.dirname(run_dir))
            
            func_4d = f"{run_dir}/filtered_func_data.nii.gz"
            func2anat = f"{run_dir}/reg/example_func2highres.mat"
            combined_mat = f"{run_dir}/reg/func2ses{anchor_ses}.mat"
            output_4d = f"{run_dir}/filtered_func_data_reg_ses{anchor_ses}.nii.gz"
            
            if not os.path.exists(func_4d): continue
            
            # Resume check
            if os.path.exists(output_4d) and os.path.getsize(output_4d) > 1000000:
                print(f"    Skipping {run_name}: Already done.")
                continue
                
            print(f"    Registering {run_name}...")
            try:
                cmd_concat = f"convert_xfm -omat {combined_mat} -concat {anat_transform} {func2anat}"
                subprocess.run(cmd_concat, shell=True, check=True)
                
                cmd_apply = f"flirt -in {func_4d} -ref {ref_brain} -out {output_4d} -applyxfm -init {combined_mat} -interp trilinear"
                subprocess.run(cmd_apply, shell=True, check=True)
                
            except subprocess.CalledProcessError as e:
                print(f"    ❌ Failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python register_raw2_4d.py <sub-ID>")
        sys.exit(1)
    subject_id = sys.argv[1]
    register_subject(subject_id)