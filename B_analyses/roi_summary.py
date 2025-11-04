# Generate detailed methods summary
# CELL 1: Imports
import numpy as np
import nibabel as nib
from pathlib import Path
import matplotlib.pyplot as plt
from scipy.stats import linregress
from scipy.ndimage import center_of_mass, label, binary_dilation
from nilearn import plotting
import pandas as pd

print("✓ Imports loaded")
def generate_methods_summary():
    """
    Create comprehensive methods documentation for ROI extraction
    """
    
    methods = """
================================================================================
DETAILED METHODS: ROI DEFINITION AND EXTRACTION
================================================================================

1. ANATOMICAL SEARCH MASK CREATION
================================================================================

1.1 FreeSurfer Parcellation
---------------------------
- Atlas: Desikan-Killiany (aparc+aseg.mgz)
- Software: FreeSurfer 7.x longitudinal stream
- All subjects processed through recon-all with longitudinal template

1.2 Parcel Selection
-------------------
Category-specific anatomical search regions were defined using the following
Desikan-Killiany parcels:

FACE:
  - Fusiform gyrus (LH: 1007, RH: 2007)

WORD:
  - Fusiform gyrus (LH: 1007, RH: 2007)
  - Inferior temporal gyrus (LH: 1009, RH: 2009)

OBJECT:
  - Lateral occipital cortex (LH: 1011, RH: 2011)

HOUSE:
  - Parahippocampal gyrus (LH: 1016, RH: 2016)
  - Lingual gyrus (LH: 1013, RH: 2013)
  - Isthmus cingulate (LH: 1010, RH: 2010)

Rationale for house parcel selection: Initial analysis using only parahippocampal
gyrus failed to capture place-selective activation in patient UD (2 voxels in
ses-01). Lingual gyrus and isthmus cingulate were added as these regions are
known to be scene-responsive and anatomically adjacent to canonical PPA. This
expanded the search region from 1,847 to 24,507 voxels for UD, successfully
capturing activation (88 voxels at z>3.0).

1.3 Registration to Native Space
--------------------------------
FreeSurfer → Subject Native Space transformation:
  - Tool: FSL FLIRT v6.0
  - Input: FreeSurfer brain.mgz
  - Reference: Subject ses-01 T1w_brain.nii.gz
  - DOF: 6 (rigid body)
  - Cost function: Correlation ratio
  - Interpolation: Nearest neighbor (for binary masks)
  - Output: fs2ses01.mat transformation matrix

Applied transformation:
  - Each anatomical parcel mask transformed from FreeSurfer to subject space
  - Interpolation: Nearest neighbor to preserve binary masks
  - Verified: Visual inspection of registration quality

1.4 Mask Dilation
-----------------
- Method: Binary dilation (scipy.ndimage.binary_dilation)
- Iterations: 1 (single 3x3x3 voxel structuring element)
- Rationale: Account for registration imprecision and anatomical variability
  in post-surgical anatomy

Final search mask sizes (UD, subject space):
  - Face: 19,331 voxels
  - Word: 40,129 voxels
  - Object: 25,843 voxels
  - House: 24,507 voxels

Final search mask sizes (TC, subject space):
  - Face: 13,736 voxels
  - Word: 29,532 voxels
  - Object: 21,271 voxels
  - House: 17,288 voxels


2. FUNCTIONAL LOCALIZER DATA
================================================================================

2.1 Experimental Design
-----------------------
- Block design category localizer
- Categories: Faces, Words, Objects, Houses (+ scrambled control)
- Registration: All functional runs co-registered to ses-01 anatomical using
  boundary-based registration (BBR)
- Preprocessing: Standard FSL FEAT pipeline
  - Motion correction
  - Slice timing correction
  - High-pass temporal filtering
  - NO spatial smoothing (to preserve fine-grained activation patterns)

2.2 Statistical Contrasts
-------------------------
- Face: Faces > Objects (cope10)
- Word: Words > Objects (cope12)
- Object: Objects > Scrambled (cope3)
- House: Houses > Objects (cope11)

- Statistical maps: z-statistics from FSL FEAT GLM
- Threshold: z > 3.0 (p < 0.001, one-tailed, uncorrected)
- Rationale: Following Nordt et al. (2021) and Liu et al. (2025) who used
  t > 3.0, approximately equivalent to z > 3.0


3. FUNCTIONAL ROI DEFINITION (APPROACH 1: GROWING/MOVING CLUSTERS)
================================================================================

3.1 Cluster Extraction Per Session
-----------------------------------
For each category, in each session:

Step 1: Threshold functional map
  - Applied z > 3.0 threshold to category contrast
  - Constrained to category-specific anatomical search mask
  - Result: Binary suprathreshold map

Step 2: Connected components labeling
  - Method: scipy.ndimage.label
  - Connectivity: 26-connected (3D, face/edge/corner adjacent voxels)
  - Output: Labeled cluster map

Step 3: Select largest cluster
  - Criterion: Maximum number of voxels
  - Minimum size: 50 voxels (clusters <50 excluded as unreliable)
  - This functional cluster = ROI for this session

Step 4: Extract metrics
  - ROI size: Number of voxels in largest cluster
  - Peak z-value: Maximum z-statistic within ROI
  - Peak coordinate: Voxel coordinate of maximum z-value
  - Centroid: Center of mass of cluster (scipy.ndimage.center_of_mass)
  - All coordinates in subject ses-01 native space

3.2 Longitudinal Tracking
-------------------------
- Each session analyzed independently
- ROI location allowed to vary across sessions (tracking plasticity)
- If no cluster ≥50 voxels found, that session excluded for that category
- Drift quantified as Euclidean distance between session centroids

UD sessions analyzed: 01, 02, 03, 05, 06
TC sessions analyzed: 01, 02, 03


4. FUNCTIONAL ROI DEFINITION (APPROACH 2: FIXED CONCENTRIC SPHERES)
================================================================================

4.1 Sphere Center Definition
----------------------------
- Center: Centroid of ses-01 functional cluster (from Approach 1)
- If no ses-01 cluster ≥50 voxels, category excluded from sphere analysis
- Coordinates: Subject ses-01 native space (mm)

4.2 Sphere Generation
---------------------
Radii: 3mm, 6mm, 9mm (following Golarai et al. 2007, 2010)

For each radius:
  - Created binary mask of all voxels within Euclidean distance from center
  - Method: 
    1. Generate 3D coordinate grid of brain volume
    2. Transform to world coordinates (mm) using affine matrix
    3. Calculate Euclidean distance from sphere center
    4. Threshold: Include voxels where distance ≤ radius
  - Result: 3 concentric spheres per category (nested)

4.3 Selectivity Measurement Across Sessions
-------------------------------------------
For each sphere, in each session:
  - Extracted z-values from all voxels within sphere
  - Calculated mean z-value across sphere
  - Result: Mean selectivity trajectory across development
  - Fixed location = measures selectivity change at same cortical location

Note: Spheres defined once (ses-01) and applied to all subsequent sessions
to assess selectivity changes at a fixed location (in contrast to Approach 1
where ROI location can move).


5. DATA HANDLING FOR LONGITUDINAL SESSIONS
================================================================================

5.1 Cross-Session Registration
------------------------------
- All functional data from later sessions (02, 03, 05, 06) registered to ses-01
- Method: FSL FEAT boundary-based registration (BBR)
- Ensures all ROI coordinates are in common ses-01 space
- Statistical maps from later sessions: zstat1_ses01.nii.gz

5.2 Handling Missing/Weak Sessions
----------------------------------
Criteria for exclusion:
  - No suprathreshold voxels (z>3.0) within search mask
  - Largest cluster <50 voxels
  - Session data not acquired or failed quality control

Categories excluded per session:
  UD ses-01: Word (61 voxels, below threshold), House (88 voxels, marginal)
  [Note: These were included in final analysis as biologically meaningful
   weak signals, but flagged as potentially unreliable]


6. QUALITY CONTROL AND VALIDATION
================================================================================

6.1 Anatomical Mask Coverage Assessment
---------------------------------------
For each category in ses-01:
  - Calculated percentage of suprathreshold activation captured by search mask
  - Verified largest cluster was within anatomically plausible region
  - Example: UD house initially showed only 2/92 voxels (2%) in parahippocampal
    mask alone, leading to expansion with lingual + isthmus cingulate

6.2 Peak Location Verification
------------------------------
- All peak coordinates visually inspected on individual anatomy
- Compared to canonical locations from literature (Golarai 2007, Liu 2025)
- Atypical locations noted (e.g., UD house in lingual rather than PHG)

6.3 Consistency Checks
---------------------
- Verified sphere trajectories showed plausible patterns (not noise)
- Cross-referenced with Liu et al. (2025) findings for same subjects
- Confirmed TC (intact hemisphere) showed more stable trajectories than UD


7. STATISTICAL ANALYSIS OUTPUTS
================================================================================

For each ROI, each session:

From Functional Clusters (Approach 1):
  - ROI volume (mm³)
  - Peak z-statistic
  - Peak coordinates (x, y, z in mm, ses-01 space)
  - Centroid coordinates (x, y, z in mm, ses-01 space)
  - Session-to-session drift (mm, Euclidean distance between centroids)

From Concentric Spheres (Approach 2):
  - Mean z-statistic per radius (3mm, 6mm, 9mm)
  - Selectivity trajectory across sessions
  - Rate of change in selectivity (Δz per session)


8. SOFTWARE AND VERSIONS
================================================================================

- FreeSurfer: 7.x (longitudinal stream)
- FSL: 6.0 (FEAT, FLIRT, fslstats)
- Python: 3.10+
  - nibabel: 5.1+ (NIFTI I/O)
  - numpy: 1.24+ (array operations)
  - scipy: 1.11+ (ndimage for clustering, dilation, center of mass)
  - nilearn: 0.10+ (visualization)
  - matplotlib: 3.7+ (plotting)


9. KEY METHODOLOGICAL DECISIONS AND RATIONALE
================================================================================

9.1 Why Category-Specific Masks Instead of Large VOTC?
------------------------------------------------------
Initial approach: Single large VOTC mask (fusiform + LO + PPA + IT + MT)
  - Result: Excessive drift (UD word: 23mm)
  - Problem: Too permissive, captured spurious peaks

Final approach: Category-specific anatomical constraints
  - Rationale: Balance between anatomical precision and capturing reorganization
  - Face: Fusiform only (FFA canonical location)
  - Word: Fusiform + inferior temporal (VWFA extends laterally)
  - Object: Lateral occipital only (LOC well-localized)
  - House: PHG + lingual + isthmus (captures both canonical and atypical PPA)

9.2 Why z>3.0 Threshold?
------------------------
- Follows Liu et al. (2025): t>3.0 (approximately z>3.0)
- Follows Nordt et al. (2021): t>3.0
- Provides good balance between sensitivity and specificity
- More liberal than p<0.001 corrected, but these are patient data with
  potentially reduced signal

9.3 Why 50 Voxel Minimum?
-------------------------
- Clusters <50 voxels likely unreliable (noise or spurious activation)
- At 2x2x2mm resolution, 50 voxels ≈ 400mm³
- Provides confidence in peak location stability

9.4 Why Two Approaches (Clusters + Spheres)?
--------------------------------------------
Following Golarai et al. (2007, 2010):
  - Approach 1 (Functional clusters): Captures plasticity via moving/growing ROIs
  - Approach 2 (Fixed spheres): Measures selectivity change at same location
  - Complementary: One shows "where", other shows "how much"
  - Critical for distinguishing local intensification vs. spatial reorganization


10. LIMITATIONS AND CAVEATS
================================================================================

- Small sample (n=2 patients)
- Post-surgical anatomy makes standard parcellation less reliable
- Category-specific masks still imperfect (UD word 61 voxels, house 88 voxels)
- No correction for multiple comparisons (exploratory single-subject analysis)
- Registration challenges with missing hemisphere
- Assumption that ses-01 peak location is "correct" reference for spheres

================================================================================
"""
    
    return methods

# Generate and save
methods_text = generate_methods_summary()
print(methods_text)

BASE_DIR = Path("/user_data/csimmon2/long_pt")
OUTPUT_DIR = BASE_DIR / "analyses" / "rsa_corrected"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Save to file
with open(OUTPUT_DIR / 'ROI_Methods_Detailed.txt', 'w') as f:
    f.write(methods_text)

print("\n✓ Methods summary saved to ROI_Methods_Detailed.txt")