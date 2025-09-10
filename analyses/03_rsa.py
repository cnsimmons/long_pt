"""
Representational Similarity Analysis (RSA) for VOTC Plasticity Study
===================================================================

This script implements the RSA analysis from:
"Cross-sectional and longitudinal changes in category-selectivity 
in visual cortex following pediatric cortical resection"

Key analyses:
1. Compute representational similarity matrices for each ROI
2. Calculate preferred vs non-preferred category correlations
3. Fisher-transform correlations (matching MATLAB implementation)
4. Prepare data for Crawford t-tests and figure recreation
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
from scipy import stats
from scipy.spatial.distance import pdist, squareform
from sklearn.metrics import pairwise_distances
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION
# =============================================================================

# Define paths
BASE_DIR = Path("/user_data/csimmon2/long_pt")
ANALYSES_DIR = BASE_DIR / "analyses"
BETA_DIR = ANALYSES_DIR / "beta_extraction"
RSA_DIR = ANALYSES_DIR / "rsa_analysis"
RSA_DIR.mkdir(exist_ok=True)

# Experimental conditions (matching paper)
CONDITIONS = ['faces', 'houses', 'objects', 'words', 'scrambled']
CONDITION_INDICES = {condition: idx for idx, condition in enumerate(CONDITIONS)}

# ROI category preferences (from paper)
ROI_PREFERENCES = {
    'lFFA': 'faces', 'rFFA': 'faces',
    'lSTS': 'faces', 'rSTS': 'faces',
    'lPPA': 'houses', 'rPPA': 'houses', 
    'lTOS': 'houses', 'rTOS': 'houses',
    'lLOC': 'objects', 'rLOC': 'objects',
    'lPF': 'objects', 'rPF': 'objects',
    'VWFA': 'words',
    'STG': 'words',
    'IFG': 'words',
    'lEVC': 'objects',  # Early visual cortex - using objects as preference
    'rEVC': 'objects'
}

print("=== VOTC Plasticity RSA Analysis ===")
print(f"Conditions: {CONDITIONS}")
print(f"ROI preferences defined for {len(ROI_PREFERENCES)} ROI types")

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def fisher_transform(r):
    """
    Apply Fisher z-transformation to correlation coefficients.
    Matches MATLAB implementation: 0.5*log((1+r)/(1-r))
    """
    # Clip values to avoid inf
    r = np.clip(r, -0.99999, 0.99999)
    return 0.5 * np.log((1 + r) / (1 - r))

def compute_representational_similarity(beta_matrix, distance_metric='correlation'):
    """
    Compute representational similarity matrix from beta values.
    
    Parameters:
    -----------
    beta_matrix : np.array, shape (n_conditions, n_voxels)
        Beta values for each condition
    distance_metric : str
        Distance metric for computing similarity
        
    Returns:
    --------
    similarity_matrix : np.array, shape (n_conditions, n_conditions)
        Representational similarity matrix (correlations)
    """
    if distance_metric == 'correlation':
        # Compute correlation-based similarity
        similarity_matrix = np.corrcoef(beta_matrix)
    else:
        # Compute distance-based dissimilarity, then convert to similarity
        distances = pairwise_distances(beta_matrix, metric=distance_metric)
        # Convert distances to similarities (higher similarity = lower distance)
        similarity_matrix = 1 - (distances / np.max(distances))
    
    return similarity_matrix

def extract_preferred_vs_nonpreferred_correlation(similarity_matrix, roi_name, conditions):
    """
    Extract correlation between preferred category and all other categories.
    This matches the analysis in the paper's MATLAB code.
    
    Parameters:
    -----------
    similarity_matrix : np.array, shape (n_conditions, n_conditions)
        Representational similarity matrix
    roi_name : str
        Name of the ROI
    conditions : list
        List of condition names
        
    Returns:
    --------
    correlation : float
        Mean correlation between preferred category and all other categories
    """
    if roi_name not in ROI_PREFERENCES:
        return np.nan
    
    preferred_category = ROI_PREFERENCES[roi_name]
    
    if preferred_category not in conditions:
        return np.nan
    
    # Get index of preferred category
    preferred_idx = conditions.index(preferred_category)
    
    # Get correlations between preferred category and all others
    preferred_row = similarity_matrix[preferred_idx, :]
    
    # Exclude self-correlation and compute mean
    other_indices = [i for i in range(len(conditions)) if i != preferred_idx]
    correlations_with_others = preferred_row[other_indices]
    
    return np.mean(correlations_with_others)

# =============================================================================
# LOAD DATA
# =============================================================================

print("\n" + "="*50)
print("LOADING DATA")
print("="*50)

# Load session inventory
session_inventory = pd.read_csv(BETA_DIR / "session_inventory.csv")
print(f"Found {len(session_inventory)} sessions")

# Load ROI coordinates for reference
roi_coords = pd.read_csv(ANALYSES_DIR / "roi_extraction" / "peak_roi_coordinates.csv")
print(f"Found {len(roi_coords)} ROI coordinates")

# =============================================================================
# RSA COMPUTATION
# =============================================================================

print("\n" + "="*50)
print("COMPUTING RSA")
print("="*50)

rsa_results = []
failed_sessions = []

print("Processing sessions...")
for idx, row in session_inventory.iterrows():
    session_id = f"{row['subject']}_{row['session']}"
    session_dir = BETA_DIR / row['session_dir']
    
    try:
        # Load beta matrix and ROI info
        beta_matrix = np.load(session_dir / "beta_matrix.npy")
        roi_info = pd.read_csv(session_dir / "roi_info.csv")
        
        print(f"  Processing {session_id}: {beta_matrix.shape[0]}×{beta_matrix.shape[1]} matrix")
        
        # Process each ROI
        for roi_idx, roi_row in roi_info.iterrows():
            roi_name = roi_row['roi_name']
            
            # Extract beta values for this ROI (all conditions)
            roi_betas = beta_matrix[:, roi_idx]
            
            # Skip if ROI has invalid data
            if np.any(np.isnan(roi_betas)) or np.all(roi_betas == 0):
                continue
            
            # Create single-ROI matrix for similarity computation
            # Reshape to (n_conditions, 1) for correlation computation
            roi_matrix = roi_betas.reshape(-1, 1)
            
            # For RSA with single ROI, we need to compare across conditions
            # We'll compute the correlation pattern across conditions
            
            # Method 1: Direct approach - correlation between preferred and non-preferred
            correlation = extract_preferred_vs_nonpreferred_correlation(
                np.corrcoef(roi_betas.reshape(1, -1)), roi_name, CONDITIONS
            )
            
            # Method 2: Alternative - correlation between preferred category beta and others
            if roi_name in ROI_PREFERENCES:
                preferred_category = ROI_PREFERENCES[roi_name]
                preferred_idx = CONDITION_INDICES.get(preferred_category)
                
                if preferred_idx is not None:
                    preferred_beta = roi_betas[preferred_idx]
                    other_betas = np.concatenate([
                        roi_betas[:preferred_idx], 
                        roi_betas[preferred_idx+1:]
                    ])
                    
                    # Correlation between preferred beta and mean of others
                    if len(other_betas) > 0:
                        correlation_alt = np.corrcoef([preferred_beta], [np.mean(other_betas)])[0, 1]
                    else:
                        correlation_alt = np.nan
                else:
                    correlation_alt = np.nan
            else:
                correlation_alt = np.nan
            
            # Store results
            result = {
                'subject': row['subject'],
                'session': row['session'],
                'roi_name': roi_name,
                'roi_hemisphere': roi_row.get('hemisphere', 'unknown'),
                'preferred_category': ROI_PREFERENCES.get(roi_name, 'unknown'),
                'correlation_raw': correlation_alt,  # Use alternative method
                'correlation_fisher': fisher_transform(correlation_alt),
                'beta_faces': roi_betas[CONDITION_INDICES['faces']],
                'beta_houses': roi_betas[CONDITION_INDICES['houses']],
                'beta_objects': roi_betas[CONDITION_INDICES['objects']],
                'beta_words': roi_betas[CONDITION_INDICES['words']],
                'beta_scrambled': roi_betas[CONDITION_INDICES['scrambled']],
                'beta_mean': np.mean(roi_betas),
                'beta_std': np.std(roi_betas)
            }
            rsa_results.append(result)
            
    except Exception as e:
        print(f"    Error processing {session_id}: {e}")
        failed_sessions.append({
            'session_id': session_id,
            'error': str(e)
        })

print(f"\nRSA computation complete:")
print(f"  Successful ROI analyses: {len(rsa_results)}")
print(f"  Failed sessions: {len(failed_sessions)}")

# Convert to DataFrame
rsa_df = pd.DataFrame(rsa_results)

if len(rsa_df) > 0:
    print(f"  Unique subjects: {rsa_df['subject'].nunique()}")
    print(f"  Unique ROI types: {rsa_df['roi_name'].nunique()}")
    print(f"  Sessions with data: {len(rsa_df.groupby(['subject', 'session']))}")

# =============================================================================
# DATA ORGANIZATION
# =============================================================================

print("\n" + "="*50)
print("ORGANIZING RSA DATA")
print("="*50)

if len(rsa_df) > 0:
    # Remove rows with invalid correlations
    valid_rsa = rsa_df.dropna(subset=['correlation_fisher']).copy()
    
    # Identify patients vs controls based on subject naming convention
    # Assuming patients have specific names like TC, UD, OT, KN, SN
    patient_subjects = ['TC', 'UD', 'OT', 'KN', 'SN']  # From paper
    control_pattern = r'^[Cc]\d+$|^\d+$'  # Control subjects: C01, C02, etc. or just numbers
    
    # Classify subjects
    def classify_subject(subject):
        if subject in patient_subjects:
            return 'patient'
        else:
            return 'control'  # Assume all others are controls for now
    
    valid_rsa['subject_type'] = valid_rsa['subject'].apply(classify_subject)
    
    # Print classification summary
    print("Subject classification:")
    classification_summary = valid_rsa.groupby(['subject', 'subject_type']).size().reset_index(name='n_rois')
    for _, row in classification_summary.iterrows():
        print(f"  {row['subject']}: {row['subject_type']} ({row['n_rois']} ROI measurements)")
    
    # Separate patients and controls
    patients_rsa = valid_rsa[valid_rsa['subject_type'] == 'patient'].copy()
    controls_rsa = valid_rsa[valid_rsa['subject_type'] == 'control'].copy()
    
    print(f"\nData separation:")
    print(f"  Patients: {len(patients_rsa)} ROI measurements from {patients_rsa['subject'].nunique()} subjects")
    print(f"  Controls: {len(controls_rsa)} ROI measurements from {controls_rsa['subject'].nunique()} subjects")
    
    # =============================================================================
    # RSA SUMMARY STATISTICS
    # =============================================================================
    
    print("\n" + "="*50)
    print("RSA SUMMARY STATISTICS")
    print("="*50)
    
    # Summary by ROI type
    roi_summary = valid_rsa.groupby(['roi_name', 'subject_type']).agg({
        'correlation_fisher': ['count', 'mean', 'std'],
        'correlation_raw': ['mean', 'std']
    }).round(3)
    
    print("RSA correlations by ROI type:")
    print(roi_summary)
    
    # =============================================================================
    # VISUALIZATION
    # =============================================================================
    
    print("\n" + "="*50)
    print("CREATING RSA VISUALIZATIONS")
    print("="*50)
    
    # Plot 1: Fisher-transformed correlations by ROI
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('RSA Analysis Results', fontsize=16, fontweight='bold')
    
    # Box plot of Fisher-transformed correlations by ROI
    roi_order = sorted(valid_rsa['roi_name'].unique())
    
    # Separate data for patients and controls
    if len(controls_rsa) > 0:
        ax1 = axes[0, 0]
        controls_boxplot_data = [controls_rsa[controls_rsa['roi_name'] == roi]['correlation_fisher'].values 
                                for roi in roi_order]
        ax1.boxplot(controls_boxplot_data, labels=roi_order)
        ax1.set_title('Controls: Fisher-transformed Correlations by ROI')
        ax1.set_ylabel('Fisher-transformed correlation')
        ax1.tick_params(axis='x', rotation=45)
    
    if len(patients_rsa) > 0:
        ax2 = axes[0, 1]
        # For patients, use scatter plot since fewer data points
        for i, roi in enumerate(roi_order):
            roi_data = patients_rsa[patients_rsa['roi_name'] == roi]
            if len(roi_data) > 0:
                ax2.scatter([i] * len(roi_data), roi_data['correlation_fisher'], 
                           alpha=0.7, s=50)
        ax2.set_xticks(range(len(roi_order)))
        ax2.set_xticklabels(roi_order, rotation=45)
        ax2.set_title('Patients: Fisher-transformed Correlations by ROI')
        ax2.set_ylabel('Fisher-transformed correlation')
    
    # Plot 2: Beta value distributions
    ax3 = axes[1, 0]
    beta_cols = ['beta_faces', 'beta_houses', 'beta_objects', 'beta_words', 'beta_scrambled']
    beta_data = [valid_rsa[col].dropna().values for col in beta_cols]
    ax3.boxplot(beta_data, labels=['Faces', 'Houses', 'Objects', 'Words', 'Scrambled'])
    ax3.set_title('Beta Value Distributions by Condition')
    ax3.set_ylabel('Beta value')
    
    # Plot 3: Correlation distribution
    ax4 = axes[1, 1]
    if len(controls_rsa) > 0:
        ax4.hist(controls_rsa['correlation_fisher'].dropna(), alpha=0.7, 
                label='Controls', bins=20)
    if len(patients_rsa) > 0:
        ax4.hist(patients_rsa['correlation_fisher'].dropna(), alpha=0.7, 
                label='Patients', bins=20)
    ax4.set_xlabel('Fisher-transformed correlation')
    ax4.set_ylabel('Frequency')
    ax4.set_title('Distribution of RSA Correlations')
    ax4.legend()
    
    plt.tight_layout()
    plt.show()
    
    # =============================================================================
    # SAVE RESULTS
    # =============================================================================
    
    print("\n" + "="*50)
    print("SAVING RSA RESULTS")
    print("="*50)
    
    # Save main results
    output_file = RSA_DIR / "rsa_results.csv"
    valid_rsa.to_csv(output_file, index=False)
    print(f"RSA results saved to: {output_file}")
    
    # Save separate files for patients and controls
    if len(patients_rsa) > 0:
        patients_file = RSA_DIR / "rsa_patients.csv"
        patients_rsa.to_csv(patients_file, index=False)
        print(f"Patient RSA data saved to: {patients_file}")
    
    if len(controls_rsa) > 0:
        controls_file = RSA_DIR / "rsa_controls.csv"
        controls_rsa.to_csv(controls_file, index=False)
        print(f"Control RSA data saved to: {controls_file}")
    
    # Save summary statistics
    summary_stats = {
        'total_rsa_measurements': len(valid_rsa),
        'patients': {
            'subjects': patients_rsa['subject'].unique().tolist() if len(patients_rsa) > 0 else [],
            'n_measurements': len(patients_rsa),
            'mean_correlation_fisher': patients_rsa['correlation_fisher'].mean() if len(patients_rsa) > 0 else None
        },
        'controls': {
            'subjects': controls_rsa['subject'].unique().tolist() if len(controls_rsa) > 0 else [],
            'n_measurements': len(controls_rsa),
            'mean_correlation_fisher': controls_rsa['correlation_fisher'].mean() if len(controls_rsa) > 0 else None
        },
        'roi_types': valid_rsa['roi_name'].unique().tolist(),
        'conditions': CONDITIONS,
        'roi_preferences': ROI_PREFERENCES
    }
    
    summary_file = RSA_DIR / "rsa_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary_stats, f, indent=2, default=str)
    print(f"RSA summary saved to: {summary_file}")
    
    # Save failed sessions for debugging
    if failed_sessions:
        failed_file = RSA_DIR / "failed_sessions.json"
        with open(failed_file, 'w') as f:
            json.dump(failed_sessions, f, indent=2)
        print(f"Failed sessions logged to: {failed_file}")
    
    print(f"\n✓ RSA analysis complete!")
    print(f"✓ Ready for Crawford t-tests and figure recreation")
    print(f"✓ Data files saved in: {RSA_DIR}")
    
else:
    print("❌ No valid RSA data generated. Check input data quality.")

print("\n=== RSA Analysis Complete ===")