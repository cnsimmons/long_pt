#!/bin/bash
dataDir='/user_data/csimmon2/long_pt'
CSV_FILE='/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv'
templateFSF="/lab_data/behrmannlab/vlad/ptoc/sub-004/ses-01/derivatives/fsl/loc/HighLevel.fsf"

SKIP_SUBS=("004" "007" "021" "108")
declare -A SESSION_START
SESSION_START["010"]=2
SESSION_START["018"]=2
SESSION_START["068"]=2

should_skip() {
    for skip in "${SKIP_SUBS[@]}"; do
        [[ "$1" == "$skip" ]] && return 0
    done
    return 1
}

create_highlevel_fsf() {
    local sub="$1"
    local ses="$2"
    local first_ses="$3"
    
    session_dir="$dataDir/sub-${sub}/ses-${ses}"
    [ ! -d "$session_dir/derivatives/fsl/loc" ] && return
    
    local runs=()
    for feat_dir in "$session_dir"/derivatives/fsl/loc/run-*/1stLevel.feat; do
        [ -d "$feat_dir" ] || continue
        run=$(basename "$(dirname "$feat_dir")" | sed 's/run-//')
        runs+=("$run")
    done
    
    [ ${#runs[@]} -eq 0 ] && return
    
    echo "  ses-${ses}: ${#runs[@]} runs"
    
    fsf_file="$session_dir/derivatives/fsl/loc/HighLevel.fsf"
    mkdir -p "$(dirname "$fsf_file")"
    cp "$templateFSF" "$fsf_file"
    
    sed -i "s|/lab_data/behrmannlab/vlad/ptoc|$dataDir|g" "$fsf_file"
    sed -i "s/sub-004/sub-${sub}/g" "$fsf_file"
    sed -i "s/ses-01/ses-${ses}/g" "$fsf_file"
    
    first_ses_anat="$dataDir/sub-${sub}/ses-${first_ses}/anat/sub-${sub}_ses-${first_ses}_T1w_brain.nii.gz"
    sed -i "s|set fmri(regstandard) \".*\"|set fmri(regstandard) \"$first_ses_anat\"|g" "$fsf_file"
    sed -i "s|/opt/fsl/.*/MNI152.*brain|$first_ses_anat|g" "$fsf_file"
    
    sed -i "s/set fmri(multiple) [0-9]*/set fmri(multiple) ${#runs[@]}/g" "$fsf_file"
    sed -i "s/set fmri(npts) [0-9]*/set fmri(npts) ${#runs[@]}/g" "$fsf_file"
    
    for i in "${!runs[@]}"; do
        run_num=$((i + 1))
        feat_dir="$session_dir/derivatives/fsl/loc/run-${runs[i]}/1stLevel.feat"
        sed -i "s|set feat_files($run_num) \".*\"|set feat_files($run_num) \"$feat_dir\"|g" "$fsf_file"
    done
}

tail -n +2 "$CSV_FILE" | while IFS=',' read -r sub rest; do
    subject=$(echo "$sub" | sed 's/sub-//')
    should_skip "$subject" && continue
    
    echo "=== sub-${subject} ==="
    
    start_ses=${SESSION_START[$subject]:-1}
    first_ses=$(printf "%02d" $start_ses)
    
    for ses_dir in "$dataDir/sub-${subject}"/ses-*/; do
        [ -d "$ses_dir" ] || continue
        ses=$(basename "$ses_dir" | sed 's/ses-//')
        create_highlevel_fsf "$subject" "$ses" "$first_ses"
    done
done