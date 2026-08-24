# Lobster Installation: Six-Step Compatibility Fix

Lobster (official openclaw/lobster repo, npm package @clawdbot/lobster v2026.6.11)
would not install cleanly on OpenClaw 2026.7.1-2 via the standard plugin path.
Six sequential, genuine issues were found and fixed in order:

1. Published npm package missing the openclaw.extensions field in package.json
2. No openclaw.plugin.json manifest file present at all
3. Manifest missing the required configSchema field
4. Published npm package build itself broken (ERESOLVE dependency conflict),
   requiring a manual source build from GitHub instead
5. Build script required pnpm, not installed by default
6. Even once "installed" as a plugin, it loaded with a "missing register/activate
   export" warning and exposed no usable tools

Root cause of #6, and the real fix: Lobster is not designed as an OpenClaw plugin
at all. It is a standalone CLI/SDK meant to be invoked externally (via the
terminal tool), the same integration pattern already used for Himalaya. Confirmed
via `find` that no plugin/register file exists anywhere in the source, only
standalone command scripts (openclaw_agent.ts, openclaw_invoke.ts).

Resolution: built from source, symlinked bin/lobster.js to ~/.local/bin/lobster.
Confirmed working: `lobster version` returns 2026.6.11, `lobster doctor` returns
{"ok": true}. Full command set present (exec, approve, resume, graph, llm.invoke,
workflows.run, etc), matching official documentation.

Conclusion: the currently published Lobster release has not been kept in sync
with OpenClaw's plugin-loader requirements, a real, first-hand-confirmed
compatibility gap between two projects sharing an ecosystem. Worth reporting
upstream. Not a local configuration error.
