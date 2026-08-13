# OpenClaw Setup and Provider Troubleshooting Log
Date: August 12, 2026

## Summary
Installed and configured OpenClaw (self-hosted AI agent framework) locally on macOS,
running as a persistent background service via launchd. Attempted to connect four
different model providers over the course of one session.

## What worked
- Gateway installation and persistent background service setup
- Groq provider: successfully authenticated and connected, functional for simple
  requests within its free-tier token ceiling
- Gemini provider: successfully authenticated via API key
- Anthropic provider: successfully authenticated via API key
- OpenRouter provider: installed and configured as a request-count-limited
  alternative to token-size-limited providers

## What went wrong
- Groq (llama-3.3-70b-versatile): free tier caps requests at 12,000 tokens/minute.
  Every request, including a single-word "hi", measured at approximately
  56,000 tokens due to OpenClaw's bundled system prompt and tool definitions.
  Every request failed regardless of message content.
- Gemini: manual provider configuration (editing openclaw.json directly to add
  a custom provider block) did not result in a working connection on this
  OpenClaw build (2026.7.1-2), despite the model showing as configured with
  valid auth. Root cause not fully confirmed, possibly incomplete support
  for manually-declared custom providers in this version.
- Anthropic: trial credit exhausted within 1-2 exchanges, consistent with the
  same root cause, large per-request token overhead from bundled tool
  definitions rather than actual conversation content.

## Root cause identified
OpenClaw's default agent bundles a large system prompt plus full tool/plugin
definitions into every single request, regardless of message size or content.
This overhead (~50,000+ tokens per request on the default "main" agent, which
had accumulated multiple provider and plugin installs over the session) is
incompatible with token-per-minute-limited free tiers (Groq) and burns
dollar-based trial credits fast (Anthropic), independent of actual usage volume.

## Next steps
- Create a minimal, dedicated agent with a reduced toolset rather than
  continuing to build on the default agent's accumulated configuration
- OpenRouter's free tier is request-count-limited rather than token-size-limited,
  which better fits the constraint actually being hit
- Revisit Gmail/email connector setup once a stable provider connection is
  confirmed working end to end

## Note on credentials
All API keys and tokens referenced during this session have been rotated.
config-snapshot.json has had sensitive fields redacted before being committed.
