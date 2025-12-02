#!/usr/bin/env python3
"""
Verify missing Liu distinctiveness in compiled_results.csv
"""

import pandas as pd

csv_path = '/user_data/csimmon2/git_repos/long_pt/B_analyses/compiled_results.csv'
df = pd.read_csv(csv_path)

print("="*80)
print("CURRENT CSV STATUS")
print("="*80)
print(f"Total rows: {len(df)}")
print(f"Unique subjects: {df['Subject'].nunique()}")

print("\n" + "="*80)
print("LIU DISTINCTIVENESS MISSING DATA")
print("="*80)

for group in ['OTC', 'nonOTC', 'control']:
    group_df = df[df['Group'] == group]
    
    # Bilateral categories (House/Object)
    bilateral = group_df[group_df['Category'].isin(['House', 'Object'])]
    missing_bilateral = bilateral['Liu_Distinctiveness'].isna().sum()
    total_bilateral = len(bilateral)
    
    # Unilateral categories (Face/Word)
    unilateral = group_df[group_df['Category'].isin(['Face', 'Word'])]
    missing_unilateral = unilateral['Liu_Distinctiveness'].isna().sum()
    total_unilateral = len(unilateral)
    
    print(f"\n{group}:")
    print(f"  Bilateral (House/Object): {missing_bilateral}/{total_bilateral} missing ({100*missing_bilateral/total_bilateral if total_bilateral > 0 else 0:.1f}%)")
    print(f"  Unilateral (Face/Word):   {missing_unilateral}/{total_unilateral} missing ({100*missing_unilateral/total_unilateral if total_unilateral > 0 else 0:.1f}%)")

print("\n" + "="*80)
print("CONTROL MISSING DATA BREAKDOWN")
print("="*80)

controls = df[df['Group'] == 'control']
print(f"\nTotal control rows: {len(controls)}")
print(f"Control subjects: {controls['Subject'].nunique()}")

for cat in ['House', 'Object', 'Face', 'Word']:
    cat_data = controls[controls['Category'] == cat]
    has_liu = cat_data[~cat_data['Liu_Distinctiveness'].isna()]
    missing_liu = cat_data[cat_data['Liu_Distinctiveness'].isna()]
    
    print(f"\n{cat}:")
    print(f"  Total rows: {len(cat_data)}")
    print(f"  With Liu_Distinctiveness: {len(has_liu)} (RIGHT hemisphere)")
    print(f"  Missing Liu_Distinctiveness: {len(missing_liu)} (LEFT hemisphere for bilateral)")

print("\n" + "="*80)
print("INTERPRETATION")
print("="*80)
print("\nFor controls, the CSV structure is:")
print("  - Each subject has 2 rows per category")
print("  - Row with Liu_Distinctiveness = RIGHT hemisphere")
print("  - Row with NaN = LEFT hemisphere (for bilateral categories)")
print("\nMissing values by category:")
print("  - House/Object (bilateral): 18 missing = 9 subjects × 2 categories (LEFT hemisphere)")
print("  - Face/Word (unilateral): 8-9 missing = expected (LEFT hemisphere not computed)")

print("\n" + "="*80)
print("EXPECTED AFTER RE-RUN")
print("="*80)
print("\nRe-running RSA analysis will:")
print("  1. Keep all existing data")
print("  2. Fill 18 missing control LEFT hemisphere values for House/Object")
print("  3. Add ~8 new rows for sub-079 ses-02")
print(f"\nCurrent rows: {len(df)}")
print(f"After filling: ~{len(df)} (same, just filling NaN values)")
print(f"After sub-079: ~{len(df) + 8}")