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

def extract_run_from_filename(filename):
    """Extract run number from filename like EC1loc.mat -> 1"""
    import re
    match = re.search(r'EC(\d+)loc', str(filename))
    if match:
        return int(match.group(1))
    return None

def convert_mat_to_tsv(mat_file, tsv_file=None, subject_id='079', session='01'):
    """
    Convert localizer .mat file to TSV events file with BIDS naming
    
    Parameters:
    -----------
    mat_file : str or Path
        Path to input .mat file
    tsv_file : str or Path, optional
        Path to output .tsv file. If None, auto-generated using BIDS convention.
    subject_id : str
        Subject ID for BIDS naming (default: '079')
    session : str  
        Session ID for BIDS naming (default: '01')
    
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
        
        # Extract run number from filename (EC1loc.mat -> 1)
        run_num = extract_run_from_filename(mat_path.name)
        
        if run_num is not None:
            # Generate BIDS naming: sub-079_ses-01_task-loc_run-01_events.tsv
            tsv_filename = f"sub-{subject_id}_ses-{session}_task-loc_run-{run_num:02d}_events.tsv"
        else:
            # Fallback to simple naming if run number can't be extracted
            tsv_filename = mat_path.stem + '_events.tsv'
        
        tsv_file = mat_path.parent / tsv_filename
    
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
        print("Usage: python convert_mat_to_tsv.py <input_mat_file> [output_tsv_file] [subject_id] [session]")
        print("Examples:")
        print("  python convert_mat_to_tsv.py EC1loc.mat")
        print("  python convert_mat_to_tsv.py EC1loc.mat output.tsv")
        print("  python convert_mat_to_tsv.py EC1loc.mat '' 079 01")
        sys.exit(1)
    
    mat_file = sys.argv[1]
    tsv_file = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None
    subject_id = sys.argv[3] if len(sys.argv) > 3 else '079'
    session = sys.argv[4] if len(sys.argv) > 4 else '01'
    
    # Check input file exists
    if not Path(mat_file).exists():
        print(f"Error: Input file {mat_file} does not exist!")
        sys.exit(1)
    
    try:
        convert_mat_to_tsv(mat_file, tsv_file, subject_id, session)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()