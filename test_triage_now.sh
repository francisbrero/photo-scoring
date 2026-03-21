#!/bin/bash
# Quick triage test script
# Usage: ./test_triage_now.sh YOUR_JWT_TOKEN

set -e

TOKEN="$1"
API_URL="${2:-https://photo-score-api.onrender.com}"

if [ -z "$TOKEN" ]; then
    echo "Usage: ./test_triage_now.sh YOUR_JWT_TOKEN [API_URL]"
    echo ""
    echo "To get your token:"
    echo "1. Open https://photo-scoring.vercel.app in Chrome"
    echo "2. Open DevTools (F12) > Application > Local Storage"
    echo "3. Find 'sb-rkwkvieffzffpvogebx-auth-token'"
    echo "4. Copy the 'access_token' value"
    exit 1
fi

# Check triage health
echo "=== Checking Triage Health ==="
curl -s "$API_URL/api/triage/health" | jq .

# Use the 16-photo files from previous upload
FILES_JSON='/tmp/triage_files2.json'
if [ ! -f "$FILES_JSON" ]; then
    echo "ERROR: $FILES_JSON not found. Run a test upload first via the webapp."
    exit 1
fi

NUM_FILES=$(jq length "$FILES_JSON")
echo ""
echo "=== Starting Triage with $NUM_FILES photos ==="

# Generate new job ID
JOB_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
echo "Job ID: $JOB_ID"

# Build the request payload
PAYLOAD=$(jq -n \
    --arg job_id "$JOB_ID" \
    --slurpfile files "$FILES_JSON" \
    '{
        job_id: $job_id,
        files: ($files[0] | map({original_name: .original_name, storage_path: .storage_path, size: .size})),
        target: "20%",
        criteria: "standout",
        passes: 1
    }')

# Start the triage job
RESPONSE=$(curl -s -X POST "$API_URL/api/triage/start-from-storage" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

echo "Response: $RESPONSE"

STATUS=$(echo "$RESPONSE" | jq -r '.status // "error"')
if [ "$STATUS" = "error" ] || [ "$STATUS" = "null" ]; then
    echo "ERROR: Failed to start triage"
    echo "$RESPONSE" | jq .
    exit 1
fi

# Poll for status
echo ""
echo "=== Polling Status (max 5 minutes) ==="
for i in {1..100}; do
    POLL=$(curl -s "$API_URL/api/triage/$JOB_ID/status" \
        -H "Authorization: Bearer $TOKEN")

    JOB_STATUS=$(echo "$POLL" | jq -r '.status')
    PHASE=$(echo "$POLL" | jq -r '.progress.phase // "unknown"')
    STEP=$(echo "$POLL" | jq -r '.progress.current_step // 0')
    TOTAL=$(echo "$POLL" | jq -r '.progress.total_steps // 0')
    PCT=$(echo "$POLL" | jq -r '.progress.percentage // 0')

    echo "[$i] $JOB_STATUS | $PHASE | $STEP/$TOTAL (${PCT}%)"

    if [ "$JOB_STATUS" = "completed" ]; then
        echo ""
        echo "=== SUCCESS! Triage Completed ==="
        break
    elif [ "$JOB_STATUS" = "failed" ]; then
        echo ""
        echo "=== FAILED ==="
        echo "$POLL" | jq .
        exit 1
    fi

    sleep 3
done

# Get results
echo ""
echo "=== Results ==="
RESULTS=$(curl -s "$API_URL/api/triage/$JOB_ID/results" \
    -H "Authorization: Bearer $TOKEN")

SELECTED=$(echo "$RESULTS" | jq '.selected_photos | length')
TOTAL_INPUT=$(echo "$RESULTS" | jq '.total_input')

echo "Input: $TOTAL_INPUT photos"
echo "Selected: $SELECTED photos (top $(echo "scale=1; $SELECTED * 100 / $TOTAL_INPUT" | bc)%)"
echo ""
echo "Selected photos:"
echo "$RESULTS" | jq -r '.selected_photos[].original_filename'
