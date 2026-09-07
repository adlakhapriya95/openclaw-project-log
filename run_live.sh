#!/bin/bash
# Runs the OpenClaw log parser in a loop every 30 seconds, so
# openclaw_usage.db stays current while you use OpenClaw. The Streamlit
# dashboard (with autorefresh) will then pick up the new rows on its own.
#
# Usage: ./run_live.sh
# Stop with Ctrl+C when done.

cd "$(dirname "$0")"

echo "Starting live OpenClaw log parsing loop. Press Ctrl+C to stop."
while true; do
  TODAY_LOG="/tmp/openclaw/openclaw-$(date +%Y-%m-%d).log"
  if [ -f "$TODAY_LOG" ]; then
    python3 parse_openclaw_logs.py "$TODAY_LOG" > /tmp/parser_last_run.log 2>&1
  fi
  sleep 30
done
