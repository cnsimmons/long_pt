fsf="/user_data/csimmon2/long_pt/sub-008/ses-01/derivatives/fsl/loc/HighLevel.fsf"

# Add missing entries
cat >> "$fsf" << 'EOF'
set fmri(evg4.1) 1
set fmri(evg5.1) 1
set fmri(evg6.1) 1
EOF

# Test
feat "$fsf"