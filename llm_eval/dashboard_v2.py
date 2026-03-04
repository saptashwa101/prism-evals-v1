"""LLM Eval Dashboard V2 - Dark Editorial Theme.

Run: streamlit run llm_eval/dashboard_v2.py
Set database: LLM_EVAL_DB_PATH=path/to/db.db
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

# Add parent to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_eval.models import Annotation
from llm_eval.store import TraceStore


# =============================================================================
# Theme: Dark Editorial
# =============================================================================
THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg-base: #0a0a0a;
    --bg-card: #18181b;
    --bg-elevated: #27272a;
    --bg-user: #172554;
    --bg-assistant: #14532d;
    --bg-system: #1c1c1e;
    --text-primary: #fafafa;
    --text-secondary: #d4d4d8;
    --text-muted: #71717a;
    --accent-blue: #3b82f6;
    --accent-green: #22c55e;
    --accent-red: #ef4444;
    --border: #27272a;
    --border-light: #3f3f46;
}

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background: var(--bg-base) !important;
}

.main .block-container {
    padding: 1rem 1.5rem !important;
    max-width: 1200px !important;
}

* { font-family: 'Inter', -apple-system, sans-serif !important; }
code, pre, .mono { font-family: 'JetBrains Mono', monospace !important; }

#MainMenu, footer, header, .stDeployButton { display: none !important; }
[data-testid="stHeader"] { display: none !important; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--bg-card) !important;
    border-right: 1px solid var(--border) !important;
    width: 280px !important;
}
section[data-testid="stSidebar"] > div { padding: 1rem !important; }

/* Typography */
h1 {
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    margin: 0 0 1rem 0 !important;
    letter-spacing: -0.02em !important;
}
h2 {
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    margin: 1rem 0 0.5rem 0 !important;
}
h3 {
    font-size: 1rem !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    margin: 0 !important;
}

/* Metrics */
[data-testid="stMetric"] { background: transparent !important; padding: 0 !important; }
[data-testid="stMetric"] label {
    font-size: 0.65rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    color: var(--text-muted) !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 1.25rem !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
}

/* Buttons */
.stButton > button {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: 6px !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    padding: 0.4rem 0.8rem !important;
}
.stButton > button:hover {
    background: var(--bg-elevated) !important;
    border-color: var(--border-light) !important;
}
.stButton > button[kind="primary"] {
    background: var(--accent-blue) !important;
    border-color: var(--accent-blue) !important;
}

/* Inputs */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stNumberInput > div > div > input,
.stTextArea textarea {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: 6px !important;
    font-size: 0.85rem !important;
}
.stTextInput label, .stSelectbox label, .stNumberInput label, .stTextArea label {
    font-size: 0.7rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.03em !important;
    color: var(--text-muted) !important;
}

/* Radio as pills */
.stRadio > div { flex-direction: row !important; gap: 0.5rem !important; }
.stRadio > div > label {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: var(--text-secondary) !important;
    padding: 0.3rem 0.75rem !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    cursor: pointer !important;
}
.stRadio > div > label[data-checked="true"] {
    background: var(--accent-blue) !important;
    border-color: var(--accent-blue) !important;
    color: white !important;
}

/* Checkbox */
.stCheckbox label span { color: var(--text-secondary) !important; font-size: 0.85rem !important; }

/* Expander */
[data-testid="stExpander"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.8rem !important;
    color: var(--text-muted) !important;
}

/* Divider */
hr { border-color: var(--border) !important; margin: 1rem 0 !important; }

/* Message bubbles */
.msg-bubble {
    padding: 0.75rem 1rem;
    border-radius: 8px;
    margin: 0.5rem 0;
    line-height: 1.6;
}
.msg-system {
    background: var(--bg-system);
    border-left: 3px solid var(--border-light);
    color: var(--text-muted);
    font-size: 0.8rem;
}
.msg-user {
    background: var(--bg-user);
    border-left: 3px solid var(--accent-blue);
    color: var(--text-primary);
}
.msg-assistant {
    background: var(--bg-assistant);
    border-left: 3px solid var(--accent-green);
    color: var(--text-primary);
}
.msg-role {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    margin-bottom: 0.4rem;
}
.msg-content {
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 0.9rem;
}

/* Trace card */
.trace-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    margin: 1rem 0;
}
.trace-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
}
.trace-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--text-muted);
    min-width: 2rem;
}
.trace-prompt {
    font-weight: 600;
    font-size: 0.9rem;
    color: var(--text-primary);
}
.trace-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    font-weight: 600;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
}
.badge-version { background: #1e3a5f; color: var(--accent-blue); }
.badge-ok { background: #14532d; color: var(--accent-green); }
.badge-err { background: #7f1d1d; color: var(--accent-red); }
.badge-good { background: #14532d; color: var(--accent-green); }
.badge-bad { background: #7f1d1d; color: var(--accent-red); }

.trace-metrics {
    display: flex;
    gap: 1.5rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--text-muted);
    margin: 0.75rem 0;
    padding: 0.5rem;
    background: var(--bg-base);
    border-radius: 4px;
}
.trace-metrics span { color: var(--text-secondary); }

/* Session list */
.session-item {
    padding: 0.6rem 0.75rem;
    border-radius: 6px;
    margin: 0.25rem 0;
    cursor: pointer;
    font-size: 0.85rem;
    color: var(--text-secondary);
    transition: background 0.15s;
}
.session-item:hover { background: var(--bg-elevated); }
.session-item.selected {
    background: var(--accent-blue);
    color: white;
}
.session-count {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: var(--text-muted);
}

/* Stats grid */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
    padding: 0.75rem;
    background: var(--bg-base);
    border-radius: 6px;
    margin-top: 0.5rem;
}
.stat-item { text-align: center; }
.stat-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
}
.stat-label {
    font-size: 0.6rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
}

/* General text colors */
p, span, div, label { color: var(--text-secondary) !important; }
.stMarkdown { color: var(--text-primary) !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--bg-card); }
::-webkit-scrollbar-thumb { background: var(--border-light); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }
</style>
"""


# =============================================================================
# Helpers
# =============================================================================
def get_store() -> TraceStore:
    """Get or create TraceStore from environment or session state."""
    db_path = os.environ.get("LLM_EVAL_DB_PATH", "traces.db")
    if "store" not in st.session_state or st.session_state.get("db_path") != db_path:
        st.session_state.store = TraceStore(db_path)
        st.session_state.db_path = db_path
    return st.session_state.store


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def truncate_text(text: str, max_len: int = 500) -> tuple[str, bool]:
    """Truncate text, return (truncated_text, was_truncated)."""
    if not text or len(text) <= max_len:
        return text or "", False
    return text[:max_len], True


def render_message(role: str, content: str, max_len: int = 500) -> None:
    """Render a chat message bubble."""
    if isinstance(content, list):
        content = " ".join(
            str(c.get("text", c)) if isinstance(c, dict) else str(c) for c in content
        )

    escaped = escape_html(content)
    truncated, was_truncated = truncate_text(escaped, max_len)

    role_lower = role.lower()
    msg_class = f"msg-{role_lower}" if role_lower in ["user", "assistant", "system"] else "msg-system"

    st.markdown(
        f"""
        <div class="msg-bubble {msg_class}">
            <div class="msg-role">{role.upper()}</div>
            <div class="msg-content">{truncated}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if was_truncated:
        with st.expander("Show full message"):
            st.text(content)


def render_trace(trace: dict, index: int, store: TraceStore) -> None:
    """Render a single trace with messages and annotation controls."""
    annotation = store.get_annotation(trace["id"])

    # Status and rating badges
    status_badge = "badge-ok" if trace["status"] == "success" else "badge-err"
    status_text = "OK" if trace["status"] == "success" else "ERR"

    rating_html = ""
    if annotation:
        rating_class = "badge-good" if annotation["rating"] == "good" else "badge-bad"
        rating_text = annotation["rating"].upper()
        rating_html = f'<span class="trace-badge {rating_class}">{rating_text}</span>'

    # Trace header
    st.markdown(
        f"""
        <div class="trace-card">
            <div class="trace-header">
                <span class="trace-num">#{index + 1:02d}</span>
                <span class="trace-badge {status_badge}">{status_text}</span>
                <span class="trace-prompt">{escape_html(trace["prompt_name"])}</span>
                <span class="trace-badge badge-version">v{trace["prompt_version"]}</span>
                {rating_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Messages
    messages = trace.get("input_messages", [])
    system_msgs = [m for m in messages if m.get("role", "").lower() == "system"]
    other_msgs = [m for m in messages if m.get("role", "").lower() != "system"]

    # System prompt (collapsed)
    if system_msgs:
        with st.expander(f"System prompt ({len(system_msgs)})", expanded=False):
            for msg in system_msgs:
                render_message("system", msg.get("content", ""), max_len=1000)

    # User/Assistant messages
    for msg in other_msgs:
        render_message(msg.get("role", "unknown"), msg.get("content", ""))

    # Output
    if trace["status"] == "error":
        st.markdown(
            f"""
            <div class="msg-bubble msg-system" style="border-left-color: var(--accent-red);">
                <div class="msg-role">ERROR</div>
                <div class="msg-content" style="color: var(--accent-red);">{escape_html(trace.get("error", "Unknown error"))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        output = trace.get("output_content", "") or ""
        render_message("assistant", output)

    # Metrics bar
    model = (trace.get("model_name") or "unknown")[:20]
    st.markdown(
        f"""
        <div class="trace-metrics">
            <div>in: <span>{trace.get("input_tokens", 0)}</span></div>
            <div>out: <span>{trace.get("output_tokens", 0)}</span></div>
            <div>latency: <span>{trace.get("latency_ms", 0)}ms</span></div>
            <div>model: <span>{escape_html(model)}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Annotation controls
    col_rating, col_notes, col_save = st.columns([1.5, 3, 0.8])

    with col_rating:
        current_rating = annotation["rating"] if annotation else None
        options = ["good", "bad"]
        idx = options.index(current_rating) if current_rating in options else None
        rating = st.radio(
            "Rating",
            options,
            index=idx,
            key=f"rating_{trace['id']}",
            horizontal=True,
            label_visibility="collapsed",
        )

    with col_notes:
        notes = st.text_input(
            "Notes",
            value=annotation["notes"] if annotation else "",
            key=f"notes_{trace['id']}",
            placeholder="Add notes...",
            label_visibility="collapsed",
        )

    with col_save:
        if st.button("Save", key=f"save_{trace['id']}", type="primary", use_container_width=True):
            if rating:
                store.save_annotation(
                    Annotation(
                        trace_id=trace["id"],
                        rating=rating,
                        notes=notes,
                        failure_category="",
                        annotator="user",
                    ).model_dump()
                )
                st.rerun()


# =============================================================================
# Page 1: Session Explorer
# =============================================================================
def page_sessions():
    """Session Explorer page - view and annotate conversations."""
    store = get_store()
    sessions = store.get_sessions()

    if not sessions:
        st.info("No sessions found. Run some traced LLM calls to populate the database.")
        return

    # Layout: sidebar filters handled in main(), main content here
    col_sessions, col_main = st.columns([1, 3])

    with col_sessions:
        st.markdown("## Sessions")

        # Project filter
        projects = sorted(set(s["project"] for s in sessions))
        if len(projects) > 1:
            selected_project = st.selectbox(
                "Project",
                ["All"] + projects,
                key="filter_project",
            )
            if selected_project != "All":
                sessions = [s for s in sessions if s["project"] == selected_project]

        # Session list
        for i, session in enumerate(sessions[:30]):
            session_id = session["session_id"]
            is_selected = st.session_state.get("selected_session") == session_id

            label = f"{session_id[:12]}... ({session['trace_count']})"
            if st.button(
                label,
                key=f"session_{i}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state.selected_session = session_id
                st.rerun()

    with col_main:
        selected_session = st.session_state.get("selected_session")

        if not selected_session:
            st.markdown("### Select a session")
            st.caption("Choose a session from the left to view its traces.")
            return

        # Get traces for selected session
        traces = store.get_traces({"session_id": selected_session})
        if not traces:
            st.warning("No traces found in this session.")
            return

        # Sort by time
        traces.sort(key=lambda x: x["created_at"])

        # Session header with metrics
        total_in = sum(t.get("input_tokens", 0) for t in traces)
        total_out = sum(t.get("output_tokens", 0) for t in traces)
        total_latency = sum(t.get("latency_ms", 0) for t in traces)
        avg_latency = total_latency / len(traces) if traces else 0

        st.markdown(f"### Session: `{selected_session[:16]}...`")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Traces", len(traces))
        m2.metric("Input Tokens", f"{total_in:,}")
        m3.metric("Output Tokens", f"{total_out:,}")
        m4.metric("Avg Latency", f"{avg_latency:.0f}ms")

        st.markdown("---")

        # Render each trace
        for i, trace in enumerate(traces):
            render_trace(trace, i, store)
            st.markdown("---")


# =============================================================================
# Page 2: Version Comparison
# =============================================================================
def page_versions():
    """Version Comparison page."""
    st.markdown("# Version Comparison")
    st.info("Page 2 implementation - see Task 2")


# =============================================================================
# Page 3: Failure Analysis
# =============================================================================
def page_failures():
    """Failure Analysis page."""
    st.markdown("# Failure Analysis")
    st.info("Page 3 implementation - see Task 3")


# =============================================================================
# Main App
# =============================================================================
def main():
    """Main entry point."""
    st.set_page_config(
        page_title="LLM Eval v2",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inject theme
    st.markdown(THEME_CSS, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown("## LLM Eval v2")

        # Database path
        db_path = st.text_input(
            "Database",
            value=os.environ.get("LLM_EVAL_DB_PATH", "traces.db"),
            key="db_input",
        )
        if db_path:
            os.environ["LLM_EVAL_DB_PATH"] = db_path

        st.markdown("---")

        # Navigation
        page = st.radio(
            "Navigation",
            ["Sessions", "Versions", "Failures"],
            label_visibility="collapsed",
        )

        # Quick stats
        store = get_store()
        sessions = store.get_sessions()
        total_traces = sum(s["trace_count"] for s in sessions)

        st.markdown("---")
        st.markdown(
            f"""
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">{len(sessions)}</div>
                    <div class="stat-label">Sessions</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{total_traces}</div>
                    <div class="stat-label">Traces</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Route to page
    if page == "Sessions":
        page_sessions()
    elif page == "Versions":
        page_versions()
    else:
        page_failures()


if __name__ == "__main__":
    main()
