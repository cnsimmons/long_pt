#!/usr/bin/env python3
"""
Extract voxel-wise contrast statistics from FG/OTS ROI in functional space
"""

import os
import numpy as np
import pandas as pd
import nibabel as nib
import subprocess
from pathlib import Path

class ContrastExtractor:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        
        self.subjects_info = {
            'sub-004': {'intact_hemi': 'left', 'sessions': ['01', '02', '03', '05', '06']},
            'sub-007': {'intact_hemi': 'left', 'sessions': ['01', '03', '04']},
            'sub-021': {'intact_hemi': 'left', 'sessions': ['01', '02', '03']}
        }
        
        self.contrast_zstats = {
            'face_word': 13,
            'object_house': 14,
        }
    
    def load_roi_mask_func_space(self, subject, session, run):
        """Transform ROI mask to this run's functional space"""
        
        hemi_label = 'l' if self.subjects_info[subject]['intact_hemi'] == 'left' else 'r'
        roi_path = self.base_dir / subject / 'ses-01' / 'ROIs' / f'{hemi_label}_VOTC_FG_OTS_mask.nii.gz'
        run_dir = self.base_dir / subject / f'ses-{session}' / 'derivatives' / 'fsl' / 'loc' / f'run-{run}' / '1stLevel.feat'
        
        example_func = run_dir / 'example_func.nii.gz'
        transform_mat = run_dir / 'reg' / 'highres2example_func.mat'
        func_roi = run_dir / 'roi_func_space.nii.gz'
        
        if not func_roi.exists():
            print(f"    Transforming ROI to functional space...")
            subprocess.run([
                'flirt', '-in', str(roi_path), '-ref', str(example_func),
                '-out', str(func_roi), '-applyxfm', '-init', str(transform_mat),
                '-interp', 'nearestneighbour'
            ], check=True)
        
        return nib.load(func_roi)
    
    def extract_voxel_data(self, stat_img, mask_img):
        """Extract coordinates and values for all voxels in mask"""
        stat_data = stat_img.get_fdata()
        mask_data = mask_img.get_fdata()
        
        voxel_indices = np.where(mask_data > 0)
        
        # Convert to world coordinates
        affine = stat_img.affine
        voxel_coords = np.column_stack(voxel_indices)
        world_coords = nib.affines.apply_affine(affine, voxel_coords)
        
        stat_values = stat_data[voxel_indices]
        
        return world_coords, stat_values
    
    def extract_run_level_stats(self, subject, session, run, contrast_name):
        """Extract z-statistics for one run"""
        run_dir = self.base_dir / subject / f'ses-{session}' / 'derivatives' / 'fsl' / 'loc' / f'run-{run}' / '1stLevel.feat'
        
        zstat_num = self.contrast_zstats.get(contrast_name)
        zstat_file = run_dir / 'stats' / f'zstat{zstat_num}.nii.gz'
        
        if not zstat_file.exists():
            print(f"  Warning: {zstat_file} not found")
            return None, None
        
        stat_img = nib.load(zstat_file)
        mask_img = self.load_roi_mask_func_space(subject, session, run)
        
        return stat_img, mask_img
    
    def extract_session_data(self, subject, session, contrast_name):
        """Extract and average statistics across runs for one session"""
        print(f"  Extracting {subject} ses-{session} {contrast_name}...")
        
        # Determine available runs
        if subject == 'sub-007' and session in ['03', '04']:
            runs = ['01', '02']
        else:
            runs = ['01', '02', '03']
        
        # Load all zstats
        zstat_imgs = []
        for run in runs:
            run_dir = self.base_dir / subject / f'ses-{session}' / 'derivatives' / 'fsl' / 'loc' / f'run-{run}' / '1stLevel.feat'
            zstat_num = self.contrast_zstats.get(contrast_name)
            zstat_file = run_dir / 'stats' / f'zstat{zstat_num}.nii.gz'
            if zstat_file.exists():
                zstat_imgs.append(nib.load(zstat_file))
        
        if not zstat_imgs:
            return None
        
        # Average zstats
        avg_data = np.mean([img.get_fdata() for img in zstat_imgs], axis=0)
        avg_img = nib.Nifti1Image(avg_data, zstat_imgs[0].affine, zstat_imgs[0].header)
        
        # Transform ROI to functional space (using first run)
        mask_img = self.load_roi_mask_func_space(subject, session, runs[0])
        
        # Extract from averaged data
        coords, values = self.extract_voxel_data(avg_img, mask_img)
        
        df = pd.DataFrame({
            'x': coords[:, 0],
            'y': coords[:, 1],
            'z': coords[:, 2],
            't_stat': values,
            'subject': subject,
            'session': session,
            'contrast': contrast_name
        })
        
        print(f"    Extracted {len(df)} voxels (mean: {values.mean():.2f})")
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
        
        csv_file = output_dir / f'{subject}_{contrast_name}_FGOTS.csv'
        df.to_csv(csv_file, index=False)
        print(f"Saved {csv_file}")
        
        for session in df['session'].unique():
            session_data = df[df['session'] == session][['x', 'y', 'z', 't_stat']].values
            npy_file = output_dir / f'{subject}_ses{session}_{contrast_name}_FGOTS.npy'
            np.save(npy_file, session_data)
            print(f"Saved {npy_file}")

def main():
    base_dir = '/user_data/csimmon2/long_pt'
    output_dir = Path(base_dir) / 'analyses' / 'fgots_extraction'
    
    extractor = ContrastExtractor(base_dir)
    
    for subject in ['sub-004', 'sub-007', 'sub-021']:
        print(f"\nProcessing {subject}...")
        
        for contrast_name in ['face_word', 'object_house']:
            print(f"  Contrast: {contrast_name}")
            
            df = extractor.extract_all_sessions(subject, contrast_name)
            
            if df is not None:
                extractor.save_output(df, subject, contrast_name, output_dir)
    
    print("\nExtraction complete!")

if __name__ == "__main__":
    main()