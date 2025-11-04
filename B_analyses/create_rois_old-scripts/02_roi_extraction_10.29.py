#!/usr/bin/env python3
"""
Extract voxel-wise statistics from category-specific ROIs
Fusiform: face_word (cope 13) and individual conditions (6, 9)
LO+PPA: object_house (cope 14) and individual conditions (7, 8)
"""

import numpy as np
import pandas as pd
import nibabel as nib
from pathlib import Path

class ContrastExtractor:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        
        self.subjects_info = {
            'sub-004': {'sessions': ['01', '02', '03', '05', '06'], 'hemi': 'l'},
            'sub-007': {'sessions': ['01', '03', '04'], 'hemi': 'l'},
            'sub-021': {'sessions': ['01', '02', '03'], 'hemi': 'r'}
        }
        
        # ROI mapping: which ROI for which contrast
        self.roi_mapping = {
            'face_word': 'fusiform_mask_dilated.nii.gz',
            'object_house': 'LO_PPA_mask_dilated.nii.gz'
        }
        
        # All copes to extract
        self.copes = {
            'face': 6,          # Face > All
            'house': 7,         # House > All
            'object': 8,        # Object > All
            'word': 9,          # Word > All
            'face_word': 13,    # Face > Word
            'object_house': 14  # Object > House
        }
    
    def extract_session_data(self, subject, session, cope_name, roi_name):
        """Extract from HighLevel cope"""
        print(f"  Extracting {subject} ses-{session} {cope_name} from {roi_name}...")
        
        # Load ROI mask
        hemi = self.subjects_info[subject]['hemi']
        roi_path = self.base_dir / subject / 'ses-01' / 'ROIs' / f'{hemi}_{roi_name}'
        
        if not roi_path.exists():
            print(f"    ERROR: ROI not found: {roi_path}")
            return None
            
        roi_img = nib.load(roi_path)
        roi_data = roi_img.get_fdata()
        
        # Load HighLevel zstat
        cope_num = self.copes[cope_name]
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
            'cope': cope_name,
            'roi': roi_name
        })
        
        print(f"    Extracted {len(df)} voxels (mean: {stat_values.mean():.2f})")
        return df
    
    def extract_contrast_set(self, subject, contrast_type):
        """Extract all copes for a contrast (face_word or object_house)"""
        
        # Determine which copes and ROI to use
        if contrast_type == 'face_word':
            copes_to_extract = ['face', 'word', 'face_word']
            roi_name = self.roi_mapping['face_word']
        else:  # object_house
            copes_to_extract = ['object', 'house', 'object_house']
            roi_name = self.roi_mapping['object_house']
        
        all_data = []
        
        for session in self.subjects_info[subject]['sessions']:
            for cope_name in copes_to_extract:
                df = self.extract_session_data(subject, session, cope_name, roi_name)
                if df is not None:
                    all_data.append(df)
        
        return pd.concat(all_data, ignore_index=True) if all_data else None
    
    def save_output(self, df, subject, contrast_type, output_dir):
        """Save extracted data"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save full CSV
        csv_file = output_dir / f'{subject}_{contrast_type}_all_copes.csv'
        df.to_csv(csv_file, index=False)
        print(f"Saved {csv_file}")
        
        # Save session-specific npy files for visualization (contrast cope only)
        contrast_df = df[df['cope'] == contrast_type]
        for session in contrast_df['session'].unique():
            session_data = contrast_df[contrast_df['session'] == session][['x', 'y', 'z', 't_stat']].values
            npy_file = output_dir / f'{subject}_ses{session}_{contrast_type}.npy'
            np.save(npy_file, session_data)
            print(f"  Saved {npy_file.name}")

def main():
    base_dir = '/user_data/csimmon2/long_pt'
    output_dir = Path(base_dir) / 'analyses' / 'roi_extraction'
    
    extractor = ContrastExtractor(base_dir)
    
    for subject in ['sub-004', 'sub-007', 'sub-021']:
        print(f"\n{'='*60}")
        print(f"Processing {subject}")
        print(f"{'='*60}")
        
        # Extract face_word from fusiform
        print("\n--- FUSIFORM ROI (face_word) ---")
        df = extractor.extract_contrast_set(subject, 'face_word')
        if df is not None:
            extractor.save_output(df, subject, 'face_word', output_dir)
        
        # Extract object_house from LO+PPA
        print("\n--- LO+PPA ROI (object_house) ---")
        df = extractor.extract_contrast_set(subject, 'object_house')
        if df is not None:
            extractor.save_output(df, subject, 'object_house', output_dir)
    
    print("\n" + "="*60)
    print("Extraction complete!")
    print("="*60)

if __name__ == "__main__":
    main()