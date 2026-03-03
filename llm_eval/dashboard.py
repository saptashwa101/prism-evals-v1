"""Streamlit dashboard for LLM Eval trace viewing and annotation.

Run with: streamlit run llm_eval/dashboard.py
Set database: LLM_EVAL_DB_PATH=path/to/db.db

Pages:
1. Session Explorer - Browse sessions, view traces, annotate
2. Version Comparison - Compare prompt versions side-by-side
3. Failure Analysis - Clustering of failures
"""

import json
import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_eval.store import TraceStore
from llm_eval.models import Annotation

# Compact CSS
COMPACT_CSS = """
<style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    h1 {font-size: 1.5rem !important; margin-bottom: 0.5rem !important;}
    h2 {font-size: 1.2rem !important; margin-bottom: 0.3rem !important;}
    h3 {font-size: 1rem !important; margin-bottom: 0.2rem !important;}
    .stMetric {padding: 0.2rem 0 !important;}
    .stMetric label {font-size: 0.75rem !important;}
    .stMetric [data-testid="stMetricValue"] {font-size: 1rem !important;}
    div[data-testid="stExpander"] {margin-bottom: 0.3rem !important;}
    .stRadio > div {gap: 0.3rem !important;}
    .stTextInput > div > div > input {padding: 0.3rem 0.5rem !important;}
    .stButton > button {padding: 0.2rem 0.8rem !important; font-size: 0.8rem !important;}
    .trace-card {border: 1px solid #ddd; border-radius: 4px; padding: 8px 12px; margin-bottom: 10px; background: #fff;}
    .msg-box {padding: 6px 10px; border-radius: 4px; font-size: 0.85rem; margin: 3px 0; border-left: 3px solid;}
    .msg-system {background: #f8f9fa; border-left-color: #6c757d;}
    .msg-user {background: #f8f9fa; border-left-color: #0d6efd;}
    .msg-assistant {background: #f8f9fa; border-left-color: #198754;}
    .msg-label {font-weight: 600; color: #495057; font-size: 0.75rem; text-transform: uppercase;}
    .metrics-row {display: flex; gap: 8px; font-size: 0.75rem; color: #666; margin: 4px 0;}
    .metrics-row span {background: #f8f9fa; padding: 2px 6px; border-radius: 3px; border: 1px solid #eee;}
    hr {margin: 6px 0 !important; border-color: #eee !important;}
</style>
"""


def get_store() -> TraceStore:
    """Get or create the TraceStore instance."""
    import os
    db_path = os.environ.get("LLM_EVAL_DB_PATH", "traces.db")

    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv):
            if arg == "--db-path" and i + 1 < len(sys.argv):
                db_path = sys.argv[i + 1]
                break
            if arg.startswith("--db-path="):
                db_path = arg.split("=", 1)[1]
                break

    if "store" not in st.session_state or st.session_state.get("db_path") != db_path:
        st.session_state.store = TraceStore(db_path)
        st.session_state.db_path = db_path
    return st.session_state.store


def render_message(role: str, content: str):
    """Render a message with role-based styling."""
    if isinstance(content, list):
        content = " ".join(item.get("text", str(item)) for item in content if isinstance(item, dict))

    role_lower = role.lower()
    css_class = f"msg-{role_lower}" if role_lower in ["system", "user", "assistant"] else "msg-user"
    st.markdown(f'<div class="msg-box {css_class}"><span class="msg-label">{role}</span><br>{content}</div>', unsafe_allow_html=True)


# =============================================================================
# Page 1: Session Explorer
# =============================================================================
def page_session_explorer():
    st.markdown("## Session Explorer")
    store = get_store()
    sessions = store.get_sessions()

    if not sessions:
        st.info("No sessions found.")
        return

    col_left, col_middle, col_right = st.columns([1, 2.5, 1])

    # === LEFT: Filters & Sessions ===
    with col_left:
        projects = list(set(s["project"] for s in sessions))
        selected_project = st.selectbox("Project", ["All"] + projects, key="filter_project")

        all_traces = store.get_traces({})
        prompt_names = list(set(t["prompt_name"] for t in all_traces))
        selected_prompt = st.selectbox("Prompt", ["All"] + prompt_names, key="filter_prompt")

        st.markdown("**Sessions**")
        filtered_sessions = sessions
        if selected_project != "All":
            filtered_sessions = [s for s in filtered_sessions if s["project"] == selected_project]

        for i, session in enumerate(filtered_sessions[:15]):
            session_id = session["session_id"]
            display = session_id[:18] + ".." if len(session_id) > 20 else session_id
            label = f"{display} ({session['trace_count']})"
            if st.button(label, key=f"sess_{i}", use_container_width=True):
                st.session_state.selected_session = session_id

    # === MIDDLE: Traces ===
    with col_middle:
        selected_session = st.session_state.get("selected_session")
        if not selected_session:
            st.info("Select a session")
            return

        traces = store.get_traces({"session_id": selected_session})
        if not traces:
            st.warning("No traces")
            return

        traces.sort(key=lambda x: x["created_at"])
        st.markdown(f"**{len(traces)} traces** in `{selected_session[:25]}..`")

        for i, trace in enumerate(traces):
            annotation = store.get_annotation(trace["id"])
            status = "OK" if trace["status"] == "success" else "ERR"
            ann_status = ""
            if annotation:
                ann_status = " [GOOD]" if annotation["rating"] == "good" else " [BAD]"

            # Metrics line
            metrics = f"in:{trace.get('input_tokens',0)} out:{trace.get('output_tokens',0)} | {trace.get('latency_ms',0)}ms | {trace.get('model_name','')[:20]}"

            st.markdown(f"""<div class="trace-card">
                <b>#{i+1} {trace['prompt_name']} v{trace['prompt_version']}</b> [{status}]{ann_status}
                <div class="metrics-row"><span>{metrics}</span></div>
            </div>""", unsafe_allow_html=True)

            # Input messages
            with st.expander(f"Input ({len(trace.get('input_messages', []))} msgs)", expanded=True):
                for msg in trace.get("input_messages", []):
                    render_message(msg.get("role", "unknown"), msg.get("content", ""))

            # Output
            with st.expander("Output", expanded=True):
                if trace["status"] == "error":
                    st.error(trace.get("error", "Error"))
                else:
                    st.markdown(trace.get("output_content", ""))

            # Annotation
            col_r, col_n, col_c, col_s = st.columns([1, 2, 1.5, 0.8])
            with col_r:
                current = annotation["rating"] if annotation else None
                opts = ["good", "bad"]
                idx = opts.index(current) if current in opts else None
                rating = st.radio("Rate", opts, index=idx, key=f"r_{trace['id']}", horizontal=True, label_visibility="collapsed")
            with col_n:
                notes = st.text_input("Notes", value=annotation["notes"] if annotation else "", key=f"n_{trace['id']}", label_visibility="collapsed", placeholder="Notes...")
            with col_c:
                cat = ""
                if rating == "bad":
                    cat = st.text_input("Category", value=annotation["failure_category"] if annotation else "", key=f"c_{trace['id']}", label_visibility="collapsed", placeholder="Failure type")
            with col_s:
                if st.button("Save", key=f"s_{trace['id']}"):
                    if rating:
                        store.save_annotation(Annotation(trace_id=trace["id"], rating=rating, notes=notes, failure_category=cat, annotator="user").model_dump())
                        st.rerun()

            st.markdown("---")

    # === RIGHT: Metrics ===
    with col_right:
        if selected_session and traces:
            session_data = next((s for s in sessions if s["session_id"] == selected_session), None)
            if session_data:
                c1, c2 = st.columns(2)
                c1.metric("Traces", session_data["trace_count"])
                c2.metric("Tokens", session_data["total_tokens"] or 0)
                c1.metric("OK", session_data["success_count"])
                c2.metric("Err", session_data["error_count"])

            total_in = sum(t.get("input_tokens", 0) for t in traces)
            total_out = sum(t.get("output_tokens", 0) for t in traces)
            avg_lat = sum(t.get("latency_ms", 0) for t in traces) / len(traces)

            st.markdown("---")
            c1, c2 = st.columns(2)
            c1.metric("In tok", total_in)
            c2.metric("Out tok", total_out)
            st.metric("Avg latency", f"{avg_lat:.0f}ms")

            good = sum(1 for t in traces if store.get_annotation(t["id"]) and store.get_annotation(t["id"])["rating"] == "good")
            bad = sum(1 for t in traces if store.get_annotation(t["id"]) and store.get_annotation(t["id"])["rating"] == "bad")

            st.markdown("---")
            c1, c2 = st.columns(2)
            c1.metric("Good", good)
            c2.metric("Bad", bad)
            if good + bad > 0:
                st.metric("Pass%", f"{good/(good+bad)*100:.0f}%")


# =============================================================================
# Page 2: Version Comparison
# =============================================================================
def page_version_comparison():
    st.markdown("## Version Comparison")
    store = get_store()

    all_traces = store.get_traces({})
    prompt_names = list(set(t["prompt_name"] for t in all_traces))

    if not prompt_names:
        st.info("No prompts found.")
        return

    selected_prompt = st.selectbox("Prompt", prompt_names)
    if not selected_prompt:
        return

    versions = store.list_prompt_versions(selected_prompt)
    if len(versions) < 2:
        st.info(f"Need at least 2 versions (found {len(versions)})")
        return

    col1, col2 = st.columns(2)
    with col1:
        opts_a = [f"v{v['version']}: {v.get('description', '')[:25]}" for v in versions]
        idx_a = st.selectbox("Version A", range(len(opts_a)), format_func=lambda x: opts_a[x])
        ver_a = versions[idx_a]
    with col2:
        opts_b = [f"v{v['version']}: {v.get('description', '')[:25]}" for v in versions]
        idx_b = st.selectbox("Version B", range(len(opts_b)), format_func=lambda x: opts_b[x], index=min(1, len(versions)-1))
        ver_b = versions[idx_b]

    col1, col2 = st.columns(2)

    for col, ver in [(col1, ver_a), (col2, ver_b)]:
        with col:
            st.markdown(f"**v{ver['version']}**: {ver.get('description', '')[:40]}")
            st.text_area("Template", ver["template"], height=120, disabled=True, key=f"t_{ver['version']}")

            traces = [t for t in all_traces if t["prompt_name"] == selected_prompt and t["prompt_version"] == ver["version"]]
            good = sum(1 for t in traces if store.get_annotation(t["id"]) and store.get_annotation(t["id"])["rating"] == "good")
            bad = sum(1 for t in traces if store.get_annotation(t["id"]) and store.get_annotation(t["id"])["rating"] == "bad")

            c1, c2 = st.columns(2)
            c1.metric("Traces", len(traces))
            c2.metric("Pass%", f"{good/(good+bad)*100:.0f}%" if good+bad > 0 else "N/A")


# =============================================================================
# Page 3: Failure Analysis
# =============================================================================
def page_failure_analysis():
    st.markdown("## Failure Analysis")
    store = get_store()

    col1, col2 = st.columns(2)
    with col1:
        all_traces = store.get_traces({})
        prompt_names = list(set(t["prompt_name"] for t in all_traces))
        selected_prompt = st.selectbox("Prompt", ["All"] + prompt_names, key="fa_prompt")
    with col2:
        days_back = st.number_input("Days", min_value=1, max_value=365, value=30)

    filters = {}
    if selected_prompt != "All":
        filters["prompt_name"] = selected_prompt
    filters["start_date"] = datetime.now() - timedelta(days=days_back)

    traces = store.get_traces(filters)
    bad_traces = []
    for trace in traces:
        ann = store.get_annotation(trace["id"])
        if ann and ann["rating"] == "bad":
            trace["annotation"] = ann
            bad_traces.append(trace)

    st.metric("Failures", len(bad_traces))

    if not bad_traces:
        st.info("No failures found")
        return

    categories = {}
    for trace in bad_traces:
        cat = trace["annotation"].get("failure_category", "Uncategorized") or "Uncategorized"
        categories.setdefault(cat, []).append(trace)

    for cat, cat_traces in sorted(categories.items(), key=lambda x: -len(x[1])):
        pct = len(cat_traces) / len(bad_traces) * 100
        with st.expander(f"{cat} ({len(cat_traces)} - {pct:.0f}%)"):
            for trace in cat_traces[:3]:
                st.markdown(f"**{trace['id'][:8]}**: {trace['annotation'].get('notes', '')[:50]}")
                st.caption(trace.get("output_content", "")[:150])


# =============================================================================
# Main
# =============================================================================
def main():
    st.set_page_config(page_title="LLM Eval", layout="wide", initial_sidebar_state="expanded")
    st.markdown(COMPACT_CSS, unsafe_allow_html=True)

    st.sidebar.markdown("### LLM Eval")

    import os
    default_db = os.environ.get("LLM_EVAL_DB_PATH", "traces.db")
    db_path = st.sidebar.text_input("DB Path", value=default_db, key="db_input")
    if db_path:
        os.environ["LLM_EVAL_DB_PATH"] = db_path

    page = st.sidebar.radio("Page", ["Sessions", "Versions", "Failures"], label_visibility="collapsed")

    store = get_store()
    sessions = store.get_sessions()
    c1, c2 = st.sidebar.columns(2)
    c1.metric("Sessions", len(sessions))
    c2.metric("Traces", sum(s["trace_count"] for s in sessions))

    if page == "Sessions":
        page_session_explorer()
    elif page == "Versions":
        page_version_comparison()
    elif page == "Failures":
        page_failure_analysis()


if __name__ == "__main__":
    main()
