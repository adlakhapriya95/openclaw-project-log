#!/bin/bash
# Usage: ./run-lobster-gate-all.sh <account>
# Example: ./run-lobster-gate-all.sh gmail
# Processes every unread email in the account, one at a time.

ACCOUNT=$1

IDS=$(himalaya -a "$ACCOUNT" envelope list --json | jq -r '.envelopes[] | select(.flags | length == 0) | .id')

if [ -z "$IDS" ]; then
  echo "No unread emails found."
  exit 0
fi

echo "Found unread emails: $IDS"
echo ""

for MSG_ID in $IDS; do
  echo "=================================================="
  echo "Processing email ID: $MSG_ID"
  echo "=================================================="

  himalaya -a "$ACCOUNT" message read "$MSG_ID" --raw > /tmp/test-email.txt

  jq -n --slurpfile policy email-policy.json --rawfile email /tmp/test-email.txt \
    '{prompt: "Classify the email below against the category list in the attached policy. Return only JSON with fields category_id, autonomy, confidence, reasoning.", input: {policy: $policy[0], email: $email}}' \
    > /tmp/classify-request.json

  RESULT=$(lobster "openclaw.invoke --tool llm-task --action json --args-json \"$(cat /tmp/classify-request.json)\"")

  CATEGORY=$(echo "$RESULT" | jq -r '.[0].details.json.category_id')
  AUTONOMY=$(echo "$RESULT" | jq -r '.[0].details.json.autonomy')
  REASONING=$(echo "$RESULT" | jq -r '.[0].details.json.reasoning')

  echo "Category: $CATEGORY"
  echo "Autonomy: $AUTONOMY"
  echo "Reasoning: $REASONING"
  echo ""

  if [ "$AUTONOMY" == "escalate" ]; then
    lobster "ask --prompt \"Email $MSG_ID, category: $CATEGORY. $REASONING. No draft generated. How should I proceed?\""
  elif [ "$AUTONOMY" == "draft_for_review" ]; then
    lobster "approve --prompt \"Email $MSG_ID, category: $CATEGORY. A reply should be drafted for this. Approve drafting?\""
  elif [ "$AUTONOMY" == "auto_send" ]; then
    lobster "approve --prompt \"Email $MSG_ID, category: $CATEGORY is auto-send eligible per policy. Confirm before it sends?\""
  fi

  echo ""
done

echo "Done. Processed $(echo "$IDS" | wc -w | tr -d ' ') unread email(s)."
