# %% [markdown]
# # Unified RSA Pipeline
# 
# ## Design
# - **ROI Definition**: Category > Scramble zstats from HighLevel (cope 10/12/3/11),
#   top-10% threshold within anatomical search masks
# - **RSA Pattern Extraction**: Per-condition parameter estimates from run-level FEATs,
#   registered to standard space and averaged across runs (Liu et al. approach)
# - **Univariate Measures**: Category > All Others copes from HighLevel (Ayzenberg approach),
#   patient-by-patient vs bootstrapped control CIs
# - **Sphere**: 6mm radius at session-specific centroid (dynamic)
# - **Patients**: Intact hemisphere only
# - **Controls**: Both hemispheres; averaged for primary comparison
# - **Metrics**: Liu distinctiveness, geometry preservation, MDS shift, spatial drift

# %% Cell 1: Setup & Configuration
import numpy as np
import nibabel as nib
from pathlib import Path
import pandas as pd
from scipy.ndimage import center_of_mass, label
from scipy.stats import pearsonr, mannwhitneyu, ttest_ind
from scipy.linalg import orthogonal_procrustes
import warnings
warnings.filterwarnings('ignore')

BASE_DIR = Path("/user_data/csimmon2/long_pt")
OUTPUT_DIR = BASE_DIR / "analyses" / "unified_rsa"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_FILE = Path('/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv')
df_info = pd.read_csv(CSV_FILE)

SESSION_START = {'sub-010': 2, 'sub-018': 2, 'sub-068': 2}
SUBJECTS_TO_EXCLUDE = {'sub-108'}

# ============================================================
# CONTRAST & PE MAPPING — single source of truth
# ============================================================
#
# Run-level design (1stLevel.feat, per run):
#   EV1=Face    → pe1 (HRF), pe2 (derivative)
#   EV2=House   → pe3 (HRF), pe4 (derivative)
#   EV3=Object  → pe5 (HRF), pe6 (derivative)
#   EV4=Words   → pe7 (HRF), pe8 (derivative)
#   EV5=Scramble→ pe9 (HRF), pe10 (derivative)
#   pe11+       = motion + spike regressors
#
# HighLevel contrasts (across runs):
#   cope1:  Face > Object        cope8:  Object > All Others
#   cope2:  House > Object       cope9:  Word > All Others
#   cope3:  Object > Scramble    cope10: Face > Scramble
#   cope4:  Word > Object        cope11: House > Scramble
#   cope5:  Scramble > Average   cope12: Word > Scramble
#   cope6:  Face > All Others    cope13: Face > Word
#   cope7:  House > All Others   cope14: Object > House

# For ROI DEFINITION: Category > Scramble zstats from HighLevel
LOCALIZER_COPES = {
    'face':   10,
    'word':   12,
    'object':  3,
    'house':  11,
}

# For RSA PATTERN EXTRACTION: per-condition PEs from run-level FEATs
# Registered to standard space and averaged across runs
# Files live in: {session}/derivatives/fsl/loc/registered_pes/{condition}_mean.nii.gz
RSA_CONDITIONS = ['face', 'house', 'object', 'word']

# For UNIVARIATE (Ayzenberg approach): Category > All Others from HighLevel
UNIVARIATE_COPES = {
    'face':    6,
    'house':   7,
    'object':  8,
    'word':    9,
}

CATEGORIES = ['face', 'word', 'object', 'house']
BILATERAL_CATEGORIES = ['object', 'house']
UNILATERAL_CATEGORIES = ['face', 'word']

ROI_PERCENTILE = 90
SPHERE_RADIUS = 6

print("✓ Configuration loaded")
print(f"  Localizer (ROI def): HighLevel copes {LOCALIZER_COPES}")
print(f"  RSA patterns: per-condition PEs (registered_pes/)")
print(f"  Univariate: HighLevel copes {UNIVARIATE_COPES}")
print(f"  Threshold: top {100 - ROI_PERCENTILE}%, Sphere: {SPHERE_RADIUS}mm")


# %% Cell 2: Load Subjects

def load_subjects(patient_only=None):
    filtered = df_info.copy()
    if patient_only is True:
        filtered = filtered[filtered['patient'] == 1]
    elif patient_only is False:
        filtered = filtered[filtered['patient'] == 0]

    subjects = {}
    for _, row in filtered.iterrows():
        sid = row['sub']
        if sid in SUBJECTS_TO_EXCLUDE:
            continue
        subj_dir = BASE_DIR / sid
        if not subj_dir.exists():
            continue

        sessions = sorted(
            [d.name.replace('ses-', '') for d in subj_dir.glob('ses-*') if d.is_dir()],
            key=lambda x: int(x)
        )
        start = SESSION_START.get(sid, 1)
        sessions = [s for s in sessions if int(s) >= start]
        if not sessions:
            continue

        hemi_full = row.get('intact_hemi', 'left')
        if pd.isna(hemi_full):
            hemi_full = 'left'

        subjects[sid] = {
            'code': f"{row['group']}{sid.split('-')[1]}",
            'sessions': sessions,
            'hemi': 'l' if hemi_full == 'left' else 'r',
            'group': row['group'],
            'is_patient': row['patient'] == 1,
        }
    return subjects

ALL_PATIENTS = load_subjects(patient_only=True)
ALL_CONTROLS = load_subjects(patient_only=False)
ALL_SUBJECTS = {**ALL_PATIENTS, **ALL_CONTROLS}

print(f"✓ {len(ALL_SUBJECTS)} subjects "
      f"({len(ALL_PATIENTS)} patients, {len(ALL_CONTROLS)} controls)")


# %% Cell 3: Core Utilities

def create_sphere(center_mni, affine, shape, radius=6):
    """Boolean mask for 6mm sphere around MNI coordinate."""
    grid = np.array(np.meshgrid(
        np.arange(shape[0]), np.arange(shape[1]), np.arange(shape[2]),
        indexing='ij'
    )).reshape(3, -1).T
    world = nib.affines.apply_affine(affine, grid)
    dists = np.linalg.norm(world - center_mni, axis=1)
    mask = np.zeros(shape, dtype=bool)
    for c in grid[dists <= radius]:
        mask[c[0], c[1], c[2]] = True
    return mask


def get_highlevel_stat(sid, session, cope_num, first_session, stat='zstat1'):
    """Path to HighLevel stat file (handles cross-session registration)."""
    feat_dir = (BASE_DIR / sid / f'ses-{session}' / 'derivatives' /
                'fsl' / 'loc' / 'HighLevel.gfeat')
    fname = f'{stat}.nii.gz' if session == first_session else f'{stat}_ses{first_session}.nii.gz'
    return feat_dir / f'cope{cope_num}.feat' / 'stats' / fname


def get_pe_path(sid, session, condition):
    """Path to registered, run-averaged per-condition PE.
    These are per-condition parameter estimates (vs implicit baseline),
    registered to standard space and averaged across runs.
    """
    return (BASE_DIR / sid / f'ses-{session}' / 'derivatives' /
            'fsl' / 'loc' / 'registered_pes' / f'{condition}_mean.nii.gz')


# %% Cell 4: Check Data Availability

def check_data(subjects_dict, n_show=5):
    """Verify registered PEs and HighLevel files exist."""
    print("DATA AVAILABILITY CHECK")
    print("=" * 60)

    pe_ok, pe_missing = 0, 0
    hl_ok, hl_missing = 0, 0
    shown = 0

    for sid, info in subjects_dict.items():
        first_ses = info['sessions'][0]
        pe_status = {}
        hl_status = {}

        for ses in info['sessions']:
            # Check registered PEs
            pe_files = {c: get_pe_path(sid, ses, c).exists() for c in RSA_CONDITIONS}
            pe_status[ses] = pe_files

            # Check HighLevel localizer
            hl_files = {c: get_highlevel_stat(sid, ses, cope, first_ses).exists()
                        for c, cope in LOCALIZER_COPES.items()}
            hl_status[ses] = hl_files

        all_pe = all(all(v.values()) for v in pe_status.values())
        all_hl = all(all(v.values()) for v in hl_status.values())

        if all_pe:
            pe_ok += 1
        else:
            pe_missing += 1

        if all_hl:
            hl_ok += 1
        else:
            hl_missing += 1

        if shown < n_show or not all_pe:
            print(f"\n  {info['code']} ({len(info['sessions'])} sessions):")
            for ses in info['sessions']:
                pe_check = '✓' if all(pe_status[ses].values()) else '✗ ' + str([k for k,v in pe_status[ses].items() if not v])
                hl_check = '✓' if all(hl_status[ses].values()) else '✗'
                print(f"    ses-{ses}: PEs={pe_check}  HighLevel={hl_check}")
            shown += 1

    print(f"\n  Summary:")
    print(f"    Registered PEs: {pe_ok} OK, {pe_missing} incomplete")
    print(f"    HighLevel:      {hl_ok} OK, {hl_missing} incomplete")

    if pe_missing > 0:
        print(f"\n  ⚠️  Run register_pes.sh first to create registered PE files!")
        return False
    return True

data_ready = check_data(ALL_SUBJECTS)


# %% Cell 5: ROI Definition (Localizer — from HighLevel)

def define_rois(sid, info, hemispheres, percentile=90, min_voxels=10):
    """Define ROIs using Category > Scramble from HighLevel (top-percentile)."""
    sessions = info['sessions']
    first_ses = sessions[0]
    roi_dir = BASE_DIR / sid / f'ses-{first_ses}' / 'ROIs'
    results = {}

    for hemi in hemispheres:
        for cat, cope_num in LOCALIZER_COPES.items():
            key = f"{hemi}_{cat}"
            mask_file = roi_dir / f'{hemi}_{cat}_searchmask.nii.gz'
            if not mask_file.exists():
                continue

            mask_img = nib.load(mask_file)
            search_mask = mask_img.get_fdata() > 0
            affine = mask_img.affine
            results[key] = {}

            for ses in sessions:
                zstat_path = get_highlevel_stat(sid, ses, cope_num, first_ses, stat='zstat1')
                if not zstat_path.exists():
                    continue

                zstat = nib.load(zstat_path).get_fdata()
                pos_vals = zstat[search_mask & (zstat > 0)]
                if len(pos_vals) < min_voxels:
                    continue

                thresh = max(np.percentile(pos_vals, percentile), 1.64)
                suprathresh = (zstat > thresh) & search_mask
                labeled, n_clusters = label(suprathresh)
                if n_clusters == 0:
                    continue

                sizes = [(labeled == i).sum() for i in range(1, n_clusters + 1)]
                best_idx = np.argmax(sizes) + 1
                if sizes[best_idx - 1] < 5:
                    continue

                roi_mask = (labeled == best_idx)
                centroid = nib.affines.apply_affine(affine, center_of_mass(roi_mask))
                peak_idx = np.unravel_index(np.argmax(zstat * roi_mask), zstat.shape)

                results[key][ses] = {
                    'centroid': centroid,
                    'n_voxels': sizes[best_idx - 1],
                    'peak_z': zstat[peak_idx],
                    'threshold': thresh,
                }
    return results


print("\nDEFINING ROIs (Category > Scramble, top 10%)")
print("=" * 60)

all_rois = {}
for sid, info in ALL_SUBJECTS.items():
    hemis = [info['hemi']] if info['is_patient'] else ['l', 'r']
    rois = define_rois(sid, info, hemis, percentile=ROI_PERCENTILE)
    if rois:
        all_rois[sid] = rois
        n = sum(1 for v in rois.values() if v)
        print(f"  {info['code']}: {n} ROI×hemi, hemis={hemis}")
    else:
        print(f"  {info['code']}: ⚠️ no ROIs")

print(f"\n✓ ROIs for {len(all_rois)} subjects")


# %% Cell 6: RSA Pattern Extraction (Per-Condition PEs — Liu Approach)

def extract_rsa_patterns(sid, info, roi_results, radius=6):
    """Extract per-condition PEs in 6mm sphere at centroid, compute RDMs.

    Uses registered, run-averaged parameter estimates for each condition
    (face, house, object, word) against implicit baseline.
    This is the Liu et al. approach: per-condition patterns → correlation RDM.
    """
    sessions = info['sessions']
    first_ses = sessions[0]

    # Reference geometry
    roi_dir = BASE_DIR / sid / f'ses-{first_ses}' / 'ROIs'
    ref_file = None
    for cat in CATEGORIES:
        for h in ['l', 'r']:
            f = roi_dir / f"{h}_{cat}_searchmask.nii.gz"
            if f.exists():
                ref_file = f
                break
        if ref_file:
            break
    if not ref_file:
        return {}

    ref_img = nib.load(ref_file)
    affine = ref_img.affine
    brain_shape = ref_img.shape

    roi_rdms = {}

    for roi_key, sessions_data in roi_results.items():
        if not sessions_data:
            continue

        roi_rdms[roi_key] = {
            'rdms': {}, 'fisher_corr': {}, 'patterns': {},
            'valid_categories': None, 'centroids': {},
        }

        for ses in sessions:
            if ses not in sessions_data:
                continue

            centroid = sessions_data[ses]['centroid']
            sphere = create_sphere(centroid, affine, brain_shape, radius)
            roi_rdms[roi_key]['centroids'][ses] = centroid

            # Extract per-condition PE patterns
            patterns = []
            valid_cats = []

            for cat in CATEGORIES:
                pe_path = get_pe_path(sid, ses, cat)
                if not pe_path.exists():
                    continue

                data = nib.load(pe_path).get_fdata()
                betas = data[sphere]
                betas = betas[np.isfinite(betas)]

                if len(betas) > 0:
                    patterns.append(betas)
                    valid_cats.append(cat)

            if len(patterns) < 4:
                continue

            # Equal voxel count across conditions
            min_v = min(len(p) for p in patterns)
            patterns = [p[:min_v] for p in patterns]
            beta_matrix = np.column_stack(patterns)  # N_voxels × 4

            # RDM: 1 - Pearson correlation (Liu et al.)
            corr_mat = np.corrcoef(beta_matrix.T)
            rdm = 1 - corr_mat
            fisher_corr = np.arctanh(np.clip(corr_mat, -0.999, 0.999))

            roi_rdms[roi_key]['rdms'][ses] = rdm
            roi_rdms[roi_key]['fisher_corr'][ses] = fisher_corr
            roi_rdms[roi_key]['patterns'][ses] = beta_matrix
            roi_rdms[roi_key]['valid_categories'] = valid_cats

    return roi_rdms


print("\nEXTRACTING RSA PATTERNS (per-condition PEs, Liu approach)")
print("=" * 60)

all_rdms = {}
for sid, info in ALL_SUBJECTS.items():
    if sid not in all_rois:
        continue
    rdms = extract_rsa_patterns(sid, info, all_rois[sid], SPHERE_RADIUS)
    if rdms:
        all_rdms[sid] = rdms
        n_ses = sum(len(v['rdms']) for v in rdms.values())
        print(f"  {info['code']}: {len(rdms)} ROIs, {n_ses} session×ROI RDMs")

print(f"\n✓ RDMs for {len(all_rdms)} subjects")


# %% Cell 7: Univariate Extraction (Ayzenberg Approach)

def extract_univariate(sid, info, roi_results, radius=6):
    """Extract Category > All Others activation in 6mm sphere.

    Ayzenberg approach: mean univariate activation for preferred category,
    compared patient-by-patient against bootstrapped control CIs.
    """
    sessions = info['sessions']
    first_ses = sessions[0]

    results = {}

    for roi_key, sessions_data in roi_results.items():
        if not sessions_data:
            continue

        hemi = roi_key.split('_')[0]
        category = roi_key.split('_')[1]
        cope_num = UNIVARIATE_COPES.get(category)
        if cope_num is None:
            continue

        results[roi_key] = {}

        # Reference geometry
        roi_dir = BASE_DIR / sid / f'ses-{first_ses}' / 'ROIs'
        ref_file = roi_dir / f"{hemi}_{category}_searchmask.nii.gz"
        if not ref_file.exists():
            # Try any available mask for geometry
            for cat in CATEGORIES:
                for h in ['l', 'r']:
                    f = roi_dir / f"{h}_{cat}_searchmask.nii.gz"
                    if f.exists():
                        ref_file = f
                        break
                if ref_file.exists():
                    break

        ref_img = nib.load(ref_file)
        affine = ref_img.affine
        brain_shape = ref_img.shape

        for ses in sessions:
            if ses not in sessions_data:
                continue

            centroid = sessions_data[ses]['centroid']
            sphere = create_sphere(centroid, affine, brain_shape, radius)

            # Get Category > All Others cope from HighLevel
            cope_path = get_highlevel_stat(sid, ses, cope_num, first_ses, stat='cope1')
            if not cope_path.exists():
                continue

            data = nib.load(cope_path).get_fdata()
            vals = data[sphere]
            vals = vals[np.isfinite(vals)]

            if len(vals) > 0:
                results[roi_key][ses] = {
                    'mean_activation': np.mean(vals),
                    'peak_activation': np.max(vals),
                    'n_voxels': len(vals),
                }

    return results


print("\nEXTRACTING UNIVARIATE (Category > All Others, Ayzenberg approach)")
print("=" * 60)

all_univariate = {}
for sid, info in ALL_SUBJECTS.items():
    if sid not in all_rois:
        continue
    univ = extract_univariate(sid, info, all_rois[sid], SPHERE_RADIUS)
    if univ:
        all_univariate[sid] = univ
        n = sum(len(v) for v in univ.values())
        print(f"  {info['code']}: {n} session×ROI measurements")

print(f"\n✓ Univariate for {len(all_univariate)} subjects")


# %% Cell 8: Compute All Metrics

def mds_2d(rdm):
    """Classical MDS to 2D."""
    n = rdm.shape[0]
    H = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * H @ (rdm ** 2) @ H
    eigvals, eigvecs = np.linalg.eigh(B)
    idx = np.argsort(eigvals)[::-1]
    coords = eigvecs[:, idx[:2]] * np.sqrt(np.maximum(eigvals[idx[:2]], 0))
    return coords


def compute_all_metrics(all_rdms, all_univariate, subjects_dict):
    """Compute RSA metrics + univariate selectivity."""
    rows = []

    for sid, rois in all_rdms.items():
        info = subjects_dict[sid]

        for roi_key, roi_data in rois.items():
            sessions_with_rdm = sorted(roi_data['rdms'].keys())
            if len(sessions_with_rdm) < 2:
                continue

            valid_cats = roi_data['valid_categories']
            if valid_cats is None or len(valid_cats) < 4:
                continue

            first_ses = sessions_with_rdm[0]
            last_ses = sessions_with_rdm[-1]
            hemi = roi_key.split('_')[0]
            category = roi_key.split('_')[1]

            # --- Liu Distinctiveness ---
            pref_idx = valid_cats.index(category) if category in valid_cats else None
            liu_t1, liu_t2 = None, None

            if pref_idx is not None:
                nonpref = [i for i in range(len(valid_cats)) if i != pref_idx]
                if first_ses in roi_data['fisher_corr']:
                    liu_t1 = np.mean(roi_data['fisher_corr'][first_ses][pref_idx, nonpref])
                if last_ses in roi_data['fisher_corr']:
                    liu_t2 = np.mean(roi_data['fisher_corr'][last_ses][pref_idx, nonpref])

            liu_change = abs(liu_t2 - liu_t1) if (liu_t1 is not None and liu_t2 is not None) else None

            # --- Geometry Preservation ---
            rdm_t1 = roi_data['rdms'][first_ses]
            rdm_t2 = roi_data['rdms'][last_ses]
            triu = np.triu_indices(4, k=1)
            geom_r, _ = pearsonr(rdm_t1[triu], rdm_t2[triu])

            # --- MDS Shift ---
            mds_shifts = {}
            try:
                coords_t1 = mds_2d(rdm_t1)
                coords_t2 = mds_2d(rdm_t2)
                R, _ = orthogonal_procrustes(coords_t1, coords_t2)
                aligned_t1 = coords_t1 @ R
                for i, cat in enumerate(valid_cats):
                    mds_shifts[cat] = np.linalg.norm(aligned_t1[i] - coords_t2[i])
            except Exception:
                pass

            # --- Spatial Drift ---
            drift_mm = None
            if first_ses in roi_data['centroids'] and last_ses in roi_data['centroids']:
                drift_mm = np.linalg.norm(
                    roi_data['centroids'][last_ses] - roi_data['centroids'][first_ses]
                )

            # --- Univariate Selectivity (Ayzenberg) ---
            univ_t1, univ_t2 = None, None
            if sid in all_univariate and roi_key in all_univariate[sid]:
                udata = all_univariate[sid][roi_key]
                if first_ses in udata:
                    univ_t1 = udata[first_ses]['mean_activation']
                if last_ses in udata:
                    univ_t2 = udata[last_ses]['mean_activation']

            univ_change = abs(univ_t2 - univ_t1) if (univ_t1 is not None and univ_t2 is not None) else None

            row = {
                'subject': sid, 'code': info['code'], 'group': info['group'],
                'is_patient': info['is_patient'], 'hemisphere': hemi,
                'roi_category': category,
                'category_type': 'Bilateral' if category in BILATERAL_CATEGORIES else 'Unilateral',
                'n_sessions': len(sessions_with_rdm),
                'first_session': first_ses, 'last_session': last_ses,
                # RSA metrics
                'liu_t1': liu_t1, 'liu_t2': liu_t2, 'liu_change': liu_change,
                'geometry_preservation': geom_r,
                'spatial_drift_mm': drift_mm,
                # Univariate metrics
                'selectivity_t1': univ_t1, 'selectivity_t2': univ_t2,
                'selectivity_change': univ_change,
            }
            for cat in CATEGORIES:
                row[f'mds_shift_{cat}'] = mds_shifts.get(cat, None)
            rows.append(row)

    return pd.DataFrame(rows)


print("\nCOMPUTING METRICS")
print("=" * 60)

results_df = compute_all_metrics(all_rdms, all_univariate, ALL_SUBJECTS)
print(f"\n✓ {len(results_df)} ROI measurements")
print(f"  Patients: {results_df[results_df['is_patient']].shape[0]}")
print(f"  Controls: {results_df[~results_df['is_patient']].shape[0]}")


# %% Cell 9: Build Analysis Tables

def build_analysis_table(results_df):
    """Patients: single hemisphere. Controls: average L/R."""
    patients = results_df[results_df['is_patient']].copy()
    controls = results_df[~results_df['is_patient']].copy()

    metric_cols = [c for c in results_df.columns if c.startswith(('liu_', 'geometry_',
                   'spatial_', 'selectivity_', 'mds_shift_'))]

    ctrl_avg = controls.groupby(
        ['subject', 'code', 'group', 'roi_category', 'category_type']
    ).agg({col: 'mean' for col in metric_cols}).reset_index()
    ctrl_avg['is_patient'] = False
    ctrl_avg['hemisphere'] = 'avg'

    keep = ['subject', 'code', 'group', 'is_patient', 'hemisphere',
            'roi_category', 'category_type'] + metric_cols
    combined = pd.concat([
        patients[[c for c in keep if c in patients.columns]],
        ctrl_avg[[c for c in keep if c in ctrl_avg.columns]]
    ], ignore_index=True)

    return combined, controls

analysis_df, controls_raw = build_analysis_table(results_df)

print("\nANALYSIS TABLE")
print("=" * 60)
for g in ['OTC', 'nonOTC', 'control']:
    print(f"  {g}: {len(analysis_df[analysis_df['group']==g])} rows")


# %% Cell 10: Group Analysis + Patient-Level Statistics

def run_analysis(analysis_df):
    """Group comparisons + Ayzenberg patient-by-patient tests."""

    print("\n" + "=" * 70)
    print("RSA METRICS (Liu approach: per-condition PEs)")
    print("=" * 70)

    rsa_metrics = [
        ('liu_change', 'Liu Distinctiveness Change |T2-T1|'),
        ('geometry_preservation', 'Geometry Preservation (RDM corr)'),
        ('spatial_drift_mm', 'Spatial Drift (mm)'),
    ]

    for metric, label in rsa_metrics:
        print(f"\n  {label}:")
        print(f"  {'Group':<12} {'Bilateral':<12} {'Unilateral':<12} {'Diff':<10} {'n':<6}")
        print("  " + "-" * 52)

        for grp in ['OTC', 'nonOTC', 'control']:
            g = analysis_df[analysis_df['group'] == grp]
            bil = g[g['category_type'] == 'Bilateral'][metric].dropna()
            uni = g[g['category_type'] == 'Unilateral'][metric].dropna()
            diff = bil.mean() - uni.mean() if len(bil) > 0 and len(uni) > 0 else float('nan')
            print(f"  {grp:<12} {bil.mean():<12.3f} {uni.mean():<12.3f} {diff:<10.3f} {len(bil)+len(uni):<6}")

    # MDS Shift
    mds_rows = []
    for _, row in analysis_df.iterrows():
        for cat in CATEGORIES:
            val = row.get(f'mds_shift_{cat}')
            if val is not None and not np.isnan(val):
                mds_rows.append({
                    'subject': row['subject'], 'group': row['group'],
                    'roi_category': row['roi_category'],
                    'measured_category': cat,
                    'measured_type': 'Bilateral' if cat in BILATERAL_CATEGORIES else 'Unilateral',
                    'mds_shift': val,
                })
    mds_df = pd.DataFrame(mds_rows)

    if len(mds_df) > 0:
        print(f"\n  MDS Shift (Procrustes-aligned):")
        print(f"  {'Group':<12} {'Bilateral':<12} {'Unilateral':<12} {'Diff':<10}")
        print("  " + "-" * 46)
        for grp in ['OTC', 'nonOTC', 'control']:
            g = mds_df[mds_df['group'] == grp]
            bil = g[g['measured_type'] == 'Bilateral']['mds_shift']
            uni = g[g['measured_type'] == 'Unilateral']['mds_shift']
            print(f"  {grp:<12} {bil.mean():<12.3f} {uni.mean():<12.3f} {bil.mean()-uni.mean():<10.3f}")

    # --- Univariate (Ayzenberg) ---
    print("\n" + "=" * 70)
    print("UNIVARIATE SELECTIVITY (Ayzenberg approach: Category > All Others)")
    print("=" * 70)

    print(f"\n  Selectivity Change |T2-T1|:")
    print(f"  {'Group':<12} {'Bilateral':<12} {'Unilateral':<12} {'Diff':<10}")
    print("  " + "-" * 46)
    for grp in ['OTC', 'nonOTC', 'control']:
        g = analysis_df[analysis_df['group'] == grp]
        bil = g[g['category_type'] == 'Bilateral']['selectivity_change'].dropna()
        uni = g[g['category_type'] == 'Unilateral']['selectivity_change'].dropna()
        diff = bil.mean() - uni.mean() if len(bil) > 0 and len(uni) > 0 else float('nan')
        print(f"  {grp:<12} {bil.mean():<12.3f} {uni.mean():<12.3f} {diff:<10.3f}")

    # --- Statistical Tests ---
    print("\n" + "=" * 70)
    print("STATISTICAL TESTS")
    print("=" * 70)

    test_metrics = rsa_metrics + [('selectivity_change', 'Univariate Selectivity Change')]
    for metric, label in test_metrics:
        print(f"\n  {label}:")
        otc = analysis_df[analysis_df['group'] == 'OTC']
        ctrl = analysis_df[analysis_df['group'] == 'control']

        bil_otc = otc[otc['category_type'] == 'Bilateral'][metric].dropna()
        uni_otc = otc[otc['category_type'] == 'Unilateral'][metric].dropna()
        bil_ctrl = ctrl[ctrl['category_type'] == 'Bilateral'][metric].dropna()

        if len(bil_otc) >= 2 and len(uni_otc) >= 2:
            u, p = mannwhitneyu(bil_otc, uni_otc, alternative='two-sided')
            print(f"    OTC Bil vs Uni: MW U={u:.0f}, p={p:.3f}")
        if len(bil_otc) >= 2 and len(bil_ctrl) >= 2:
            u, p = mannwhitneyu(bil_otc, bil_ctrl, alternative='two-sided')
            print(f"    OTC vs Ctrl (Bil): MW U={u:.0f}, p={p:.3f}")

    # --- Patient-by-Patient (Ayzenberg bootstrapped CI) ---
    print("\n" + "=" * 70)
    print("PATIENT-BY-PATIENT vs CONTROL DISTRIBUTION")
    print("=" * 70)

    for metric in ['liu_change', 'geometry_preservation', 'selectivity_change']:
        print(f"\n  {metric} (Bil - Uni difference):")

        # Control distribution
        ctrl = analysis_df[analysis_df['group'] == 'control']
        ctrl_diffs = []
        for subj in ctrl['subject'].unique():
            s = ctrl[ctrl['subject'] == subj]
            b = s[s['category_type'] == 'Bilateral'][metric].mean()
            u = s[s['category_type'] == 'Unilateral'][metric].mean()
            if not np.isnan(b) and not np.isnan(u):
                ctrl_diffs.append(b - u)

        ctrl_diffs = np.array(ctrl_diffs)
        if len(ctrl_diffs) < 3:
            print("    Too few controls")
            continue

        # Bootstrapped 95% CI
        np.random.seed(42)
        boots = [np.mean(np.random.choice(ctrl_diffs, len(ctrl_diffs), replace=True))
                 for _ in range(10000)]
        ci_lo, ci_hi = np.percentile(boots, [2.5, 97.5])
        print(f"    Control: mean={ctrl_diffs.mean():.3f}, 95% CI=[{ci_lo:.3f}, {ci_hi:.3f}]")

        # Each OTC patient
        for sid in sorted(ALL_PATIENTS.keys()):
            info = ALL_SUBJECTS[sid]
            if info['group'] != 'OTC':
                continue
            pt = analysis_df[analysis_df['subject'] == sid]
            b = pt[pt['category_type'] == 'Bilateral'][metric].mean()
            u = pt[pt['category_type'] == 'Unilateral'][metric].mean()
            if np.isnan(b) or np.isnan(u):
                print(f"    {info['code']}: insufficient data")
                continue
            diff = b - u
            flag = " ** OUTSIDE CI **" if diff > ci_hi or diff < ci_lo else ""
            print(f"    {info['code']}: {diff:+.3f}{flag}")

    return mds_df

mds_long = run_analysis(analysis_df)


# %% Cell 11: Sensitivity — Controls by Hemisphere

def sensitivity_hemisphere(controls_raw):
    print("\n" + "=" * 70)
    print("SENSITIVITY: CONTROLS BY HEMISPHERE")
    print("=" * 70)

    for metric in ['liu_change', 'geometry_preservation', 'selectivity_change']:
        print(f"\n  {metric}:")
        print(f"  {'Hemi':<8} {'Bilateral':<12} {'Unilateral':<12} {'Diff':<10}")
        print("  " + "-" * 42)
        for hemi in ['l', 'r']:
            h = controls_raw[controls_raw['hemisphere'] == hemi]
            bil = h[h['category_type'] == 'Bilateral'][metric].dropna()
            uni = h[h['category_type'] == 'Unilateral'][metric].dropna()
            diff = bil.mean() - uni.mean() if len(bil) > 0 and len(uni) > 0 else float('nan')
            print(f"  {'Left' if hemi=='l' else 'Right':<8} {bil.mean():<12.3f} {uni.mean():<12.3f} {diff:<10.3f}")

sensitivity_hemisphere(controls_raw)


# %% Cell 12: Verification

print("\n" + "=" * 70)
print("VERIFICATION")
print("=" * 70)

print(f"\nSubjects: {analysis_df['subject'].nunique()}")
for grp in ['OTC', 'nonOTC', 'control']:
    g = analysis_df[analysis_df['group'] == grp]
    print(f"\n  {grp}: {g['subject'].nunique()} subjects, {len(g)} ROIs")
    for ct in ['Bilateral', 'Unilateral']:
        c = g[g['category_type'] == ct]
        print(f"    {ct}: {len(c)} ({c['subject'].nunique()} subjects)")

print(f"\nPer-subject:")
for _, row in analysis_df.groupby(['code', 'group']).size().reset_index(name='n').iterrows():
    flag = " ⚠️" if row['n'] < 4 else ""
    print(f"  {row['code']} ({row['group']}): {row['n']} ROIs{flag}")


# %% Cell 13: Save

import pickle

save_data = {
    'all_rois': all_rois,
    'all_rdms': all_rdms,
    'all_univariate': all_univariate,
    'results_df': results_df,
    'analysis_df': analysis_df,
    'controls_raw': controls_raw,
    'config': {
        'localizer_copes': LOCALIZER_COPES,
        'rsa_input': 'per-condition PEs (registered_pes/), Liu approach',
        'univariate_copes': UNIVARIATE_COPES,
        'percentile': ROI_PERCENTILE,
        'sphere_radius': SPHERE_RADIUS,
        'excluded_subjects': SUBJECTS_TO_EXCLUDE,
    }
}

with open(OUTPUT_DIR / "unified_rsa_results.pkl", 'wb') as f:
    pickle.dump(save_data, f)

analysis_df.to_csv(OUTPUT_DIR / "analysis_table.csv", index=False)
results_df.to_csv(OUTPUT_DIR / "full_results.csv", index=False)

print(f"\n✓ Saved to {OUTPUT_DIR}")
print("\n" + "=" * 70)
print("PIPELINE COMPLETE")
print("=" * 70)