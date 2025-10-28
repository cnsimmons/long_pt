# Comprehensive completion check
echo "=========================================="
echo "COMPLETE ANALYSIS STATUS CHECK"
echo "=========================================="

for sub in 004 007 021; do
    echo ""
    echo "=== sub-${sub} ==="
    
    for ses_dir in /user_data/csimmon2/long_pt/sub-${sub}/ses-*/derivatives/fsl/loc; do
        if [ -d "$ses_dir" ]; then
            ses=$(basename $(dirname $(dirname $(dirname $ses_dir))))
            echo ""
            echo "  $ses:"
            
            # Check first-level runs
            first_level_complete=0
            first_level_total=0
            for run_dir in $ses_dir/run-*/1stLevel.feat; do
                if [ -d "$run_dir" ]; then
                    ((first_level_total++))
                    run=$(basename $(dirname $run_dir))
                    if [ -f "$run_dir/stats/cope1.nii.gz" ]; then
                        echo "    ✓ $run first-level"
                        ((first_level_complete++))
                    else
                        echo "    ✗ $run first-level FAILED"
                    fi
                fi
            done
            
            # Check HighLevel
            if [ -d "$ses_dir/HighLevel.gfeat" ]; then
                if [ -f "$ses_dir/HighLevel.gfeat/cope1.feat/stats/cope1.nii.gz" ]; then
                    echo "    ✓ HighLevel complete"
                else
                    echo "    ✗ HighLevel FAILED"
                fi
            else
                echo "    ○ HighLevel not created"
            fi
            
            echo "    Summary: $first_level_complete/$first_level_total first-level runs complete"
        fi
    done
done

echo ""
echo "=========================================="
echo "END STATUS CHECK"
echo "=========================================="