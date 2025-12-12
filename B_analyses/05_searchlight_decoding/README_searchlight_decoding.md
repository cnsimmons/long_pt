# Searchlight Decoding Pipeline for Longitudinal VOTC Study

## Overview

This pipeline implements searchlight decoding analysis to investigate how category representations reorganize following pediatric OTC resection. It complements the ROI-based measures from your previous analyses.

## Research Question

**Do bilateral visual categories (Object, House) show greater representational reorganization than unilateral categories (Face, Word) following pediatric OTC resection?**

### Key Hypotheses (from handoff document)

| Measure | Bilateral Prediction | Unilateral Prediction | Interpretation |
|---------|---------------------|----------------------|----------------|
| Accuracy Change | NEGATIVE (degradation) | STABLE | Bilateral degrades in place |
| Cross-Temporal Acc | LOW | HIGH | Bilateral code changed |
| Spatial Overlap (Dice) | HIGH | LOW | Unilateral maps relocate |

## Pipeline Components

### 1. `searchlight_decoding_longitudinal.py`
**Full-featured analysis with BrainIAK support**
- Complete searchlight implementation
- Cross-validation strategies (leave-one-run-out, stratified shuffle)
- All three key analyses (accuracy change, cross-temporal, Dice overlap)

### 2. `searchlight_decoding_nilearn.py` 
**Practical implementation using nilearn**
- Faster ROI-based alternative to full searchlight
- Full searchlight option available with `--searchlight` flag
- Properly handles your specific data structure

**Usage:**
```bash
# Single subject (fast ROI-based)
python searchlight_decoding_nilearn.py sub-004

# Single subject (full searchlight)
python searchlight_decoding_nilearn.py sub-004 --searchlight

# All subjects
python searchlight_decoding_nilearn.py --all
```

### 3. `searchlight_group_analysis.py`
**Group-level statistical analysis**
- Bootstrap confidence intervals (following Ayzenberg 2023)
- Within-subject comparisons
- Linear Mixed Models (following Nordt 2023)
- Summary tables matching ROI format from handoff

**Usage:**
```bash
python searchlight_group_analysis.py [results_csv_path]
```

## Data Structure Expected

```
/user_data/csimmon2/long_pt/
├── sub-XXX/
│   ├── ses-XX/
│   │   ├── derivatives/fsl/loc/
│   │   │   ├── HighLevel.gfeat/
│   │   │   │   ├── cope{N}.feat/stats/zstat1.nii.gz
│   │   │   ├── run-01.feat/filtered_func_data_reg.nii.gz
│   │   │   ├── run-02.feat/filtered_func_data_reg.nii.gz
│   │   ├── ROIs/
│   │   │   ├── r_face_searchmask.nii.gz
│   │   │   ├── l_word_searchmask.nii.gz
│   │   ├── covs/
│   │   │   ├── catloc_{sub}_run-0{run}_{category}.txt
```

## Subject Groups

| Group | N | Subjects | Notes |
|-------|---|----------|-------|
| OTC | 6 | sub-004, sub-008, sub-010, sub-017, sub-021, sub-079 | Resection includes VOTC |
| nonOTC | 9 | sub-007, sub-045, sub-047, sub-049, sub-070, sub-072, sub-073, sub-081, sub-086 | Resection outside VOTC |
| Control | 9 | sub-018, sub-022, sub-025, sub-027, sub-052, sub-058, sub-062, sub-064, sub-068 | Typically developing |

### Session Overrides
```python
SESSION_START = {'sub-010': 2, 'sub-018': 2, 'sub-068': 2, 'sub-021': 2}
```

## COPE Definitions

| Category | COPE | Contrast |
|----------|------|----------|
| Face | 10 | Face > Scramble |
| Word | 12 | Word > Scramble |
| Object | 3 | Object > Scramble |
| House | 11 | House > Scramble |

**Note:** Word uses cope12 (Word>Scramble) rather than cope13 (Word>Face inverted) as it has stronger signal.

## Methodological Basis

### Ayzenberg et al. (2023)
- SVM classifier with 30-fold cross-validation (80/20 split)
- StratifiedShuffleSplit for balanced folds
- Decoding contrasts: category vs. scramble

### Liu et al. (2025)
- Same raw data
- Longitudinal tracking framework
- McNemar's test for voxel-wise changes

### Nordt et al. (2023)
- Linear Mixed Models with participant random effects
- tSNR as covariate (recommend adding to pipeline)
- Distinctiveness measures

## Analysis Flow

```
1. Load functional data (filtered_func_data_reg.nii.gz)
     ↓
2. Load timing files (catloc_*_{category}.txt)
     ↓
3. Extract block patterns (account for HRF delay)
     ↓
4. Run searchlight SVM classification
     ↓
5. Compare accuracy maps between sessions
     - Dice coefficient for spatial overlap
     - Mean accuracy change
     ↓
6. Cross-temporal generalization test
     - Train session 1 → Test session 2
     ↓
7. Group-level analysis
     - OTC bilateral vs unilateral
     - OTC vs nonOTC vs Control
```

## Output Files

```
/user_data/csimmon2/git_repos/long_pt/B_analyses/searchlight_decoding/
├── sub-XXX_decoding_results.csv     # Individual subject results
├── all_subjects_decoding_results.csv # Combined results
├── summary_table.csv                 # Summary matching ROI format
```

## Key Outputs

| Metric | Description | Range |
|--------|-------------|-------|
| `accuracy_sesN` | Within-session decoding accuracy | 0.5-1.0 |
| `accuracy_change` | Session 2 - Session 1 accuracy | -0.5 to 0.5 |
| `cross_temporal_forward` | Train ses1 → test ses2 | 0.5-1.0 |
| `cross_temporal_backward` | Train ses2 → test ses1 | 0.5-1.0 |
| `cross_temporal_mean` | Average of forward/backward | 0.5-1.0 |
| `dice_0.55` | Spatial overlap at 55% threshold | 0-1 |

## Dependencies

**Required:**
- numpy
- pandas
- nibabel
- nilearn
- scikit-learn
- scipy

**Optional (for full functionality):**
- brainiak (for faster searchlight)
- statsmodels (for LMM analyses)

## Tips for Running

1. **Start with ROI-based analysis** (fast) to verify data loading works:
   ```bash
   python searchlight_decoding_nilearn.py sub-004
   ```

2. **Then run full searchlight** on one subject to check results:
   ```bash
   python searchlight_decoding_nilearn.py sub-004 --searchlight
   ```

3. **Finally run all subjects** (consider submitting as cluster job):
   ```bash
   python searchlight_decoding_nilearn.py --all
   ```

4. **Run group analysis** after all subjects complete:
   ```bash
   python searchlight_group_analysis.py
   ```

## Alignment with ROI Measures (from handoff)

| ROI Measure | Decoding Equivalent | Expected Pattern |
|-------------|---------------------|------------------|
| Spatial Relocation (mm) | Map Overlap (Dice) | Uni moves more, Bil stable |
| Selectivity Change | Accuracy Change | Bil degrades more |
| Geometry Preservation | Cross-temporal accuracy | Bil loses generalization |

## Questions to Address (from handoff)

1. **Search mask:** Currently using whole-brain mask from functional data. Can add anatomical ventral mask if available.

2. **Classifier:** Using SVM (following Ayzenberg). Could also try LDA.

3. **Cross-validation:** Using leave-one-run-out when multiple runs available, otherwise stratified shuffle.

4. **Threshold for accuracy maps:** Testing 0.55 and 0.60 for Dice calculation.

5. **Statistical comparison:** Bootstrap CI (Ayzenberg) + LMM (Nordt) + within-subject tests.

6. **Runs per session:** Automatically detected from file system.

## Contact

For questions about this pipeline, refer to the handoff document in project knowledge.
