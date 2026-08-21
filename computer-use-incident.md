# Computer Use / Accessibility Access Incident

During calendar setup, an Accessibility Access request from "CuaDriver" appeared
unexpectedly and was denied. Investigation traced this to Hermes's computer_use
tool, which had been deselected in the setup wizard earlier but was found, via
direct inspection of ~/.hermes/config.yaml, to still be listed as active in
platform_toolsets.cli. The wizard deselection did not take effect.

Separately, the agent's own account of its actions during the calendar permission
flow (two read-only "capture" calls plus one "open" command, no click action) was
checked directly against the raw tool-call trace and found to be accurate, unlike
earlier findings this session (the fabricated cron job, the false "resolved itself"
claim), this explanation held up under independent verification.

Action taken: computer_use manually removed from the active toolset in config.yaml,
confirmed removed via direct file inspection, verified again after restart.

Lesson: a setup wizard's displayed selections do not necessarily match the actual
resulting configuration; the only reliable check is the raw config file itself.
