cat > /user_data/csimmon2/long_pt/sub-007/ses-03/func/README_ses-03_source.txt << EOF
DATA SOURCE DOCUMENTATION
=========================
Subject: sub-007
Session: ses-03
Date converted: $(date)

SOURCE:
These events.tsv files were converted from BrainVoyager .prt files
provided by the original study authors.

Original files:
- Localizer_run1 - vol.prt
- Localizer_run2 - vol.prt

Conversion details:
- TR: 2.0s
- Volume offset: 1 (BrainVoyager indexing)
- Conversion script: convert_prt_local.py
- Converter: Claire Simmons

NOTES:
- Only runs 01 and 02 available for this session
- Run 03 is missing (no .prt file provided)
- These differ from other sessions which used direct .tsv exports
- Stored in processed directory due to Raw folder permissions

Generated files:
- sub-007_ses-03_task-loc_run-01_events.tsv
- sub-007_ses-03_task-loc_run-02_events.tsv
EOF