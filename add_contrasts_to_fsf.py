#!/usr/bin/env python3
"""
Add Face-Word and Object-House contrasts to existing FSF files
"""

import re
from pathlib import Path

def add_contrasts_to_fsf(fsf_path):
    """Add two new contrasts to an FSF file"""
    
    with open(fsf_path, 'r') as f:
        content = f.read()
    
    # Find current number of contrasts
    ncon_match = re.search(r'set fmri\(ncon_orig\) (\d+)', content)
    if not ncon_match:
        print(f"  Could not find contrast count in {fsf_path}")
        return False
    
    current_ncon = int(ncon_match.group(1))
    new_ncon = current_ncon + 2
    
    print(f"  Current contrasts: {current_ncon}, adding 2, new total: {new_ncon}")
    
    # Update contrast counts
    content = re.sub(r'set fmri\(ncon_orig\) \d+', f'set fmri(ncon_orig) {new_ncon}', content)
    content = re.sub(r'set fmri\(ncon_real\) \d+', f'set fmri(ncon_real) {new_ncon}', content)
    
    # Add Face-Word contrast (contrast 13)
    face_word_contrast = f"""
# Contrast 13: Face-Word
set fmri(conpic_real.{current_ncon + 1}) 1
set fmri(conname_real.{current_ncon + 1}) "Face-Word"
set fmri(conname_orig.{current_ncon + 1}) "Face-Word"
set fmri(con_real{current_ncon + 1}.1) 1
set fmri(con_real{current_ncon + 1}.2) 0
set fmri(con_real{current_ncon + 1}.3) 0
set fmri(con_real{current_ncon + 1}.4) -1
set fmri(con_real{current_ncon + 1}.5) 0
"""
    
    # Add Object-House contrast (contrast 14)
    object_house_contrast = f"""
# Contrast 14: Object-House
set fmri(conpic_real.{current_ncon + 2}) 1
set fmri(conname_real.{current_ncon + 2}) "Object-House"
set fmri(conname_orig.{current_ncon + 2}) "Object-House"
set fmri(con_real{current_ncon + 2}.1) 0
set fmri(con_real{current_ncon + 2}.2) -1
set fmri(con_real{current_ncon + 2}.3) 1
set fmri(con_real{current_ncon + 2}.4) 0
set fmri(con_real{current_ncon + 2}.5) 0
"""
    
    # Append new contrasts at the end
    content += face_word_contrast
    content += object_house_contrast
    
    # Write back
    with open(fsf_path, 'w') as f:
        f.write(content)
    
    print(f"  ✓ Added Face-Word and Object-House contrasts")
    return True

def main():
    base_dir = Path('/user_data/csimmon2/long_pt')
    
    # Subject and session configuration
    subjects_sessions = {
        'sub-004': ['01', '02', '03', '05', '06'],
        'sub-007': ['01', '03', '04'],
        'sub-021': ['01', '02', '03']
    }
    
    modified_count = 0
    
    for subject, sessions in subjects_sessions.items():
        print(f"\nProcessing {subject}...")
        
        for session in sessions:
            # Determine runs
            if subject == 'sub-007' and session in ['03', '04']:
                runs = ['01', '02']
            else:
                runs = ['01', '02', '03']
            
            for run in runs:
                fsf_path = base_dir / subject / f'ses-{session}' / 'derivatives' / 'fsl' / 'loc' / f'run-{run}' / '1stLevel.fsf'
                
                if fsf_path.exists():
                    print(f"  {subject} ses-{session} run-{run}")
                    if add_contrasts_to_fsf(fsf_path):
                        modified_count += 1
                else:
                    print(f"  ⚠ FSF not found: {fsf_path}")
    
    print(f"\n✅ Modified {modified_count} FSF files")
    print("\nNext steps:")
    print("1. Review one FSF file to verify contrasts were added correctly")
    print("2. Rerun FEAT for all subjects/sessions/runs")
    print("3. Re-extract data using zstat13 (Face-Word) and zstat14 (Object-House)")

if __name__ == "__main__":
    main()