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

    def calculate_preferred_vs_others_correlation(self, correlation_matrix, condition_order, roi_info):
        """
        Calculate RSA: correlation between preferred and non-preferred categories
        THIS IS THE ACTUAL PAPER METHOD
        """
        
        rsa_results = []
        
        for roi_idx, roi_row in roi_info.iterrows():
            # Handle different possible column names for ROI
            roi_name = roi_row.get('roi', roi_row.get('roi_name', f'roi_{roi_idx}'))
            roi_type = roi_row.get('roi_type', roi_name.replace('l', '').replace('r', ''))
            
            if roi_type not in self.roi_preferences:
                continue
                
            # Get preference definition
            pref_def = self.roi_preferences[roi_type]
            preferred = pref_def['preferred']
            non_preferred = pref_def['non_preferred']
            
            # Find condition indices
            try:
                pref_idx = condition_order.index(preferred)
                non_pref_indices = [condition_order.index(cond) 
                                  for cond in non_preferred if cond in condition_order]
                
                if len(non_pref_indices) == 0:
                    continue
                
                # Extract correlations between preferred and non-preferred categories
                correlations_with_others = []
                for non_pref_idx in non_pref_indices:
                    correlation = correlation_matrix[pref_idx, non_pref_idx]
                    correlations_with_others.append(correlation)
                
                # Take mean correlation (as in paper)
                mean_correlation = np.mean(correlations_with_others)
                
                # Fisher z-transform (as in paper: 0.5*log((1+r)/(1-r)))
                if np.abs(mean_correlation) < 0.999:  # Avoid log(0)
                    fisher_z = 0.5 * np.log((1 + mean_correlation) / (1 - mean_correlation))
                else:
                    fisher_z = np.sign(mean_correlation) * 5.0  # Cap extreme values
                
                rsa_results.append({
                    'roi': roi_name,
                    'roi_type': roi_type,
                    'hemisphere': roi_row.get('hemisphere', 'unknown'),
                    'x': roi_row.get('x', np.nan),
                    'y': roi_row.get('y', np.nan), 
                    'z': roi_row.get('z', np.nan),
                    'preferred_category': preferred,
                    'correlation_raw': mean_correlation,
                    'correlation_fisher_z': fisher_z,
                    'correlations_with_others': correlations_with_others,
                    'n_comparisons': len(non_pref_indices)
                })
                
            except (ValueError, IndexError) as e:
                print(f"  Warning: Could not process {roi_type} {roi_name}: {e}")
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