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
