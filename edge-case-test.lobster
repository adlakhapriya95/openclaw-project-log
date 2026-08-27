# edge-case-test.lobster
#
# Deterministic-only version, no llm.invoke/llm_task.invoke dependency.
# Purpose: test whether the approval-gate mechanism itself (approve, ask,
# resume tokens) genuinely works, using simple pattern matching instead of
# real AI classification. Once the llm.invoke integration is fixed, swap
# the pattern-matching step for real classification, everything downstream
# (the gates) stays the same.

name: edge-case-test
args:
  account:
    default: testvolunteer002
  message_id:
    required: true

steps:
  - id: fetch
    exec: --json --shell "himalaya -a ${account} message read ${message_id} --raw"

  - id: check_injection
    exec: --json --shell "echo '${fetch}' | grep -iE 'ignore all previous|system note|forward.*inbox|reply.*password' > /dev/null && echo true || echo false"

  - id: check_phishing
    exec: --json --shell "echo '${fetch}' | grep -iE 'verify your account|click.*link.*immediately|suspended|urgent.*payment' > /dev/null && echo true || echo false"

  - id: check_noreply
    exec: --json --shell "echo '${fetch}' | grep -iE 'from:.*no-?reply' > /dev/null && echo true || echo false"

  - id: escalate_injection
    when: $check_injection == true
    ask:
      prompt: "Possible prompt injection detected in this email. No action will be taken. Confirm you want it marked as spam."

  - id: escalate_phishing
    when: $check_phishing == true and $check_injection == false
    ask:
      prompt: "Possible phishing detected. No action will be taken. Confirm you want it marked as spam."

  - id: skip_noreply
    when: $check_noreply == true and $check_injection == false and $check_phishing == false
    exec: --shell "echo 'No action: automated/no-reply sender'"

  - id: needs_review
    when: $check_injection == false and $check_phishing == false and $check_noreply == false
    approve:
      prompt: "This email needs review. Draft a reply, or handle manually?"
