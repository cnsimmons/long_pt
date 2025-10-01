#!/usr/bin/env python3
"""
Extract voxel-wise contrast statistics from FG/OTS ROI
Matches the Liu et al. analysis approach
"""

import os
import numpy as np
import pandas as pd
import nibabel as nib
from pathlib import Path
from scipy import stats as scipy_stats

class ContrastExtractor:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        
        # Subject configuration
        self.subjects_info = {
            'sub-004': {'intact_hemi': 'left', 'sessions': ['01', '02', '03', '05', '06', '07']},
            'sub-007': {'intact_hemi': 'right', 'sessions': ['01', '03', '04', '05']},
            'sub-021': {'intact_hemi': 'left', 'sessions': ['01', '02', '03']}
        }
        
        # Contrast definitions matching your localizer
        self.contrasts = {
            'face_word': {'cope': 'cope1.nii.gz', 'zstat': 'zstat1.nii.gz'},  # face > word or similar
            'face_house': {'cope': 'cope1.nii.gz', 'zstat': 'zstat1.nii.gz'},  # faces > houses
            'object_scramble': {'cope': 'cope3.nii.gz', 'zstat': 'zstat3.nii.gz'},  # objects > scrambled
            # Add other contrasts as needed
        }
    
    def load_roi_mask(self, subject):
        """Load the ventral temporal ROI mask for this subject"""
        hemi_label = 'l' if self.subjects_info[subject]['intact_hemi'] == 'left' else 'r'
        roi_path = self.base_dir / subject / 'ses-01' / 'ROIs' / f'{hemi_label}_ventral_temporal_mask.nii.gz'
        
        if not roi_path.exists():
            raise FileNotFoundError(f"ROI mask not found: {roi_path}")
        
        return nib.load(roi_path)
    
    def extract_voxel_data(self, stat_img, mask_img):
        """Extract coordinates and values for all voxels in mask"""
        stat_data = stat_img.get_fdata()
        mask_data = mask_img.get_fdata()
        
        # Get voxel indices where mask > 0
        voxel_indices = np.where(mask_data > 0)
        
        # Convert to world coordinates
        affine = stat_img.affine
        voxel_coords = np.column_stack(voxel_indices)
        world_coords = nib.affines.apply_affine(affine, voxel_coords)
        
        # Extract statistics for these voxels
        stat_values = stat_data[voxel_indices]
        
        return world_coords, stat_values
    
    def extract_run_level_stats(self, subject, session, run, contrast_name):
        """Extract statistics from a single run"""
        # Path to run-level stats
        run_dir = self.base_dir / subject / f'ses-{session}' / 'derivatives' / 'fsl' / 'loc' / f'run-{run}' / '1stLevel.feat'
        
        # Use registered stats (in ses-01 space)
        stats_dir = run_dir / 'reg_standard' / 'stats'
        
        contrast_file = stats_dir / self.contrasts[contrast_name]['zstat']
        
        if not contrast_file.exists():
            print(f"  Warning: {contrast_file} not found")
            return None
        
        return nib.load(contrast_file)
    
    def extract_session_data(self, subject, session, contrast_name):
        """Extract and average statistics across runs for one session"""
        print(f"  Extracting {subject} ses-{session} {contrast_name}...")
        
        # Load ROI mask
        mask_img = self.load_roi_mask(subject)
        
        # Determine available runs for this session
        if subject == 'sub-007' and session in ['03', '04']:
            runs = ['01', '02']  # Only 2 runs for UD ses-03 and ses-04
        else:
            runs = ['01', '02', '03']
        
        # Collect statistics from all runs
        run_stats = []
        for run in runs:
            stat_img = self.extract_run_level_stats(subject, session, run, contrast_name)
            if stat_img is not None:
                run_stats.append(stat_img)
        
        if not run_stats:
            print(f"    No valid runs found for {subject} ses-{session}")
            return None
        
        # Average across runs
        avg_data = np.mean([img.get_fdata() for img in run_stats], axis=0)
        avg_img = nib.Nifti1Image(avg_data, run_stats[0].affine, run_stats[0].header)
        
        # Extract voxel coordinates and values
        coords, values = self.extract_voxel_data(avg_img, mask_img)
        
        # Create dataframe
        df = pd.DataFrame({
            'x': coords[:, 0],
            'y': coords[:, 1],
            'z': coords[:, 2],
            't_stat': values,
            'subject': subject,
            'session': session,
            'contrast': contrast_name
        })
        
        print(f"    Extracted {len(df)} voxels")
        return df
    
    def extract_all_sessions(self, subject, contrast_name):
        """Extract data for all sessions of one subject"""
        all_data = []
        
        for session in self.subjects_info[subject]['sessions']:
            df = self.extract_session_data(subject, session, contrast_name)
            if df is not None:
                all_data.append(df)
        
        if not all_data:
            return None
        
        return pd.concat(all_data, ignore_index=True)
    
    def save_for_matlab(self, df, subject, contrast_name, output_dir):
        """Save in format similar to original .mat files"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as CSV (can be loaded in MATLAB or Python)
        csv_file = output_dir / f'{subject}_{contrast_name}_FGOTS.csv'
        df.to_csv(csv_file, index=False)
        
        print(f"Saved {csv_file}")
        
        # Also save session-specific arrays matching .mat structure
        for session in df['session'].unique():
            session_data = df[df['session'] == session][['x', 'y', 'z', 't_stat']].values
            npy_file = output_dir / f'{subject}_ses{session}_{contrast_name}_FGOTS.npy'
            np.save(npy_file, session_data)
            print(f"Saved {npy_file}")

def main():
    base_dir = '/user_data/csimmon2/long_pt'
    output_dir = Path(base_dir) / 'analyses' / 'fgots_extraction'
    
    extractor = ContrastExtractor(base_dir)
    
    # Extract for each subject and contrast
    for subject in ['sub-004', 'sub-007', 'sub-021']:
        print(f"\nProcessing {subject}...")
        
        for contrast_name in ['face_word', 'object_scramble']:
            print(f"  Contrast: {contrast_name}")
            
            df = extractor.extract_all_sessions(subject, contrast_name)
            
            if df is not None:
                extractor.save_for_matlab(df, subject, contrast_name, output_dir)
    
    print("\nExtraction complete!")
    print(f"Results saved to: {output_dir}")

if __name__ == "__main__":
    main()