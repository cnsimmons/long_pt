"""
Master pipeline script for hemispherectomy patient fMRI preprocessing
Runs the complete pipeline from raw data to GLMSingle analysis
"""
import os
import sys
import time
import argparse
import logging
from datetime import datetime

# Add current directory to path
curr_dir = '/user_data/csimmon2/git_repos/long_pt'
sys.path.insert(0, curr_dir)

# Import all preprocessing modules
import hemi_config as config
import data_organization
import anatomical_preprocessing
import registration
import functional_preprocessing
import glmsingle_analysis

def setup_logging(subject_id=None):
    """
    Set up logging for the pipeline
    """
    log_dir = f"{config.PROCESSED_DIR}/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if subject_id:
        log_file = f"{log_dir}/{subject_id}_pipeline_{timestamp}.log"
    else:
        log_file = f"{log_dir}/pipeline_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return log_file

def check_prerequisites():
    """
    Check if all necessary software and data are available
    """
    print("Checking prerequisites...")
    
    # Check if FSL is available
    try:
        import subprocess
        result = subprocess.run(['which', 'flirt'], capture_output=True, text=True)
        if result.returncode != 0:
            print("  Error: FSL not found. Please ensure FSL is installed and in PATH.")
            return False
        print("  FSL found")
    except:
        print("  Error: Could not check for FSL")
        return False
    
    # Check if GLMSingle is available
    try:
        from glmsingle.glmsingle import GLM_single
        print("  GLMSingle found")
    except ImportError:
        print("  Warning: GLMSingle not found. Install with: pip install glmsingle")
        print("  Statistical analysis will be skipped")
    
    # Check if data directories exist
    if not os.path.exists(config.RAW_DATA_DIR):
        print(f"  Error: Raw data directory not found: {config.RAW_DATA_DIR}")
        return False
    print(f"  Raw data directory found: {config.RAW_DATA_DIR}")
    
    # Check if subjects exist
    missing_subjects = []
    for subject_id in config.SUBJECTS.keys():
        subject_dir = f"{config.RAW_DATA_DIR}/{subject_id}"
        if not os.path.exists(subject_dir):
            missing_subjects.append(subject_id)
    
    if missing_subjects:
        print(f"  Warning: Missing subjects: {missing_subjects}")
    
    print("  Prerequisites check complete")
    return True

def run_single_subject_pipeline(subject_id, steps_to_run=None):
    """
    Run the complete pipeline for a single subject
    """
    if steps_to_run is None:
        steps_to_run = ['organize', 'anatomical', 'registration', 'functional', 'glmsingle']
    
    print(f"\n{'='*60}")
    print(f"Processing subject: {subject_id}")
    print(f"Steps to run: {steps_to_run}")
    print(f"{'='*60}")
    
    start_time = time.time()
    results = {}
    
    try:
        # Step 1: Data organization
        if 'organize' in steps_to_run:
            print(f"\n[STEP 1] Data Organization")
            step_start = time.time()
            try:
                data_organization.organize_subject_data(subject_id)
                results['organize'] = 'SUCCESS'
                print(f"  Completed in {time.time() - step_start:.2f} seconds")
            except Exception as e:
                print(f"  Error in data organization: {e}")
                results['organize'] = f'FAILED: {e}'
                return results
        
        # Step 2: Anatomical preprocessing
        if 'anatomical' in steps_to_run:
            print(f"\n[STEP 2] Anatomical Preprocessing")
            step_start = time.time()
            try:
                success = anatomical_preprocessing.process_anatomical_data(subject_id)
                if success:
                    results['anatomical'] = 'SUCCESS'
                    print(f"  Completed in {time.time() - step_start:.2f} seconds")
                else:
                    results['anatomical'] = 'FAILED'
                    print(f"  Anatomical preprocessing failed")
                    return results
            except Exception as e:
                print(f"  Error in anatomical preprocessing: {e}")
                results['anatomical'] = f'FAILED: {e}'
                return results
        
        # Step 3: Registration
        if 'registration' in steps_to_run:
            print(f"\n[STEP 3] Registration")
            step_start = time.time()
            try:
                success = registration.process_registration(subject_id)
                if success:
                    results['registration'] = 'SUCCESS'
                    print(f"  Completed in {time.time() - step_start:.2f} seconds")
                else:
                    results['registration'] = 'FAILED'
                    print(f"  Registration failed")
            except Exception as e:
                print(f"  Error in registration: {e}")
                results['registration'] = f'FAILED: {e}'
        
        # Step 4: Functional preprocessing
        if 'functional' in steps_to_run:
            print(f"\n[STEP 4] Functional Preprocessing")
            step_start = time.time()
            try:
                func_info, qc_results = functional_preprocessing.process_functional_data(subject_id)
                results['functional'] = 'SUCCESS'
                results['qc_results'] = qc_results
                print(f"  Completed in {time.time() - step_start:.2f} seconds")
            except Exception as e:
                print(f"  Error in functional preprocessing: {e}")
                results['functional'] = f'FAILED: {e}'
        
        # Step 5: GLMSingle analysis
        if 'glmsingle' in steps_to_run:
            print(f"\n[STEP 5] GLMSingle Analysis")
            step_start = time.time()
            try:
                success = glmsingle_analysis.process_glmsingle_analysis(subject_id)
                if success:
                    results['glmsingle'] = 'SUCCESS'
                    print(f"  Completed in {time.time() - step_start:.2f} seconds")
                else:
                    results['glmsingle'] = 'FAILED'
                    print(f"  GLMSingle analysis failed")
            except Exception as e:
                print(f"  Error in GLMSingle analysis: {e}")
                results['glmsingle'] = f'FAILED: {e}'
        
        total_time = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"Subject {subject_id} completed in {total_time:.2f} seconds")
        print(f"{'='*60}")
        
        return results
        
    except Exception as e:
        print(f"Unexpected error processing {subject_id}: {e}")
        results['pipeline'] = f'FAILED: {e}'
        return results

def run_full_pipeline(subjects=None, steps_to_run=None):
    """
    Run the complete pipeline for all or specified subjects
    """
    if subjects is None:
        subjects = list(config.SUBJECTS.keys())
    
    if steps_to_run is None:
        steps_to_run = ['organize', 'anatomical', 'registration', 'functional', 'glmsingle']
    
    print(f"Starting hemispherectomy fMRI preprocessing pipeline")
    print(f"Subjects to process: {subjects}")
    print(f"Pipeline steps: {steps_to_run}")
    
    pipeline_start = time.time()
    all_results = {}
    
    for subject_id in subjects:
        if subject_id not in config.SUBJECTS:
            print(f"Warning: {subject_id} not found in config.SUBJECTS")
            continue
        
        subject_results = run_single_subject_pipeline(subject_id, steps_to_run)
        all_results[subject_id] = subject_results
    
    # Print summary
    total_time = time.time() - pipeline_start
    print(f"\n{'='*80}")
    print(f"PIPELINE SUMMARY")
    print(f"{'='*80}")
    print(f"Total processing time: {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
    print(f"Subjects processed: {len(subjects)}")
    
    for subject_id, results in all_results.items():
        print(f"\n{subject_id}:")
        for step, result in results.items():
            if step != 'qc_results':
                print(f"  {step}: {result}")
    
    return all_results

def main():
    """
    Main function with command-line interface
    """
    parser = argparse.ArgumentParser(description='Hemispherectomy fMRI preprocessing pipeline')
    parser.add_argument('--subject', type=str, help='Process single subject (e.g., sub-004)')
    parser.add_argument('--steps', nargs='+', 
                       choices=['organize', 'anatomical', 'registration', 'functional', 'glmsingle'],
                       help='Specific steps to run')
    parser.add_argument('--check-only', action='store_true', help='Only check prerequisites')
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = setup_logging(args.subject)
    print(f"Logging to: {log_file}")
    
    # Check prerequisites
    if not check_prerequisites():
        print("Prerequisites check failed. Exiting.")
        return
    
    if args.check_only:
        print("Prerequisites check complete. Exiting.")
        return
    
    # Run pipeline
    if args.subject:
        # Single subject
        if args.subject not in config.SUBJECTS:
            print(f"Error: Subject {args.subject} not found in configuration")
            return
        
        results = run_single_subject_pipeline(args.subject, args.steps)
        
    else:
        # All subjects
        results = run_full_pipeline(steps_to_run=args.steps)
    
    print(f"\nPipeline complete! Check log file: {log_file}")

if __name__ == "__main__":
    main()
