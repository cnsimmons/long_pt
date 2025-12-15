#!/usr/bin/env python3
"""
Searchlight Decoding - Pairwise Category Comparisons
=====================================================
Face vs Word, Face vs Object, Object vs House, etc.
More discriminative than category vs scramble.
"""

import os
import sys
import argparse
import numpy as np
import nibabel as nib
import pandas as pd
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
CSV_FILE = Path('/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv')
OUTPUT_DIR = Path('/user_data/csimmon2/git_repos/long_pt/B_analyses/searchlight_decoding_pairwise')

CATEGORIES = ['Face', 'Object', 'House', 'Word']

# Pairwise comparisons of interest
COMPARISONS = [
    ('Face', 'Word'),    # Unilateral vs Unilateral
    ('Face', 'Object'),  # Unilateral vs Bilateral
    ('Face', 'House'),   # Unilateral vs Bilateral
    ('Word', 'Object'),  # Unilateral vs Bilateral
    ('Word', 'House'),   # Unilateral vs Bilateral
    ('Object', 'House'), # Bilateral vs Bilateral
]

# Category types for interpretation
COMPARISON_TYPES = {
    ('Face', 'Word'): 'uni_vs_uni',
    ('Face', 'Object'): 'uni_vs_bil',
    ('Face', 'House'): 'uni_vs_bil',
    ('Word', 'Object'): 'uni_vs_bil',
    ('Word', 'House'): 'uni_vs_bil',
    ('Object', 'House'): 'bil_vs_bil',
}

TR = 2.0
HRF_DELAY = 4
SL_RADIUS = 6
ACCURACY_THRESHOLD = 0.55

SESSION_ANCHOR_EXCEPTIONS = {
    'sub-010': '02',
    'sub-018': '02',
    'sub-068': '02'
}

# ============================================================================
# CSV & Info Functions
# ============================================================================

def get_subject_info_from_csv(sub):
    if not CSV_FILE.exists():
        print(f"CRITICAL: CSV file not found at {CSV_FILE}")
        sys.exit(1)
    df = pd.read_csv(CSV_FILE)
    row = df[df['sub'] == sub]
    if row.empty:
        return {'intact_hemi': 'l', 'group': 'unknown'}
    hemi_full = row.iloc[0]['intact_hemi']
    hemi = 'l' if 'left' in str(hemi_full).lower() else 'r' if 'right' in str(hemi_full).lower() else 'l'
    return {'intact_hemi': hemi, 'group': row.iloc[0]['group']}


def get_sessions(sub):
    anchor = SESSION_ANCHOR_EXCEPTIONS.get(sub, '01')
    if sub == 'sub-007':
        return '01', '03'
    return anchor, f"{int(anchor) + 1:02d}"


# ============================================================================
# Data Loading
# ============================================================================

def get_available_runs(sub, ses):
    func_base = BASE_DIR / sub / f'ses-{ses}' / 'derivatives' / 'fsl' / 'loc'
    runs = []
    for run_dir in sorted(func_base.glob('run-*')):
        func_file = run_dir / '1stLevel.feat' / 'filtered_func_data_reg.nii.gz'
        if func_file.exists():
            runs.append(run_dir.name)
    return runs


def load_functional_data(sub, ses, run, use_registered=False):
    func_dir = (BASE_DIR / sub / f'ses-{ses}' / 'derivatives' / 'fsl' / 'loc' /
                run / '1stLevel.feat')
    anchor_ses, comp_ses = get_sessions(sub)
    
    if use_registered and ses == comp_ses:
        func_file = func_dir / f'filtered_func_data_reg_ses{anchor_ses}.nii.gz'
        if not func_file.exists():
            print(f"    Warning: Registered file not found")
            func_file = func_dir / 'filtered_func_data_reg.nii.gz'
    else:
        func_file = func_dir / 'filtered_func_data_reg.nii.gz'
    
    if not func_file.exists():
        return None, None
    img = nib.load(func_file)
    return img.get_fdata(), img.affine


def load_timing(sub, ses, run, category):
    sub_num = sub.replace('sub-', '')
    timing_file = BASE_DIR / sub / f'ses-{ses}' / 'timing' / f'catloc_{sub_num}_{run}_{category}.txt'
    if timing_file.exists():
        return np.loadtxt(timing_file)
    return None


def load_mask(sub, ses, hemi, categories):
    """Load union of masks for both categories in comparison."""
    anchor_ses, _ = get_sessions(sub)
    
    masks = []
    affine = None
    for cat in categories:
        mask_file = (BASE_DIR / sub / f'ses-{anchor_ses}' / 'ROIs' / 
                     f'{hemi}_{cat.lower()}_searchmask.nii.gz')
        if mask_file.exists():
            img = nib.load(mask_file)
            masks.append(img.get_fdata() > 0)
            if affine is None:
                affine = img.affine
    
    if not masks:
        return None, None
    
    # Union of masks
    union_mask = masks[0]
    for m in masks[1:]:
        union_mask = union_mask | m
    
    return union_mask, affine


# ============================================================================
# Pattern Extraction
# ============================================================================

def extract_blocks(func_data, timing, tr=TR, hrf_delay=HRF_DELAY):
    patterns = []
    for onset, duration, _ in timing:
        start_vol = int((onset + hrf_delay) / tr)
        end_vol = int((onset + duration + hrf_delay) / tr)
        end_vol = min(end_vol, func_data.shape[-1])
        if start_vol < end_vol:
            patterns.append(np.mean(func_data[..., start_vol:end_vol], axis=-1))
    return np.array(patterns) if patterns else None


def extract_pairwise_patterns(sub, ses, cat1, cat2, hemi, use_registered=False):
    """Extract patterns for two categories."""
    runs = get_available_runs(sub, ses)
    all_patterns, all_labels, all_runs = [], [], []
    
    for run in runs:
        func_data, _ = load_functional_data(sub, ses, run, use_registered=use_registered)
        if func_data is None:
            continue
        run_num = int(run.split('-')[1])
        
        for cat_idx, cat in enumerate([cat1, cat2]):
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
# Searchlight Functions
# ============================================================================

def svm_cv(data, sl_mask, myrad, bcvar):
    y, groups = bcvar
    bold = data[0].reshape(-1, data[0].shape[-1]).T
    if bold.shape[1] < 5:
        return 0.5
    try:
        clf = SVC(kernel='linear')
        cv = LeaveOneGroupOut()
        return np.mean(cross_val_score(clf, bold, y, cv=cv, groups=groups))
    except:
        return 0.5


def run_searchlight(X, y, runs, mask_data):
    try:
        from brainiak.searchlight.searchlight import Searchlight, Ball
    except ImportError:
        print("ERROR: BrainIAK not available")
        return None
    
    sl = Searchlight(sl_rad=SL_RADIUS, max_blk_edge=5, shape=Ball)
    sl.distribute([np.transpose(X, (1, 2, 3, 0))], mask_data.astype(int))
    sl.broadcast((y, runs))
    return np.array(sl.run_searchlight(svm_cv, pool_size=1), dtype=float)


def svm_cross_temporal(data, sl_mask, myrad, bcvar):
    y1, y2 = bcvar
    bold1 = data[0].reshape(-1, data[0].shape[-1]).T
    bold2 = data[1].reshape(-1, data[1].shape[-1]).T
    if bold1.shape[1] < 5:
        return 0.5
    try:
        scaler = StandardScaler()
        clf = SVC(kernel='linear')
        clf.fit(scaler.fit_transform(bold1), y1)
        return clf.score(scaler.transform(bold2), y2)
    except:
        return 0.5


def run_cross_temporal_searchlight(X1, y1, X2, y2, mask_data):
    try:
        from brainiak.searchlight.searchlight import Searchlight, Ball
    except ImportError:
        return None
    
    sl = Searchlight(sl_rad=SL_RADIUS, max_blk_edge=5, shape=Ball)
    sl.distribute([np.transpose(X1, (1, 2, 3, 0)), np.transpose(X2, (1, 2, 3, 0))], 
                  mask_data.astype(int))
    sl.broadcast((y1, y2))
    return np.array(sl.run_searchlight(svm_cross_temporal, pool_size=1), dtype=float)


# ============================================================================
# Metrics
# ============================================================================

def compute_region_stats(acc_map, mask_data, threshold=ACCURACY_THRESHOLD):
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


def compute_dice(map1, map2, mask, threshold=ACCURACY_THRESHOLD):
    bin1 = (map1 > threshold) & mask
    bin2 = (map2 > threshold) & mask
    intersection = np.sum(bin1 & bin2)
    total = np.sum(bin1) + np.sum(bin2)
    return 2 * intersection / total if total > 0 else 0


# ============================================================================
# Main Analysis
# ============================================================================

def analyze_pairwise_session(sub, ses, cat1, cat2, hemi, save_maps=True):
    """Run searchlight for one pairwise comparison in one session."""
    anchor_ses, comp_ses = get_sessions(sub)
    is_comparison = (ses == comp_ses)
    comp_name = f"{cat1}_vs_{cat2}"
    comp_type = COMPARISON_TYPES.get((cat1, cat2), 'unknown')
    
    print(f"\n=== {sub} / ses-{ses} / {comp_name} / {hemi} [{comp_type}] ===")
    if is_comparison:
        print(f"  (Using registered data: ses-{ses} -> ses-{anchor_ses} space)")
    
    # Load union mask
    mask_data, affine = load_mask(sub, ses, hemi, [cat1, cat2])
    if mask_data is None:
        print(f"  ERROR: No mask found")
        return None
    print(f"  Mask voxels: {np.sum(mask_data)}")
    
    # Extract patterns
    X, y, runs = extract_pairwise_patterns(sub, ses, cat1, cat2, hemi, use_registered=is_comparison)
    if X is None:
        print(f"  ERROR: No patterns extracted")
        return None
    print(f"  Samples: {len(y)} ({np.sum(y==0)} {cat1}, {np.sum(y==1)} {cat2})")
    print(f"  Runs: {len(np.unique(runs))}")
    
    # Run searchlight
    print(f"  Running searchlight (radius={SL_RADIUS}mm)...")
    acc_map = run_searchlight(X, y, runs, mask_data)
    if acc_map is None:
        return None
    
    # Stats
    stats = compute_region_stats(acc_map, mask_data)
    stats.update({
        'subject': sub, 'session': ses, 'comparison': comp_name,
        'cat1': cat1, 'cat2': cat2, 'comparison_type': comp_type,
        'hemisphere': hemi, 'mask_voxels': int(np.sum(mask_data)),
        'n_samples': len(y), 'n_runs': len(np.unique(runs))
    })
    
    print(f"  Mean accuracy: {stats['mean_accuracy']:.3f}")
    print(f"  Peak accuracy: {stats['peak_accuracy']:.3f}")
    print(f"  Volume (>{ACCURACY_THRESHOLD}): {stats['volume_above_thresh']}")
    print(f"  Clusters: {stats['n_clusters']}")
    
    if save_maps:
        out_dir = OUTPUT_DIR / sub
        out_dir.mkdir(parents=True, exist_ok=True)
        
        out_nii = out_dir / f'{sub}_ses-{ses}_{hemi}_{comp_name.lower()}_accuracy.nii.gz'
        nib.save(nib.Nifti1Image(acc_map, affine), out_nii)
        print(f"  Saved: {out_nii.name}")
        
        out_json = out_dir / f'{sub}_ses-{ses}_{hemi}_{comp_name.lower()}_stats.json'
        with open(out_json, 'w') as f:
            json.dump(stats, f, indent=2)
    
    return {'accuracy_map': acc_map, 'stats': stats, 'mask': mask_data, 'affine': affine}


def analyze_pairwise_cross_sessions(sub, cat1, cat2, hemi, results_anchor, results_comp):
    """Cross-session analysis for pairwise comparison."""
    anchor_ses, comp_ses = get_sessions(sub)
    comp_name = f"{cat1}_vs_{cat2}"
    comp_type = COMPARISON_TYPES.get((cat1, cat2), 'unknown')
    
    print(f"\n=== Cross-session: {sub} / {comp_name} (ses-{anchor_ses} vs ses-{comp_ses}) [{comp_type}] ===")
    
    out_dir = OUTPUT_DIR / sub
    out_dir.mkdir(parents=True, exist_ok=True)
    
    mask_data = results_anchor['mask']
    affine = results_anchor['affine']
    
    # Dice
    dice = compute_dice(results_anchor['accuracy_map'], results_comp['accuracy_map'], mask_data)
    print(f"  Dice coefficient: {dice:.3f}")
    
    # Accuracy change
    acc_change = results_comp['stats']['mean_accuracy'] - results_anchor['stats']['mean_accuracy']
    print(f"  Accuracy change: {acc_change:+.3f}")
    
    # Cross-temporal
    print(f"  Running cross-temporal searchlight...")
    X1, y1, _ = extract_pairwise_patterns(sub, anchor_ses, cat1, cat2, hemi, use_registered=False)
    X2, y2, _ = extract_pairwise_patterns(sub, comp_ses, cat1, cat2, hemi, use_registered=True)
    
    ct_mean = None
    if X1 is not None and X2 is not None:
        ct_map = run_cross_temporal_searchlight(X1, y1, X2, y2, mask_data)
        if ct_map is not None:
            ct_mean = float(np.nanmean(ct_map[mask_data]))
            print(f"  Cross-temporal accuracy: {ct_mean:.3f}")
            
            out_nii = out_dir / f'{sub}_{hemi}_{comp_name.lower()}_cross_temporal.nii.gz'
            nib.save(nib.Nifti1Image(ct_map, affine), out_nii)
    else:
        print(f"  ERROR: Could not run cross-temporal")
    
    summary = {
        'subject': sub, 'comparison': comp_name, 'comparison_type': comp_type,
        'cat1': cat1, 'cat2': cat2, 'hemisphere': hemi,
        'anchor_session': anchor_ses, 'comparison_session': comp_ses,
        'anchor_mean_acc': results_anchor['stats']['mean_accuracy'],
        'comp_mean_acc': results_comp['stats']['mean_accuracy'],
        'accuracy_change': acc_change, 'dice_coefficient': dice,
        'cross_temporal_mean': ct_mean,
        'anchor_volume': results_anchor['stats']['volume_above_thresh'],
        'comp_volume': results_comp['stats']['volume_above_thresh']
    }
    
    out_json = out_dir / f'{sub}_{hemi}_{comp_name.lower()}_cross_session.json'
    with open(out_json, 'w') as f:
        json.dump(summary, f, indent=2)
    
    return summary


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Pairwise category searchlight decoding')
    parser.add_argument('--sub', type=str, required=True)
    parser.add_argument('--ses', type=str)
    parser.add_argument('--comp', type=str, help='Comparison (e.g., Face_vs_Word)')
    parser.add_argument('--hemi', type=str, choices=['l', 'r'])
    parser.add_argument('--all-comps', action='store_true', help='Run all comparisons')
    parser.add_argument('--cross-session', action='store_true')
    args = parser.parse_args()
    
    sub_info = get_subject_info_from_csv(args.sub)
    if args.hemi is None:
        args.hemi = sub_info['intact_hemi']
        print(f"-> Detected hemisphere from CSV: {args.hemi}")
    
    anchor_ses, comp_ses = get_sessions(args.sub)
    print(f"-> Sessions: anchor={anchor_ses}, comparison={comp_ses}")
    
    # Determine comparisons to run
    if args.all_comps:
        comparisons_to_run = COMPARISONS
    elif args.comp:
        parts = args.comp.split('_vs_')
        if len(parts) == 2:
            comparisons_to_run = [(parts[0], parts[1])]
        else:
            print(f"ERROR: Invalid comparison format: {args.comp}")
            sys.exit(1)
    else:
        comparisons_to_run = COMPARISONS
    
    sessions_to_run = [args.ses] if args.ses else [anchor_ses, comp_ses]
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    all_results = {}
    
    for cat1, cat2 in comparisons_to_run:
        comp_key = f"{cat1}_vs_{cat2}"
        all_results[comp_key] = {}
        
        for ses in sessions_to_run:
            result = analyze_pairwise_session(args.sub, ses, cat1, cat2, args.hemi)
            if result:
                all_results[comp_key][ses] = result
        
        # Cross-session
        if args.cross_session or (args.ses is None):
            if anchor_ses in all_results[comp_key] and comp_ses in all_results[comp_key]:
                analyze_pairwise_cross_sessions(
                    args.sub, cat1, cat2, args.hemi,
                    all_results[comp_key][anchor_ses],
                    all_results[comp_key][comp_ses]
                )
    
    print("\n=== COMPLETE ===")


if __name__ == '__main__':
    main()