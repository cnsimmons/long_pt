#!/usr/bin/env python3
"""
Extract voxel-wise contrast statistics from FG/OTS ROI
Uses HighLevel FEAT outputs in ses-01 anatomical space
"""

import numpy as np
import pandas as pd
import nibabel as nib
from pathlib import Path

class ContrastExtractor:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        
        self.subjects_info = {
            'sub-004': {'sessions': ['01', '02', '03', '05', '06']},
            'sub-007': {'sessions': ['01', '03', '04']},
            'sub-021': {'sessions': ['01', '02', '03']}
        }
        
        # Map contrast names to cope numbers
        self.contrasts = {
            'face_word': 13,
            'object_house': 14,
        }
    
    def extract_session_data(self, subject, session, contrast_name):
        """Extract from HighLevel cope in ses-01 space"""
        print(f"  Extracting {subject} ses-{session} {contrast_name}...")
        
        # Load ROI mask (in ses-01 space)
        roi_path = self.base_dir / subject / 'ses-01' / 'ROIs' / 'l_VOTC_FG_OTS_mask.nii.gz'
        roi_img = nib.load(roi_path)
        roi_data = roi_img.get_fdata()
        
        # Load HighLevel zstat (already in ses-01 space)
        cope_num = self.contrasts[contrast_name]
        highlevel_dir = self.base_dir / subject / f'ses-{session}' / 'derivatives' / 'fsl' / 'loc' / 'HighLevel.gfeat'
        zstat_file = highlevel_dir / f'cope{cope_num}.feat' / 'stats' / 'zstat1.nii.gz'
        
        if not zstat_file.exists():
            print(f"    Warning: {zstat_file} not found")
            return None
        
        zstat_img = nib.load(zstat_file)
        zstat_data = zstat_img.get_fdata()
        
        # Extract voxels
        voxel_indices = np.where(roi_data > 0)
        voxel_coords = np.column_stack(voxel_indices)
        world_coords = nib.affines.apply_affine(zstat_img.affine, voxel_coords)
        stat_values = zstat_data[voxel_indices]
        
        df = pd.DataFrame({
            'x': world_coords[:, 0],
            'y': world_coords[:, 1],
            'z': world_coords[:, 2],
            't_stat': stat_values,
            'subject': subject,
            'session': session,
            'contrast': contrast_name
        })
        
        print(f"    Extracted {len(df)} voxels (mean: {stat_values.mean():.2f})")
        return df
    
    def extract_all_sessions(self, subject, contrast_name):
        """Extract data for all sessions"""
        all_data = []
        
        for session in self.subjects_info[subject]['sessions']:
            df = self.extract_session_data(subject, session, contrast_name)
            if df is not None:
                all_data.append(df)
        
        return pd.concat(all_data, ignore_index=True) if all_data else None
    
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

def main():
    base_dir = '/user_data/csimmon2/long_pt'
    output_dir = Path(base_dir) / 'analyses' / 'fgots_extraction'
    
    extractor = ContrastExtractor(base_dir)
    
    for subject in ['sub-004', 'sub-007', 'sub-021']:
        print(f"\nProcessing {subject}...")
        
        for contrast_name in ['face_word', 'object_house']:
            df = extractor.extract_all_sessions(subject, contrast_name)
            if df is not None:
                extractor.save_output(df, subject, contrast_name, output_dir)
    
    print("\nExtraction complete!")

if __name__ == "__main__":
    main()