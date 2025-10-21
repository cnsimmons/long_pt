#!/bin/bash
# submit_freesurfer_mirrored.sh

module load freesurfer-7.1.0
export SUBJECTS_DIR=/user_data/csimmon2/long_pt/derivatives/freesurfer
mkdir -p $SUBJECTS_DIR
mkdir -p slurm_out

# Submit jobs using mirrored anatomicals
for sub in sub-004 sub-007 sub-021; do
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

recon-all -s ${sub}_ses01_mirror \\
          -i /user_data/csimmon2/long_pt/${sub}/ses-01/anat/${sub}_ses-01_T1w_brain_mirrored.nii.gz \\
          -all \\
          -3T \\
          -qcache \\
          -parallel \\
          -openmp 4
EOF
    echo "Submitted ${sub} with mirrored anatomy"
done

echo "All 3 jobs submitted"
