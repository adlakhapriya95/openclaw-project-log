"""
Parses OpenClaw's raw log files into a per-request table, matching each
request's start and finish by runId so latency reflects one real prompt,
not two disconnected facts.

No AI model is used. Pure text/pattern parsing of log metadata only, never
the actual prompt or response content.

Honesty notes, read before trusting any field:
- prompt_chars, duration_ms: directly extracted from the logs. Real.
- word_count_estimate: chars / 5.5, a standard rough estimate, NOT a real
  word count. Logs do not record actual word counts.
- context_window_tokens: NOT AVAILABLE. These logs do not expose how much
  of the model's context window was actually used per request. Left NULL
  rather than guessed, per instruction to skip what can't be judged.
- estimated_cost_usd: computed from prompt_chars using a rough chars-to-token
  ratio (~4 chars/token) and a hardcoded Anthropic Claude Sonnet price table.
  This is an ESTIMATE, not the real billed cost, since the logs do not
  record actual input/output/cache token splits the way Hermes's own
  database does. Treat this column as directional, not exact.
- intent_guess: only filled when a clear keyword signal exists in the log
  line itself (not the actual prompt content). Left NULL when no signal
  exists, rather than forced into a category, per instruction.
- skill_update_event: True for log lines that indicate a skill/memory file
  was written or updated, used to bucket other requests into
  before/after that event for comparison.
"""
import json
import re
import sqlite3
import sys
from pathlib import Path
from collections import defaultdict

DB_PATH = Path("openclaw_usage.db")

# Rough, clearly-labeled Anthropic pricing (USD per million tokens).
# These are illustrative; verify against current published pricing before
# citing exact dollar figures anywhere.
PRICE_PER_MILLION_INPUT = 3.00
CHARS_PER_TOKEN_ESTIMATE = 4.0
CHARS_PER_WORD_ESTIMATE = 5.5

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS openclaw_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    log_file TEXT NOT NULL,
    timestamp_iso TEXT,
    provider TEXT,
    model TEXT,
    prompt_chars INTEGER,
    word_count_estimate INTEGER,
    context_window_tokens INTEGER,   -- always NULL: not available in logs
    duration_ms INTEGER,
    estimated_cost_usd REAL,
    status TEXT,
    intent_guess TEXT,               -- NULL when no clear signal exists
    skill_update_nearby TEXT,        -- 'before' / 'after' / NULL
    raw_line_excerpt TEXT
);
"""

CREATE_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS skill_update_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_file TEXT NOT NULL,
    timestamp_iso TEXT,
    raw_line_excerpt TEXT
);
"""

INTENT_RULES = [
    ("email", r"himalaya|gmail|envelope|inbox|draft|spam"),
    ("calendar", r"calendar|applescript|ics"),
    ("cron_scheduled_job", r"trigger=heartbeat|trigger=cron"),
    ("coding_or_shell", r"exec --shell|\bnpm\b|\bgit\b"),
    ("plugin_or_config", r"\bplugins\.|\bconfig\.|\bsecrets\."),
]

SKILL_UPDATE_PATTERN = re.compile(
    r"skill.*(update|creat|writ)|memory.*(update|writ|append)|MEMORY\.md",
    re.IGNORECASE,
)


def guess_intent(message: str):
    for label, pattern in INTENT_RULES:
        if re.search(pattern, message, re.IGNORECASE):
            return label
    return None  # explicitly skipped, not forced


def estimate_cost(prompt_chars: int) -> float:
    tokens = prompt_chars / CHARS_PER_TOKEN_ESTIMATE
    return round((tokens / 1_000_000) * PRICE_PER_MILLION_INPUT, 6)


def load_events(log_files):
    """First pass: collect (timestamp) of every skill/memory update event,
    plus every request start/finish keyed by run_id."""
    starts = {}   # run_id -> dict(prompt_chars, timestamp, log_file, provider, model)
    finishes = {} # run_id -> dict(duration_ms, timestamp, status)
    skill_events = []  # list of (timestamp_iso, log_file, excerpt)

    for path in log_files:
        with open(path, "r", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                message = obj.get("message", "")
                timestamp_iso = obj.get("time") or obj.get("_meta", {}).get("date")
                run_id_match = re.search(r"runId=([\w\-]+)", message)
                run_id = run_id_match.group(1) if run_id_match else obj.get("traceId")

                if SKILL_UPDATE_PATTERN.search(message):
                    skill_events.append((timestamp_iso, str(path.name), message[:200]))

                if "promptChars=" in message:
                    m = re.search(r"promptChars=(\d+)", message)
                    prov = re.search(r"provider=([\w\-]+)", message)
                    mod = re.search(r"model=([\w\.\-/]+)", message)
                    if m and run_id:
                        starts[run_id] = {
                            "prompt_chars": int(m.group(1)),
                            "timestamp_iso": timestamp_iso,
                            "log_file": str(path.name),
                            "provider": prov.group(1) if prov else None,
                            "model": mod.group(1) if mod else None,
                            "raw": message[:200],
                        }

                if "durationMs=" in message and run_id:
                    m = re.search(r"durationMs=(\d+)", message)
                    if m:
                        status = "error" if ("failure" in message or "error" in message.lower()) else "ok"
                        finishes[run_id] = {
                            "duration_ms": int(m.group(1)),
                            "status": status,
                        }

    return starts, finishes, skill_events


def nearest_skill_update_side(timestamp_iso, skill_events):
    """Returns 'before' or 'after' relative to the nearest skill update
    event, or None if no timestamp/events available for comparison."""
    if not timestamp_iso or not skill_events:
        return None
    try:
        ts = timestamp_iso
        for ev_ts, _, _ in skill_events:
            if ev_ts and ts < ev_ts:
                return "before"
        return "after"
    except TypeError:
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_openclaw_logs.py <log_dir_or_file> [more files...]")
        sys.exit(1)

    log_files = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_dir():
            log_files.extend(sorted(p.glob("openclaw-*.log")))
        elif p.is_file():
            log_files.append(p)
        else:
            print(f"Skipping, not found: {p}")

    if not log_files:
        print("No log files found.")
        sys.exit(1)

    starts, finishes, skill_events = load_events(log_files)

    conn = sqlite3.connect(DB_PATH)
    conn.execute(CREATE_TABLE)
    conn.execute(CREATE_EVENTS_TABLE)

    for ts, lf, excerpt in skill_events:
        conn.execute(
            "INSERT INTO skill_update_events (log_file, timestamp_iso, raw_line_excerpt) VALUES (?, ?, ?)",
            (lf, ts, excerpt),
        )

    matched = 0
    unmatched_no_finish = 0
    for run_id, start in starts.items():
        finish = finishes.get(run_id)
        prompt_chars = start["prompt_chars"]
        word_count_estimate = round(prompt_chars / CHARS_PER_WORD_ESTIMATE)
        intent = guess_intent(start["raw"])
        side = nearest_skill_update_side(start["timestamp_iso"], skill_events)
        cost = estimate_cost(prompt_chars)

        duration_ms = finish["duration_ms"] if finish else None
        status = finish["status"] if finish else "unknown_no_finish_logged"
        if not finish:
            unmatched_no_finish += 1
        else:
            matched += 1

        conn.execute(
            """INSERT INTO openclaw_requests
               (run_id, log_file, timestamp_iso, provider, model, prompt_chars,
                word_count_estimate, context_window_tokens, duration_ms,
                estimated_cost_usd, status, intent_guess, skill_update_nearby,
                raw_line_excerpt)
               VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)""",
            (
                run_id, start["log_file"], start["timestamp_iso"],
                start["provider"], start["model"], prompt_chars,
                word_count_estimate, duration_ms, cost, status, intent,
                side, start["raw"],
            ),
        )

    conn.commit()

    print(f"Skill/memory update events found: {len(skill_events)}")
    print(f"Requests with matched start+finish (real latency): {matched}")
    print(f"Requests with a start but no matching finish logged: {unmatched_no_finish}")

    cur = conn.execute(
        "SELECT COUNT(*), AVG(prompt_chars), AVG(word_count_estimate), "
        "AVG(duration_ms), SUM(estimated_cost_usd) FROM openclaw_requests"
    )
    n, avg_chars, avg_words, avg_dur, total_cost = cur.fetchone()
    print(f"\nTotal requests: {n}")
    print(f"Avg prompt_chars: {avg_chars}")
    print(f"Avg word_count_estimate: {avg_words}")
    print(f"Avg duration_ms (matched only): {avg_dur}")
    print(f"Total estimated_cost_usd: {total_cost}")

    print("\nIntent breakdown (NULL = no clear signal, skipped rather than guessed):")
    for label, count in conn.execute(
        "SELECT COALESCE(intent_guess,'(unclassifiable)'), COUNT(*) FROM openclaw_requests GROUP BY intent_guess ORDER BY 2 DESC"
    ):
        print(f"  {label}: {count}")

    print("\nBefore vs after nearest skill/memory update (avg cost, avg prompt size):")
    for side, count, avg_cost, avg_chars in conn.execute(
        "SELECT COALESCE(skill_update_nearby,'(no comparison possible)'), COUNT(*), "
        "AVG(estimated_cost_usd), AVG(prompt_chars) FROM openclaw_requests GROUP BY skill_update_nearby"
    ):
        print(f"  {side}: {count} requests, avg cost ${avg_cost:.6f}, avg prompt {avg_chars:.0f} chars")

    conn.close()
    print(f"\nWrote database: {DB_PATH.resolve()}")
    print("context_window_tokens column is intentionally NULL for every row: not present in these logs.")


if __name__ == "__main__":
    main()
