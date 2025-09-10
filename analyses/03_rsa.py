#!/usr/bin/env python3
"""
FIXED RSA Analysis for VOTC Plasticity Study
Matches the paper's actual method: correlation-based RSA
"""

import os
import numpy as np
import pandas as pd
import json
from pathlib import Path
from scipy.stats import pearsonr
from scipy.spatial.distance import pdist, squareform
import warnings
warnings.filterwarnings('ignore')

class VOTCRSAAnalyzer:
    def __init__(self, beta_extraction_dir):
        """
        Initialize RSA analyzer with extracted beta values
        
        Parameters:
        -----------
        beta_extraction_dir : str or Path
            Directory containing beta extraction results
        """
        self.beta_dir = Path(beta_extraction_dir)
        
        # Load session inventory
        inventory_file = self.beta_dir / "session_inventory.csv"
        if not inventory_file.exists():
            raise FileNotFoundError(f"Session inventory not found: {inventory_file}")
            
        self.session_inventory = pd.read_csv(inventory_file)
        
        # ROI preferences for RSA analysis (preferred vs non-preferred)
        self.roi_preferences = {
            'FFA': {'preferred': 'faces', 'non_preferred': ['houses', 'objects', 'words']},
            'STS': {'preferred': 'faces', 'non_preferred': ['houses', 'objects', 'words']},
            'PPA': {'preferred': 'houses', 'non_preferred': ['faces', 'objects', 'words']},
            'TOS': {'preferred': 'houses', 'non_preferred': ['faces', 'objects', 'words']},
            'LOC': {'preferred': 'objects', 'non_preferred': ['faces', 'houses', 'words']},
            'pF': {'preferred': 'objects', 'non_preferred': ['faces', 'houses', 'words']},
            'VWFA': {'preferred': 'words', 'non_preferred': ['faces', 'houses', 'objects']},
            'STG': {'preferred': 'words', 'non_preferred': ['faces', 'houses', 'objects']},
            'IFG': {'preferred': 'words', 'non_preferred': ['faces', 'houses', 'objects']},
            'EVC': {'preferred': 'objects', 'non_preferred': ['faces', 'houses', 'words']},
        }
        
        print(f"Loaded {len(self.session_inventory)} sessions for RSA analysis")
        print(f"Beta extraction directory: {self.beta_dir}")

    def load_session_data(self, session_id):
        """Load beta matrix and ROI info for a session"""
        session_dir = self.beta_dir / session_id
        
        # Load beta matrix
        beta_file = session_dir / "beta_matrix.npy"
        if not beta_file.exists():
            return None, None, None
            
        beta_matrix = np.load(beta_file)
        
        # Load ROI info
        roi_file = session_dir / "roi_info.csv"
        roi_info = pd.read_csv(roi_file)
        
        # Load metadata for condition order
        metadata_file = session_dir / "metadata.json"
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
            
        return beta_matrix, roi_info, metadata

    def compute_condition_correlation_matrix(self, beta_matrix):
        """
        Compute correlation matrix between conditions across ROIs
        This is the core of RSA analysis
        
        Parameters:
        -----------
        beta_matrix : np.ndarray
            Shape (n_conditions, n_rois) - beta values per condition per ROI
            
        Returns:
        --------
        correlation_matrix : np.ndarray
            Correlation matrix between conditions (n_conditions x n_conditions)
        """
        
        # Compute correlation between conditions across ROIs (voxels)
        correlation_matrix = np.corrcoef(beta_matrix)
        
        return correlation_matrix

    # In your VOTCRSAAnalyzer class...

    def calculate_preferred_vs_others_correlation(self, correlation_matrix, condition_order, roi_info):
        """
        Calculate RSA to EXACTLY match the paper's Matlab script.
        - Uses specific, hard-coded indices from the Matlab script.
        - Applies Fisher z-transform BEFORE averaging correlations.
        """
        
        # This dictionary maps ROI types to the exact indices used in the Matlab script.
        # Assumes condition_order is ['faces', 'houses', 'objects', 'words', 'scrambled']
        # Indices are 0-based for Python.
        
        # Matlab (1-based) -> Python (0-based) translation:
        # VWFA/STG/IFG: (5, 1:4) -> row 4 (scrambled), cols [0, 1, 2, 3]
        # FFA/STS: (1, 2:5) -> row 0 (faces), cols [1, 2, 3, 4]
        # pF/LOC: (2, [1 3:5]) -> row 1 (houses), cols [0, 2, 3, 4]
        # PPA/TOS: (3, [1 2 4 5]) -> row 2 (objects), cols [0, 1, 3, 4]
        
        matlab_style_preferences = {
            'IFG':  {'row_idx': 4, 'col_indices': [0, 1, 2, 3]},
            'STG':  {'row_idx': 4, 'col_indices': [0, 1, 2, 3]},
            'VWFA': {'row_idx': 4, 'col_indices': [0, 1, 2, 3]},
            'FFA':  {'row_idx': 0, 'col_indices': [1, 2, 3, 4]},
            'STS':  {'row_idx': 0, 'col_indices': [1, 2, 3, 4]},
            'pF':   {'row_idx': 1, 'col_indices': [0, 2, 3, 4]},
            'LOC':  {'row_idx': 1, 'col_indices': [0, 2, 3, 4]},
            'PPA':  {'row_idx': 2, 'col_indices': [0, 1, 3, 4]},
            'TOS':  {'row_idx': 2, 'col_indices': [0, 1, 3, 4]},
            # Note: EVC was not in the final Matlab script's figure calculation loop.
            # You can add it here if needed, but it may not be part of Fig 5.
        }
        
        rsa_results = []
        
        for _, roi_row in roi_info.iterrows():
            roi_name = roi_row.get('roi', 'unknown_roi')
            roi_type = roi_row.get('roi_type', '').replace('l', '').replace('r', '')
            
            if roi_type not in matlab_style_preferences:
                continue
                
            pref_def = matlab_style_preferences[roi_type]
            row_idx = pref_def['row_idx']
            col_indices = pref_def['col_indices']

            try:
                # Extract the raw correlation values based on the Matlab script's logic
                correlations_to_average = correlation_matrix[row_idx, col_indices]
                
                # **FIX 2: Apply Fisher z-transform to EACH correlation value BEFORE averaging**
                # Use np.arctanh which is equivalent to 0.5 * np.log((1+r)/(1-r))
                # Add a small epsilon to avoid infinity with perfect correlations of 1 or -1
                epsilon = 1e-9
                fisher_z_values = np.arctanh(np.clip(correlations_to_average, -1 + epsilon, 1 - epsilon))
                
                # **FIX 1: Average the transformed values**
                mean_fisher_z = np.mean(fisher_z_values)
                
                # For reference, calculate the mean of raw correlations
                mean_raw_correlation = np.mean(correlations_to_average)

                rsa_results.append({
                    'roi': roi_name,
                    'roi_type': roi_type,
                    'hemisphere': roi_row.get('hemisphere', 'unknown'),
                    'x': roi_row.get('x', np.nan),
                    'y': roi_row.get('y', np.nan), 
                    'z': roi_row.get('z', np.nan),
                    'preferred_category_matlab': condition_order[row_idx], # What Matlab used as the 'preferred'
                    'correlation_raw_mean': mean_raw_correlation,
                    'correlation_fisher_z': mean_fisher_z, # This is the value to plot
                    'n_comparisons': len(col_indices)
                })
                
            except IndexError as e:
                print(f"  Warning: Could not process {roi_type} {roi_name} due to indexing: {e}")
                continue
                
        return rsa_results

    def process_single_session(self, session_row):
        """Process RSA for a single session"""
        
        session_id = session_row['session_id']
        print(f"Processing RSA for {session_id}")
        
        # Load session data
        beta_matrix, roi_info, metadata = self.load_session_data(session_id)
        
        if beta_matrix is None:
            print(f"  Error: Could not load data for {session_id}")
            return None
            
        condition_order = metadata['condition_order']
        print(f"  Conditions: {condition_order}")
        print(f"  ROIs: {len(roi_info)}")
        print(f"  Beta matrix shape: {beta_matrix.shape}")
        
        # Compute correlation matrix between conditions
        correlation_matrix = self.compute_condition_correlation_matrix(beta_matrix)
        print(f"  Correlation matrix shape: {correlation_matrix.shape}")
        
        # Calculate preferred vs others correlations (main analysis)
        rsa_results = self.calculate_preferred_vs_others_correlation(
            correlation_matrix, condition_order, roi_info)
        
        print(f"  RSA computed for {len(rsa_results)} ROIs")
        
        # Compute RDM (1 - correlation) for compatibility
        rdm = 1 - correlation_matrix
        
        # Package results
        session_results = {
            'session_info': {
                'session_id': session_id,
                'subject': session_row['subject'],
                'session': session_row['session'],
                'run': session_row['run'],
                'n_rois': len(roi_info),
                'n_conditions': len(condition_order)
            },
            'correlation_matrix': correlation_matrix,
            'rdm': rdm,
            'condition_order': condition_order,
            'rsa_correlations': rsa_results
        }
        
        return session_results

    def process_all_sessions(self):
        """Process RSA for all sessions"""
        
        all_results = []
        rsa_summary = []
        
        print(f"Processing RSA for {len(self.session_inventory)} sessions...")
        print("=" * 60)
        
        for _, session_row in self.session_inventory.iterrows():
            
            # Process this session
            results = self.process_single_session(session_row)
            
            if results is not None:
                all_results.append(results)
                
                # Add RSA correlations to summary DataFrame
                for rsa_result in results['rsa_correlations']:
                    summary_row = {
                        'subject': session_row['subject'],
                        'session': session_row['session'],
                        'run': session_row['run'],
                        'session_id': session_row['session_id'],
                        **rsa_result
                    }
                    rsa_summary.append(summary_row)
                    
        print(f"\nSuccessfully processed {len(all_results)} sessions")
        print(f"Generated {len(rsa_summary)} ROI RSA correlations")
        
        return all_results, pd.DataFrame(rsa_summary)

    def save_rsa_results(self, all_results, rsa_summary, output_dir):
        """Save RSA results"""
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save main RSA results (for statistical analysis)
        rsa_file = output_dir / "rsa_correlations.csv"
        rsa_summary.to_csv(rsa_file, index=False)
        print(f"RSA correlations saved to: {rsa_file}")
        
        # Save detailed matrices for each session
        matrices_dir = output_dir / "correlation_matrices"
        matrices_dir.mkdir(exist_ok=True)
        
        for results in all_results:
            session_id = results['session_info']['session_id']
            
            # Save correlation matrix and RDM
            np.save(matrices_dir / f"{session_id}_correlation_matrix.npy", 
                   results['correlation_matrix'])
            np.save(matrices_dir / f"{session_id}_rdm.npy", results['rdm'])
            
            # Save session info
            with open(matrices_dir / f"{session_id}_info.json", 'w') as f:
                json.dump({
                    'session_info': results['session_info'],
                    'condition_order': results['condition_order']
                }, f, indent=2)
                
        print(f"Correlation matrices saved to: {matrices_dir}")
        
        return rsa_file

def main():
    """Main execution function"""
    
    # Paths
    base_dir = "/user_data/csimmon2/long_pt"
    beta_extraction_dir = Path(base_dir) / "analyses" / "beta_extraction"
    output_dir = Path(base_dir) / "analyses" / "rsa_analysis_fixed"
    
    print("FIXED VOTC RSA Analysis")
    print("=" * 60)
    print(f"Beta extraction dir: {beta_extraction_dir}")
    print(f"Output directory: {output_dir}")
    
    # Check input directory exists
    if not beta_extraction_dir.exists():
        raise FileNotFoundError(f"Beta extraction directory not found: {beta_extraction_dir}")
        
    # Initialize analyzer
    analyzer = VOTCRSAAnalyzer(beta_extraction_dir)
    
    # Process all sessions
    print("\nStarting FIXED RSA analysis...")
    all_results, rsa_summary = analyzer.process_all_sessions()
    
    if len(all_results) == 0:
        print("ERROR: No sessions successfully processed!")
        return None, None
        
    # Save results
    print(f"\nSaving RSA results...")
    rsa_file = analyzer.save_rsa_results(all_results, rsa_summary, output_dir)
    
    print(f"\n✓ FIXED RSA Analysis Complete!")
    print(f"✓ Processed {len(all_results)} sessions")
    print(f"✓ Generated {len(rsa_summary)} ROI correlations")
    print(f"✓ Main results file: {rsa_file}")
    
    # Print summary statistics
    print(f"\nRSA Summary by ROI Type:")
    if len(rsa_summary) > 0:
        roi_summary = rsa_summary.groupby(['roi_type', 'hemisphere']).agg({
            'correlation_fisher_z': ['count', 'mean', 'std']
        }).round(3)
        print(roi_summary)
    
    return all_results, rsa_summary

if __name__ == "__main__":
    results, summary = main()