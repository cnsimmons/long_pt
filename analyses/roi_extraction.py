#!/usr/bin/env python3
"""
Extract peak ROI coordinates from long_pt FEAT results
Adapted for 3D volume analysis matching VOTC plasticity paper approach
"""

import os
import numpy as np
import pandas as pd
import nibabel as nib
from pathlib import Path
from scipy import ndimage
import warnings
warnings.filterwarnings('ignore')

class VOTCROIExtractor:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        
        # ROI definitions based on VOTC paper contrasts
        self.roi_definitions = {
            # ROI_name: (pos_contrast, neg_contrast, hemisphere_pref, threshold, anatomical_region)
            'FFA': ('zstat1.nii.gz', 'zstat2.nii.gz', 'bilateral', 2.3, 'fusiform'),      # faces > houses
            'STS': ('zstat1.nii.gz', 'zstat2.nii.gz', 'bilateral', 2.3, 'temporal'),     # faces > houses
            'PPA': ('zstat2.nii.gz', 'zstat1.nii.gz', 'bilateral', 2.3, 'parahipp'),     # houses > faces  
            'TOS': ('zstat2.nii.gz', 'zstat1.nii.gz', 'bilateral', 2.3, 'occipital'),    # houses > faces
            'LOC': ('zstat3.nii.gz', 'zstat5.nii.gz', 'bilateral', 2.3, 'lateral_occ'),  # objects > scrambled
            'pF': ('zstat3.nii.gz', 'zstat5.nii.gz', 'bilateral', 2.3, 'post_fusiform'), # objects > scrambled
            'VWFA': ('zstat4.nii.gz', 'zstat1.nii.gz', 'left', 2.3, 'fusiform'),         # words > faces
            'STG': ('zstat4.nii.gz', 'zstat1.nii.gz', 'left', 2.3, 'temporal'),          # words > faces  
            'IFG': ('zstat4.nii.gz', 'zstat1.nii.gz', 'left', 2.3, 'frontal'),           # words > faces
            'EVC': ('zstat6.nii.gz', None, 'bilateral', 2.3, 'occipital'),               # face-all vs baseline
        }
        
        # Anatomical constraints for ROI identification
        self.anatomical_bounds = {
            'fusiform': {'y_min': -70, 'y_max': -20, 'z_min': -30, 'z_max': 10},
            'temporal': {'y_min': -70, 'y_max': 0, 'z_min': -20, 'z_max': 20}, 
            'parahipp': {'y_min': -60, 'y_max': -10, 'z_min': -30, 'z_max': 10},
            'occipital': {'y_min': -110, 'y_max': -50, 'z_min': -20, 'z_max': 30},
            'lateral_occ': {'y_min': -100, 'y_max': -30, 'z_min': -20, 'z_max': 30},
            'post_fusiform': {'y_min': -80, 'y_max': -30, 'z_min': -30, 'z_max': 10},
            'frontal': {'y_min': -10, 'y_max': 50, 'z_min': -10, 'z_max': 40},
        }

    def find_feat_directories(self):
        """Find all completed FEAT directories"""
        feat_dirs = []
        for feat_path in self.base_dir.rglob("*.feat"):
            if (feat_path / "report.html").exists():
                feat_dirs.append(feat_path)
        return sorted(feat_dirs)

    def create_contrast_map(self, stats_dir, pos_contrast, neg_contrast=None):
        """Create contrast map from zstat files"""
        pos_file = stats_dir / pos_contrast
        
        if not pos_file.exists():
            return None
            
        pos_img = nib.load(pos_file)
        pos_data = pos_img.get_fdata()
        
        if neg_contrast is not None:
            neg_file = stats_dir / neg_contrast
            if neg_file.exists():
                neg_data = nib.load(neg_file).get_fdata()
                contrast_data = pos_data - neg_data
            else:
                contrast_data = pos_data
        else:
            contrast_data = pos_data
            
        return nib.Nifti1Image(contrast_data, pos_img.affine, pos_img.header)

    def apply_anatomical_constraints(self, img, region):
        """Apply anatomical constraints to limit search region"""
        if region not in self.anatomical_bounds:
            return img
            
        data = img.get_fdata()
        affine = img.affine
        
        # Create coordinate grids
        i_coords, j_coords, k_coords = np.mgrid[0:data.shape[0], 0:data.shape[1], 0:data.shape[2]]
        coords = np.vstack([i_coords.ravel(), j_coords.ravel(), k_coords.ravel(), np.ones(i_coords.size)])
        
        # Convert to world coordinates
        world_coords = affine.dot(coords)
        world_coords = world_coords[:3, :].T.reshape(data.shape + (3,))
        
        # Apply constraints
        bounds = self.anatomical_bounds[region]
        mask = np.ones(data.shape, dtype=bool)
        
        if 'y_min' in bounds:
            mask &= (world_coords[..., 1] >= bounds['y_min'])
        if 'y_max' in bounds:
            mask &= (world_coords[..., 1] <= bounds['y_max'])
        if 'z_min' in bounds:
            mask &= (world_coords[..., 2] >= bounds['z_min'])
        if 'z_max' in bounds:
            mask &= (world_coords[..., 2] <= bounds['z_max'])
            
        # Apply mask
        constrained_data = np.where(mask, data, 0)
        
        return nib.Nifti1Image(constrained_data, affine, img.header)

    def find_peak_coordinates(self, contrast_img, threshold, region):
        """Find peak coordinates with anatomical constraints"""
        # Apply anatomical constraints
        constrained_img = self.apply_anatomical_constraints(contrast_img, region)
        data = constrained_img.get_fdata()
        affine = constrained_img.affine
        
        # Apply threshold
        thresholded = data > threshold
        
        if not np.any(thresholded):
            return None
            
        # Find connected components
        labeled, num_features = ndimage.label(thresholded)
        
        if num_features == 0:
            return None
            
        # Find the largest cluster
        cluster_sizes = [(labeled == i).sum() for i in range(1, num_features + 1)]
        largest_cluster = np.argmax(cluster_sizes) + 1
        
        # Find peak within largest cluster
        cluster_mask = labeled == largest_cluster
        cluster_data = np.where(cluster_mask, data, 0)
        peak_idx = np.unravel_index(np.argmax(cluster_data), cluster_data.shape)
        
        # Convert to world coordinates
        peak_world = nib.affines.apply_affine(affine, peak_idx)
        
        return {
            'x': peak_world[0],
            'y': peak_world[1], 
            'z': peak_world[2],
            'peak_z': data[peak_idx],
            'cluster_size': cluster_sizes[largest_cluster - 1]
        }

    def determine_hemisphere(self, coords, hemisphere_pref):
        """Determine hemisphere based on x-coordinate and preference"""
        if hemisphere_pref == 'left':
            return 'left' if coords['x'] < 0 else 'right'
        elif hemisphere_pref == 'right':
            return 'right' if coords['x'] > 0 else 'left'
        else:  # bilateral
            return 'left' if coords['x'] < 0 else 'right'

    def extract_rois_from_feat(self, feat_dir):
        """Extract all ROI coordinates from a single FEAT directory"""
        stats_dir = feat_dir / "stats"
        all_rois = {}
        
        for roi_name, (pos_contrast, neg_contrast, hemi_pref, threshold, region) in self.roi_definitions.items():
            # Create contrast map
            contrast_img = self.create_contrast_map(stats_dir, pos_contrast, neg_contrast)
            
            if contrast_img is None:
                continue
                
            # Find peak coordinates
            coords = self.find_peak_coordinates(contrast_img, threshold, region)
            
            if coords is not None:
                # Determine hemisphere
                hemisphere = self.determine_hemisphere(coords, hemi_pref)
                
                # Create ROI key
                if hemi_pref == 'bilateral':
                    roi_key = f"{hemisphere[0]}{roi_name}"  # lFFA, rFFA, etc.
                else:
                    roi_key = roi_name  # VWFA, STG, IFG
                    
                coords['hemisphere'] = hemisphere
                coords['roi_type'] = roi_name
                all_rois[roi_key] = coords
                
        return all_rois

    def parse_feat_path(self, feat_path):
        """Parse subject/session/run info from FEAT path"""
        path_parts = feat_path.parts
        
        # Find indices
        sub_idx = [i for i, part in enumerate(path_parts) if part.startswith('sub-')]
        ses_idx = [i for i, part in enumerate(path_parts) if part.startswith('ses-')]
        run_idx = [i for i, part in enumerate(path_parts) if part.startswith('run-')]
        
        if not (sub_idx and ses_idx):
            return None
            
        subject = path_parts[sub_idx[0]]
        session = path_parts[ses_idx[0]]
        run = path_parts[run_idx[0]] if run_idx else 'run-01'
        
        return {
            'subject': subject,
            'session': session,
            'run': run,
            'feat_path': str(feat_path)
        }

    def process_all_subjects(self):
        """Process all subjects and extract ROI coordinates"""
        feat_dirs = self.find_feat_directories()
        all_results = []
        
        print(f"Found {len(feat_dirs)} completed FEAT directories")
        
        for feat_dir in feat_dirs:
            # Parse path info
            path_info = self.parse_feat_path(feat_dir)
            if path_info is None:
                continue
                
            print(f"Processing {path_info['subject']} {path_info['session']} {path_info['run']}...")
            
            # Extract ROI coordinates
            roi_coords = self.extract_rois_from_feat(feat_dir)
            
            # Convert to rows for DataFrame
            for roi_key, coords in roi_coords.items():
                row = {
                    'subject': path_info['subject'],
                    'session': path_info['session'],
                    'run': path_info['run'],
                    'roi': roi_key,
                    'roi_type': coords['roi_type'],
                    'hemisphere': coords['hemisphere'],
                    'x': coords['x'],
                    'y': coords['y'],
                    'z': coords['z'],
                    'peak_z': coords['peak_z'],
                    'cluster_size': coords['cluster_size'],
                    'feat_path': path_info['feat_path']
                }
                all_results.append(row)
                
        return pd.DataFrame(all_results)

def main():
    """Main execution function"""
    # Set up paths - script in git_repos, data in user_data
    base_dir = "/user_data/csimmon2/long_pt"
    output_dir = Path(base_dir) / "analyses" / "roi_extraction"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Script location: {Path(__file__).parent}")
    print(f"Data location: {base_dir}")
    print(f"Output location: {output_dir}")
    
    # Initialize extractor
    extractor = VOTCROIExtractor(base_dir)
    
    # Process all subjects
    print("Starting ROI coordinate extraction...")
    results_df = extractor.process_all_subjects()
    
    # Save results
    output_file = output_dir / "peak_roi_coordinates.csv"
    results_df.to_csv(output_file, index=False)
    
    print(f"\nExtraction complete!")
    print(f"Found {len(results_df)} ROI coordinates across {results_df['subject'].nunique()} subjects")
    print(f"Results saved to: {output_file}")
    
    # Print summary
    print("\nROI Summary:")
    roi_summary = results_df.groupby(['roi_type', 'hemisphere']).size()
    print(roi_summary)
    
    return results_df

if __name__ == "__main__":
    results = main()