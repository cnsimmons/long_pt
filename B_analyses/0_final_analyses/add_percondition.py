#!/usr/bin/env python3
"""
Add per-condition contrasts (15-19) to first-level FEATs, run contrast_mgr,
create HighLevel fixed-effects, and register to first-session space.

New contrasts (applied to 118-column design matrix):
  cope15: Face     [1 0 0 0 0 0 0 0 0 0 ... 0]  (column 1 = pe1)
  cope16: House    [0 0 1 0 0 0 0 0 0 0 ... 0]  (column 3 = pe3)
  cope17: Object   [0 0 0 0 1 0 0 0 0 0 ... 0]  (column 5 = pe5)
  cope18: Word     [0 0 0 0 0 0 1 0 0 0 ... 0]  (column 7 = pe7)
  cope19: Scramble [0 0 0 0 0 0 0 0 1 0 ... 0]  (column 9 = pe9)

Usage:
  python add_percondition_contrasts.py              # all subjects
  python add_percondition_contrasts.py sub-004      # single subject
"""
import os
import sys
import shutil
import subprocess
import pandas as pd
import numpy as np
from glob import glob

data_dir = '/user_data/csimmon2/long_pt'
CSV_FILE = '/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv'
SUBJECTS_TO_EXCLUDE = ['sub-108']
SESSION_START = {'sub-010': 2, 'sub-018': 2, 'sub-068': 2}

# New per-condition contrasts to add
# (name, PE column index in 118-column design matrix)
NEW_CONTRASTS = [
    ('Face_alone', 0),      # pe1 = column 0 (0-indexed)
    ('House_alone', 2),     # pe3 = column 2
    ('Object_alone', 4),    # pe5 = column 4
    ('Word_alone', 6),      # pe7 = column 6
    ('Scramble_alone', 8),  # pe9 = column 8
]

single_sub = sys.argv[1] if len(sys.argv) > 1 else None
df = pd.read_csv(CSV_FILE)


def run_cmd(cmd, check=True):
    """Run shell command."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"    ERROR: {result.stderr[:200]}")
        return False
    return True


def get_sessions(sub, row):
    """Get available sessions."""
    age_cols = ['age_1', 'age_2', 'age_3', 'age_4', 'age_5']
    n_ses = sum(1 for c in age_cols if pd.notna(row[c]) and row[c] != '')
    start = SESSION_START.get(sub, 1)
    sessions = []
    for i in range(n_ses):
        ses_str = f"{start + i:02d}"
        if os.path.isdir(f'{data_dir}/{sub}/ses-{ses_str}'):
            sessions.append(ses_str)
    return sessions


def get_runs(sub, ses):
    """Find completed FEAT runs."""
    loc_dir = f'{data_dir}/{sub}/ses-{ses}/derivatives/fsl/loc'
    runs = []
    for feat in glob(f'{loc_dir}/run-*/1stLevel.feat'):
        run = feat.split('run-')[1].split('/')[0]
        runs.append(run)
    return sorted(runs)


def read_design_con(con_file):
    """Read existing design.con and return header info + matrix rows."""
    with open(con_file, 'r') as f:
        lines = f.readlines()

    # Parse header
    header_lines = []
    matrix_lines = []
    in_matrix = False
    num_waves = None
    num_contrasts = None

    for line in lines:
        stripped = line.strip()
        if stripped == '/Matrix':
            in_matrix = True
            continue
        if in_matrix and stripped:
            matrix_lines.append(stripped)
        else:
            header_lines.append(line)
            if stripped.startswith('/NumWaves'):
                num_waves = int(stripped.split()[-1])
            elif stripped.startswith('/NumContrasts'):
                num_contrasts = int(stripped.split()[-1])

    return header_lines, matrix_lines, num_waves, num_contrasts


def write_new_design_con(con_file, header_lines, matrix_lines, num_waves,
                          old_num_contrasts, new_contrasts):
    """Write design.con with new contrasts appended."""
    new_num = old_num_contrasts + len(new_contrasts)

    with open(con_file, 'w') as f:
        for line in header_lines:
            stripped = line.strip()
            if stripped.startswith('/NumContrasts'):
                f.write(f'/NumContrasts   {new_num}\n')
            elif stripped.startswith('/ContrastName') or stripped.startswith('/PPheights') or stripped.startswith('/RequiredEffect'):
                f.write(line)
                # After the last ContrastName, add new ones
                if stripped.startswith(f'/ContrastName{old_num_contrasts}'):
                    for i, (name, _) in enumerate(new_contrasts):
                        f.write(f'\n/ContrastName{old_num_contrasts + i + 1}  {name} \n')
            else:
                f.write(line)

        # PPheights and RequiredEffect for new contrasts
        # (FSL doesn't strictly need these, but add placeholders)

        f.write('\n/Matrix\n')

        # Existing contrast rows
        for row in matrix_lines:
            f.write(row + '\n')

        # New per-condition contrast rows
        for name, col_idx in new_contrasts:
            row = ['0.000000e+00'] * num_waves
            row[col_idx] = '1.000000e+00'
            f.write(' '.join(row) + ' \n')


def add_contrasts_to_feat(feat_dir):
    """Add per-condition contrasts to a 1stLevel.feat directory."""
    con_file = f'{feat_dir}/design.con'
    backup = f'{feat_dir}/design.con.orig'

    if not os.path.exists(con_file):
        return False

    # Check if already added
    header, matrix, num_waves, num_contrasts = read_design_con(con_file)
    if num_contrasts >= 19:
        return True  # Already done

    # Backup original
    if not os.path.exists(backup):
        shutil.copy2(con_file, backup)

    # Write new design.con
    write_new_design_con(con_file, header, matrix, num_waves,
                          num_contrasts, NEW_CONTRASTS)

    return True


def run_contrast_mgr(feat_dir):
    """Run FSL contrast_mgr to generate new cope files."""
    stats_dir = f'{feat_dir}/stats'
    con_file = f'{feat_dir}/design.con'

    # Check if cope19 already exists (last new contrast)
    if os.path.exists(f'{stats_dir}/cope19.nii.gz'):
        return True

    cmd = f'contrast_mgr {stats_dir} {con_file}'
    return run_cmd(cmd)


def create_highlevel_cope(sub, ses, cope_num, runs, first_ses):
    """Create HighLevel fixed-effects for a single cope using flameo.

    Merges run-level copes/varcopes into 4D, runs flameo with fixed effects.
    """
    hl_dir = f'{data_dir}/{sub}/ses-{ses}/derivatives/fsl/loc/HighLevel.gfeat'
    cope_dir = f'{hl_dir}/cope{cope_num}.feat'
    stats_dir = f'{cope_dir}/stats'

    # Skip if already exists
    if os.path.exists(f'{stats_dir}/cope1.nii.gz') and os.path.exists(f'{stats_dir}/zstat1.nii.gz'):
        return True

    os.makedirs(stats_dir, exist_ok=True)

    # Collect run-level cope and varcope files
    cope_files = []
    varcope_files = []
    for run in runs:
        feat = f'{data_dir}/{sub}/ses-{ses}/derivatives/fsl/loc/run-{run}/1stLevel.feat'
        cope_f = f'{feat}/stats/cope{cope_num}.nii.gz'
        var_f = f'{feat}/stats/varcope{cope_num}.nii.gz'

        if os.path.exists(cope_f) and os.path.exists(var_f):
            cope_files.append(cope_f)
            varcope_files.append(var_f)

    if len(cope_files) == 0:
        print(f"    cope{cope_num}: no run-level files found")
        return False

    # Get mask from existing HighLevel
    mask = f'{hl_dir}/mask.nii.gz'
    if not os.path.exists(mask):
        # Try to find it from an existing cope directory
        for c in range(1, 15):
            alt_mask = f'{hl_dir}/cope{c}.feat/mask.nii.gz'
            if os.path.exists(alt_mask):
                mask = alt_mask
                break

    # Merge into 4D
    tmp_cope4d = f'{stats_dir}/tmp_cope4d.nii.gz'
    tmp_var4d = f'{stats_dir}/tmp_var4d.nii.gz'

    run_cmd(f'fslmerge -t {tmp_cope4d} {" ".join(cope_files)}')
    run_cmd(f'fslmerge -t {tmp_var4d} {" ".join(varcope_files)}')

    # Create simple design for flameo (column of 1s, one group)
    n_runs = len(cope_files)
    design_mat = f'{stats_dir}/tmp_design.mat'
    design_con = f'{stats_dir}/tmp_design.con'
    design_grp = f'{stats_dir}/tmp_design.grp'

    with open(design_mat, 'w') as f:
        f.write(f'/NumWaves 1\n/NumPoints {n_runs}\n/PPheights 1\n/Matrix\n')
        for _ in range(n_runs):
            f.write('1\n')

    with open(design_con, 'w') as f:
        f.write('/ContrastName1 group_mean\n/NumWaves 1\n/NumContrasts 1\n')
        f.write('/PPheights 1\n/RequiredEffect 1\n/Matrix\n1\n')

    with open(design_grp, 'w') as f:
        f.write(f'/NumWaves 1\n/NumPoints {n_runs}\n/Matrix\n')
        for _ in range(n_runs):
            f.write('1\n')

    # Run flameo (fixed effects)
    mask_arg = f'--mask={mask}' if os.path.exists(mask) else ''
    cmd = (f'flameo --cope={tmp_cope4d} --vc={tmp_var4d} '
           f'{mask_arg} --ld={stats_dir} '
           f'--dm={design_mat} --tc={design_con} --cs={design_grp} '
           f'--runmode=fe')

    success = run_cmd(cmd)

    # flameo outputs pe1, cope1, varcope1, tstat1, zstat1 etc.
    # Clean up temp files
    for tmp in [tmp_cope4d, tmp_var4d, design_mat, design_con, design_grp]:
        if os.path.exists(tmp):
            os.remove(tmp)

    return success


def register_highlevel_cope(sub, ses, cope_num, first_ses):
    """Register HighLevel cope to first-session space (matches existing pipeline)."""
    hl_dir = f'{data_dir}/{sub}/ses-{ses}/derivatives/fsl/loc/HighLevel.gfeat'
    cope_dir = f'{hl_dir}/cope{cope_num}.feat/stats'

    first_ses_str = f'{first_ses}'
    ref_anat = f'{data_dir}/{sub}/ses-{first_ses_str}/anat/{sub}_ses-{first_ses_str}_T1w_brain.nii.gz'

    if not os.path.exists(ref_anat):
        return False

    if ses == first_ses_str:
        # First session: symlink
        for stat in ['zstat1', 'cope1']:
            src = f'{cope_dir}/{stat}.nii.gz'
            dst = f'{cope_dir}/{stat}_ses{first_ses_str}.nii.gz'
            if os.path.exists(src) and not os.path.exists(dst):
                os.symlink(os.path.abspath(src), dst)
    else:
        # Later session: register using anat2ses transform
        anat_xfm = f'{data_dir}/{sub}/ses-{ses}/anat/anat2ses{first_ses_str}.mat'
        if not os.path.exists(anat_xfm):
            print(f"    WARNING: no anat2ses{first_ses_str}.mat for ses-{ses}")
            return False

        for stat in ['zstat1', 'cope1']:
            src = f'{cope_dir}/{stat}.nii.gz'
            dst = f'{cope_dir}/{stat}_ses{first_ses_str}.nii.gz'
            if os.path.exists(src) and not os.path.exists(dst):
                cmd = (f'flirt -in {src} -ref {ref_anat} -out {dst} '
                       f'-applyxfm -init {anat_xfm} -interp trilinear')
                run_cmd(cmd)

    return True


# ============================================================
# MAIN
# ============================================================
print("=" * 60)
print("ADDING PER-CONDITION CONTRASTS (15-19)")
print("=" * 60)

for _, row in df.iterrows():
    sub = row['sub']
    if sub in SUBJECTS_TO_EXCLUDE:
        continue
    if single_sub and sub != single_sub:
        continue

    first_ses_num = SESSION_START.get(sub, 1)
    first_ses = f"{first_ses_num:02d}"
    sessions = get_sessions(sub, row)

    if not sessions:
        continue

    print(f"\n--- {sub} ---")

    for ses in sessions:
        runs = get_runs(sub, ses)
        if not runs:
            continue

        print(f"  ses-{ses}: {len(runs)} runs")

        # Step 1: Add contrasts to each run's design.con
        all_ok = True
        for run in runs:
            feat = f'{data_dir}/{sub}/ses-{ses}/derivatives/fsl/loc/run-{run}/1stLevel.feat'
            if not add_contrasts_to_feat(feat):
                print(f"    run-{run}: ⚠️ could not modify design.con")
                all_ok = False

        if not all_ok:
            continue

        # Step 2: Run contrast_mgr for each run
        print(f"    Running contrast_mgr...")
        for run in runs:
            feat = f'{data_dir}/{sub}/ses-{ses}/derivatives/fsl/loc/run-{run}/1stLevel.feat'
            if not run_contrast_mgr(feat):
                print(f"    run-{run}: ⚠️ contrast_mgr failed")

        # Step 3: Create HighLevel fixed effects for new copes
        print(f"    Creating HighLevel fixed effects...")
        for cope_num in range(15, 20):
            if create_highlevel_cope(sub, ses, cope_num, runs, first_ses):
                cond = NEW_CONTRASTS[cope_num - 15][0]
                print(f"    cope{cope_num} ({cond}): ✓")
            else:
                print(f"    cope{cope_num}: ⚠️ failed")

        # Step 4: Register to first-session space
        print(f"    Registering to ses-{first_ses} space...")
        for cope_num in range(15, 20):
            register_highlevel_cope(sub, ses, cope_num, first_ses)

        print(f"    ✓ ses-{ses} complete")

print("\n" + "=" * 60)
print("COMPLETE")
print("=" * 60)
print("\nNew HighLevel copes available:")
print("  cope15 = Face (per-condition)")
print("  cope16 = House (per-condition)")
print("  cope17 = Object (per-condition)")
print("  cope18 = Word (per-condition)")
print("  cope19 = Scramble (per-condition)")
print("\nFor RSA pipeline, use RSA_COPES = {'face': 15, 'house': 16, 'object': 17, 'word': 18}")