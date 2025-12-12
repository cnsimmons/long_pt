"""
Group Analysis for Searchlight Decoding Results
================================================

This script performs group-level analyses to test the key hypotheses:

1. Bilateral vs Unilateral comparison in OTC patients
   - Prediction: Bilateral categories (Object, House) show MORE accuracy degradation
   - Prediction: Unilateral categories (Face, Word) show MORE spatial drift but maintain accuracy

2. Cross-temporal generalization
   - Prediction: Bilateral categories show LOWER cross-temporal accuracy (code changed)
   - Prediction: Unilateral categories show HIGHER cross-temporal accuracy (code stable, just relocated)

3. OTC vs nonOTC vs Control comparisons

Statistical approaches:
- Linear Mixed Models (following Nordt 2023)
- Bootstrap confidence intervals (following Ayzenberg 2023)
- Within-subject comparisons for longitudinal data

Author: PhD Research Project
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats
from scipy.stats import ttest_rel, ttest_ind, wilcoxon, mannwhitneyu
import warnings
warnings.filterwarnings("ignore")

# Try to import statsmodels for LMM
try:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    from statsmodels.stats.multitest import multipletests
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    print("Warning: statsmodels not available. LMM analyses will be skipped.")


# =============================================================================
# CONFIGURATION
# =============================================================================

OUTPUT_DIR = Path('/user_data/csimmon2/git_repos/long_pt/B_analyses/searchlight_decoding')
ALPHA = 0.05
N_BOOTSTRAP = 10000


# =============================================================================
# DATA LOADING
# =============================================================================

def load_results(results_path=None):
    """Load combined results CSV"""
    if results_path is None:
        results_path = OUTPUT_DIR / 'all_subjects_decoding_results.csv'
    
    return pd.read_csv(results_path)


def prepare_data_for_analysis(df):
    """Prepare data with derived variables"""
    
    # Ensure numeric columns
    numeric_cols = ['accuracy_change', 'cross_temporal_mean', 'cross_temporal_forward',
                    'cross_temporal_backward', 'dice_0.55']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Add binary coding
    df['is_bilateral'] = (df['category_type'] == 'bilateral').astype(int)
    df['is_otc'] = (df['group'] == 'OTC').astype(int)
    
    return df


# =============================================================================
# STATISTICAL TESTS
# =============================================================================

def bootstrap_ci(data, n_bootstrap=N_BOOTSTRAP, ci=95, func=np.mean):
    """Compute bootstrap confidence interval"""
    data = data.dropna()
    if len(data) < 2:
        return np.nan, np.nan, np.nan
    
    bootstrap_samples = np.random.choice(data, size=(n_bootstrap, len(data)), replace=True)
    bootstrap_stats = func(bootstrap_samples, axis=1)
    
    lower = np.percentile(bootstrap_stats, (100 - ci) / 2)
    upper = np.percentile(bootstrap_stats, 100 - (100 - ci) / 2)
    
    return func(data), lower, upper


def bootstrap_diff_test(data1, data2, n_bootstrap=N_BOOTSTRAP):
    """Test if two groups differ using bootstrap"""
    data1 = np.array(data1.dropna())
    data2 = np.array(data2.dropna())
    
    if len(data1) < 2 or len(data2) < 2:
        return np.nan, np.nan
    
    observed_diff = np.mean(data1) - np.mean(data2)
    
    # Pool data for permutation test
    pooled = np.concatenate([data1, data2])
    n1 = len(data1)
    
    null_diffs = []
    for _ in range(n_bootstrap):
        np.random.shuffle(pooled)
        null_diff = np.mean(pooled[:n1]) - np.mean(pooled[n1:])
        null_diffs.append(null_diff)
    
    null_diffs = np.array(null_diffs)
    p_value = np.mean(np.abs(null_diffs) >= np.abs(observed_diff))
    
    return observed_diff, p_value


def within_subject_test(df, group, metric, category_type1, category_type2):
    """Within-subject comparison of category types"""
    
    group_data = df[df['group'] == group]
    
    # Get data for each subject
    subjects = group_data['subject'].unique()
    
    diffs = []
    for sub in subjects:
        sub_data = group_data[group_data['subject'] == sub]
        
        type1_vals = sub_data[sub_data['category_type'] == category_type1][metric].values
        type2_vals = sub_data[sub_data['category_type'] == category_type2][metric].values
        
        if len(type1_vals) > 0 and len(type2_vals) > 0:
            # Average across categories within each type
            diff = np.nanmean(type1_vals) - np.nanmean(type2_vals)
            if not np.isnan(diff):
                diffs.append(diff)
    
    if len(diffs) < 2:
        return {'n': len(diffs), 'mean_diff': np.nan, 'p': np.nan}
    
    diffs = np.array(diffs)
    
    # One-sample t-test against 0
    t_stat, p_val = stats.ttest_1samp(diffs, 0)
    
    # Also do Wilcoxon signed-rank test (non-parametric)
    try:
        w_stat, w_pval = wilcoxon(diffs)
    except:
        w_stat, w_pval = np.nan, np.nan
    
    return {
        'n': len(diffs),
        'mean_diff': np.mean(diffs),
        'std_diff': np.std(diffs),
        't_stat': t_stat,
        'p_ttest': p_val,
        'w_stat': w_stat,
        'p_wilcoxon': w_pval
    }


def run_lmm(df, formula, group=None):
    """Run Linear Mixed Model analysis"""
    if not STATSMODELS_AVAILABLE:
        return None
    
    if group:
        df = df[df['group'] == group]
    
    df = df.dropna(subset=formula.split('~')[0].strip().split('+'))
    
    if len(df) < 10:
        return None
    
    try:
        model = smf.mixedlm(formula, df, groups=df['subject'])
        result = model.fit()
        return result
    except Exception as e:
        print(f"LMM error: {e}")
        return None


# =============================================================================
# MAIN ANALYSIS FUNCTIONS
# =============================================================================

def test_bilateral_vs_unilateral(df):
    """Test primary hypothesis: Bilateral categories show more degradation than unilateral
    
    Expected pattern based on ROI findings:
    - Bilateral: DEGRADE IN PLACE (accuracy drops, spatial maps stable)
    - Unilateral: RELOCATE but maintain code (spatial maps shift, accuracy stable)
    """
    
    print("\n" + "="*70)
    print("HYPOTHESIS 1: BILATERAL VS UNILATERAL CATEGORY REORGANIZATION")
    print("="*70)
    
    results = {}
    
    # Test within OTC patients
    print("\n--- OTC Patients (n=6) ---")
    
    # Accuracy change comparison
    print("\nAccuracy Change (Session 2 - Session 1):")
    
    otc_data = df[df['group'] == 'OTC']
    bil_change = otc_data[otc_data['category_type'] == 'bilateral']['accuracy_change']
    uni_change = otc_data[otc_data['category_type'] == 'unilateral']['accuracy_change']
    
    bil_mean, bil_low, bil_high = bootstrap_ci(bil_change)
    uni_mean, uni_low, uni_high = bootstrap_ci(uni_change)
    
    print(f"  Bilateral (Object, House): {bil_mean:.3f} [{bil_low:.3f}, {bil_high:.3f}]")
    print(f"  Unilateral (Face, Word):   {uni_mean:.3f} [{uni_low:.3f}, {uni_high:.3f}]")
    
    # Within-subject test
    ws_result = within_subject_test(df, 'OTC', 'accuracy_change', 'bilateral', 'unilateral')
    print(f"  Within-subject difference: {ws_result['mean_diff']:.3f}")
    print(f"  t({ws_result['n']-1}) = {ws_result['t_stat']:.2f}, p = {ws_result['p_ttest']:.4f}")
    
    results['accuracy_change'] = {
        'bilateral_mean': bil_mean,
        'bilateral_ci': (bil_low, bil_high),
        'unilateral_mean': uni_mean,
        'unilateral_ci': (uni_low, uni_high),
        'within_subject': ws_result
    }
    
    # Cross-temporal generalization comparison
    if 'cross_temporal_mean' in df.columns:
        print("\nCross-Temporal Generalization (Train ses1 → Test ses2):")
        
        bil_cross = otc_data[otc_data['category_type'] == 'bilateral']['cross_temporal_mean']
        uni_cross = otc_data[otc_data['category_type'] == 'unilateral']['cross_temporal_mean']
        
        bil_mean, bil_low, bil_high = bootstrap_ci(bil_cross)
        uni_mean, uni_low, uni_high = bootstrap_ci(uni_cross)
        
        print(f"  Bilateral: {bil_mean:.3f} [{bil_low:.3f}, {bil_high:.3f}]")
        print(f"  Unilateral: {uni_mean:.3f} [{uni_low:.3f}, {uni_high:.3f}]")
        
        ws_result = within_subject_test(df, 'OTC', 'cross_temporal_mean', 'bilateral', 'unilateral')
        print(f"  Within-subject difference: {ws_result['mean_diff']:.3f}")
        print(f"  p = {ws_result['p_ttest']:.4f}")
        
        results['cross_temporal'] = {
            'bilateral_mean': bil_mean,
            'unilateral_mean': uni_mean,
            'within_subject': ws_result
        }
    
    # Dice overlap comparison (if available)
    if 'dice_0.55' in df.columns and df['dice_0.55'].notna().any():
        print("\nSpatial Map Overlap (Dice @ threshold=0.55):")
        
        bil_dice = otc_data[otc_data['category_type'] == 'bilateral']['dice_0.55']
        uni_dice = otc_data[otc_data['category_type'] == 'unilateral']['dice_0.55']
        
        bil_mean, bil_low, bil_high = bootstrap_ci(bil_dice)
        uni_mean, uni_low, uni_high = bootstrap_ci(uni_dice)
        
        print(f"  Bilateral: {bil_mean:.3f} [{bil_low:.3f}, {bil_high:.3f}]")
        print(f"  Unilateral: {uni_mean:.3f} [{uni_low:.3f}, {uni_high:.3f}]")
        
        ws_result = within_subject_test(df, 'OTC', 'dice_0.55', 'bilateral', 'unilateral')
        print(f"  Within-subject difference: {ws_result['mean_diff']:.3f}")
        print(f"  p = {ws_result['p_ttest']:.4f}")
        
        results['dice_overlap'] = {
            'bilateral_mean': bil_mean,
            'unilateral_mean': uni_mean,
            'within_subject': ws_result
        }
    
    return results


def test_group_comparisons(df):
    """Compare OTC vs nonOTC vs Control groups"""
    
    print("\n" + "="*70)
    print("HYPOTHESIS 2: GROUP COMPARISONS")
    print("="*70)
    
    results = {}
    
    for metric in ['accuracy_change', 'cross_temporal_mean']:
        if metric not in df.columns:
            continue
            
        print(f"\n--- {metric} ---")
        
        for cat_type in ['bilateral', 'unilateral']:
            print(f"\n  {cat_type.upper()} categories:")
            
            type_data = df[df['category_type'] == cat_type]
            
            for group in ['OTC', 'nonOTC', 'Control']:
                group_vals = type_data[type_data['group'] == group][metric]
                mean, low, high = bootstrap_ci(group_vals)
                n = group_vals.notna().sum()
                print(f"    {group}: {mean:.3f} [{low:.3f}, {high:.3f}] (n={n})")
            
            # OTC vs Control comparison
            otc_vals = type_data[type_data['group'] == 'OTC'][metric]
            ctrl_vals = type_data[type_data['group'] == 'Control'][metric]
            
            diff, p = bootstrap_diff_test(otc_vals, ctrl_vals)
            print(f"    OTC vs Control: diff = {diff:.3f}, p = {p:.4f}")
            
            results[f'{metric}_{cat_type}'] = {
                'otc_vs_control_diff': diff,
                'otc_vs_control_p': p
            }
    
    return results


def test_category_specific(df):
    """Test effects for each specific category"""
    
    print("\n" + "="*70)
    print("CATEGORY-SPECIFIC ANALYSES")
    print("="*70)
    
    categories = df['category'].unique()
    results = {}
    
    for category in categories:
        cat_data = df[df['category'] == category]
        print(f"\n--- {category.upper()} ---")
        
        for group in ['OTC', 'nonOTC', 'Control']:
            group_data = cat_data[cat_data['group'] == group]
            
            if 'accuracy_change' in group_data.columns:
                acc_change = group_data['accuracy_change']
                mean, low, high = bootstrap_ci(acc_change)
                print(f"  {group} accuracy change: {mean:.3f} [{low:.3f}, {high:.3f}]")
            
            if 'cross_temporal_mean' in group_data.columns:
                cross_temp = group_data['cross_temporal_mean']
                mean, low, high = bootstrap_ci(cross_temp)
                print(f"  {group} cross-temporal: {mean:.3f} [{low:.3f}, {high:.3f}]")
    
    return results


def run_lmm_analyses(df):
    """Run Linear Mixed Model analyses"""
    
    if not STATSMODELS_AVAILABLE:
        print("\nSkipping LMM analyses (statsmodels not available)")
        return None
    
    print("\n" + "="*70)
    print("LINEAR MIXED MODEL ANALYSES")
    print("="*70)
    
    results = {}
    
    # Model 1: Accuracy change ~ category_type + group, random intercept per subject
    print("\n--- Model: accuracy_change ~ category_type * group ---")
    
    model_df = df.dropna(subset=['accuracy_change', 'category_type', 'group', 'subject'])
    
    if len(model_df) > 0:
        try:
            formula = "accuracy_change ~ C(category_type) * C(group)"
            model = smf.mixedlm(formula, model_df, groups=model_df['subject'])
            result = model.fit()
            print(result.summary())
            results['accuracy_change_lmm'] = result
        except Exception as e:
            print(f"Error: {e}")
    
    # Model 2: Cross-temporal ~ category_type + group
    if 'cross_temporal_mean' in df.columns:
        print("\n--- Model: cross_temporal_mean ~ category_type * group ---")
        
        model_df = df.dropna(subset=['cross_temporal_mean', 'category_type', 'group', 'subject'])
        
        if len(model_df) > 0:
            try:
                formula = "cross_temporal_mean ~ C(category_type) * C(group)"
                model = smf.mixedlm(formula, model_df, groups=model_df['subject'])
                result = model.fit()
                print(result.summary())
                results['cross_temporal_lmm'] = result
            except Exception as e:
                print(f"Error: {e}")
    
    return results


def generate_summary_table(df):
    """Generate summary table matching the ROI measures format from handoff"""
    
    print("\n" + "="*70)
    print("SUMMARY TABLE (matches ROI format from handoff)")
    print("="*70)
    
    # Create summary for OTC patients only
    otc_data = df[df['group'] == 'OTC']
    
    rows = []
    
    for metric in ['accuracy_change', 'cross_temporal_mean', 'dice_0.55']:
        if metric not in df.columns or df[metric].isna().all():
            continue
        
        bil = otc_data[otc_data['category_type'] == 'bilateral'][metric].dropna()
        uni = otc_data[otc_data['category_type'] == 'unilateral'][metric].dropna()
        
        bil_mean = bil.mean() if len(bil) > 0 else np.nan
        uni_mean = uni.mean() if len(uni) > 0 else np.nan
        gap = bil_mean - uni_mean
        
        # Within-subject test
        ws_result = within_subject_test(df, 'OTC', metric, 'bilateral', 'unilateral')
        
        # Bootstrap comparison vs nonOTC
        nonotc_bil = df[(df['group'] == 'nonOTC') & (df['category_type'] == 'bilateral')][metric]
        diff, bootstrap_p = bootstrap_diff_test(bil, nonotc_bil)
        
        row = {
            'Measure': metric,
            'OTC_Bilateral': bil_mean,
            'OTC_Unilateral': uni_mean,
            'Gap': gap,
            'p_within_subject': ws_result['p_ttest'],
            'p_vs_nonOTC': bootstrap_p
        }
        rows.append(row)
    
    summary_df = pd.DataFrame(rows)
    
    print("\n" + summary_df.to_string(index=False))
    
    # Save
    summary_path = OUTPUT_DIR / 'summary_table.csv'
    summary_df.to_csv(summary_path, index=False)
    print(f"\nSaved to: {summary_path}")
    
    return summary_df


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main(results_path=None):
    """Run all group-level analyses"""
    
    print("\n" + "="*70)
    print("SEARCHLIGHT DECODING GROUP ANALYSIS")
    print("="*70)
    
    # Load data
    df = load_results(results_path)
    df = prepare_data_for_analysis(df)
    
    print(f"\nLoaded {len(df)} observations from {df['subject'].nunique()} subjects")
    print(f"Groups: {df['group'].value_counts().to_dict()}")
    
    # Run analyses
    results = {}
    
    results['bilateral_vs_unilateral'] = test_bilateral_vs_unilateral(df)
    results['group_comparisons'] = test_group_comparisons(df)
    results['category_specific'] = test_category_specific(df)
    
    if STATSMODELS_AVAILABLE:
        results['lmm'] = run_lmm_analyses(df)
    
    summary = generate_summary_table(df)
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    
    # Key findings summary
    print("\n" + "-"*70)
    print("KEY FINDINGS INTERPRETATION:")
    print("-"*70)
    
    print("""
Based on the handoff document hypotheses:

EXPECTED PATTERN:
| Measure                | Bilateral      | Unilateral     | Interpretation          |
|------------------------|----------------|----------------|-------------------------|
| Accuracy Change        | NEGATIVE       | STABLE/SMALL   | Bilateral DEGRADES      |
| Cross-Temporal Acc     | LOW            | HIGH           | Bilateral code CHANGED  |
| Spatial Overlap (Dice) | HIGH           | LOW            | Unilateral MOVES        |

This pattern would confirm that:
- Bilateral representations DEGRADE IN PLACE
- Unilateral representations RELOCATE but maintain their character

ALIGNMENT WITH ROI MEASURES:
| ROI Measure            | Decoding Equivalent    | Expected Pattern           |
|------------------------|------------------------|----------------------------|
| Spatial Relocation (mm)| Map Overlap (Dice)     | Unilateral moves more      |
| Selectivity Change     | Accuracy Change        | Bilateral degrades more    |
| Geometry Preservation  | Cross-temporal accuracy| Bilateral loses generalize |
    """)
    
    return df, results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        results_path = sys.argv[1]
    else:
        results_path = None
    
    df, results = main(results_path)
