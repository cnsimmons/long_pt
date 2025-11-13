#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

BASE_DIR = Path('/user_data/csimmon2/long_pt')
CSV_FILE = Path('/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv')
SESSION_START = {'sub-010': 2, 'sub-018': 2, 'sub-068': 2}
SKIP_SUBS = ['sub-079' 'sub-108']

df = pd.read_csv(CSV_FILE)
incomplete = []

for _, row in df.iterrows():
    sub = row['sub']
    if sub in SKIP_SUBS:
        continue
    
    session_count = sum(1 for col in ['age_1', 'age_2', 'age_3', 'age_4', 'age_5'] 
                       if pd.notna(row[col]) and row[col] != '')
    start_ses = SESSION_START.get(sub, 1)
    
    for i in range(session_count):
        ses = f"{(start_ses + i):02d}"
        highlevel_dir = BASE_DIR / sub / f'ses-{ses}' / 'derivatives' / 'fsl' / 'loc' / 'HighLevel.gfeat'
        
        if not highlevel_dir.exists():
            incomplete.append(f"{sub} ses-{ses}: no HighLevel directory")
            continue
        
        # Check cope1 as indicator of completion
        cope1_zstat = highlevel_dir / 'cope1.feat' / 'stats' / 'zstat1.nii.gz'
        if not cope1_zstat.exists():
            incomplete.append(f"{sub} ses-{ses}: incomplete")

if incomplete:
    print(f"Incomplete HighLevel: {len(incomplete)}")
    for item in incomplete:
        print(f"  {item}")
else:
    print("All HighLevel analyses complete ✓")