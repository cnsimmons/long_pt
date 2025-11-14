#!/usr/bin/env python3
"""
Convert localizer .mat files to BIDS-compatible TSV events files

Usage: python convert_mat_to_tsv.py <input_mat_file> [output_tsv_file]

If output_tsv_file is not specified, it will be auto-generated based on input filename.
"""

import sys
import scipy.io
import pandas as pd
from pathlib import Path

def convert_mat_to_tsv(mat_file, tsv_file=None):
    """
    Convert localizer .mat file to TSV events file
    
    Parameters:
    -----------
    mat_file : str or Path
        Path to input .mat file
    tsv_file : str or Path, optional
        Path to output .tsv file. If None, auto-generated.
    
    Returns:
    --------
    pd.DataFrame
        Events dataframe
    """
    
    # Load .mat file
    print(f"Loading {mat_file}...")
    mat = scipy.io.loadmat(mat_file)
    
    # Extract timing and condition data
    block_starts = mat['block_starts'][0]  # get the array
    stimOrd = mat['stimOrd'].flatten()     # flatten to 1D
    
    # Convert to relative onsets with +8 offset (initial fixation period)
    onsets = block_starts - block_starts[0] + 8
    
    # Map condition codes to labels (confirmed from experiment script)
    condition_map = {
        0: 'Face', 
        1: 'Word', 
        2: 'Scramble', 
        3: 'House',     # Places/Houses
        4: 'Object'
    }
    
    # Convert stimOrd to block types
    block_types = [condition_map[code] for code in stimOrd]
    
    # Create dataframe
    df = pd.DataFrame({
        'onset': onsets,
        'duration': [16.0] * len(onsets),  # all blocks are 16 seconds
        'block_type': block_types
    })
    
    # Generate output filename if not provided
    if tsv_file is None:
        mat_path = Path(mat_file)
        tsv_file = mat_path.with_suffix('.tsv')
        # Better naming: if input is "XXloc1.mat", output is "XXloc1_events.tsv"
        tsv_file = mat_path.parent / (mat_path.stem + '_events.tsv')
    
    # Save as TSV
    print(f"Saving to {tsv_file}...")
    df.to_csv(tsv_file, sep='\t', index=False, float_format='%.3f')
    
    # Print summary
    print(f"\nConversion complete!")
    print(f"- Total blocks: {len(df)}")
    print(f"- Duration: {onsets[-1] + 16:.1f} seconds")
    print(f"- Conditions: {', '.join(sorted(set(block_types)))}")
    print(f"\nFirst few rows:")
    print(df.head())
    
    return df

def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_mat_to_tsv.py <input_mat_file> [output_tsv_file]")
        sys.exit(1)
    
    mat_file = sys.argv[1]
    tsv_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Check input file exists
    if not Path(mat_file).exists():
        print(f"Error: Input file {mat_file} does not exist!")
        sys.exit(1)
    
    try:
        convert_mat_to_tsv(mat_file, tsv_file)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()