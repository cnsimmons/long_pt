"""
Registration quality control checks for hemispherectomy patients
Provides visual inspection commands and quantitative metrics
"""
"""
# Usage BASH
# Run QC for single subject
python 06_registration_qc.py --subject sub-004

# Or check all subjects  
python 06_registration_qc.py

# Manual inspection (after QC script runs)
cd /path/to/sub-004/ses-01/derivatives/qc
bash fsleyes_commands.sh

"""
import os
import subprocess
import numpy as np
import nibabel as nib
from nilearn import image, plotting
import matplotlib.pyplot as plt
import hemi_config as config

def create_registration_overlays(subject_id):
    """
    Create overlay images for visual inspection of registration quality
    """
    print(f"Creating registration overlays for {subject_id}")
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    anat_dir = f"{sub_dir}/anat"
    qc_dir = f"{sub_dir}/derivatives/qc"
    
    os.makedirs(qc_dir, exist_ok=True)
    
    # Files to check
    original_brain = f"{anat_dir}/{subject_id}_ses-01_T1w_brain.nii.gz"
    mirrored_brain = f"{anat_dir}/{subject_id}_ses-01_T1w_brain_mirrored.nii.gz"
    registered_brain = f"{anat_dir}/{subject_id}_ses-01_T1w_brain_stand.nii.gz"
    
    if not all([os.path.exists(f) for f in [original_brain, registered_brain]]):
        print(f"  Error: Required files not found for {subject_id}")
        return False
    
    try:
        # 1. Original brain overlay on MNI
        print("  Creating original brain → MNI overlay...")
        cmd = [
            'slicer', 
            config.MNI_BRAIN, registered_brain,
            '-s', '2',
            '-x', '0.35', f"{qc_dir}/reg_check_sag.png",
            '-x', '0.45', f"{qc_dir}/reg_check_sag2.png", 
            '-x', '0.55', f"{qc_dir}/reg_check_sag3.png",
            '-x', '0.65', f"{qc_dir}/reg_check_sag4.png",
            '-y', '0.35', f"{qc_dir}/reg_check_cor.png",
            '-y', '0.45', f"{qc_dir}/reg_check_cor2.png",
            '-y', '0.55', f"{qc_dir}/reg_check_cor3.png", 
            '-y', '0.65', f"{qc_dir}/reg_check_cor4.png",
            '-z', '0.35', f"{qc_dir}/reg_check_ax.png",
            '-z', '0.45', f"{qc_dir}/reg_check_ax2.png",
            '-z', '0.55', f"{qc_dir}/reg_check_ax3.png",
            '-z', '0.65', f"{qc_dir}/reg_check_ax4.png"
        ]
        subprocess.run(cmd, check=True)
        
        # 2. Create edge overlay for boundary checking
        print("  Creating edge overlay...")
        temp_edges = f"{qc_dir}/temp_edges.nii.gz"
        
        # Create edges of MNI brain
        cmd = ['fslmaths', config.MNI_BRAIN, '-edge', temp_edges]
        subprocess.run(cmd, check=True)
        
        # Overlay edges on registered brain
        cmd = [
            'slicer',
            registered_brain, temp_edges,
            '-s', '2',
            '-x', '0.5', f"{qc_dir}/edge_check_sag.png",
            '-y', '0.5', f"{qc_dir}/edge_check_cor.png", 
            '-z', '0.5', f"{qc_dir}/edge_check_ax.png"
        ]
        subprocess.run(cmd, check=True)
        
        # Clean up
        os.remove(temp_edges)
        
        print(f"  Registration overlays saved to: {qc_dir}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"  Error creating overlays: {e}")
        return False

def compute_registration_metrics(subject_id):
    """
    Compute quantitative registration quality metrics
    """
    print(f"Computing registration metrics for {subject_id}")
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    anat_dir = f"{sub_dir}/anat"
    qc_dir = f"{sub_dir}/derivatives/qc"
    
    # Load images
    mni_img = image.load_img(config.MNI_BRAIN)
    registered_img_file = f"{anat_dir}/{subject_id}_ses-01_T1w_brain_stand.nii.gz"
    
    if not os.path.exists(registered_img_file):
        print(f"  Error: Registered brain not found: {registered_img_file}")
        return None
    
    registered_img = image.load_img(registered_img_file)
    
    try:
        # Resample to same space for comparison
        registered_resampled = image.resample_to_img(registered_img, mni_img, interpolation='linear')
        
        # Get data arrays
        mni_data = mni_img.get_fdata()
        reg_data = registered_resampled.get_fdata()
        
        # Create binary masks
        mni_mask = (mni_data > 0).astype(int)
        reg_mask = (reg_data > 0).astype(int)
        
        # Compute overlap metrics
        intersection = np.sum(mni_mask * reg_mask)
        union = np.sum((mni_mask + reg_mask) > 0)
        mni_volume = np.sum(mni_mask)
        reg_volume = np.sum(reg_mask)
        
        # Calculate metrics
        dice_coefficient = 2 * intersection / (mni_volume + reg_volume)
        jaccard_index = intersection / union
        overlap_ratio = intersection / mni_volume
        volume_ratio = reg_volume / mni_volume
        
        # Compute center of mass
        def center_of_mass(data):
            indices = np.indices(data.shape)
            total_mass = np.sum(data)
            com = []
            for i in range(data.ndim):
                com.append(np.sum(indices[i] * data) / total_mass)
            return np.array(com)
        
        mni_com = center_of_mass(mni_mask)
        reg_com = center_of_mass(reg_mask)
        com_distance = np.linalg.norm(mni_com - reg_com)
        
        # Compile metrics
        metrics = {
            'subject_id': subject_id,
            'dice_coefficient': dice_coefficient,
            'jaccard_index': jaccard_index,
            'overlap_ratio': overlap_ratio,
            'volume_ratio': volume_ratio,
            'com_distance_voxels': com_distance,
            'mni_volume_voxels': mni_volume,
            'registered_volume_voxels': reg_volume
        }
        
        # Save metrics
        import json
        metrics_file = f"{qc_dir}/registration_metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        # Print summary
        print(f"  Registration Quality Metrics:")
        print(f"    Dice coefficient: {dice_coefficient:.3f}")
        print(f"    Jaccard index: {jaccard_index:.3f}")
        print(f"    Overlap ratio: {overlap_ratio:.3f}")
        print(f"    Volume ratio: {volume_ratio:.3f}")
        print(f"    Center of mass distance: {com_distance:.2f} voxels")
        
        # Quality assessment
        if dice_coefficient > 0.8:
            quality = "GOOD"
        elif dice_coefficient > 0.7:
            quality = "ACCEPTABLE"
        else:
            quality = "POOR"
        
        print(f"    Overall quality: {quality}")
        metrics['quality_assessment'] = quality
        
        return metrics
        
    except Exception as e:
        print(f"  Error computing metrics: {e}")
        return None

def create_registration_report(subject_id):
    """
    Create a comprehensive registration quality report
    """
    print(f"Creating registration report for {subject_id}")
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    qc_dir = f"{sub_dir}/derivatives/qc"
    
    # Get subject info
    subject_info = config.SUBJECTS[subject_id]
    intact_hemi = subject_info['intact_hemi']
    group = subject_info['group']
    
    # Load metrics
    metrics_file = f"{qc_dir}/registration_metrics.json"
    if os.path.exists(metrics_file):
        import json
        with open(metrics_file, 'r') as f:
            metrics = json.load(f)
    else:
        metrics = None
    
    # Create report
    report_file = f"{qc_dir}/registration_report.txt"
    
    with open(report_file, 'w') as f:
        f.write(f"REGISTRATION QUALITY CONTROL REPORT\n")
        f.write(f"=" * 50 + "\n\n")
        f.write(f"Subject ID: {subject_id}\n")
        f.write(f"Group: {group}\n")
        f.write(f"Intact Hemisphere: {intact_hemi}\n")
        f.write(f"Processing Date: {config.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write(f"FILES PROCESSED:\n")
        f.write(f"- Original brain: {subject_id}_ses-01_T1w_brain.nii.gz\n")
        if group == 'patient':
            f.write(f"- Mirrored brain: {subject_id}_ses-01_T1w_brain_mirrored.nii.gz\n")
        f.write(f"- Registered brain: {subject_id}_ses-01_T1w_brain_stand.nii.gz\n")
        f.write(f"- Transform matrix: anat2stand.mat\n\n")
        
        if metrics:
            f.write(f"QUANTITATIVE METRICS:\n")
            f.write(f"- Dice coefficient: {metrics['dice_coefficient']:.3f}\n")
            f.write(f"- Jaccard index: {metrics['jaccard_index']:.3f}\n")
            f.write(f"- Overlap ratio: {metrics['overlap_ratio']:.3f}\n")
            f.write(f"- Volume ratio: {metrics['volume_ratio']:.3f}\n")
            f.write(f"- Center of mass distance: {metrics['com_distance_voxels']:.2f} voxels\n")
            f.write(f"- Quality assessment: {metrics['quality_assessment']}\n\n")
        
        f.write(f"VISUAL INSPECTION:\n")
        f.write(f"Check the following images for registration quality:\n")
        f.write(f"- Sagittal views: reg_check_sag*.png\n")
        f.write(f"- Coronal views: reg_check_cor*.png\n")
        f.write(f"- Axial views: reg_check_ax*.png\n")
        f.write(f"- Edge overlays: edge_check_*.png\n\n")
        
        f.write(f"FSLEYES INSPECTION COMMANDS:\n")
        f.write(f"# Overlay registered brain on MNI\n")
        f.write(f"fsleyes {config.MNI_BRAIN} {sub_dir}/anat/{subject_id}_ses-01_T1w_brain_stand.nii.gz -a 70\n\n")
        
        if group == 'patient':
            f.write(f"# Compare original vs mirrored brain\n")
            f.write(f"fsleyes {sub_dir}/anat/{subject_id}_ses-01_T1w_brain.nii.gz {sub_dir}/anat/{subject_id}_ses-01_T1w_brain_mirrored.nii.gz -a 70\n\n")
        
        f.write(f"MANUAL CHECKS:\n")
        f.write(f"1. Verify brain boundaries align with MNI template\n")
        f.write(f"2. Check for proper hemisphere alignment (especially for patients)\n")
        f.write(f"3. Ensure no significant distortion in key regions\n")
        f.write(f"4. Verify ventricular alignment\n")
        f.write(f"5. Check brainstem and cerebellum alignment\n")
    
    print(f"  Registration report saved: {report_file}")
    return report_file

def generate_fsleyes_commands(subject_id):
    """
    Generate FSLeyes commands for manual inspection
    """
    print(f"Generating FSLeyes inspection commands for {subject_id}")
    
    sub_dir = f"{config.PROCESSED_DIR}/{subject_id}/ses-01"
    anat_dir = f"{sub_dir}/anat"
    
    commands = []
    
    # Basic registration check
    commands.append(f"# Registration quality check for {subject_id}")
    commands.append(f"fsleyes {config.MNI_BRAIN} {anat_dir}/{subject_id}_ses-01_T1w_brain_stand.nii.gz -a 70 &")
    
    # Original vs mirrored (for patients)
    if config.SUBJECTS[subject_id]['group'] == 'patient':
        commands.append(f"# Original vs mirrored brain comparison")
        commands.append(f"fsleyes {anat_dir}/{subject_id}_ses-01_T1w_brain.nii.gz {anat_dir}/{subject_id}_ses-01_T1w_brain_mirrored.nii.gz -a 70 &")
    
    # ROI checks (if ROIs exist)
    roi_dir = f"{sub_dir}/derivatives/rois/parcels"
    if os.path.exists(roi_dir):
        commands.append(f"# ROI registration check")
        commands.append(f"fsleyes {anat_dir}/{subject_id}_ses-01_T1w_brain.nii.gz {roi_dir}/*.nii.gz -a 50 &")
    
    # Print commands
    print("  FSLeyes inspection commands:")
    for cmd in commands:
        print(f"    {cmd}")
    
    # Save commands to file
    qc_dir = f"{sub_dir}/derivatives/qc"
    os.makedirs(qc_dir, exist_ok=True)
    commands_file = f"{qc_dir}/fsleyes_commands.sh"
    
    with open(commands_file, 'w') as f:
        f.write("#!/bin/bash\n")
        f.write(f"# FSLeyes inspection commands for {subject_id}\n\n")
        for cmd in commands:
            f.write(f"{cmd}\n")
    
    # Make executable
    os.chmod(commands_file, 0o755)
    
    print(f"  Commands saved to: {commands_file}")
    return commands

def run_registration_qc(subject_id):
    """
    Run complete registration quality control for a subject
    """
    print(f"\nRunning registration QC for {subject_id}")
    
    # Step 1: Create visual overlays
    create_registration_overlays(subject_id)
    
    # Step 2: Compute quantitative metrics
    metrics = compute_registration_metrics(subject_id)
    
    # Step 3: Generate FSLeyes commands
    generate_fsleyes_commands(subject_id)
    
    # Step 4: Create comprehensive report
    report_file = create_registration_report(subject_id)
    
    print(f"  Registration QC complete for {subject_id}")
    print(f"  Report available at: {report_file}")
    
    return metrics

def main():
    """
    Run registration QC for all subjects
    """
    print("Starting registration quality control...")
    
    all_metrics = []
    
    for subject_id in config.SUBJECTS.keys():
        metrics = run_registration_qc(subject_id)
        if metrics:
            all_metrics.append(metrics)
    
    # Create summary report
    if all_metrics:
        summary_file = f"{config.PROCESSED_DIR}/registration_qc_summary.txt"
        with open(summary_file, 'w') as f:
            f.write("REGISTRATION QC SUMMARY\n")
            f.write("=" * 30 + "\n\n")
            
            for metrics in all_metrics:
                f.write(f"{metrics['subject_id']}: ")
                f.write(f"Dice={metrics['dice_coefficient']:.3f}, ")
                f.write(f"Quality={metrics['quality_assessment']}\n")
        
        print(f"\nQC summary saved to: {summary_file}")
    
    print("Registration QC complete!")

if __name__ == "__main__":
    main()
