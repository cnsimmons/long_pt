# After jobs complete, move outputs (handling both .feat and +.feat)

for sub in sub-004 sub-021; do
  for ses_dir in /lab_data/behrmannlab/hemi/Raw/${sub}/ses-*/derivatives/fsl/loc/; do
    if [ -d "$ses_dir" ]; then
      ses=$(basename $(dirname $(dirname $(dirname $ses_dir))) | cut -d'-' -f2)
      target_dir="/user_data/csimmon2/long_pt/${sub}/ses-${ses}/derivatives/fsl/loc/"
      mkdir -p "$target_dir"
      
      # Move and rename +.feat to .feat
      for run_dir in ${ses_dir}run-*/1stLevel+.feat; do
        if [ -d "$run_dir" ]; then
          run=$(basename $(dirname $run_dir))
          mv "$run_dir" "${target_dir}${run}/1stLevel.feat"
        fi
      done
      echo "Moved ${sub} ses-${ses}"
    fi
  done
done

# Then delete entire derivatives folder from Raw
rm -rf /lab_data/behrmannlab/hemi/Raw/sub-*/ses-*/derivatives/
#rm -rf /user_data/csimmon2/long_pt/sub-*/ses-*/derivatives/fsl/loc/*/1stLevel+.feat