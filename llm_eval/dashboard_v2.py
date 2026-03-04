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


# =============================================================================
# Page 1: Session Explorer
# =============================================================================
def page_sessions():
    """Session Explorer page."""
    st.markdown("# Session Explorer")
    st.info("Page 1 implementation - see Task 1")


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
