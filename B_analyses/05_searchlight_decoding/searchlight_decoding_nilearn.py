"""
Searchlight Decoding - Nilearn Implementation
==============================================

A practical implementation using nilearn's SearchLight for the longitudinal VOTC study.
This script is designed to work with the specific data structure from the handoff document.

Data Structure Expected:
    /user_data/csimmon2/long_pt/
    ├── sub-XXX/
    │   ├── ses-XX/
    │   │   ├── derivatives/fsl/loc/
    │   │   │   ├── HighLevel.gfeat/
    │   │   │   │   ├── cope{N}.feat/stats/zstat1.nii.gz
    │   │   │   ├── run-01.feat/filtered_func_data_reg.nii.gz
    │   │   │   ├── run-02.feat/filtered_func_data_reg.nii.gz
    │   │   ├── ROIs/
    │   │   │   ├── r_face_searchmask.nii.gz
    │   │   │   ├── l_word_searchmask.nii.gz

Key Analyses:
1. Within-session category vs scramble decoding
2. Cross-session accuracy comparison (Dice overlap)  
3. Cross-temporal generalization (train ses1, test ses2)

Author: PhD Research Project
"""

import numpy as np
import pandas as pd
from pathlib import Path
from nilearn import image
from nilearn.image import load_img, get_data, new_img_like, concat_imgs, index_img
from nilearn.masking import compute_brain_mask, apply_mask, unmask
from nilearn.decoding import SearchLight
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import (StratifiedShuffleSplit, LeaveOneGroupOut, 
                                     cross_val_score, StratifiedKFold)
import warnings
warnings.filterwarnings("ignore")

# =============================================================================
# PATHS AND CONFIGURATION
# =============================================================================

BASE_DIR = Path('/user_data/csimmon2/long_pt')
OUTPUT_DIR = Path('/user_data/csimmon2/git_repos/long_pt/B_analyses/searchlight_decoding')

# Subject lists from handoff document
OTC_SUBJECTS = {
    'sub-004': {'ses': (1, 2), 'intact_hemi': 'left'},   # Right resection
    'sub-008': {'ses': (1, 2), 'intact_hemi': 'left'},   # Right resection  
    'sub-010': {'ses': (2, 3), 'intact_hemi': 'right'},  # Left resection
    'sub-017': {'ses': (1, 2), 'intact_hemi': 'right'},  # Left resection
    'sub-021': {'ses': (2, 3), 'intact_hemi': 'right'},  # Left resection
    'sub-079': {'ses': (1, 2), 'intact_hemi': 'right'},  # Left resection
}

NON_OTC_SUBJECTS = ['sub-007', 'sub-045', 'sub-047', 'sub-049', 'sub-070', 
                    'sub-072', 'sub-073', 'sub-081', 'sub-086']

CONTROL_SUBJECTS = ['sub-018', 'sub-022', 'sub-025', 'sub-027', 'sub-052', 
                    'sub-058', 'sub-062', 'sub-064', 'sub-068']

# Session overrides
SESSION_START = {'sub-010': 2, 'sub-018': 2, 'sub-068': 2, 'sub-021': 2}

# COPE mappings for contrasts
COPE_MAP = {
    'face': {'cope': 10, 'name': 'Face > Scramble'},
    'word': {'cope': 12, 'name': 'Word > Scramble'},  # cope12 preferred over cope13
    'object': {'cope': 3, 'name': 'Object > Scramble'},
    'house': {'cope': 11, 'name': 'House > Scramble'},
    'scramble': {'cope': 1, 'name': 'Scramble baseline'}  # For extracting scramble patterns
}

# Analysis parameters
SEARCHLIGHT_RADIUS = 6  # mm
N_CV_FOLDS = 30
TEST_SIZE = 0.2
TR = 2.0
BLOCK_DURATION = 12  # seconds
HRF_DELAY = 4  # seconds


# =============================================================================
# DATA LOADING FUNCTIONS
# =============================================================================

def get_subject_info(subject):
    """Get session and hemisphere info for a subject"""
    if subject in OTC_SUBJECTS:
        return OTC_SUBJECTS[subject], 'OTC'
    elif subject in NON_OTC_SUBJECTS:
        start_ses = SESSION_START.get(subject, 1)
        return {'ses': (start_ses, start_ses + 1), 'intact_hemi': 'both'}, 'nonOTC'
    elif subject in CONTROL_SUBJECTS:
        start_ses = SESSION_START.get(subject, 1)
        return {'ses': (start_ses, start_ses + 1), 'intact_hemi': 'both'}, 'Control'
    else:
        raise ValueError(f"Unknown subject: {subject}")


def find_runs(subject, session, base_dir=BASE_DIR):
    """Find available functional runs"""
    loc_dir = base_dir / subject / f'ses-{session:02d}' / 'derivatives' / 'fsl' / 'loc'
    
    runs = []
    for run_num in range(1, 10):
        func_file = loc_dir / f'run-{run_num:02d}.feat' / 'filtered_func_data_reg.nii.gz'
        if func_file.exists():
            runs.append(run_num)
    
    return runs


def load_func_data(subject, session, run, base_dir=BASE_DIR):
    """Load preprocessed functional data"""
    func_path = (base_dir / subject / f'ses-{session:02d}' / 'derivatives' / 
                 'fsl' / 'loc' / f'run-{run:02d}.feat' / 'filtered_func_data_reg.nii.gz')
    
    if not func_path.exists():
        raise FileNotFoundError(f"Not found: {func_path}")
    
    return load_img(str(func_path))


def load_zstat(subject, session, cope_num, base_dir=BASE_DIR):
    """Load zstat image from HighLevel GLM"""
    zstat_path = (base_dir / subject / f'ses-{session:02d}' / 'derivatives' / 
                  'fsl' / 'loc' / 'HighLevel.gfeat' / f'cope{cope_num}.feat' / 
                  'stats' / 'zstat1.nii.gz')
    
    if not zstat_path.exists():
        raise FileNotFoundError(f"Not found: {zstat_path}")
    
    return load_img(str(zstat_path))


def load_roi_mask(subject, session, roi_name, hemisphere=None, base_dir=BASE_DIR):
    """Load ROI mask
    
    Parameters
    ----------
    roi_name : str
        One of: 'face', 'word', 'object', 'house', 'ventral', 'visual'
    hemisphere : str, optional
        'left', 'right', or None for bilateral
    """
    roi_dir = base_dir / subject / f'ses-{session:02d}' / 'ROIs'
    
    # Try various naming conventions
    if hemisphere:
        hemi_prefix = 'l' if hemisphere == 'left' else 'r'
        patterns = [
            f'{hemi_prefix}_{roi_name}_searchmask.nii.gz',
            f'{hemisphere}_{roi_name}.nii.gz',
            f'{roi_name}_{hemi_prefix}.nii.gz',
        ]
    else:
        patterns = [
            f'{roi_name}_mask.nii.gz',
            f'{roi_name}.nii.gz',
            f'bilateral_{roi_name}.nii.gz',
        ]
    
    for pattern in patterns:
        mask_path = roi_dir / pattern
        if mask_path.exists():
            return load_img(str(mask_path))
    
    return None


def load_timing(subject, session, run, category, base_dir=BASE_DIR):
    """Load block timing for a category
    
    Expected file format: onset duration [amplitude]
    Returns array of shape (n_blocks, 2) with onset and duration
    """
    covs_dir = base_dir / subject / f'ses-{session:02d}' / 'covs'
    
    # Try various naming patterns
    sub_num = subject.replace('sub-', '').lstrip('0')
    patterns = [
        f'catloc_{subject}_run-0{run}_{category}.txt',
        f'catloc_{sub_num}_run-0{run}_{category}.txt',
        f'{category}_run{run}.txt',
        f'run{run}_{category}.txt',
    ]
    
    for pattern in patterns:
        timing_path = covs_dir / pattern
        if timing_path.exists():
            try:
                data = np.loadtxt(str(timing_path))
                if data.ndim == 1:
                    data = data.reshape(1, -1)
                return data[:, :2]  # onset, duration
            except Exception as e:
                print(f"    Warning: Could not parse {timing_path}: {e}")
    
    return None


# =============================================================================
# BLOCK PATTERN EXTRACTION
# =============================================================================

def extract_block_patterns_from_4d(func_img, timing, tr=TR, hrf_delay=HRF_DELAY):
    """Extract mean pattern for each block from 4D functional data
    
    Parameters
    ----------
    func_img : Nifti image
        4D functional data
    timing : array (n_blocks, 2)
        Block onsets and durations in seconds
        
    Returns
    -------
    patterns : array (n_blocks, x, y, z)
        Block-averaged 3D patterns
    """
    data = get_data(func_img)
    n_vols = data.shape[-1]
    
    patterns = []
    for onset, duration in timing:
        # Account for hemodynamic delay
        start_time = onset + hrf_delay
        end_time = onset + duration + hrf_delay
        
        start_vol = int(np.floor(start_time / tr))
        end_vol = int(np.ceil(end_time / tr))
        
        start_vol = max(0, start_vol)
        end_vol = min(n_vols, end_vol)
        
        if end_vol > start_vol:
            block_mean = np.mean(data[..., start_vol:end_vol], axis=-1)
            patterns.append(block_mean)
    
    return np.array(patterns)


def prepare_decoding_data(subject, session, target_category, contrast_category='scramble',
                          base_dir=BASE_DIR):
    """Prepare data for binary classification
    
    Parameters
    ----------
    target_category : str
        Category to decode (face, word, object, house)
    contrast_category : str
        Baseline category (default: scramble)
        
    Returns
    -------
    X : array (n_samples, x, y, z)
        Block patterns
    y : array (n_samples,)
        Labels (1 for target, 0 for contrast)
    groups : array (n_samples,)
        Run labels for cross-validation
    affine : array
        Image affine matrix
    """
    runs = find_runs(subject, session, base_dir)
    
    if not runs:
        raise ValueError(f"No runs found for {subject} ses-{session}")
    
    all_X = []
    all_y = []
    all_groups = []
    affine = None
    
    for run in runs:
        try:
            # Load functional data
            func_img = load_func_data(subject, session, run, base_dir)
            if affine is None:
                affine = func_img.affine
            
            # Load timing for both categories
            target_timing = load_timing(subject, session, run, target_category, base_dir)
            contrast_timing = load_timing(subject, session, run, contrast_category, base_dir)
            
            if target_timing is None or contrast_timing is None:
                print(f"    Skipping run {run}: missing timing files")
                continue
            
            # Extract patterns
            target_patterns = extract_block_patterns_from_4d(func_img, target_timing)
            contrast_patterns = extract_block_patterns_from_4d(func_img, contrast_timing)
            
            # Combine
            n_target = len(target_patterns)
            n_contrast = len(contrast_patterns)
            
            all_X.extend(target_patterns)
            all_X.extend(contrast_patterns)
            all_y.extend([1] * n_target)
            all_y.extend([0] * n_contrast)
            all_groups.extend([run] * (n_target + n_contrast))
            
        except Exception as e:
            print(f"    Error in run {run}: {e}")
            continue
    
    if not all_X:
        raise ValueError(f"No valid data extracted for {subject} ses-{session}")
    
    return np.array(all_X), np.array(all_y), np.array(all_groups), affine


# =============================================================================
# SEARCHLIGHT ANALYSIS
# =============================================================================

def run_searchlight(X, y, mask_img, groups=None, radius=SEARCHLIGHT_RADIUS, 
                    n_jobs=-1, verbose=1):
    """Run searchlight classification
    
    Parameters
    ----------
    X : array (n_samples, x, y, z)
        4D data array
    y : array (n_samples,)
        Labels
    mask_img : Nifti image
        Brain mask
    groups : array, optional
        Group labels for leave-one-group-out CV
        
    Returns
    -------
    accuracy_img : Nifti image
        Searchlight accuracy map
    """
    # Set up cross-validation
    if groups is not None and len(np.unique(groups)) >= 2:
        # Use leave-one-run-out
        cv = LeaveOneGroupOut()
    else:
        # Use stratified shuffle split
        cv = StratifiedShuffleSplit(n_splits=N_CV_FOLDS, test_size=TEST_SIZE, 
                                     random_state=42)
    
    # Set up classifier
    clf = make_pipeline(StandardScaler(), SVC(kernel='linear', C=1))
    
    # Create searchlight
    sl = SearchLight(
        mask_img=mask_img,
        radius=radius,
        estimator=clf,
        cv=cv,
        n_jobs=n_jobs,
        verbose=verbose
    )
    
    # Convert X to list of 3D images for nilearn
    # SearchLight expects a list of Nifti images or a 4D image
    sample_imgs = [new_img_like(mask_img, x) for x in X]
    X_4d = concat_imgs(sample_imgs)
    
    # Fit
    sl.fit(X_4d, y, groups)
    
    return sl.scores_img_


def roi_based_decoding(X, y, mask_data, groups=None):
    """Simplified ROI-based decoding (faster alternative to searchlight)
    
    Returns mean accuracy within mask
    """
    # Flatten spatial dimensions
    n_samples = X.shape[0]
    X_flat = X.reshape(n_samples, -1)
    
    # Apply mask
    mask_flat = mask_data.flatten() > 0
    X_masked = X_flat[:, mask_flat]
    
    # Remove zero-variance features
    feature_std = np.std(X_masked, axis=0)
    valid_features = feature_std > 0
    
    if np.sum(valid_features) < 10:
        print("    Warning: Too few valid features")
        return {'accuracy': 0.5, 'std': 0.0}
    
    X_masked = X_masked[:, valid_features]
    
    # Set up CV
    if groups is not None and len(np.unique(groups)) >= 2:
        cv = LeaveOneGroupOut()
    else:
        cv = StratifiedShuffleSplit(n_splits=N_CV_FOLDS, test_size=TEST_SIZE, 
                                     random_state=42)
    
    # Classify
    clf = make_pipeline(StandardScaler(), SVC(kernel='linear', C=1))
    scores = cross_val_score(clf, X_masked, y, cv=cv, groups=groups)
    
    return {
        'accuracy': np.mean(scores),
        'std': np.std(scores),
        'n_features': np.sum(valid_features),
        'n_samples': n_samples
    }


# =============================================================================
# COMPARISON METRICS
# =============================================================================

def compute_dice(map1, map2, threshold=0.55):
    """Compute Dice coefficient between thresholded accuracy maps"""
    bin1 = map1 > threshold
    bin2 = map2 > threshold
    
    intersection = np.sum(np.logical_and(bin1, bin2))
    total = np.sum(bin1) + np.sum(bin2)
    
    if total == 0:
        return 0.0
    
    return 2 * intersection / total


def cross_temporal_generalization(X1, y1, X2, y2, mask_data):
    """Test cross-session generalization
    
    Train on session 1, test on session 2 (and vice versa)
    """
    # Flatten and mask
    mask_flat = mask_data.flatten() > 0
    
    X1_flat = X1.reshape(X1.shape[0], -1)[:, mask_flat]
    X2_flat = X2.reshape(X2.shape[0], -1)[:, mask_flat]
    
    # Remove zero-variance features (using training data statistics)
    feature_std = np.std(X1_flat, axis=0)
    valid = feature_std > 0
    
    if np.sum(valid) < 10:
        return {'forward': 0.5, 'backward': 0.5, 'mean': 0.5}
    
    X1_valid = X1_flat[:, valid]
    X2_valid = X2_flat[:, valid]
    
    clf = make_pipeline(StandardScaler(), SVC(kernel='linear', C=1))
    
    # Forward: train ses1 → test ses2
    clf.fit(X1_valid, y1)
    forward_acc = clf.score(X2_valid, y2)
    
    # Backward: train ses2 → test ses1
    clf.fit(X2_valid, y2)
    backward_acc = clf.score(X1_valid, y1)
    
    return {
        'forward': forward_acc,
        'backward': backward_acc,
        'mean': (forward_acc + backward_acc) / 2
    }


# =============================================================================
# MAIN ANALYSIS FUNCTIONS
# =============================================================================

def analyze_subject(subject, categories=None, use_searchlight=False, 
                    base_dir=BASE_DIR, output_dir=OUTPUT_DIR):
    """Run complete analysis for one subject
    
    Parameters
    ----------
    subject : str
        Subject ID (e.g., 'sub-004')
    categories : list, optional
        Categories to analyze (default: all four)
    use_searchlight : bool
        If True, run full searchlight. If False, run faster ROI-based analysis.
    """
    categories = categories or ['face', 'word', 'object', 'house']
    
    print(f"\n{'='*60}")
    print(f"Analyzing {subject}")
    print(f"{'='*60}")
    
    # Get subject info
    sub_info, group = get_subject_info(subject)
    ses1, ses2 = sub_info['ses']
    intact_hemi = sub_info['intact_hemi']
    
    print(f"Group: {group}")
    print(f"Sessions: {ses1} → {ses2}")
    print(f"Intact hemisphere: {intact_hemi}")
    
    results = {
        'subject': subject,
        'group': group,
        'sessions': (ses1, ses2),
        'intact_hemi': intact_hemi,
        'categories': {}
    }
    
    # Create brain mask from functional data
    try:
        func_img = load_func_data(subject, ses1, find_runs(subject, ses1, base_dir)[0], base_dir)
        mask_img = compute_brain_mask(image.mean_img(func_img))
        mask_data = get_data(mask_img)
    except Exception as e:
        print(f"Error creating mask: {e}")
        return None
    
    for category in categories:
        print(f"\n--- {category.upper()} ---")
        cat_type = 'unilateral' if category in ['face', 'word'] else 'bilateral'
        
        cat_results = {
            'category_type': cat_type,
            'sessions': {}
        }
        
        session_data = {}
        
        for ses in [ses1, ses2]:
            print(f"  Session {ses}...")
            
            try:
                X, y, groups, affine = prepare_decoding_data(
                    subject, ses, category, 'scramble', base_dir
                )
                
                session_data[ses] = {'X': X, 'y': y, 'groups': groups}
                
                print(f"    Data: {X.shape[0]} samples, {np.sum(y==1)} target, {np.sum(y==0)} scramble")
                
                if use_searchlight:
                    # Full searchlight (slow)
                    acc_img = run_searchlight(X, y, mask_img, groups, n_jobs=-1, verbose=0)
                    acc_data = get_data(acc_img)
                    
                    cat_results['sessions'][ses] = {
                        'mean_accuracy': np.mean(acc_data[mask_data > 0]),
                        'max_accuracy': np.max(acc_data[mask_data > 0]),
                        'accuracy_map': acc_data
                    }
                else:
                    # Faster ROI-based analysis
                    roi_result = roi_based_decoding(X, y, mask_data, groups)
                    cat_results['sessions'][ses] = roi_result
                
                print(f"    Accuracy: {cat_results['sessions'][ses]['accuracy']:.3f}")
                
            except Exception as e:
                print(f"    Error: {e}")
                cat_results['sessions'][ses] = {'error': str(e)}
        
        # Cross-session comparisons
        if ses1 in session_data and ses2 in session_data:
            try:
                # Cross-temporal generalization
                cross_temp = cross_temporal_generalization(
                    session_data[ses1]['X'], session_data[ses1]['y'],
                    session_data[ses2]['X'], session_data[ses2]['y'],
                    mask_data
                )
                cat_results['cross_temporal'] = cross_temp
                print(f"  Cross-temporal: {cross_temp['mean']:.3f}")
                
                # Accuracy change
                if ('accuracy' in cat_results['sessions'].get(ses1, {}) and
                    'accuracy' in cat_results['sessions'].get(ses2, {})):
                    acc_change = (cat_results['sessions'][ses2]['accuracy'] - 
                                  cat_results['sessions'][ses1]['accuracy'])
                    cat_results['accuracy_change'] = acc_change
                    print(f"  Accuracy change: {acc_change:+.3f}")
                
                # Dice coefficient (if searchlight maps available)
                if use_searchlight and 'accuracy_map' in cat_results['sessions'].get(ses1, {}):
                    dice = compute_dice(
                        cat_results['sessions'][ses1]['accuracy_map'],
                        cat_results['sessions'][ses2]['accuracy_map'],
                        threshold=0.55
                    )
                    cat_results['dice_0.55'] = dice
                    print(f"  Dice overlap: {dice:.3f}")
                    
            except Exception as e:
                print(f"  Cross-session error: {e}")
        
        results['categories'][category] = cat_results
    
    # Save results
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save as CSV-friendly format
    rows = []
    for cat, cat_results in results['categories'].items():
        row = {
            'subject': subject,
            'group': group,
            'category': cat,
            'category_type': cat_results['category_type'],
            'intact_hemi': intact_hemi,
        }
        
        for ses in [ses1, ses2]:
            ses_results = cat_results['sessions'].get(ses, {})
            row[f'accuracy_ses{ses}'] = ses_results.get('accuracy', np.nan)
            row[f'std_ses{ses}'] = ses_results.get('std', np.nan)
        
        row['accuracy_change'] = cat_results.get('accuracy_change', np.nan)
        
        cross_temp = cat_results.get('cross_temporal', {})
        row['cross_temporal_forward'] = cross_temp.get('forward', np.nan)
        row['cross_temporal_backward'] = cross_temp.get('backward', np.nan)
        row['cross_temporal_mean'] = cross_temp.get('mean', np.nan)
        
        row['dice_0.55'] = cat_results.get('dice_0.55', np.nan)
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    csv_path = output_dir / f'{subject}_decoding_results.csv'
    df.to_csv(csv_path, index=False)
    print(f"\nSaved: {csv_path}")
    
    return results, df


def run_all_subjects(use_searchlight=False, base_dir=BASE_DIR, output_dir=OUTPUT_DIR):
    """Run analysis for all subjects"""
    
    all_subjects = (list(OTC_SUBJECTS.keys()) + NON_OTC_SUBJECTS + CONTROL_SUBJECTS)
    
    all_dfs = []
    
    for subject in all_subjects:
        try:
            result, df = analyze_subject(subject, use_searchlight=use_searchlight,
                                         base_dir=base_dir, output_dir=output_dir)
            all_dfs.append(df)
        except Exception as e:
            print(f"\nFailed to process {subject}: {e}")
    
    # Combine all results
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        combined_path = Path(output_dir) / 'all_subjects_decoding_results.csv'
        combined_df.to_csv(combined_path, index=False)
        print(f"\n{'='*60}")
        print(f"Combined results saved to: {combined_path}")
        
        # Print summary statistics
        print(f"\n{'='*60}")
        print("SUMMARY STATISTICS")
        print(f"{'='*60}")
        
        for group in ['OTC', 'nonOTC', 'Control']:
            group_data = combined_df[combined_df['group'] == group]
            if len(group_data) > 0:
                print(f"\n{group} (n={len(group_data['subject'].unique())} subjects):")
                
                for cat_type in ['unilateral', 'bilateral']:
                    type_data = group_data[group_data['category_type'] == cat_type]
                    if len(type_data) > 0:
                        acc_change = type_data['accuracy_change'].dropna()
                        cross_temp = type_data['cross_temporal_mean'].dropna()
                        
                        print(f"  {cat_type}:")
                        if len(acc_change) > 0:
                            print(f"    Accuracy change: {acc_change.mean():.3f} ± {acc_change.std():.3f}")
                        if len(cross_temp) > 0:
                            print(f"    Cross-temporal: {cross_temp.mean():.3f} ± {cross_temp.std():.3f}")
        
        return combined_df
    
    return None


# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--all':
            use_sl = '--searchlight' in sys.argv
            run_all_subjects(use_searchlight=use_sl)
        else:
            subject = sys.argv[1]
            use_sl = '--searchlight' in sys.argv
            analyze_subject(subject, use_searchlight=use_sl)
    else:
        print(__doc__)
        print("\nUsage:")
        print("  python searchlight_decoding_nilearn.py sub-004          # Single subject (fast ROI)")
        print("  python searchlight_decoding_nilearn.py sub-004 --searchlight  # Single subject (full searchlight)")
        print("  python searchlight_decoding_nilearn.py --all            # All subjects (fast ROI)")
        print("  python searchlight_decoding_nilearn.py --all --searchlight  # All subjects (full searchlight)")
