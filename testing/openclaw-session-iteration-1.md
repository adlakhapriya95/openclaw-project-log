# OpenClaw Testing Log

## Iteration 1

### Setup
- Configured OpenClaw on local machine
- Provided calendar access using POP/IMAP
- Did not use Google OAuth to limit access to other Google services
- Added email response instructions to memory
- Configured scheduled jobs for email monitoring

### Testing
- Tested OpenClaw using 28 emails
- Evaluated email intent classification
- Evaluated response quality
- Tested prompt injection and malicious emails
- Checked whether calendar-related instructions were followed

### Key Observations

#### What Worked
- Agent asked for confirmation before sending emails
- Correctly identified malicious and prompt injection emails
- Classified emails according to intent
- Provided a "Note to Self" when responses needed modification

#### Issues Found
- Used em dashes in responses
- Inconsistent line formatting
- Incorrectly used "Dear" in some professional responses
- Made mistakes with date and time despite using a time tool
- Did not consistently update the calendar after an email was sent

### Improvements Made
- Added instructions to highlight calendar conflicts
- Added instructions to update the calendar after sending an email
- Configured a job to scan emails every 4 hours
- Configured a morning notification job