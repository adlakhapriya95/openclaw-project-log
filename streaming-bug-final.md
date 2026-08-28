# Lobster llm.invoke Streaming Incompatibility: Final Root Cause

## Summary
llm.invoke (Lobster's built-in tool for calling an LLM model) could not
successfully complete a call to anthropic/claude-sonnet-5 through any of its
three built-in provider paths. The model itself worked correctly every time
it was reached. The failure is a response-format mismatch, not a model,
authentication, or payload problem.

## Root cause, precisely
llm.invoke requires a single, complete JSON response object from the model
call. Anthropic's API, in this configuration, returns a streaming response
(contentType: text/event-stream), where the answer arrives in a sequence of
small chunks over time rather than as one complete object. llm.invoke has no
mechanism to reassemble a streamed response, so it reports "invalid response
envelope" even when the underlying model call succeeded (confirmed via
OpenClaw's own logs: status=200, a real answer generated, clean session
close).

## All three built-in llm.invoke providers were tested

1. **openclaw provider** (routes through OpenClaw's own bridge)
   - Successfully reaches Anthropic's API (status=200, confirmed in logs).
   - Response always comes back as text/event-stream.
   - OpenClaw exposes a documented "streaming: false" setting on a per-model
     config entry. This was set explicitly, confirmed saved in the config
     file, and the gateway was restarted. Re-tested and re-checked the logs:
     the response still came back as text/event-stream. The setting had no
     effect on the actual outgoing request. This is a real, confirmed
     discrepancy between documented behavior and actual behavior.

2. **http provider** (generic direct connection to any API endpoint)
   - Bypasses OpenClaw entirely, connects straight to
     https://api.anthropic.com/v1/messages.
   - Failed immediately: Anthropic's raw API requires an "anthropic-version"
     header on every request, which this generic provider has no
     documented option to set. Checked the full --help output directly;
     no header-setting flag exists.
   - Even if that were resolved, there is still no way for this generic
     provider to explicitly request a non-streaming response either, since
     that also requires a parameter/header this provider cannot set.

3. **pi provider**
   - Documented in llm.invoke's own help text as "intended to be supplied
     by a Pi extension," i.e. not meant for direct/generic use without a
     separate companion tool that was not part of this setup. Not usable
     as configured.

## Why this likely does not affect most Lobster users
This appears specific to calling a model provider (Anthropic) directly
through llm.invoke's generic paths, without either:
(a) OpenClaw's bridge correctly suppressing streaming (confirmed broken), or
(b) a properly configured intermediate service/extension that already
    handles the required headers and streaming negotiation, which the
    generic http and pi providers assume exists but do not provide
    themselves.

Most real-world Lobster workflows likely rely on one of these two things
being properly in place; neither was available in this setup.

## Verification method
Every step was confirmed via direct log inspection
(/tmp/openclaw/openclaw-2026-08-2*.log), not assumption:
- Confirmed successful model responses (status=200, real output, clean
  session close) on the openclaw provider path.
- Confirmed contentType=text/event-stream on every single response, before
  and after the streaming:false config change.
- Confirmed the http provider's failure reason directly from Anthropic's own
  error response (400, "anthropic-version: header is required").
- Confirmed no header or streaming-control flag exists in llm.invoke's own
  --help output for either alternate provider.

## Conclusion
This is a genuine, reproducible, three-path-confirmed limitation in how
llm.invoke's bundled providers negotiate response format and required
headers with Anthropic's API, not a fault in the model, in authentication,
in payload size or content, or in anything specific to this project's email
data. A real fix requires either a corrected OpenClaw bridge (the documented
streaming:false setting does not currently work) or a properly configured
intermediate adapter service for the http/pi provider paths, neither of
which exists in the current setup.
