"""
Streamlit dashboard for OpenClaw vs Hermes usage.

Reads only real, already-extracted data:
- OpenClaw: openclaw_usage.db (built by parse_openclaw_logs.py)
- Hermes: ~/.hermes/state.db (session_model_usage table, native to Hermes)

No numbers are invented. Sample sizes are shown explicitly since OpenClaw's
current log retention window is much smaller than Hermes's full history.
"""
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="OpenClaw vs Hermes: Usage Dashboard", layout="wide")

OPENCLAW_DB = Path("openclaw_usage.db")
HERMES_DB = Path.home() / ".hermes" / "state.db"

st.title("OpenClaw vs Hermes: Real Usage Comparison")
st.caption(
    "Every number here comes directly from each tool's own logs or database. "
    "No figure is estimated except where explicitly labeled 'estimated'."
)
st.info(
    "**Important:** these cost figures represent what this usage would cost under "
    "standard pay-per-token API pricing. Both agents in this project were connected "
    "via a Claude Pro subscription (flat monthly rate) instead, so no per-token "
    "charge was actually incurred. These numbers are useful for comparing relative "
    "token efficiency between the two agents, not as a real bill."
)

# ---- Load OpenClaw data ----
oc_df = pd.DataFrame()
if OPENCLAW_DB.exists():
    conn = sqlite3.connect(OPENCLAW_DB)
    oc_df = pd.read_sql_query("SELECT * FROM openclaw_requests", conn)
    conn.close()

# ---- Load Hermes data ----
hermes_df = pd.DataFrame()
if HERMES_DB.exists():
    conn = sqlite3.connect(HERMES_DB)
    hermes_df = pd.read_sql_query("SELECT * FROM session_model_usage", conn)
    conn.close()

if oc_df.empty and hermes_df.empty:
    st.error("No data found. Run parse_openclaw_logs.py first, and confirm ~/.hermes/state.db exists.")
    st.stop()

# ---- Sample size warning, front and center ----
col1, col2 = st.columns(2)
with col1:
    st.metric("OpenClaw requests (from current logs)", len(oc_df))
    if len(oc_df) < 20:
        st.warning(
            f"Only {len(oc_df)} OpenClaw requests are available. OpenClaw's log "
            "retention rotated out older sessions; this is a small, directional "
            "sample, not a full history."
        )
with col2:
    st.metric("Hermes sessions (full history)", hermes_df["session_id"].nunique() if not hermes_df.empty else 0)
    st.caption("Hermes keeps a persistent usage table, so this reflects the full recorded history.")

st.divider()

# ---- Section 1: Cost per request/session ----
st.header("1. Token Cost")

c1, c2 = st.columns(2)
with c1:
    st.subheader("OpenClaw: estimated cost per request")
    if not oc_df.empty:
        st.caption("Estimated from prompt_chars using an approximate chars-to-token ratio. Not the real billed figure.")
        st.line_chart(oc_df.set_index("timestamp_iso")["estimated_cost_usd"])
        st.write(f"Total estimated cost across {len(oc_df)} requests: **${oc_df['estimated_cost_usd'].sum():.4f}**")
    else:
        st.info("No OpenClaw data.")

with c2:
    st.subheader("Hermes: real cost per session")
    if not hermes_df.empty:
        st.caption("Real, recorded cost from Hermes's own usage table.")
        session_cost = hermes_df.groupby("session_id")["estimated_cost_usd"].sum().reset_index()
        st.line_chart(session_cost.set_index("session_id")["estimated_cost_usd"])
        st.write(f"Total real cost across {hermes_df['session_id'].nunique()} sessions: **${hermes_df['estimated_cost_usd'].sum():.4f}**")
    else:
        st.info("No Hermes data.")

st.divider()

# ---- Section 2: Where tokens actually go (Hermes: real breakdown) ----
st.header("2. Where Tokens Are Actually Going (Hermes, real data)")
if not hermes_df.empty:
    totals = hermes_df[["input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens"]].sum()
    st.caption(
        "Real token VOLUME by type. Important: cache-read tokens are typically priced "
        "far lower than fresh input tokens (often a small fraction of the cost per "
        "token), so a large cache-read bar does not mean that's where the cost is "
        "concentrated, only where the volume is. See the cost-weighted view below "
        "for where the actual dollars go."
    )
    breakdown_df = totals.reset_index()
    breakdown_df.columns = ["token_type", "total"]
    st.bar_chart(breakdown_df.set_index("token_type"))
    cache_pct = totals["cache_read_tokens"] / totals.sum() * 100
    st.write(f"Cache-read tokens account for {cache_pct:.1f}% of total token **volume** (not necessarily cost).")

    st.subheader("Cost-weighted view (this is what actually drives your bill)")
    st.caption(
        "estimated_cost_usd is Hermes's own recorded figure per session/model/task row. "
        "If this field does not separately discount cache-read pricing, it may "
        "overstate cache cost relative to real API pricing. Verify against Anthropic's "
        "published cache pricing before treating this as exact."
    )
    cost_by_task = hermes_df.groupby("task")["estimated_cost_usd"].sum().reset_index().sort_values("estimated_cost_usd", ascending=False)
    st.dataframe(cost_by_task, use_container_width=True)
else:
    st.info("No Hermes data available for this breakdown.")

st.divider()

# ---- Section 3: Latency ----
st.header("3. Latency")
if not oc_df.empty and oc_df["duration_ms"].notna().any():
    matched = oc_df[oc_df["duration_ms"].notna()]
    st.caption(f"Only {len(matched)} of {len(oc_df)} OpenClaw requests had a matching completion logged; latency is real but sparse.")
    st.bar_chart(matched.set_index("timestamp_iso")["duration_ms"])
else:
    st.info("No matched latency data available for OpenClaw in the current log window.")
st.caption("Context window size per request is not available in OpenClaw's logs and is intentionally omitted rather than estimated.")

st.divider()

# ---- Section 4: Intent, where to focus optimization ----
st.header("4. Intent Breakdown (where cost concentrates)")
if not oc_df.empty:
    intent_counts = oc_df["intent_guess"].fillna("(unclassifiable, no keyword signal)").value_counts().reset_index()
    intent_counts.columns = ["intent", "count"]
    st.caption("Only assigned when a clear keyword signal exists in the log line itself. Left unclassified rather than guessed otherwise.")
    st.bar_chart(intent_counts.set_index("intent"))

    intent_cost = oc_df.groupby(oc_df["intent_guess"].fillna("(unclassifiable)"))["estimated_cost_usd"].sum().reset_index()
    intent_cost.columns = ["intent", "total_estimated_cost"]
    st.write("Estimated cost by intent category (where identifiable):")
    st.dataframe(intent_cost.sort_values("total_estimated_cost", ascending=False), use_container_width=True)
else:
    st.info("No OpenClaw data.")

st.divider()

# ---- Section 5: Reliability ----
st.header("5. Reliability")
c1, c2 = st.columns(2)
with c1:
    st.subheader("OpenClaw")
    if not oc_df.empty:
        status_counts = oc_df["status"].value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        st.dataframe(status_counts, use_container_width=True)
with c2:
    st.subheader("Hermes")
    st.caption("Hermes's usage table does not record a per-session status/error field the way OpenClaw's logs do; not directly comparable.")

st.divider()

st.divider()

# ---- Section: Full picture, combining real data with documented history ----
st.header("6. Full Picture: Combining Quantitative and Documented Evidence")
st.caption(
    "Raw request logs only survive from Sept 2 onward due to log rotation. "
    "Everything before that is not recoverable as numeric data, but it was "
    "documented directly, in writing, at the time. Both are shown here rather "
    "than presenting only the incomplete numeric slice as the whole story."
)

st.subheader("Documented history (OpenClaw, Aug 11 - Sept 1, from written testing notes)")
st.markdown("""
- **Setup:** required troubleshooting Groq (token ceiling hit immediately), Gemini
  (config didn't work as documented), and Anthropic trial credit (exhausted in
  1-2 exchanges) before landing on the Claude Code CLI connection.
- **Default overhead:** ~56,000 tokens per request out of the box, caused by 51
  bundled plugin definitions sent with every call; required manual pruning.
- **Iteration 1 (28 emails):** correct classification, malicious-intent detection,
  and confirmation-before-sending. Issues: em-dashes, "Dear" greetings, no
  automatic calendar updates.
- **Iteration 2 (25 emails):** writing-style issues fixed. New issues: token use
  increased after adding skills; drafts stayed in inbox after sending (IMAP vs.
  native Gmail drafts); calendar automation still did not work even after being
  directly targeted.
- **v1 to v2 update:** introduced a new, undocumented authentication failure
  (MCP-related session reset) with no available fix, and a one-way database
  schema migration (v1 to v15) that made reverting to v1 impossible without a
  full reset.
""")

st.subheader("Quantitative data (numeric, parsed directly from surviving logs/databases)")
st.markdown(f"""
- **OpenClaw:** {len(oc_df)} requests recoverable (Sept 2 onward only).
- **Hermes:** {hermes_df['session_id'].nunique() if not hermes_df.empty else 0} sessions recoverable (full history, Aug 20 onward).
""")

st.warning(
    "The numeric sections above (1-5) understate OpenClaw's real usage history "
    "on their own. Read them alongside the documented history here, not in "
    "isolation, for an accurate overall picture."
)
tab1, tab2 = st.tabs(["OpenClaw requests", "Hermes sessions"])
with tab1:
    st.dataframe(oc_df, use_container_width=True)
with tab2:
    st.dataframe(hermes_df, use_container_width=True)
