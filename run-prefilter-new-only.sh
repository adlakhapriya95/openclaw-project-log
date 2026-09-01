#!/bin/bash
ACCOUNT=$1
STATE_FILE=~/Desktop/openclaw-project-log/.last-processed-id-${ACCOUNT}.txt

if [ -f "$STATE_FILE" ]; then
  LAST_ID=$(cat "$STATE_FILE")
else
  LAST_ID=0
fi

echo "Last processed ID was: $LAST_ID"
echo "Checking for anything newer..."
echo ""

HIGHEST_SEEN=$LAST_ID

himalaya -a "$ACCOUNT" envelope list --json | jq -r '.envelopes[].id' | sort -n | while read -r id; do
  if [ "$id" -gt "$LAST_ID" ]; then
    echo "=== Email $id ==="
        RESULT=$(./deterministic-prefilter.sh "$ACCOUNT" "$id")
    echo "$RESULT"
    if echo "$RESULT" | grep -q "unresolved by deterministic rules"; then
      echo "$id" >> ~/.openclaw/workspace/needs-strategy2.txt
    fi
    echo ""
    if [ "$id" -gt "$HIGHEST_SEEN" ]; then
      echo "$id" > "$STATE_FILE"
    fi
  fi
done

echo "Done. State file updated: $STATE_FILE"
