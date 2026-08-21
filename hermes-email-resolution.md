# Hermes Email Connection: Root Cause Found

After extensive troubleshooting (fresh app passwords, confirmed 2-Step Verification,
confirmed IMAP settings, confirmed Keychain storage, ruled out managed/Workspace
account, ruled out passkey interference, ruled out "skip password" setting), the
actual root cause was much simpler: the Gmail account was created as
testvolunteer002@gmail.com, but every command since had targeted
volunteertest002@gmail.com, a similar but different, non-existent address.

Once the correct email address was used in the Himalaya config and Keychain entry,
the connection worked immediately (imap: OK, smtp: OK).

Lesson: verify the exact account identifier first, before investigating deeper
technical causes. Several hours were spent ruling out legitimate but ultimately
irrelevant possibilities because the simplest explanation, a typo in the account
name, wasn't checked first.

## Follow-up: inaccurate self-report after resolution
After the fix, Hermes initially reported the issue had "resolved itself" and that
the config "was already correct," which was false, the fix required manually
identifying and correcting a typo (testvolunteer002 vs volunteertest002) across
multiple hours of troubleshooting. It also deleted a memory note based on this
false belief, without asking first. Corrected via direct instruction. Corrected
memory entry verified directly against the raw file:

"Test gmail account for himalaya is testvolunteer002@gmail.com. Earlier
config/commands incorrectly used the transposed address volunteertest002@gmail.com
for hours, causing auth failures that looked like a backend/OAuth issue but were
actually just a wrong-address typo. User manually caught and fixed it."

Fifth documented instance tonight of self-reported agent state not matching
actual ground truth, and the first case where the correction, once prompted,
was fully accurate.

## Follow-up: self-correction after resolution
After the fix, the agent's first explanation of what happened didn't match reality,
it described the issue as having "resolved itself" rather than crediting the
manual fix. Once corrected with the actual sequence of events, it updated its own
memory accurately (verified directly against the raw file). Documented here as a
concrete example of why the system design in this project treats agent
self-reports as something to verify, not something to trust by default.
