#!/bin/bash
# register_pes.sh
# Register run-level PEs to first-session anatomical space, average across runs.
#
# Registration chain (matches existing HighLevel pipeline):
#   Session 1 runs: func → ses01 anat  (example_func2highres.mat)
#   Session N runs: func → sesN anat → ses01 anat  (concat: func2highres + anat2ses01)
#
# PE mapping: pe1=Face, pe3=House, pe5=Object, pe7=Word, pe9=Scramble
#
# Usage:
#   bash register_pes.sh              # all subjects
#   bash register_pes.sh sub-004      # single subject

module load fsl 2>/dev/null

BASE=/user_data/csimmon2/long_pt

# PE numbers and condition names
PE_NUMS=(1 3 5 7 9)
COND_NAMES=("face" "house" "object" "word" "scramble")

SINGLE_SUB="$1"

echo "============================================"
echo "REGISTERING RUN-LEVEL PEs TO SES01 ANAT SPACE"
echo "============================================"

# Check FSL
if ! command -v flirt &>/dev/null; then
    echo "ERROR: flirt not found. Run 'module load fsl' first."
    exit 1
fi
echo "FSL: $(which flirt)"
echo ""

# --- Subject loop ---
for SUB_DIR in ${BASE}/sub-*; do
    SUB=$(basename ${SUB_DIR})

    # Skip excluded
    if [ "$SUB" = "sub-108" ]; then continue; fi

    # Single subject mode
    if [ -n "$SINGLE_SUB" ] && [ "$SUB" != "$SINGLE_SUB" ]; then continue; fi

    # Determine first session
    case $SUB in
        sub-010) FIRST_SES="02" ;;
        sub-018) FIRST_SES="02" ;;
        sub-068) FIRST_SES="02" ;;
        *)       FIRST_SES="01" ;;
    esac

    # Reference anatomy
    REF_ANAT=${BASE}/${SUB}/ses-${FIRST_SES}/anat/${SUB}_ses-${FIRST_SES}_T1w_brain.nii.gz
    if [ ! -f "$REF_ANAT" ]; then
        echo "${SUB}: WARNING - no reference anatomy"
        continue
    fi

    echo "--- ${SUB} (ref=ses-${FIRST_SES}) ---"

    # Loop over sessions
    for SES_DIR in ${SUB_DIR}/ses-*; do
        SES=$(basename ${SES_DIR} | sed 's/ses-//')
        LOC_DIR=${SES_DIR}/derivatives/fsl/loc
        OUT_DIR=${LOC_DIR}/registered_pes

        if [ ! -d "$LOC_DIR" ]; then continue; fi

        # Find runs
        RUNS=()
        for FEAT in ${LOC_DIR}/run-*/1stLevel.feat; do
            if [ -d "$FEAT" ]; then
                RUN=$(echo $FEAT | grep -oP 'run-\K[^/]+')
                RUNS+=("$RUN")
            fi
        done
        IFS=$'\n' RUNS=($(sort <<<"${RUNS[*]}")); unset IFS

        if [ ${#RUNS[@]} -eq 0 ]; then continue; fi

        mkdir -p ${OUT_DIR}

        # Is this the first session?
        if [ "$SES" = "$FIRST_SES" ]; then
            IS_FIRST=1
        else
            IS_FIRST=0
            # Cross-session anat transform
            ANAT_XFM=${SES_DIR}/anat/anat2ses${FIRST_SES}.mat
            if [ ! -f "$ANAT_XFM" ]; then
                echo "  ses-${SES}: WARNING - no anat2ses${FIRST_SES}.mat, skipping"
                continue
            fi
        fi

        echo "  ses-${SES}: ${#RUNS[@]} runs (first_ses=${IS_FIRST})"

        # Step 1: Register each PE from each run
        for RUN in "${RUNS[@]}"; do
            FEAT=${LOC_DIR}/run-${RUN}/1stLevel.feat
            FUNC2ANAT=${FEAT}/reg/example_func2highres.mat

            if [ ! -f "$FUNC2ANAT" ]; then
                echo "    run-${RUN}: WARNING - no func2highres.mat"
                continue
            fi

            for i in "${!PE_NUMS[@]}"; do
                PE=${PE_NUMS[$i]}
                COND=${COND_NAMES[$i]}

                IN=${FEAT}/stats/pe${PE}.nii.gz
                OUT=${OUT_DIR}/run-${RUN}_${COND}.nii.gz

                # Skip if already done
                if [ -f "$OUT" ]; then continue; fi
                if [ ! -f "$IN" ]; then continue; fi

                if [ $IS_FIRST -eq 1 ]; then
                    # Session 1: func → ses01 anat (one step)
                    flirt -in ${IN} -ref ${REF_ANAT} -out ${OUT} \
                          -applyxfm -init ${FUNC2ANAT} -interp trilinear
                else
                    # Later session: chain func2highres + anat2ses01
                    COMBINED=${OUT_DIR}/run-${RUN}_func2ses${FIRST_SES}.mat
                    if [ ! -f "$COMBINED" ]; then
                        convert_xfm -omat ${COMBINED} -concat ${ANAT_XFM} ${FUNC2ANAT}
                    fi
                    flirt -in ${IN} -ref ${REF_ANAT} -out ${OUT} \
                          -applyxfm -init ${COMBINED} -interp trilinear
                fi
            done
        done

        # Step 2: Average across runs per condition
        for COND in "${COND_NAMES[@]}"; do
            MEAN=${OUT_DIR}/${COND}_mean.nii.gz
            if [ -f "$MEAN" ]; then continue; fi

            # Collect run files
            RUN_FILES=($(ls ${OUT_DIR}/run-*_${COND}.nii.gz 2>/dev/null | sort))

            if [ ${#RUN_FILES[@]} -eq 0 ]; then
                continue
            elif [ ${#RUN_FILES[@]} -eq 1 ]; then
                cp "${RUN_FILES[0]}" "$MEAN"
            else
                CMD="fslmaths ${RUN_FILES[0]}"
                for ((j=1; j<${#RUN_FILES[@]}; j++)); do
                    CMD="${CMD} -add ${RUN_FILES[$j]}"
                done
                CMD="${CMD} -div ${#RUN_FILES[@]} ${MEAN}"
                eval $CMD
            fi
            echo "    ${COND}: averaged ${#RUN_FILES[@]} runs"
        done

        # Summary
        N_MEANS=$(ls ${OUT_DIR}/*_mean.nii.gz 2>/dev/null | wc -l)
        echo "    ✓ ${N_MEANS}/5 condition means"

    done
done

echo ""
echo "============================================"
echo "COMPLETE"
echo "============================================"