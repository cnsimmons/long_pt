# Long PT Study

## Description
Longitudinal hemispherectomy patient study investigating visual category development using RSA (Representational Similarity Analysis) and spatial drift analysis.

## Subjects
- **Current datasets**: See `long_pt_sub_info.csv` for complete subject list
- **Subject groups**: OTC patients (primary), nonOTC patients (secondary), controls
- **Data abnormalities**: 
  - sub-010, sub-018, sub-068: Start at ses-02 (skip ses-01)
  - sub-017: Missing ses-03, ses-01/02 collected same day
  - sub-079: Missing ses-02 events files

---

# Data Organization and Processing Pipeline

## Required Preprocessing
**Critical**: Both FSL and FreeSurfer processing required before RSA analysis

### 1. FSL Pipeline
- Motion correction, registration, GLM analysis
- Produces statistical maps (zstat files) for RSA
- See existing processing scripts (00-09 series)

### 2. FreeSurfer Pipeline  
- **Input**: Mirrored anatomy (for post-surgical brains)
- **Output**: Desikan-Killiany parcellation (aparc+aseg.mgz)
- **Purpose**: Creates anatomical search masks for functional ROIs
- **Status**: Complete for sub-004, sub-007, sub-021; in progress for additional subjects

## RSA Analysis Pipeline

### Anatomical ROI Definition
- **Atlas**: Desikan-Killiany (FreeSurfer) 
- **Registration**: FreeSurfer → Subject space (FSL FLIRT, 6 DOF)
- **Category-specific search regions**:
  - Face: Fusiform gyrus
  - Word: Fusiform gyrus  
  - Object: Lateral occipital cortex
  - House: Parahippocampal + lingual + isthmus cingulate

### Functional ROI Extraction
- **Input**: FSL zstat maps + FreeSurfer search masks
- **Threshold**: z > 2.3 (following Liu et al. 2025)
- **Method**: Largest connected component within anatomical constraints
- **Output**: Session-specific ROI locations (spatial plasticity tracking)

### RSA Measures
- **Distinctiveness**: Liu's correlation-based measure
- **Spatial drift**: Euclidean distance between session centroids  
- **Statistical testing**: Bootstrap slope analysis
- **Comparison**: Bilateral vs unilateral category patterns

## Data Sources
- **Raw data**: `/lab_data/behrmannlab/hemi/Raw`
- **Processed data**: `/user_data/csimmon2/long_pt`
- **Subject info**: `/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv`
- **Analysis outputs**: `/user_data/csimmon2/long_pt/analyses/rsa_corrected/`

## File Structure
```
/user_data/csimmon2/long_pt/
├── analyses/rsa_corrected/           # RSA analysis outputs
├── derivatives/freesurfer/           # FreeSurfer outputs (mirrored anatomy)
└── sub-*/
    ├── ses-*/
    │   ├── anat/                    # Anatomical + registration files
    │   ├── ROIs/                    # Category-specific search masks  
    │   └── derivatives/fsl/loc/     # FSL functional analysis
```

## Processing Status
- **FSL preprocessing**: Complete for primary subjects
- **FreeSurfer**: Complete for sub-004, sub-007, sub-021; additional subjects in progress
- **RSA analysis**: Framework established, expanding to full cohort

## References
- Liu et al. (2025): Patient RSA methodology
- Golarai et al. (2007): Developmental framework
- Nordt et al. (2021): Longitudinal approaches