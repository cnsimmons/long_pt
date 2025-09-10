#!/usr/bin/env python3
"""
Quick check of RSA results
"""

import pandas as pd
import numpy as np
from pathlib import Path

def quick_check_rsa():
    """Quick check of current RSA results"""
    
    rsa_file = Path("/user_data/csimmon2/long_pt/analyses/rsa_analysis_fixed/rsa_correlations.csv")
    
    if not rsa_file.exists():
        print(f"ERROR: File not found: {rsa_file}")
        return
    
    rsa_data = pd.read_csv(rsa_file)
    print(f"Loaded RSA data: {rsa_data.shape}")
    print(f"Columns: {list(rsa_data.columns)}")
    
    print(f"\nFisher z-transformed correlation statistics:")
    print(f"Min:    {rsa_data['correlation_fisher_z'].min():.3f}")
    print(f"Max:    {rsa_data['correlation_fisher_z'].max():.3f}")
    print(f"Mean:   {rsa_data['correlation_fisher_z'].mean():.3f}")
    print(f"Median: {rsa_data['correlation_fisher_z'].median():.3f}")
    print(f"Std:    {rsa_data['correlation_fisher_z'].std():.3f}")
    
    print(f"\nRaw correlation statistics:")
    print(f"Min:    {rsa_data['correlation_raw'].min():.3f}")
    print(f"Max:    {rsa_data['correlation_raw'].max():.3f}")
    print(f"Mean:   {rsa_data['correlation_raw'].mean():.3f}")
    print(f"Median: {rsa_data['correlation_raw'].median():.3f}")
    print(f"Std:    {rsa_data['correlation_raw'].std():.3f}")
    
    print(f"\nFull summary by ROI type:")
    roi_summary = rsa_data.groupby('roi_type').agg({
        'correlation_fisher_z': ['count', 'mean', 'std', 'min', 'max'],
        'correlation_raw': ['mean', 'std']
    }).round(3)
    
    print(roi_summary)
    
    print(f"\nBy hemisphere:")
    hem_summary = rsa_data.groupby(['roi_type', 'hemisphere']).agg({
        'correlation_fisher_z': ['count', 'mean', 'std']
    }).round(3)
    
    print(hem_summary)
    
    # Check for potential issues
    print(f"\nData quality checks:")
    print(f"NaN values in fisher_z: {rsa_data['correlation_fisher_z'].isna().sum()}")
    print(f"Inf values in fisher_z: {np.isinf(rsa_data['correlation_fisher_z']).sum()}")
    print(f"Values > 5: {(rsa_data['correlation_fisher_z'] > 5).sum()}")
    print(f"Values < -5: {(rsa_data['correlation_fisher_z'] < -5).sum()}")
    
    return rsa_data

if __name__ == "__main__":
    rsa_data = quick_check_rsa()