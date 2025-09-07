"""
GLMSingle statistical analysis for hemispherectomy patients
"""
import os
import time
import numpy as np
import pandas as pd
import nibabel as nib
from nilearn import image
import hemi_config as config

# Import GLMSingle
try:
    from glmsingle.glmsingle import GLM_single
except ImportError:
    print("Warning: GLMSingle not installed. Please install with: pip install glmsingle")
    GLM_single = None

def create_design_matrices(subject_id):
    """
    Create design matrices for GLMSingle from timing files
    """
    print(f"Creating design matrices for {subject_id}")
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    
    # First, get the number of volumes from functional data
    func_info = {}
    for run in config.RUNS:
        func_file = f"{sub_dir}/func/{subject_id}_ses-01_task-{config.TASK}_run-0{run}_bold.nii.gz"
        if os.path.exists(func_file):
            img = nib.load(func_file)
            func_info[run] = img.shape[3] if len(img.shape) == 4 else 1
        else:
            print(f"  Warning: Functional file not found for run {run}")
            return None
    
    design_matrices = []
    
    for run in config.RUNS:
        n_vols = func_info.get(run)
        if n_vols is None:
            continue
            
        # Initialize design matrix for this run
        design_matrix = np.zeros((n_vols, len(config.CONDITIONS)))
        
        print(f"  Creating design matrix for run {run} ({n_vols} volumes)")
        
        for i, condition in enumerate(config.CONDITIONS):
            timing_file = f"{sub_dir}/timing/{config.TASK}_{subject_id}_run-0{run}_{condition}.txt"
            
            if os.path.exists(timing_file):
                try:
                    timing_data = pd.read_csv(timing_file, sep='\t', header=None)
                    timing_data.columns = ['onset', 'duration', 'amplitude']
                    
                    # Convert to TR units
                    onset_trs = (timing_data['onset'] / config.TR).astype(int)
                    duration_trs = (timing_data['duration'] / config.TR).astype(int)
                    
                    # Fill design matrix (block design)
                    for onset, duration in zip(onset_trs, duration_trs):
                        end_tr = min(onset + duration, n_vols)
                        if onset < n_vols:
                            design_matrix[onset:end_tr, i] = 1
                    
                    print(f"    Added {condition}: {len(onset_trs)} blocks")
                    
                except Exception as e:
                    print(f"    Error processing timing file for {condition}: {e}")
            else:
                print(f"    Warning: Timing file not found for {condition}")
        
        design_matrices.append(design_matrix)
        
        # Save design matrix
        np.save(f"{sub_dir}/timing/design_matrix_run-0{run}.npy", design_matrix)
    
    print(f"  Created {len(design_matrices)} design matrices")
    return design_matrices

def load_functional_data_for_glmsingle(subject_id):
    """
    Load functional data in format required by GLMSingle
    """
    print(f"Loading functional data for GLMSingle: {subject_id}")
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    functional_data = []
    
    for run in config.RUNS:
        func_file = f"{sub_dir}/func/{subject_id}_ses-01_task-{config.TASK}_run-0{run}_bold.nii.gz"
        
        if os.path.exists(func_file):
            try:
                # Load using nilearn to ensure proper formatting
                img = image.load_img(func_file)
                data = img.get_fdata()
                
                # GLMSingle expects 4D data (x, y, z, time)
                if len(data.shape) != 4:
                    print(f"  Error: Expected 4D data, got {data.shape}")
                    return None
                
                functional_data.append(data)
                print(f"  Loaded run {run}: shape {data.shape}")
                
            except Exception as e:
                print(f"  Error loading functional data for run {run}: {e}")
                return None
        else:
            print(f"  Error: Functional file not found for run {run}")
            return None
    
    return functional_data

def run_glmsingle_analysis(subject_id):
    """
    Run GLMSingle analysis for a subject
    """
    if GLM_single is None:
        print("GLMSingle not available. Skipping analysis.")
        return False
        
    print(f"Running GLMSingle analysis for {subject_id}")
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    output_dir = f"{sub_dir}/derivatives/glmsingle"
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if analysis already completed
    if os.path.exists(f"{output_dir}/TYPED_FITHRF_GLMDENOISE_RR.npy"):
        print(f"  GLMSingle analysis already completed for {subject_id}")
        return True
    
    # Load design matrices
    design_matrices = create_design_matrices(subject_id)
    if design_matrices is None:
        print(f"  Error: Could not create design matrices for {subject_id}")
        return False
    
    # Load functional data
    functional_data = load_functional_data_for_glmsingle(subject_id)
    if functional_data is None:
        print(f"  Error: Could not load functional data for {subject_id}")
        return False
    
    # Check data consistency
    if len(design_matrices) != len(functional_data):
        print(f"  Error: Mismatch between design matrices ({len(design_matrices)}) and functional data ({len(functional_data)})")
        return False
    
    try:
        # Create GLMSingle object
        glmsingle_obj = GLM_single(config.GLMSINGLE_OPTIONS)
        
        print(f"  Starting GLMSingle analysis...")
        start_time = time.time()
        
        # Run GLMSingle
        results = glmsingle_obj.fit(
            design_matrices,
            functional_data,
            config.STIMDUR,
            config.TR,
            outputdir=output_dir
        )
        
        elapsed_time = time.time() - start_time
        print(f"  GLMSingle completed in {elapsed_time:.2f} seconds")
        
        # Save additional information
        analysis_info = {
            'subject_id': subject_id,
            'n_runs': len(functional_data),
            'n_conditions': len(config.CONDITIONS),
            'conditions': config.CONDITIONS,
            'tr': config.TR,
            'stimdur': config.STIMDUR,
            'analysis_time': elapsed_time
        }
        
        np.save(f"{output_dir}/analysis_info.npy", analysis_info)
        
        print(f"  Successfully completed GLMSingle analysis for {subject_id}")
        return True
        
    except Exception as e:
        print(f"  Error during GLMSingle analysis: {e}")
        return False

def extract_roi_timeseries(subject_id):
    """
    Extract ROI time series from functional data
    """
    print(f"Extracting ROI timeseries for {subject_id}")
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    roi_dir = f"{sub_dir}/derivatives/rois"
    output_dir = f"{sub_dir}/derivatives/timeseries"
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if ROIs exist
    roi_files = []
    for roi_name in config.ROI_PARCELS:
        roi_file = f"{roi_dir}/parcels/{roi_name}.nii.gz"
        if os.path.exists(roi_file):
            roi_files.append((roi_name, roi_file))
        else:
            print(f"  Warning: ROI not found: {roi_file}")
    
    if not roi_files:
        print(f"  No ROIs found for {subject_id}")
        return False
    
    # Extract timeseries for each run
    for run in config.RUNS:
        func_file = f"{sub_dir}/func/{subject_id}_ses-01_task-{config.TASK}_run-0{run}_bold.nii.gz"
        
        if not os.path.exists(func_file):
            print(f"  Warning: Functional file not found for run {run}")
            continue
        
        print(f"  Extracting timeseries for run {run}")
        
        try:
            # Load functional data
            func_img = image.load_img(func_file)
            
            run_timeseries = {}
            
            for roi_name, roi_file in roi_files:
                # Load ROI mask
                roi_img = image.load_img(roi_file)
                
                # Extract mean timeseries
                timeseries = image.masking.apply_mask(func_img, roi_img)
                mean_timeseries = np.mean(timeseries, axis=1)
                
                run_timeseries[roi_name] = mean_timeseries
                print(f"    Extracted {roi_name}: {len(mean_timeseries)} timepoints")
            
            # Save timeseries
            timeseries_file = f"{output_dir}/timeseries_run-0{run}.npy"
            np.save(timeseries_file, run_timeseries)
            
        except Exception as e:
            print(f"  Error extracting timeseries for run {run}: {e}")
    
    return True

def process_glmsingle_analysis(subject_id):
    """
    Complete GLMSingle analysis pipeline for a subject
    """
    print(f"\nRunning GLMSingle analysis for {subject_id}")
    
    # Step 1: Run GLMSingle statistical analysis
    success = run_glmsingle_analysis(subject_id)
    if not success:
        print(f"  GLMSingle analysis failed for {subject_id}")
        return False
    
    # Step 2: Extract ROI timeseries
    extract_roi_timeseries(subject_id)
    
    return True

def main():
    """
    Run GLMSingle analysis for all subjects
    """
    print("Starting GLMSingle analysis pipeline...")
    
    if GLM_single is None:
        print("Error: GLMSingle not available. Please install GLMSingle package.")
        return
    
    for subject_id in config.SUBJECTS.keys():
        success = process_glmsingle_analysis(subject_id)
        if not success:
            print(f"  Warning: GLMSingle analysis failed for {subject_id}")
    
    print("GLMSingle analysis pipeline complete!")

if __name__ == "__main__":
    main()
