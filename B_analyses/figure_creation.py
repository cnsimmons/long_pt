#!/usr/bin/env python3
"""
Figure 5 Data Check: See what data you have without saving anything
"""

import nibabel as nib
import numpy as np
from pathlib import Path

def check_longitudinal_data():
    """
    Check what data exists for Figure 5 analysis without saving anything
    """
    
    base_dir = Path("/user_data/csimmon2/long_pt")
    bids_dir = base_dir / "data"
    
    # Longitudinal patients from the paper
    longitudinal_patients = ['sub-004', 'sub-007', 'sub-021']  # TC, UD, OT
    patient_names = {'sub-004': 'TC', 'sub-007': 'UD', 'sub-021': 'OT'}
    
    print("Checking data for Figure 5 longitudinal analysis")
    print("=" * 60)
    
    for subject in longitudinal_patients:
        patient_name = patient_names[subject]
        print(f"\n{patient_name} ({subject}):")
        
        # Find subject directory
        subject_dir = bids_dir / subject
        if not subject_dir.exists():
            print(f"  Subject directory not found: {subject_dir}")
            continue
            
        # Find sessions
        sessions = sorted([d for d in subject_dir.iterdir() if d.is_dir() and d.name.startswith('ses-')])
        print(f"  Sessions: {[s.name for s in sessions]}")
        
        if len(sessions) == 0:
            print(f"  No sessions found")
            continue
            
        # Check each session
        for session in sessions:
            print(f"    {session.name}:")
            
            # Check anatomy
            anat_dir = session / "anat"
            if anat_dir.exists():
                t1w_files = list(anat_dir.glob("*T1w.nii.gz"))
                if t1w_files:
                    t1w_file = t1w_files[0]
                    img = nib.load(t1w_file)
                    print(f"      T1w: {t1w_file.name} {img.shape}")
                else:
                    print(f"      No T1w found")
            else:
                print(f"      No anat directory")
                
            # Check functional
            func_dir = session / "func"
            if func_dir.exists():
                bold_files = list(func_dir.glob("*bold.nii.gz"))
                print(f"      BOLD files: {len(bold_files)}")
                for bold_file in bold_files:
                    print(f"        {bold_file.name}")
            else:
                print(f"      No func directory")

def check_beta_extraction_results():
    """
    Check if beta extraction results exist for longitudinal patients
    """
    
    base_dir = Path("/user_data/csimmon2/long_pt")
    beta_dir = base_dir / "analyses" / "beta_extraction"
    
    print(f"\nChecking beta extraction results:")
    print("-" * 40)
    
    if not beta_dir.exists():
        print(f"Beta extraction directory not found: {beta_dir}")
        return
        
    # Check session inventory
    inventory_file = beta_dir / "session_inventory.csv"
    if inventory_file.exists():
        import pandas as pd
        inventory = pd.read_csv(inventory_file)
        
        # Filter for longitudinal patients
        long_subjects = ['sub-004', 'sub-007', 'sub-021']
        long_sessions = inventory[inventory['subject'].isin(long_subjects)]
        
        print(f"Longitudinal sessions in inventory: {len(long_sessions)}")
        
        for subject in long_subjects:
            subj_sessions = long_sessions[long_sessions['subject'] == subject]
            patient_name = {'sub-004': 'TC', 'sub-007': 'UD', 'sub-021': 'OT'}[subject]
            print(f"  {patient_name}: {len(subj_sessions)} sessions")
            
        # Check if beta matrices exist
        print(f"\nChecking beta matrices:")
        for _, row in long_sessions.iterrows():
            session_id = row['session_id']
            beta_file = beta_dir / session_id / "beta_matrix.npy"
            roi_file = beta_dir / session_id / "roi_info.csv"
            
            if beta_file.exists() and roi_file.exists():
                beta_matrix = np.load(beta_file)
                print(f"    {session_id}: {beta_matrix.shape}")
            else:
                print(f"    {session_id}: Missing files")
    else:
        print(f"Session inventory not found: {inventory_file}")

def outline_next_steps():
    """
    Outline what needs to be done for Figure 5
    """
    
    print(f"\nFigure 5 Analysis Steps:")
    print("-" * 40)
    print("1. Create anatomical FG/OTS masks for TC, UD, OT")
    print("   - Hand-draw regions on T1w images using FSLeyes")
    print("   - Or use coordinate-based approach")
    print("2. Extract voxel-wise beta values within masks")
    print("3. Compute t(face-word) contrasts for each session")
    print("4. Statistical tests for changes over time")
    print("5. Create RDMs and MDS visualizations")
    
    print(f"\nImmediate next step:")
    print("Define FG/OTS anatomical regions (manually or programmatically)")

if __name__ == "__main__":
    check_longitudinal_data()
    check_beta_extraction_results()
    outline_next_steps()