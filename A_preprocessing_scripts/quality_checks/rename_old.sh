#!/bin/bash
# verify_backup.sh - Check that FEAT outputs were backed up correctly

PROCESSED_DIR='/user_data/csimmon2/long_pt'

echo "Verifying FEAT backup..."
echo "========================"

# Count old directories
n_first_old=$(find "$PROCESSED_DIR" -type d -name "1stLevel_old.feat" | wc -l)
n_high_old=$(find "$PROCESSED_DIR" -type d -name "HighLevel_old.gfeat" | wc -l)

# Count remaining original directories (should be 0)
n_first_remain=$(find "$PROCESSED_DIR" -type d -name "1stLevel.feat" | wc -l)
n_high_remain=$(find "$PROCESSED_DIR" -type d -name "HighLevel.gfeat" | wc -l)

echo ""
echo "BACKUP STATUS:"
echo "  1stLevel_old.feat found: ${n_first_old}"
echo "  HighLevel_old.gfeat found: ${n_high_old}"
echo ""
echo "REMAINING (should be 0):"
echo "  1stLevel.feat found: ${n_first_remain}"
echo "  HighLevel.gfeat found: ${n_high_remain}"

# Show specific examples
echo ""
echo "Sample backup locations (first 5):"
find "$PROCESSED_DIR" -type d -name "*_old.feat" -o -name "*_old.gfeat" | head -5

# Check if any originals remain
if [ $n_first_remain -gt 0 ] || [ $n_high_remain -gt 0 ]; then
    echo ""
    echo "⚠️  WARNING: Original directories still exist!"
    echo "Remaining originals:"
    find "$PROCESSED_DIR" -type d -name "1stLevel.feat" -o -name "HighLevel.gfeat"
else
    echo ""
    echo "✓ All FEAT outputs successfully backed up!"
fi

# Show directory structure for one subject
echo ""
echo "Sample structure (sub-004/ses-01/derivatives/fsl/loc):"
ls -la "$PROCESSED_DIR/sub-004/ses-01/derivatives/fsl/loc/" 2>/dev/null || echo "  Directory not found"