"""
Configuration file for hemispherectomy patient preprocessing pipeline
"""
import os

# Study information
STUDY_NAME = 'long_pt'
PROJECT_DIR = '/user_data/csimmon2/git_repos/long_pt'

# Data directories
RAW_DATA_DIR = '/Users/clairesimmons/lab_data/behrmannlab/behrmannlab/hemi/Raw'
PROCESSED_DIR = '/Users/clairesimmons/lab_data/behrmannlab/behrmannlab/claire/long_pt'

# Subject information
SUBJECTS = {
    'sub-004': {
        'intact_hemi': 'left',
        'group': 'patient'
    },
    'sub-007': {
        'intact_hemi': 'right', 
        'group': 'patient'
    },
    'sub-021': {
        'intact_hemi': 'left',
        'group': 'patient'
    }
}

# Task information
TASK = 'loc'
RUNS = [1, 2]  # Adjust based on your data
CONDITIONS = ['Face', 'House', 'Object', 'Scramble', 'Word']

# MRI parameters
TR = 2.0  # Repetition time in seconds
STIMDUR = 16  # Stimulus duration in seconds (adjust based on your design)

# FSL paths
MNI_BRAIN = '/opt/fsl/6.0.3/data/standard/MNI152_T1_2mm_brain.nii.gz'
FSL_DIR = '/opt/fsl/6.0.3'

# ROI information
ROI_PARCELS = ['ventral_visual_cortex', 'dorsal_visual_cortex']  # Add your ROIs
PARCEL_DIR = f'{PROJECT_DIR}/roiParcels'

# Processing options
GLMSINGLE_OPTIONS = {
    'wantlibrary': 1,      # Fit HRF to each voxel
    'wantglmdenoise': 1,   # Use GLMdenoise
    'wantfracridge': 1,    # Use ridge regression
    'wantfileoutputs': [1, 1, 1, 1],
    'wantmemoryoutputs': [0, 0, 0, 0]  # Save memory
}

# Create directories
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(PARCEL_DIR, exist_ok=True)
