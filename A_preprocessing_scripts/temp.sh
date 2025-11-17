# Quick debug - check what's in the CSV and why no subjects were processed
echo "=== DEBUGGING CSV READING ==="

CSV_FILE="/user_data/csimmon2/git_repos/long_pt/long_pt_sub_info.csv"

echo "1. CSV file exists?"
ls -la "$CSV_FILE"

echo -e "\n2. First few lines of CSV:"
head -5 "$CSV_FILE"

echo -e "\n3. Test CSV reading logic:"
while IFS=',' read -r sub patient intact_hemi rest; do
    echo "Read: sub='$sub', patient='$patient', intact_hemi='$intact_hemi'"
    
    # Only process first 3 lines for testing
    if [[ "$sub" == "sub-008" ]]; then
        echo "  → Would process $sub"
        break
    fi
done < "$CSV_FILE"

echo -e "\n4. Check if any subjects qualify:"
awk -F',' 'NR>1 && $2==1 {print "Qualifies:", $1, $2, $3}' "$CSV_FILE" | head -5