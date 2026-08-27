# Lobster / llm-task Integration Bug: Final Diagnosis

## Summary
Lobster's standalone CLI and deterministic mechanism (exec, where, approve, ask,
resume tokens) all work correctly, confirmed and tested. The one integration
that never worked, across the full session, was Lobster calling the AI model
automatically via openclaw.invoke --tool llm-task.

## What was ruled out, in order, each confirmed with direct evidence
1. Shell quoting: single-quoted pipelines broke on apostrophes in real email text.
2. Expired Claude Code OAuth session.
3. Accidentally wiped claude-cli credential in OpenClaw's own auth store.
4. Missing required "prompt" field in the request payload.
5. Request payload size, checked and ruled out (179KB against a 1MB limit).
6. Same failure reproduced on a small test email, ruling out size/complexity.
7. Traced into the plugin's actual source code, confirmed it correctly builds
   a well-formed single message, ruling out the plugin's own code as the cause.

## Actual root cause, as far as traceable
The error "messages: at least one message is required" originates inside
api.runtime.agent.runSingleTurn, an internal OpenClaw function, not visible
in the llm-task plugin's own source. Further tracing requires OpenClaw's
core agent-runtime source open directly.

## What works, confirmed and used successfully
OpenClaw's normal chat, given the same email-policy.json file, correctly
classified and acted on a full batch of real test emails, marking two
confirmed threats as spam without approval and holding two legitimate items
for review, exactly matching policy.

## Conclusion
The system works end to end today via OpenClaw's chat directly. The Lobster
automation of that same step is a real, precisely-located, unresolved bug
worth revisiting with the full source open, not through chat debugging.
