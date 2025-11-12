# Long PT Study

## Description
This repository contains data for the longitudinal patient study.

## Data Structure
- `sub-004/`: Subject 004 data
- `sub-007/`: Subject 007 data  
- `sub-021/`: Subject 021 data

## Notes
[# Long_pt Data Organization and Processing

## Data Sources

### Longitudinal Dataset (`long_pt_sub_info.csv`)
- **Purpose**: Longitudinal analysis (multiple timepoints per subject)
- **Raw data**: `/lab_data/behrmannlab/hemi/Raw`
- **Processed data**: `/user_data/csimmon2/long_pt`
- **Structure**: Multiple sessions per subject (up to 5 timepoints)
- **Scanner**: Mixed (Verio and Prisma - see scanner column in CSV)

### Categorical/Cross-sectional Dataset (`cat_pt_sub_info.csv`)
- **Purpose**: Categorical analysis (single timepoint per subject)
- **Raw data**: `/lab_data/behrmannlab/hemi/Raw`
- **Processed data**: `/lab_data/behrmannlab/vlad/ptoc`
- **Structure**: One session per row
- **Scanner**: All Prisma
- **Note**: Preprocessing identical to long_pt but saved in different directory

## Participant Groups

- **Patients**: Hemispherectomy with OTC (occipitotemporal cortex) lesions
- **Control Patients**: Hemispherectomy with lesions outside OTC
- **Controls**: Healthy participants

## Scanner Information

### Verio vs Prisma
- **Coverage difference**: Older Verio scans have 27 slices (focused region), Prisma/newer Verio have 69 slices (whole brain)
- **Analysis approach**: Generally kept separate, may require harmonization
- **cat_pt dataset**: All Prisma (69 slices)
- **long_pt dataset**: Mixed scanners (check CSV)

## Dataset Overlap

### Subjects in BOTH datasets:
- sub-004 (long_pt: ses-01,02,03,05,06 | cat_pt: ses-07)
- sub-007 (long_pt: ses-01,03,04 | cat_pt: ses-05)
- sub-025 (long_pt: multiple sessions | cat_pt: ses-03)
- sub-064 (long_pt: multiple sessions | cat_pt: ses-02)
- sub-068 (long_pt: multiple sessions | cat_pt: ses-02)
- sub-079 (long_pt: ses-01,02 | cat_pt: ses-01)

### Unique to cat_pt:
sub-066, sub-069, sub-074, sub-075, sub-076, sub-077, sub-078, sub-089, sub-090, sub-091, sub-092, sub-093, sub-094, sub-095, sub-096, sub-097, sub-107, sub-hemispace1004, sub-hemispace1006, sub-hemispace1007

## Known Issues

### Missing/Problematic Data
- **sub-079 ses-02**: Missing events.tsv files (functional data exists but no timing info)
- **sub-017 ses-01 & ses-02**: Collected same day, unclear distinction. Sessions 1,2,4 exist (missing 3). Ses-02 has rotated anatomy.

### Special Session Numbering
- **sub-010**: Uses ses-02, ses-03 (skip ses-01)
- **sub-018**: Uses ses-02, ses-03 (skip ses-01)

## Processing Pipeline

All scripts updated to use CSV-driven approach:
1. `00_setup_directories.py` - Create directory structure
2. `00_convert_timing_FS2FSL_full.sh` - Convert events to FSL timing files
3. `01_extract_confounds.sh` - Extract motion confounds
4. `02_register_mirror.py` - Skull strip, mirror, register to MNI
5. `03_create_fsf.sh` - Generate FEAT design files
6. `submit_jobs.py` - Submit SLURM jobs

### Currently Processed (SKIP_SUBS)
- sub-004, sub-007, sub-021, sub-108]





----
# Long_pt Data Organization and Processing

## Data Sources

### Longitudinal Dataset (`long_pt_sub_info.csv`)
- **Purpose**: Longitudinal analysis (multiple timepoints per subject)
- **Raw data**: `/lab_data/behrmannlab/hemi/Raw`
- **Processed data**: `/user_data/csimmon2/long_pt`
- **CSV location**: `/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv`
- **Structure**: Multiple sessions per subject (up to 5 timepoints)
- **Scanner**: Mixed (Verio and Prisma - see scanner column in CSV)

### Categorical/Cross-sectional Dataset (`cat_pt_sub_info.csv`)
- **Purpose**: Categorical analysis (single timepoint per subject)
- **Raw data**: `/lab_data/behrmannlab/hemi/Raw`
- **Processed data**: `/lab_data/behrmannlab/vlad/ptoc`
- **Structure**: One session per row
- **Scanner**: All Prisma
- **Note**: Preprocessing identical to long_pt but saved in different directory

## Participant Groups

- **Patients**: Hemispherectomy with OTC (occipitotemporal cortex) lesions
- **Control Patients**: Hemispherectomy with lesions outside OTC
- **Controls**: Healthy participants

## Scanner Information

### Verio vs Prisma
- **Coverage difference**: Older Verio scans have 27 slices (focused region), Prisma/newer Verio have 69 slices (whole brain)
- **Analysis approach**: Generally kept separate, may require harmonization
- **Patients same scanner across sessions**: No cross-scanner issues within subjects
- **cat_pt dataset**: All Prisma (69 slices)
- **long_pt dataset**: Mixed scanners (check CSV)

## Dataset Overlap

### Subjects in BOTH datasets:
- sub-004 (long_pt: ses-01,02,03,05,06 | cat_pt: ses-07)
- sub-007 (long_pt: ses-01,03,04 | cat_pt: ses-05)
- sub-025 (long_pt: multiple sessions | cat_pt: ses-03)
- sub-064 (long_pt: multiple sessions | cat_pt: ses-02)
- sub-068 (long_pt: multiple sessions | cat_pt: ses-02)
- sub-079 (long_pt: ses-01,02 | cat_pt: ses-01)

### Unique to cat_pt:
sub-066, sub-069, sub-074, sub-075, sub-076, sub-077, sub-078, sub-089, sub-090, sub-091, sub-092, sub-093, sub-094, sub-095, sub-096, sub-097, sub-107, sub-hemispace1004, sub-hemispace1006, sub-hemispace1007

## Known Issues

### Missing/Problematic Data
- **sub-079 ses-02**: Missing events.tsv files (functional data exists but no timing info)
- **sub-017**: Sessions 1,2,4 exist (missing 3). Ses-01 and ses-02 collected same day. Ses-02 has rotated anatomy.

### Special Session Numbering
- **sub-010**: Uses ses-02, ses-03 (skip ses-01)
- **sub-018**: Uses ses-02, ses-03 (skip ses-01)
- **sub-068**: Uses ses-02, ses-03 (skip ses-01)

**Important**: All scripts include `SESSION_START` dictionary to handle these cases.

### Confound Files
- `fsl_motion_outliers` only creates spike files when motion outliers are detected
- Missing confound files = clean run with no motion above threshold (--fd --thresh=0.5)
- This is normal FSL behavior, not an error
- FEAT runs fine without confound files (just no motion regressors added)

## Processing Pipeline

All scripts updated to CSV-driven approach with automatic run detection:

1. `00_setup_directories.py` - Create directory structure
2. `00_convert_timing_FS2FSL_full.sh` - Convert events to FSL timing files (saves to `timing/`)
3. `01_extract_confounds.sh` - Extract motion confounds (optional output)
4. `02_register_mirror.py` - Skull strip, mirror (patients), register to MNI
5. `03_create_fsf.sh` - Generate FEAT 1stLevel design files
6. `submit_jobs.py` - Submit SLURM jobs for 1stLevel FEAT
7. `04_1stLevel.py` - Register filtered_func_data to anatomical space
8. `05_create_firstses_matrices.sh` - Create session-to-first-session registration
9. `06_register_atlas.sh` - Register Harvard-Oxford parcels to subject space
10. `07_register_zstats.py` - Register zstats to first-session anatomy
11. `08_create_highlevel_feat.sh` - Generate HighLevel FSF files
12. `submit_jobs.py` - Submit SLURM jobs for HighLevel FEAT
13. `09_highLevel.py` - Process HighLevel outputs to first-session space
14. `09.5_register_ho_atlas.sh` - Register full H-O atlas to subject space
15. `10_extract_dk_parcels.py` - Extract Desikan-Killiany parcels from FreeSurfer

### Currently Processed (SKIP_SUBS)
- sub-004, sub-007, sub-021, sub-108

### CSV Format Notes
- Remove Windows line endings: `sed -i 's/\r$//' long_pt_sub_info.csv`
- No commas in quoted fields
- End file with newline

## Technical Notes

### Registration Strategy
- All analyses registered to **first session** anatomy (not MNI)
- Enables consistent cross-session comparison
- HighLevel outputs use first-session as standard space

### File Locations
- Timing files: `ses-*/timing/`
- Confounds: `ses-*/derivatives/fsl/loc/run-*/`
- ROIs: `ses-01/ROIs/` (first session only)
- Registration matrices: `ses-*/anat/`

## Job Management
```bash
# Submit jobs
python submit_jobs.py

# Check status
squeue -u $USER

# Cancel jobs
scancel <job_id>
scancel -u $USER  # all jobs
```

## Validation

Check preprocessing completeness:
```bash
python check_completeness.py
```

Checks: timing files, confounds, skull stripping, registration, FSF files, FEAT completion