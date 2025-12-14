#!/usr/bin/env python3
"""
Searchlight Decoding for Longitudinal Visual Category Analysis
===============================================================

Based on notebook cells 1-10. Runs category vs scramble decoding 
within anatomical search masks for each session.

Usage:
    python searchlight_decoding_cluster.py --sub sub-004 --ses 01 --cat Face --hemi l
    
For all categories in one session:
    python searchlight_decoding_cluster.py --sub sub-004 --ses 01 --hemi l --all-cats

SLURM submission:
    sbatch submit_searchlight.sh

Author: Long_PT Project
Date: December 2024
"""

import os
import sys
import argparse
import numpy as np
import nibabel as nib
from pathlib import Path
from scipy.ndimage import label
from sklearn.svm import SVC
from sklearn.model_selection import cross_val_score, LeaveOneGroupOut
from sklearn.preprocessing import StandardScaler
import json
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# Configuration
# ============================================================================

BASE_DIR = Path('/user_data/csimmon2/long_pt')
OUTPUT_DIR = Path('/user_data/csimmon2/git_repos/long_pt/B_analyses/searchlight_decoding')

CATEGORIES = ['Face', 'Object', 'House', 'Word']
CATEGORY_TYPES = {'Face': 'unilateral', 'Word': 'unilateral', 
                  'Object': 'bilateral', 'House': 'bilateral'}

# Timing parameters
TR = 2.0
HRF_DELAY = 4  # seconds

# Searchlight parameters
SL_RADIUS = 6  # mm
ACCURACY_THRESHOLD = 0.55


# ============================================================================
# Data Loading Functions (Cells 1-3)
# ============================================================================

def get_subject_info(sub):
    """Get subject-specific info."""
    info = {
        'sub-004': {'intact_hemi': 'l'},
        'sub-008': {'intact_hemi': 'l'},
        'sub-010': {'intact_hemi': 'l'},
        'sub-017': {'intact_hemi': 'r'},
        'sub-021': {'intact_hemi': 'r'},
        'sub-079': {'intact_hemi': 'r'},
    }
    return info.get(sub, {'intact_hemi': 'l'})


def get_available_runs(sub, ses):
    """Find runs with functional data."""
    func_base = BASE_DIR / sub / f'ses-{ses}' / 'derivatives' / 'fsl' / 'loc'
    runs = []
    for run_dir in sorted(func_base.glob('run-*')):
        func_file = run_dir / '1stLevel.feat' / 'filtered_func_data_reg.nii.gz'
        if func_file.exists():
            runs.append(run_dir.name)
    return runs


def load_functional_data(sub, ses, run):
    """Load 4D functional data."""
    func_file = (BASE_DIR / sub / f'ses-{ses}' / 'derivatives' / 'fsl' / 'loc' /
                 run / '1stLevel.feat' / 'filtered_func_data_reg.nii.gz')
    img = nib.load(func_file)
    return img.get_fdata(), img.affine


def load_timing(sub, ses, run, category):
    """Load timing file for a category."""
    sub_num = sub.replace('sub-', '')
    timing_file = BASE_DIR / sub / f'ses-{ses}' / 'timing' / f'catloc_{sub_num}_{run}_{category}.txt'
    if timing_file.exists():
        return np.loadtxt(timing_file)
    return None


def load_mask(sub, ses, hemi, category):
    """Load search mask. Try ses-01 first (consistent across sessions)."""
    for s in ['01', ses]:
        mask_file = (BASE_DIR / sub / f'ses-{s}' / 'ROIs' / 
                     f'{hemi}_{category.lower()}_searchmask.nii.gz')
        if mask_file.exists():
            img = nib.load(mask_file)
            return img.get_fdata() > 0, img.affine, img
    return None, None, None


# ============================================================================
# Pattern Extraction (Cell 2)
# ============================================================================

def extract_blocks(func_data, timing, tr=TR, hrf_delay=HRF_DELAY):
    """Extract mean pattern for each block."""
    patterns = []
    for onset, duration, _ in timing:
        start_vol = int((onset + hrf_delay) / tr)
        end_vol = int((onset + duration + hrf_delay) / tr)
        end_vol = min(end_vol, func_data.shape[-1])
        if start_vol < end_vol:
            block_mean = np.mean(func_data[..., start_vol:end_vol], axis=-1)
            patterns.append(block_mean)
    return np.array(patterns) if patterns else None


def extract_session_patterns(sub, ses, category, hemi):
    """Extract all patterns for a category in a session."""
    runs = get_available_runs(sub, ses)
    
    all_patterns = []
    all_labels = []
    all_runs = []
    
    for run in runs:
        func_data, _ = load_functional_data(sub, ses, run)
        run_num = int(run.split('-')[1])
        
        for cat_idx, cat in enumerate([category, 'Scramble']):
            timing = load_timing(sub, ses, run, cat)
            if timing is None:
                continue
            
            patterns = extract_blocks(func_data, timing)
            if patterns is None:
                continue
            
            for p in patterns:
                all_patterns.append(p)
                all_labels.append(cat_idx)
                all_runs.append(run_num)
    
    if not all_patterns:
        return None, None, None
    
    return np.array(all_patterns), np.array(all_labels), np.array(all_runs)


# ============================================================================
# Searchlight Functions (Cells 4-5)
# ============================================================================

def svm_cv(data, sl_mask, myrad, bcvar):
    """SVM classification at each searchlight."""
    y, groups = bcvar
    bold = data[0].reshape(-1, data[0].shape[-1]).T
    
    if bold.shape[1] < 5:
        return 0.5
    
    clf = SVC(kernel='linear')
    cv = LeaveOneGroupOut()
    try:
        scores = cross_val_score(clf, bold, y, cv=cv, groups=groups)
        return np.mean(scores)
    except:
        return 0.5


def run_searchlight(X, y, runs, mask_data, radius=SL_RADIUS):
    """Run BrainIAK searchlight."""
    try:
        from brainiak.searchlight.searchlight import Searchlight, Ball
    except ImportError:
        print("ERROR: BrainIAK not available. Install with: conda install -c brainiak brainiak")
        return None
    
    data_4d = np.transpose(X, (1, 2, 3, 0))
    
    sl = Searchlight(sl_rad=radius, max_blk_edge=5, shape=Ball)
    sl.distribute([data_4d], mask_data.astype(int))
    sl.broadcast((y, runs))
    
    results = sl.run_searchlight(svm_cv, pool_size=1)
    return np.array(results, dtype=float)


# ============================================================================
# Cross-Temporal Analysis (Cell 8)
# ============================================================================

def svm_cross_temporal(data, sl_mask, myrad, bcvar):
    """Train on ses-01, test on ses-02."""
    y1, y2 = bcvar
    bold1 = data[0].reshape(-1, data[0].shape[-1]).T
    bold2 = data[1].reshape(-1, data[1].shape[-1]).T
    
    if bold1.shape[1] < 5:
        return 0.5
    
    try:
        scaler = StandardScaler()
        bold1_scaled = scaler.fit_transform(bold1)
        bold2_scaled = scaler.transform(bold2)
        
        clf = SVC(kernel='linear')
        clf.fit(bold1_scaled, y1)
        return clf.score(bold2_scaled, y2)
    except:
        return 0.5


def run_cross_temporal_searchlight(X1, y1, X2, y2, mask_data, radius=SL_RADIUS):
    """Cross-temporal searchlight: train ses-01, test ses-02."""
    try:
        from brainiak.searchlight.searchlight import Searchlight, Ball
    except ImportError:
        return None
    
    data1_4d = np.transpose(X1, (1, 2, 3, 0))
    data2_4d = np.transpose(X2, (1, 2, 3, 0))
    
    sl = Searchlight(sl_rad=radius, max_blk_edge=5, shape=Ball)
    sl.distribute([data1_4d, data2_4d], mask_data.astype(int))
    sl.broadcast((y1, y2))
    
    results = sl.run_searchlight(svm_cross_temporal, pool_size=1)
    return np.array(results, dtype=float)


# ============================================================================
# Analysis Metrics (Cells 7, 10)
# ============================================================================

def compute_dice(map1, map2, mask, threshold=ACCURACY_THRESHOLD):
    """Dice coefficient between thresholded accuracy maps."""
    bin1 = (map1 > threshold) & mask
    bin2 = (map2 > threshold) & mask
    intersection = np.sum(bin1 & bin2)
    total = np.sum(bin1) + np.sum(bin2)
    return 2 * intersection / total if total > 0 else 0


def compute_region_stats(acc_map, mask_data, threshold=ACCURACY_THRESHOLD):
    """Compute decodable region characteristics (Cell 10)."""
    acc_masked = acc_map.copy()
    acc_masked[~mask_data] = np.nan
    
    above_thresh = (acc_masked > threshold) & mask_data
    vol = int(np.sum(above_thresh))
    
    labeled, n_clusters = label(above_thresh)
    
    largest_cluster = 0
    if n_clusters > 0:
        cluster_sizes = [np.sum(labeled == i) for i in range(1, n_clusters + 1)]
        largest_cluster = max(cluster_sizes)
    
    return {
        'volume_above_thresh': vol,
        'n_clusters': int(n_clusters),
        'largest_cluster': int(largest_cluster),
        'peak_accuracy': float(np.nanmax(acc_masked)),
        'mean_accuracy': float(np.nanmean(acc_masked[mask_data]))
    }


def get_peak_location(acc_map, mask_data):
    """Get peak accuracy location."""
    acc_masked = acc_map.copy()
    acc_masked[~mask_data] = np.nan
    peak = np.unravel_index(np.nanargmax(acc_masked), acc_masked.shape)
    return peak


# ============================================================================
# Main Analysis Functions
# ============================================================================

def analyze_single_session(sub, ses, category, hemi, save_maps=True):
    """Run searchlight for one category in one session."""
    print(f"\n=== {sub} / ses-{ses} / {category} / {hemi} ===")
    
    # Load mask
    mask_data, affine, mask_img = load_mask(sub, ses, hemi, category)
    if mask_data is None:
        print(f"  ERROR: No mask found")
        return None
    print(f"  Mask voxels: {np.sum(mask_data)}")
    
    # Extract patterns
    X, y, runs = extract_session_patterns(sub, ses, category, hemi)
    if X is None:
        print(f"  ERROR: No patterns extracted")
        return None
    print(f"  Samples: {len(y)} ({np.sum(y==0)} {category}, {np.sum(y==1)} Scramble)")
    print(f"  Runs: {len(np.unique(runs))}")
    
    # Run searchlight
    print(f"  Running searchlight (radius={SL_RADIUS}mm)...")
    acc_map = run_searchlight(X, y, runs, mask_data)
    if acc_map is None:
        return None
    
    # Compute stats
    stats = compute_region_stats(acc_map, mask_data)
    stats['subject'] = sub
    stats['session'] = ses
    stats['category'] = category
    stats['hemisphere'] = hemi
    stats['category_type'] = CATEGORY_TYPES.get(category, 'unknown')
    
    print(f"  Mean accuracy: {stats['mean_accuracy']:.3f}")
    print(f"  Peak accuracy: {stats['peak_accuracy']:.3f}")
    print(f"  Volume (>{ACCURACY_THRESHOLD}): {stats['volume_above_thresh']}")
    print(f"  Clusters: {stats['n_clusters']}")
    
    # Save outputs
    if save_maps:
        out_dir = OUTPUT_DIR / sub
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Save accuracy map
        out_nii = out_dir / f'{sub}_ses-{ses}_{hemi}_{category.lower()}_accuracy.nii.gz'
        out_img = nib.Nifti1Image(acc_map, affine)
        nib.save(out_img, out_nii)
        print(f"  Saved: {out_nii.name}")
        
        # Save stats
        out_json = out_dir / f'{sub}_ses-{ses}_{hemi}_{category.lower()}_stats.json'
        with open(out_json, 'w') as f:
            json.dump(stats, f, indent=2)
    
    return {'accuracy_map': acc_map, 'stats': stats, 'mask': mask_data, 'affine': affine}


def analyze_cross_sessions(sub, category, hemi, results_ses01, results_ses02):
    """Compare sessions and run cross-temporal analysis (Cells 7-9)."""
    print(f"\n=== Cross-session analysis: {sub} / {category} ===")
    
    out_dir = OUTPUT_DIR / sub
    out_dir.mkdir(parents=True, exist_ok=True)
    
    mask_data = results_ses01['mask']
    affine = results_ses01['affine']
    
    # Dice coefficient
    dice = compute_dice(
        results_ses01['accuracy_map'],
        results_ses02['accuracy_map'],
        mask_data
    )
    print(f"  Dice coefficient: {dice:.3f}")
    
    # Accuracy change
    acc_change = results_ses02['stats']['mean_accuracy'] - results_ses01['stats']['mean_accuracy']
    print(f"  Accuracy change: {acc_change:+.3f}")
    
    # Cross-temporal searchlight
    print(f"  Running cross-temporal searchlight...")
    X1, y1, _ = extract_session_patterns(sub, '01', category, hemi)
    X2, y2, _ = extract_session_patterns(sub, '02', category, hemi)
    
    if X1 is not None and X2 is not None:
        ct_map = run_cross_temporal_searchlight(X1, y1, X2, y2, mask_data)
        if ct_map is not None:
            ct_mean = np.nanmean(ct_map[mask_data])
            print(f"  Cross-temporal accuracy: {ct_mean:.3f}")
            
            # Save cross-temporal map
            out_nii = out_dir / f'{sub}_{hemi}_{category.lower()}_cross_temporal.nii.gz'
            out_img = nib.Nifti1Image(ct_map, affine)
            nib.save(out_img, out_nii)
    
    # Summary stats
    summary = {
        'subject': sub,
        'category': category,
        'hemisphere': hemi,
        'category_type': CATEGORY_TYPES.get(category, 'unknown'),
        'ses01_mean_acc': results_ses01['stats']['mean_accuracy'],
        'ses02_mean_acc': results_ses02['stats']['mean_accuracy'],
        'accuracy_change': acc_change,
        'dice_coefficient': dice,
        'cross_temporal_mean': ct_mean if 'ct_mean' in dir() else None
    }
    
    out_json = out_dir / f'{sub}_{hemi}_{category.lower()}_cross_session.json'
    with open(out_json, 'w') as f:
        json.dump(summary, f, indent=2)
    
    return summary


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Searchlight decoding for longitudinal analysis')
    parser.add_argument('--sub', type=str, required=True, help='Subject ID (e.g., sub-004)')
    parser.add_argument('--ses', type=str, help='Session (01 or 02). If omitted, runs both.')
    parser.add_argument('--cat', type=str, choices=CATEGORIES, help='Category')
    parser.add_argument('--hemi', type=str, choices=['l', 'r'], help='Hemisphere')
    parser.add_argument('--all-cats', action='store_true', help='Run all categories')
    parser.add_argument('--cross-session', action='store_true', help='Run cross-session analysis')
    
    args = parser.parse_args()
    
    # Defaults
    if args.hemi is None:
        args.hemi = get_subject_info(args.sub)['intact_hemi']
    
    categories_to_run = CATEGORIES if args.all_cats else ([args.cat] if args.cat else CATEGORIES)
    sessions_to_run = ['01', '02'] if args.ses is None else [args.ses]
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    all_results = {}
    
    for cat in categories_to_run:
        all_results[cat] = {}
        
        for ses in sessions_to_run:
            result = analyze_single_session(args.sub, ses, cat, args.hemi)
            if result:
                all_results[cat][ses] = result
        
        # Cross-session analysis if both sessions available
        if args.cross_session or (args.ses is None):
            if '01' in all_results[cat] and '02' in all_results[cat]:
                analyze_cross_sessions(
                    args.sub, cat, args.hemi,
                    all_results[cat]['01'],
                    all_results[cat]['02']
                )
    
    print("\n=== COMPLETE ===")


if __name__ == '__main__':
    main()
