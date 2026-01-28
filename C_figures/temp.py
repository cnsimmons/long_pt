# Fixed LORO Implementation for Controls

import numpy as np
import nibabel as nib
from pathlib import Path
import pandas as pd
from scipy.ndimage import label, center_of_mass
from scipy.stats import pearsonr
from itertools import combinations

# %% LORO Helper Functions

def get_run_zstat_path(subject_id, session, run, cope_num):
    """
    Get path to zstat file for a specific run.
    
    Path structure: .../run-0{X}/1stLevel.feat/stats/zstat{cope}.nii.gz
    """
    # Handle run naming (might be 'run-01' or 'run-1' or just '1')
    if not run.startswith('run-'):
        run = f'run-0{run}' if len(str(run)) == 1 else f'run-{run}'
    
    zstat_path = (BASE_DIR / subject_id / f'ses-{session}' / 'derivatives' / 
                  'fsl' / 'loc' / run / '1stLevel.feat' / 'stats' / f'zstat{cope_num}.nii.gz')
    
    if zstat_path.exists():
        return zstat_path
    
    # Try cope instead of zstat
    cope_path = (BASE_DIR / subject_id / f'ses-{session}' / 'derivatives' / 
                 'fsl' / 'loc' / run / '1stLevel.feat' / 'stats' / f'cope{cope_num}.nii.gz')
    
    if cope_path.exists():
        return cope_path
    
    return None


def average_run_zstats(subject_id, session, runs, cope_num, mult=1):
    """
    Average zstat maps across multiple runs.
    
    Parameters:
    -----------
    subject_id : str
    session : str
    runs : list of str
        Run identifiers to average (e.g., ['run-01', 'run-02'])
    cope_num : int
        Contrast number
    mult : int
        Multiplier (1 or -1)
    
    Returns:
    --------
    avg_data : ndarray or None
        Averaged zstat data
    affine : ndarray or None
        Affine matrix
    """
    zstat_data = []
    affine = None
    
    for run in runs:
        zstat_path = get_run_zstat_path(subject_id, session, run, cope_num)
        
        if zstat_path is None:
            return None, None
        
        try:
            img = nib.load(zstat_path)
            zstat_data.append(img.get_fdata() * mult)
            if affine is None:
                affine = img.affine
        except Exception as e:
            print(f"    Error loading {zstat_path}: {e}")
            return None, None
    
    if len(zstat_data) == 0:
        return None, None
    
    # Average across runs
    avg_data = np.mean(zstat_data, axis=0)
    return avg_data, affine


def extract_rois_loro(cope_map, threshold_z=2.3, min_voxels=20):
    """
    Extract ROIs using Leave-One-Run-Out for controls.
    
    For each fold:
    - Define ROI using averaged zstats from N-1 training runs
    - Store info for pattern extraction from held-out run
    
    Returns:
    --------
    rois_loro : dict
        {subject_id: {roi_key: {'folds': [...], 'n_folds': int}}}
    """
    rois_loro = {}
    
    for sid, info in SUBJECTS.items():
        # Only apply LORO to controls
        if info['group'] != 'control':
            continue
        
        first_ses = info['sessions'][0]
        runs = detect_runs(sid, first_ses)
        
        if len(runs) < 2:
            print(f"  {sid}: Only {len(runs)} runs, skipping LORO")
            continue
        
        print(f"  {sid}: {len(runs)} runs detected - {runs}")
        
        # Load search masks (these are anatomical constraints, independent of runs)
        roi_dir = BASE_DIR / sid / f'ses-{first_ses}' / 'ROIs'
        if not roi_dir.exists():
            print(f"    No ROI directory found")
            continue
        
        rois_loro[sid] = {}
        
        for hemi in ['l', 'r']:
            for category in CATEGORIES:
                cope_num, mult = cope_map[category]
                roi_key = f'{hemi}_{category}'
                
                # Load search mask
                mask_file = roi_dir / f'{hemi}_{category}_searchmask.nii.gz'
                if not mask_file.exists():
                    continue
                
                try:
                    mask_img = nib.load(mask_file)
                    search_mask = mask_img.get_fdata() > 0
                    mask_affine = mask_img.affine
                    mask_shape = search_mask.shape
                except Exception as e:
                    print(f"    Error loading mask {mask_file}: {e}")
                    continue
                
                folds = []
                
                # Leave-one-run-out: each run as held-out
                for held_out_run in runs:
                    train_runs = [r for r in runs if r != held_out_run]
                    
                    # Average zstats from training runs for ROI definition
                    avg_zstat, affine = average_run_zstats(
                        sid, first_ses, train_runs, cope_num, mult
                    )
                    
                    if avg_zstat is None:
                        continue
                    
                    # Threshold and find ROI
                    suprathresh = (avg_zstat > threshold_z) & search_mask
                    
                    if suprathresh.sum() < min_voxels:
                        continue
                    
                    labeled, n_clusters = label(suprathresh)
                    if n_clusters == 0:
                        continue
                    
                    # Largest cluster
                    sizes = [(labeled == i).sum() for i in range(1, n_clusters + 1)]
                    best_idx = np.argmax(sizes) + 1
                    roi_mask = (labeled == best_idx)
                    
                    if roi_mask.sum() < min_voxels:
                        continue
                    
                    # Get centroid and peak
                    centroid = nib.affines.apply_affine(affine, center_of_mass(roi_mask))
                    peak_idx = np.unravel_index(
                        np.argmax(avg_zstat * roi_mask), 
                        avg_zstat.shape
                    )
                    peak_z = avg_zstat[peak_idx]
                    
                    folds.append({
                        'held_out_run': held_out_run,
                        'train_runs': train_runs,
                        'roi_mask': roi_mask,
                        'centroid': centroid,
                        'peak_z': peak_z,
                        'n_voxels': int(roi_mask.sum()),
                        'affine': affine,
                        'shape': avg_zstat.shape
                    })
                
                if len(folds) > 0:
                    rois_loro[sid][roi_key] = {
                        'folds': folds,
                        'n_folds': len(folds)
                    }
                    print(f"    {roi_key}: {len(folds)} folds")
    
    return rois_loro


def compute_geometry_loro(rois_loro, pattern_cope_map, radius=6):
    """
    Compute geometry preservation using LORO for controls.
    
    For each fold:
    - Use ROI defined on training runs
    - Extract patterns from held-out run (both sessions)
    - Compute RDM correlation
    
    Average across folds for final estimate.
    """
    results = []
    
    for sid, roi_data in rois_loro.items():
        info = SUBJECTS[sid]
        sessions = info['sessions']
        
        if len(sessions) < 2:
            continue
        
        first_ses = sessions[0]
        last_ses = sessions[-1]
        
        for roi_key, loro_info in roi_data.items():
            hemi = roi_key.split('_')[0]
            category = roi_key.split('_')[1]
            
            fold_gp_values = []
            rdms_t1 = []
            rdms_t2 = []
            
            for fold in loro_info['folds']:
                held_out_run = fold['held_out_run']
                centroid = fold['centroid']
                affine = fold['affine']
                shape = fold['shape']
                
                # Create sphere around centroid
                sphere = create_sphere(centroid, affine, shape, radius)
                
                # Extract patterns from held-out run for BOTH sessions
                rdms = {}
                
                for ses in [first_ses, last_ses]:
                    patterns = []
                    valid = True
                    
                    for cat in CATEGORIES:
                        cope_num, mult = pattern_cope_map[cat]
                        
                        # Get held-out run's zstat for this session
                        zstat_path = get_run_zstat_path(sid, ses, held_out_run, cope_num)
                        
                        if zstat_path is None:
                            valid = False
                            break
                        
                        try:
                            data = nib.load(zstat_path).get_fdata() * mult
                            pattern = data[sphere]
                            
                            if len(pattern) == 0 or not np.all(np.isfinite(pattern)):
                                valid = False
                                break
                            
                            patterns.append(pattern)
                        except:
                            valid = False
                            break
                    
                    if valid and len(patterns) == 4:
                        corr_matrix = np.corrcoef(patterns)
                        rdm = 1 - corr_matrix
                        rdms[ses] = rdm
                
                # Compute geometry preservation for this fold
                if len(rdms) == 2:
                    triu = np.triu_indices(4, k=1)
                    r, _ = pearsonr(rdms[first_ses][triu], rdms[last_ses][triu])
                    fold_gp_values.append(r)
                    rdms_t1.append(rdms[first_ses])
                    rdms_t2.append(rdms[last_ses])
            
            # Average across folds
            if len(fold_gp_values) > 0:
                results.append({
                    'subject': sid,
                    'code': info['code'],
                    'group': info['group'],
                    'hemi': hemi,
                    'category': category,
                    'geometry_preservation': np.mean(fold_gp_values),
                    'gp_std': np.std(fold_gp_values),
                    'gp_values': fold_gp_values,
                    'n_folds': len(fold_gp_values),
                    'method': 'LORO',
                    'rdm_t1': np.mean(rdms_t1, axis=0),
                    'rdm_t2': np.mean(rdms_t2, axis=0)
                })
    
    return pd.DataFrame(results)


# %% Quick diagnostic to verify paths exist

def diagnose_run_paths():
    """Check that run-level stats files exist"""
    print("\n" + "="*70)
    print("DIAGNOSING RUN-LEVEL STATS PATHS")
    print("="*70)
    
    for sid, info in SUBJECTS.items():
        if info['group'] != 'control':
            continue
        
        first_ses = info['sessions'][0]
        runs = detect_runs(sid, first_ses)
        
        print(f"\n{sid} (session {first_ses}):")
        print(f"  Detected runs: {runs}")
        
        if len(runs) > 0:
            # Check first run
            run = runs[0]
            for cope_num in [3, 10, 11, 12]:  # Key copes for RSA
                path = get_run_zstat_path(sid, first_ses, run, cope_num)
                status = "✓" if path and path.exists() else "✗"
                print(f"  cope{cope_num}: {status} {path}")
        
        break  # Just check first control


# Run diagnostic first
diagnose_run_paths()