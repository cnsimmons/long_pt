#!/bin/bash
# FreeSurfer for ALL remaining patients

module load freesurfer-7.1.0
export SUBJECTS_DIR=/user_data/csimmon2/long_pt/derivatives/freesurfer
mkdir -p $SUBJECTS_DIR
mkdir -p slurm_out

# Array of subjects to process (patient=1, not already done)
SUBJECTS=(
    "sub-008:01"  # OTC
    "sub-010:02"  # OTC (starts at ses-02)
    "sub-017:01"  # OTC  
    "sub-045:01"  # nonOTC
    "sub-047:01"  # nonOTC
    "sub-049:01"  # nonOTC
    "sub-070:01"  # nonOTC
    "sub-072:01"  # nonOTC
    "sub-073:01"  # nonOTC
    "sub-079:01"  # OTC
    "sub-081:01"  # nonOTC
    "sub-086:01"  # nonOTC
    "sub-108:01"  # OTC
)

for entry in "${SUBJECTS[@]}"; do
    sub=$(echo $entry | cut -d: -f1)
    ses=$(echo $entry | cut -d: -f2)
    
    echo "Submitting $sub (ses-$ses)"
    
    sbatch <<EOF
#!/bin/bash
#SBATCH --job-name=fs_${sub}_mirror
#SBATCH --time=24:00:00
#SBATCH --mem=48gb
#SBATCH --cpus-per-task=4
#SBATCH -p cpu
#SBATCH --output=slurm_out/freesurfer_${sub}_mirror.out

module load freesurfer-7.1.0
export SUBJECTS_DIR=/user_data/csimmon2/long_pt/derivatives/freesurfer

recon-all -s ${sub}_ses${ses}_mirror \\
          -i /user_data/csimmon2/long_pt/${sub}/ses-${ses}/anat/${sub}_ses-${ses}_T1w_brain_mirrored.nii.gz \\
          -all -3T -qcache -parallel -openmp 4
EOF
done

echo "All ${#SUBJECTS[@]} patient jobs submitted"