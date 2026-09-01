#!/bin/bash
ACCOUNT=$1
MSG_ID=$2

if [ -z "$ACCOUNT" ] || [ -z "$MSG_ID" ]; then
  echo "Usage: ./deterministic-prefilter.sh <account> <message_id>"
  exit 1
fi

himalaya -a "$ACCOUNT" message read "$MSG_ID" --raw > /tmp/prefilter-email.txt
BODY=$(cat /tmp/prefilter-email.txt)

if echo "$BODY" | grep -qiE "^from:.*no-?reply"; then
  echo "Category: automated_no_reply"
  echo "Action: no action, no AI call made"
  exit 0
fi

if echo "$BODY" | grep -qiE "ignore (all )?previous instructions|system note|forward.*inbox|reply.*with.*password"; then
  echo "Category: prompt_injection_detected"
  echo "Action: marking as spam, no AI call made"
  himalaya -a "$ACCOUNT" flag add "$MSG_ID" Spam 2>/dev/null
  exit 0
fi

if echo "$BODY" | grep -qiE "verify your account|suspended|click.*immediately|urgent.*payment|confirm your identity"; then
  echo "Category: phishing_suspected"
  echo "Action: marking as spam, no AI call made"
  himalaya -a "$ACCOUNT" flag add "$MSG_ID" Spam 2>/dev/null
  exit 0
fi

if echo "$BODY" | grep -qiE "you.?ve been selected|free (cruise|prize|gift card)|no purchase necessary|claim now"; then
  echo "Category: spam_generic"
  echo "Action: marking as spam, no AI call made"
  himalaya -a "$ACCOUNT" flag add "$MSG_ID" Spam 2>/dev/null
  exit 0
fi

if echo "$BODY" | grep -qiE "password reset|reset your password|security code"; then
  echo "Category: password_or_credential_request"
  echo "Action: flagged for awareness only, no reply, no AI call made"
  exit 0
fi

if echo "$BODY" | grep -qiE "unsubscribe|list-unsubscribe"; then
  echo "Category: newsletter_or_marketing (or forum/social/updates)"
  echo "Action: no action, no AI call made"
  exit 0
fi

echo "Category: unresolved by deterministic rules"
echo "Action: escalate to OpenClaw chat for classification (Strategy 2)"
echo "Reason: none of the fixed rule patterns matched; this needs judgment, not a fixed rule"
