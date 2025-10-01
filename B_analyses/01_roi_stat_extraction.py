#!/usr/bin/env python3
"""
Extract voxel-wise category selectivity from FG/OTS ROI
Computing t-statistics from cope and varcope files
"""

import os
import numpy as np
import pandas as pd
import nibabel as nib
from pathlib import Path

class ContrastExtractor:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        
        # Subject configuration
        self.subjects_info = {
            'sub-004': {'intact_hemi': 'left', 'sessions': ['01', '02', '03', '05', '06']},
            'sub-007': {'intact_hemi': 'left', 'sessions': ['01', '03', '04']},
            'sub-021': {'intact_hemi': 'left', 'sessions': ['01', '02', '03']}
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
        """Compute t-statistics from cope and varcope files"""
        run_dir = self.base_dir / subject / f'ses-{session}' / 'derivatives' / 'fsl' / 'loc' / f'run-{run}' / '1stLevel.feat'
        stats_dir = run_dir / 'reg_standard' / 'stats'
        
        # Define contrasts
        contrast_defs = {
            'face_word': (1, 4),      # Face - Word
            'object_house': (3, 2),   # Object - House
        }
        
        if contrast_name not in contrast_defs:
            return None
        
        c1, c2 = contrast_defs[contrast_name]
        
        # Load cope and varcope files
        cope1_file = stats_dir / f'cope{c1}.nii.gz'
        cope2_file = stats_dir / f'cope{c2}.nii.gz'
        varcope1_file = stats_dir / f'varcope{c1}.nii.gz'
        varcope2_file = stats_dir / f'varcope{c2}.nii.gz'
        
        required_files = [cope1_file, cope2_file, varcope1_file, varcope2_file]
        if not all(f.exists() for f in required_files):
            print(f"  Warning: Required files not found for {contrast_name}")
            return None
        
        # Load data
        cope1 = nib.load(cope1_file).get_fdata()
        cope2 = nib.load(cope2_file).get_fdata()
        varcope1 = nib.load(varcope1_file).get_fdata()
        varcope2 = nib.load(varcope2_file).get_fdata()
        
        # Compute contrast
        contrast = cope1 - cope2
        
        # Compute variance of contrast
        var_contrast = varcope1 + varcope2
        
        # Compute t-statistic: contrast / sqrt(variance)
        # Avoid division by zero
        t_stat = np.divide(contrast, 
                          np.sqrt(var_contrast), 
                          out=np.zeros_like(contrast), 
                          where=var_contrast > 0)
        
        # Return as nifti image
        img = nib.load(cope1_file)
        return nib.Nifti1Image(t_stat, img.affine, img.header)
    
    def extract_session_data(self, subject, session, contrast_name):
        """Extract and average t-statistics across runs for one session"""
        print(f"  Extracting {subject} ses-{session} {contrast_name}...")
        
        # Load ROI mask
        mask_img = self.load_roi_mask(subject)
        
        # Determine available runs for this session
        if subject == 'sub-007' and session in ['03', '04']:
            runs = ['01', '02']
        else:
            runs = ['01', '02', '03']
        
        # Collect t-statistics from all runs
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
        
        print(f"    Extracted {len(df)} voxels (min: {values.min():.2f}, max: {values.max():.2f}, mean: {values.mean():.2f})")
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
    
    def save_output(self, df, subject, contrast_name, output_dir):
        """Save extracted data"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as CSV
        csv_file = output_dir / f'{subject}_{contrast_name}_FGOTS.csv'
        df.to_csv(csv_file, index=False)
        print(f"Saved {csv_file}")
        
        # Save session-specific arrays
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
        
        for contrast_name in ['face_word', 'object_house']:
            print(f"  Contrast: {contrast_name}")
            
            df = extractor.extract_all_sessions(subject, contrast_name)
            
            if df is not None:
                extractor.save_output(df, subject, contrast_name, output_dir)
    
    print("\nExtraction complete!")
    print(f"Results saved to: {output_dir}")

if __name__ == "__main__":
    main()