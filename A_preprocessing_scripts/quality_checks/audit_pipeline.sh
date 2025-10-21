echo "=== Finding your actual working timing files ==="

# Check where sub-004 ses-01 timing files are (we know this worked)
echo "Sub-004 ses-01 timing files:"
find /lab_data/behrmannlab -type f -name "*catloc_004_run-01_Face.txt" 2>/dev/null

echo ""
echo "All timing file locations for sub-004:"
find /lab_data/behrmannlab -type d -name "covs" -path "*sub-004*" 2>/dev/null

echo ""
echo "=== Checking what a working FSF pointed to ==="
# Find a working FEAT output to see what FSF was used
find /lab_data/behrmannlab -name "design.fsf" -path "*sub-004*ses-01*" -path "*1stLevel.feat*" 2>/dev/null | head -1 | while read fsf; do
    echo "Found working FSF: $fsf"
    echo "Timing files it used:"
    grep "set fmri(custom" "$fsf" | head -5
done