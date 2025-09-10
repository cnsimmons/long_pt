#!/usr/bin/env python3
"""
Beta Value Extraction for VOTC Plasticity Study
Extract beta values from spherical ROIs around peak coordinates
"""

import os
import numpy as np
import pandas as pd
import nibabel as nib
from pathlib import Path
from nilearn.input_data import NiftiSpheresMasker
from nilearn.image import load_img
import json
import warnings
warnings.filterwarnings('ignore')

class VOTCBetaExtractor:
    def __init__(self, roi_coordinates_csv, base_dir, sphere_radius=7.0):
        """
        Initialize beta extractor
        
        Parameters:
        -----------
        roi_coordinates_csv : str or Path
            Path to CSV file with ROI coordinates from roi_extraction.py
        base_dir : str or Path
            Base directory containing FEAT results
        sphere_radius : float
            Radius in mm for spherical ROI extraction (default: 7mm per paper)
        """
        self.base_dir = Path(base_dir)
        self.roi_coords = pd.read_csv(roi_coordinates_csv)
        self.sphere_radius = sphere_radius
        
        # FEAT condition mappings (cope files)
        self.conditions = {
            'faces': 'cope1.nii.gz',
            'houses': 'cope2.nii.gz', 
            'objects': 'cope3.nii.gz',
            'words': 'cope4.nii.gz',
            'scrambled': 'cope5.nii.gz'
        }
        
        # Track extraction statistics
        self.extraction_stats = {
            'sessions_attempted': 0,
            'sessions_successful': 0,
            'rois_extracted': 0,
            'missing_cope_files': [],
            'failed_extractions': []
        }
        
        print(f"Initialized beta extractor:")
        print(f"  - {len(self.roi_coords)} ROI coordinates loaded")
        print(f"  - Sphere radius: {sphere_radius}mm")
        print(f"  - Subjects: {sorted(self.roi_coords['subject'].unique())}")
        print(f"  - Sessions per subject: {self.roi_coords.groupby('subject')['session'].nunique().to_dict()}")

    def validate_feat_directory(self, feat_path):
        """
        Validate FEAT directory has required cope files
        
        Returns:
        --------
        valid_copes : dict
            Dictionary of available condition -> cope file mappings
        missing_copes : list
            List of missing cope files
        """
        feat_path = Path(feat_path)
        stats_dir = feat_path / "stats"
        
        if not stats_dir.exists():
            return {}, list(self.conditions.keys())
            
        valid_copes = {}
        missing_copes = []
        
        for condition, cope_file in self.conditions.items():
            cope_path = stats_dir / cope_file
            if cope_path.exists() and cope_path.stat().st_size > 0:
                valid_copes[condition] = str(cope_path)
            else:
                missing_copes.append(condition)
                
        return valid_copes, missing_copes

    def extract_session_betas(self, subject, session, run):
        """
        Extract beta values for a single subject/session/run
        
        Returns:
        --------
        session_data : dict or None
            Dictionary containing extracted beta values and metadata
        """
        
        # Get ROIs for this session
        roi_subset = self.roi_coords[
            (self.roi_coords['subject'] == subject) & 
            (self.roi_coords['session'] == session) &
            (self.roi_coords['run'] == run)
        ].copy()
        
        if len(roi_subset) == 0:
            print(f"  Warning: No ROIs found for {subject} {session} {run}")
            return None
            
        # Get FEAT path and validate
        feat_path = roi_subset.iloc[0]['feat_path']
        valid_copes, missing_copes = self.validate_feat_directory(feat_path)
        
        if len(valid_copes) == 0:
            print(f"  Error: No valid cope files found in {feat_path}")
            self.extraction_stats['failed_extractions'].append(f"{subject}_{session}_{run}")
            return None
            
        if missing_copes:
            print(f"  Warning: Missing cope files for {subject} {session} {run}: {missing_copes}")
            self.extraction_stats['missing_cope_files'].extend(
                [f"{subject}_{session}_{run}_{cope}" for cope in missing_copes]
            )
        
        print(f"  Extracting {subject} {session} {run}: {len(roi_subset)} ROIs, {len(valid_copes)} conditions")
        
        try:
            # Prepare ROI coordinates and info
            coords = roi_subset[['x', 'y', 'z']].values
            roi_info = roi_subset[['roi', 'roi_type', 'hemisphere', 'x', 'y', 'z', 
                                  'peak_z', 'cluster_size']].to_dict('records')
            
            # Initialize masker - allow overlapping spheres (common in visual cortex)
            masker = NiftiSpheresMasker(
                seeds=coords,
                radius=self.sphere_radius,
                standardize=False,  # Keep raw beta values
                detrend=False,
                allow_overlap=True  # Allow overlapping ROIs
            )
            
            # Extract beta values for each condition
            beta_matrix = []
            condition_order = []
            extraction_info = {}
            
            for condition in ['faces', 'houses', 'objects', 'words', 'scrambled']:
                if condition in valid_copes:
                    # Load and extract
                    cope_img = load_img(valid_copes[condition])
                    betas = masker.fit_transform(cope_img)
                    
                    # Store results (betas is shape [1, n_rois] for single volume)
                    beta_matrix.append(betas.flatten())
                    condition_order.append(condition)
                    
                    # Store extraction info
                    extraction_info[condition] = {
                        'cope_file': valid_copes[condition],
                        'n_voxels_extracted': betas.size,
                        'beta_mean': float(np.mean(betas)),
                        'beta_std': float(np.std(betas)),
                        'beta_range': [float(np.min(betas)), float(np.max(betas))]
                    }
                    
            beta_matrix = np.array(beta_matrix)  # Shape: (n_conditions, n_rois)
            
            # Create session data package
            session_data = {
                'subject': subject,
                'session': session,
                'run': run,
                'feat_path': feat_path,
                'beta_matrix': beta_matrix,
                'condition_order': condition_order,
                'roi_info': roi_info,
                'extraction_info': extraction_info,
                'sphere_radius': self.sphere_radius,
                'n_rois': len(roi_info),
                'n_conditions': len(condition_order),
                'missing_conditions': missing_copes
            }
            
            # Update stats
            self.extraction_stats['rois_extracted'] += len(roi_info)
            
            return session_data
            
        except Exception as e:
            print(f"  Error extracting betas for {subject} {session} {run}: {e}")
            self.extraction_stats['failed_extractions'].append(f"{subject}_{session}_{run}")
            return None

    def extract_all_sessions(self):
        """
        Extract beta values for all subjects/sessions/runs
        
        Returns:
        --------
        all_session_data : list
            List of session data dictionaries
        """
        
        # Get unique sessions
        sessions = self.roi_coords[['subject', 'session', 'run']].drop_duplicates()
        
        all_session_data = []
        
        print(f"\nStarting beta extraction for {len(sessions)} sessions...")
        print("=" * 60)
        
        for _, session_info in sessions.iterrows():
            self.extraction_stats['sessions_attempted'] += 1
            
            subject = session_info['subject']
            session = session_info['session']
            run = session_info['run']
            
            # Extract betas for this session
            session_data = self.extract_session_betas(subject, session, run)
            
            if session_data is not None:
                all_session_data.append(session_data)
                self.extraction_stats['sessions_successful'] += 1
                print(f"  ✓ Success: {len(session_data['roi_info'])} ROIs, {len(session_data['condition_order'])} conditions")
            else:
                print(f"  ✗ Failed")
                
        return all_session_data

    def validate_extracted_data(self, all_session_data):
        """
        Perform quality control checks on extracted data
        
        Returns:
        --------
        qc_report : dict
            Quality control metrics and warnings
        """
        
        qc_report = {
            'total_sessions': len(all_session_data),
            'total_rois': sum(len(data['roi_info']) for data in all_session_data),
            'conditions_per_session': {},
            'roi_types_found': set(),
            'beta_value_ranges': {},
            'potential_issues': []
        }
        
        all_betas = []
        
        for data in all_session_data:
            session_id = f"{data['subject']}_{data['session']}_{data['run']}"
            
            # Conditions per session
            qc_report['conditions_per_session'][session_id] = data['condition_order']
            
            # ROI types
            for roi in data['roi_info']:
                qc_report['roi_types_found'].add(f"{roi['hemisphere']}{roi['roi_type']}")
                
            # Beta value ranges
            beta_matrix = data['beta_matrix']
            all_betas.extend(beta_matrix.flatten())
            
            session_min = np.min(beta_matrix)
            session_max = np.max(beta_matrix)
            session_mean = np.mean(beta_matrix)
            
            qc_report['beta_value_ranges'][session_id] = {
                'min': float(session_min),
                'max': float(session_max),
                'mean': float(session_mean),
                'std': float(np.std(beta_matrix))
            }
            
            # Check for potential issues
            if session_min == session_max:
                qc_report['potential_issues'].append(f"{session_id}: All beta values identical")
            if np.abs(session_mean) > 100:
                qc_report['potential_issues'].append(f"{session_id}: Unusually large beta values (mean: {session_mean:.2f})")
            if len(data['condition_order']) < 4:
                qc_report['potential_issues'].append(f"{session_id}: Missing conditions: {data['missing_conditions']}")
                
        # Overall beta statistics
        qc_report['overall_beta_stats'] = {
            'min': float(np.min(all_betas)),
            'max': float(np.max(all_betas)),
            'mean': float(np.mean(all_betas)),
            'std': float(np.std(all_betas)),
            'n_values': len(all_betas)
        }
        
        return qc_report

    def save_extracted_data(self, all_session_data, output_dir):
        """
        Save extracted beta values in organized format
        
        Parameters:
        -----------
        all_session_data : list
            Session data from extract_all_sessions()
        output_dir : str or Path
            Output directory for saved data
        """
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\nSaving extracted data to: {output_dir}")
        
        # Save individual session files
        session_inventory = []
        
        for data in all_session_data:
            session_id = f"{data['subject']}_{data['session']}_{data['run']}"
            session_dir = output_dir / session_id
            session_dir.mkdir(exist_ok=True)
            
            # Save beta matrix
            np.save(session_dir / "beta_matrix.npy", data['beta_matrix'])
            
            # Save ROI info as CSV
            roi_df = pd.DataFrame(data['roi_info'])
            roi_df.to_csv(session_dir / "roi_info.csv", index=False)
            
            # Save metadata
            metadata = {
                'subject': data['subject'],
                'session': data['session'],
                'run': data['run'],
                'feat_path': str(data['feat_path']),
                'condition_order': data['condition_order'],
                'extraction_info': data['extraction_info'],
                'sphere_radius': data['sphere_radius'],
                'n_rois': data['n_rois'],
                'n_conditions': data['n_conditions'],
                'missing_conditions': data['missing_conditions'],
                'beta_matrix_shape': data['beta_matrix'].shape
            }
            
            with open(session_dir / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
                
            # Add to inventory
            session_inventory.append({
                'session_id': session_id,
                'subject': data['subject'],
                'session': data['session'],
                'run': data['run'],
                'n_rois': data['n_rois'],
                'n_conditions': data['n_conditions'],
                'condition_order': ','.join(data['condition_order']),
                'missing_conditions': ','.join(data['missing_conditions']) if data['missing_conditions'] else '',
                'beta_matrix_shape': f"{data['beta_matrix'].shape[0]}x{data['beta_matrix'].shape[1]}",
                'feat_path': str(data['feat_path'])
            })
            
        # Save session inventory
        inventory_df = pd.DataFrame(session_inventory)
        inventory_df.to_csv(output_dir / "session_inventory.csv", index=False)
        
        # Save extraction statistics
        with open(output_dir / "extraction_stats.json", 'w') as f:
            json.dump(self.extraction_stats, f, indent=2)
            
        print(f"  ✓ Saved {len(all_session_data)} sessions")
        print(f"  ✓ Session inventory: {output_dir / 'session_inventory.csv'}")
        print(f"  ✓ Extraction stats: {output_dir / 'extraction_stats.json'}")
        
        return output_dir / "session_inventory.csv"

    def print_extraction_summary(self):
        """Print summary of extraction process"""
        
        stats = self.extraction_stats
        
        print("\n" + "=" * 60)
        print("BETA EXTRACTION SUMMARY")
        print("=" * 60)
        print(f"Sessions attempted: {stats['sessions_attempted']}")
        print(f"Sessions successful: {stats['sessions_successful']}")
        print(f"Success rate: {stats['sessions_successful']/stats['sessions_attempted']*100:.1f}%")
        print(f"Total ROIs extracted: {stats['rois_extracted']}")
        
        if stats['failed_extractions']:
            print(f"\nFailed extractions ({len(stats['failed_extractions'])}):")
            for failure in stats['failed_extractions']:
                print(f"  - {failure}")
                
        if stats['missing_cope_files']:
            print(f"\nMissing cope files ({len(stats['missing_cope_files'])}):")
            for missing in set(stats['missing_cope_files']):
                print(f"  - {missing}")

def main():
    """Main execution function"""
    
    # Paths
    base_dir = "/user_data/csimmon2/long_pt"
    roi_coords_file = Path(base_dir) / "analyses" / "roi_extraction" / "peak_roi_coordinates.csv"
    output_dir = Path(base_dir) / "analyses" / "beta_extraction"
    
    print("VOTC Beta Value Extraction")
    print("=" * 60)
    print(f"ROI coordinates: {roi_coords_file}")
    print(f"Output directory: {output_dir}")
    
    # Check input file exists
    if not roi_coords_file.exists():
        raise FileNotFoundError(f"ROI coordinates file not found: {roi_coords_file}")
        
    # Initialize extractor
    extractor = VOTCBetaExtractor(roi_coords_file, base_dir, sphere_radius=7.0)
    
    # Extract beta values
    all_session_data = extractor.extract_all_sessions()
    
    if len(all_session_data) == 0:
        print("ERROR: No sessions successfully extracted!")
        return None
        
    # Quality control
    print(f"\nPerforming quality control checks...")
    qc_report = extractor.validate_extracted_data(all_session_data)
    
    # Save results
    inventory_file = extractor.save_extracted_data(all_session_data, output_dir)
    
    # Save QC report
    with open(output_dir / "qc_report.json", 'w') as f:
        json.dump(qc_report, f, indent=2, default=str)
        
    # Print summary
    extractor.print_extraction_summary()
    
    print(f"\n✓ Beta extraction complete!")
    print(f"✓ Main inventory file: {inventory_file}")
    print(f"✓ QC report: {output_dir / 'qc_report.json'}")
    
    return all_session_data, qc_report

if __name__ == "__main__":
    data, qc = main()