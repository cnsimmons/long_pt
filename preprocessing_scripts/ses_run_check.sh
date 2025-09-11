#!/bin/bash
# Check what sessions exist in raw data for longitudinal patients

RAW_DIR='/lab_data/behrmannlab/hemi/Raw'

echo "Checking raw data structure for longitudinal patients..."
echo "======================================================"

# Correct patient mappings from Figure 1
echo "Patient mappings: TC=sub-004, UD=sub-007, OT=sub-021"
echo ""

for subject in "004" "007" "021"; do
    if [ "$subject" == "004" ]; then
        patient="TC"
    elif [ "$subject" == "007" ]; then
        patient="UD"  
    else
        patient="OT"
    fi
    
    echo "${patient} (sub-${subject}):"
    subject_dir="${RAW_DIR}/sub-${subject}"
    
    if [ -d "$subject_dir" ]; then
        # List all sessions
        sessions=($(ls -d ${subject_dir}/ses-* 2>/dev/null | sort))
        
        if [ ${#sessions[@]} -eq 0 ]; then
            echo "  No sessions found"
        else
            echo "  Sessions found: ${#sessions[@]}"
            
            for session_dir in "${sessions[@]}"; do
                ses=$(basename "$session_dir")
                echo "    $ses:"
                
                # Check anatomical
                anat_dir="$session_dir/anat"
                if [ -d "$anat_dir" ]; then
                    t1w_count=$(ls ${anat_dir}/*T1w*.nii.gz 2>/dev/null | wc -l)
                    echo "      T1w files: $t1w_count"
                else
                    echo "      No anat directory"
                fi
                
                # Check functional
                func_dir="$session_dir/func"
                if [ -d "$func_dir" ]; then
                    bold_count=$(ls ${func_dir}/*task-loc*bold.nii.gz 2>/dev/null | wc -l)
                    events_count=$(ls ${func_dir}/*task-loc*events.tsv 2>/dev/null | wc -l)
                    echo "      BOLD files: $bold_count"
                    echo "      Events files: $events_count"
                    
                    # List specific runs
                    if [ $bold_count -gt 0 ]; then
                        echo "      Runs available:"
                        for bold_file in ${func_dir}/*task-loc*bold.nii.gz; do
                            if [ -f "$bold_file" ]; then
                                run=$(basename "$bold_file" | grep -o 'run-[0-9]*' || echo "run-unknown")
                                echo "        $run"
                            fi
                        done
                    fi
                else
                    echo "      No func directory"
                fi
                echo ""
            done
        fi
    else
        echo "  Subject directory not found: $subject_dir"
    fi
    echo ""
done

echo "Summary for Figure 5 longitudinal analysis:"
echo "- TC (sub-004): Need multiple sessions"
echo "- UD (sub-007): Need multiple sessions" 
echo "- OT (sub-021): Need multiple sessions"