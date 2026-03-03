"""Streamlit dashboard for LLM Eval trace viewing and annotation.

Run with: streamlit run llm_eval/dashboard.py -- --db-path traces.db

Pages:
1. Session Explorer - Browse sessions, view traces, annotate
2. Version Comparison - Compare prompt versions side-by-side
3. Failure Analysis - LLM-powered clustering of failures
"""

import json
import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path

# Add parent to path for imports when running directly
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_eval.store import TraceStore
from llm_eval.models import Annotation


def get_store() -> TraceStore:
    """Get or create the TraceStore instance."""
    # Check for command line argument or environment variable
    import os

    db_path = os.environ.get("LLM_EVAL_DB_PATH", "traces.db")

    # Also check command line args
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv):
            if arg == "--db-path" and i + 1 < len(sys.argv):
                db_path = sys.argv[i + 1]
                break
            # Also support --db-path=value format
            if arg.startswith("--db-path="):
                db_path = arg.split("=", 1)[1]
                break

    if "store" not in st.session_state or st.session_state.get("db_path") != db_path:
        st.session_state.store = TraceStore(db_path)
        st.session_state.db_path = db_path
    return st.session_state.store


def format_messages(messages: list) -> str:
    """Format messages for display."""
    if not messages:
        return "No messages"

    formatted = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, list):
            # Handle multimodal content
            content = " ".join(
                item.get("text", str(item))
                for item in content
                if isinstance(item, dict)
            )
        formatted.append(f"**{role.upper()}**: {content}")
    return "\n\n".join(formatted)


# =============================================================================
# Page 1: Session Explorer
# =============================================================================
def page_session_explorer():
    """Main page - Session browser with trace viewer and annotation."""
    st.title("Session Explorer")

    store = get_store()

    # Get all sessions
    sessions = store.get_sessions()

    if not sessions:
        st.info("No sessions found. Run some traced LLM calls first.")
        return

    # Three-column layout
    col_left, col_middle, col_right = st.columns([1, 2, 1])

    # === LEFT PANEL: Filters & Session List ===
    with col_left:
        st.subheader("Filters")

        # Get unique projects
        projects = list(set(s["project"] for s in sessions))
        selected_project = st.selectbox(
            "Project",
            ["All"] + projects,
            key="filter_project"
        )

        # Get unique prompt names from traces
        all_traces = store.get_traces({})
        prompt_names = list(set(t["prompt_name"] for t in all_traces))
        selected_prompt = st.selectbox(
            "Prompt",
            ["All"] + prompt_names,
            key="filter_prompt"
        )

        # Date range
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            start_date = st.date_input(
                "From",
                value=datetime.now() - timedelta(days=7),
                key="filter_start"
            )
        with col_d2:
            end_date = st.date_input(
                "To",
                value=datetime.now(),
                key="filter_end"
            )

        # Annotation status filter
        annotation_filter = st.selectbox(
            "Annotation Status",
            ["All", "Unannotated", "Good", "Bad"],
            key="filter_annotation"
        )

        st.divider()
        st.subheader("Sessions")

        # Filter sessions
        filtered_sessions = sessions
        if selected_project != "All":
            filtered_sessions = [s for s in filtered_sessions if s["project"] == selected_project]

        # Display session list
        for i, session in enumerate(filtered_sessions[:20]):  # Limit to 20
            session_id = session["session_id"]
            display_name = session_id[:20] + "..." if len(session_id) > 20 else session_id

            # Show session stats
            label = f"{display_name}\n{session['trace_count']} traces | {session['total_tokens'] or 0} tok"

            if st.button(label, key=f"session_{i}", use_container_width=True):
                st.session_state.selected_session = session_id

    # === MIDDLE PANEL: Conversation Thread ===
    with col_middle:
        st.subheader("Conversation Thread")

        selected_session = st.session_state.get("selected_session")

        if not selected_session:
            st.info("Select a session from the left panel")
            return

        # Get traces for selected session
        traces = store.get_traces({"session_id": selected_session})

        if not traces:
            st.warning("No traces in this session")
            return

        # Sort by created_at
        traces.sort(key=lambda x: x["created_at"])

        # Display each trace as a card
        for i, trace in enumerate(traces):
            with st.container():
                # Card header
                status_icon = "✅" if trace["status"] == "success" else "❌"
                st.markdown(f"### {status_icon} Trace {i+1} - {trace['prompt_name']} v{trace['prompt_version']}")

                # Input messages (collapsible)
                with st.expander("Input Messages", expanded=False):
                    st.markdown(format_messages(trace.get("input_messages", [])))

                # Output
                st.markdown("**Output:**")
                if trace["status"] == "error":
                    st.error(f"Error: {trace.get('error', 'Unknown error')}")
                else:
                    st.markdown(trace.get("output_content", "No output"))

                # Annotation form
                st.markdown("---")
                annotation = store.get_annotation(trace["id"])

                col_a1, col_a2 = st.columns([1, 2])
                with col_a1:
                    current_rating = annotation["rating"] if annotation else None
                    rating_options = ["good", "bad"]
                    rating_index = rating_options.index(current_rating) if current_rating in rating_options else None

                    new_rating = st.radio(
                        "Rating",
                        rating_options,
                        index=rating_index,
                        key=f"rating_{trace['id']}",
                        horizontal=True
                    )

                with col_a2:
                    current_notes = annotation["notes"] if annotation else ""
                    new_notes = st.text_input(
                        "Notes",
                        value=current_notes,
                        key=f"notes_{trace['id']}"
                    )

                # Failure category (only show if rating is bad)
                current_category = annotation["failure_category"] if annotation else ""
                if new_rating == "bad":
                    new_category = st.text_input(
                        "Failure Category",
                        value=current_category,
                        key=f"category_{trace['id']}"
                    )
                else:
                    new_category = ""

                # Save button
                if st.button("Save Annotation", key=f"save_{trace['id']}"):
                    if new_rating:
                        ann = Annotation(
                            trace_id=trace["id"],
                            rating=new_rating,
                            notes=new_notes,
                            failure_category=new_category,
                            annotator="dashboard_user"
                        )
                        store.save_annotation(ann.model_dump())
                        st.success("Saved!")
                        st.rerun()

                st.divider()

                # Track selected trace for right panel
                if st.button("Show Details", key=f"details_{trace['id']}"):
                    st.session_state.selected_trace = trace

    # === RIGHT PANEL: Metrics ===
    with col_right:
        st.subheader("Metrics")

        if selected_session:
            # Session summary
            session_data = next((s for s in sessions if s["session_id"] == selected_session), None)
            if session_data:
                st.metric("Total Traces", session_data["trace_count"])
                st.metric("Total Tokens", session_data["total_tokens"] or 0)
                st.metric("Success", session_data["success_count"])
                st.metric("Errors", session_data["error_count"])

        st.divider()

        # Selected trace details
        selected_trace = st.session_state.get("selected_trace")
        if selected_trace:
            st.subheader("Selected Trace")
            st.text(f"ID: {selected_trace['id'][:8]}...")
            st.text(f"Model: {selected_trace.get('model_name', 'N/A')}")
            st.text(f"Input: {selected_trace.get('input_tokens', 0)} tok")
            st.text(f"Output: {selected_trace.get('output_tokens', 0)} tok")
            st.text(f"Latency: {selected_trace.get('latency_ms', 0)} ms")
            st.text(f"Prompt: v{selected_trace.get('prompt_version', '?')}")


# =============================================================================
# Page 2: Version Comparison
# =============================================================================
def page_version_comparison():
    """Compare two prompt versions side by side."""
    st.title("Version Comparison")

    store = get_store()

    # Get all unique prompt names
    all_traces = store.get_traces({})
    prompt_names = list(set(t["prompt_name"] for t in all_traces))

    if not prompt_names:
        st.info("No prompts found.")
        return

    # Select prompt
    selected_prompt = st.selectbox("Select Prompt", prompt_names)

    if not selected_prompt:
        return

    # Get versions for this prompt
    versions = store.list_prompt_versions(selected_prompt)

    if len(versions) < 2:
        st.info(f"Only {len(versions)} version(s) found. Need at least 2 for comparison.")
        return

    # Select two versions
    col1, col2 = st.columns(2)

    with col1:
        v1_options = [f"v{v['version']}: {v.get('description', '')[:30]}" for v in versions]
        v1_idx = st.selectbox("Version A", range(len(v1_options)), format_func=lambda x: v1_options[x])
        version_a = versions[v1_idx]

    with col2:
        v2_options = [f"v{v['version']}: {v.get('description', '')[:30]}" for v in versions]
        v2_idx = st.selectbox("Version B", range(len(v2_options)), format_func=lambda x: v2_options[x], index=min(1, len(versions)-1))
        version_b = versions[v2_idx]

    st.divider()

    # Side by side comparison
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"Version {version_a['version']}")
        st.caption(version_a.get("description", "No description"))
        st.text_area("Template", version_a["template"], height=200, disabled=True, key="template_a")

        # Get traces for this version
        traces_a = [t for t in all_traces if t["prompt_name"] == selected_prompt and t["prompt_version"] == version_a["version"]]

        # Calculate stats
        good_count = sum(1 for t in traces_a if store.get_annotation(t["id"]) and store.get_annotation(t["id"])["rating"] == "good")
        bad_count = sum(1 for t in traces_a if store.get_annotation(t["id"]) and store.get_annotation(t["id"])["rating"] == "bad")
        total_annotated = good_count + bad_count

        st.metric("Traces", len(traces_a))
        if total_annotated > 0:
            pass_rate = good_count / total_annotated * 100
            st.metric("Pass Rate", f"{pass_rate:.1f}%")
        else:
            st.metric("Pass Rate", "N/A")

    with col2:
        st.subheader(f"Version {version_b['version']}")
        st.caption(version_b.get("description", "No description"))
        st.text_area("Template", version_b["template"], height=200, disabled=True, key="template_b")

        # Get traces for this version
        traces_b = [t for t in all_traces if t["prompt_name"] == selected_prompt and t["prompt_version"] == version_b["version"]]

        # Calculate stats
        good_count = sum(1 for t in traces_b if store.get_annotation(t["id"]) and store.get_annotation(t["id"])["rating"] == "good")
        bad_count = sum(1 for t in traces_b if store.get_annotation(t["id"]) and store.get_annotation(t["id"])["rating"] == "bad")
        total_annotated = good_count + bad_count

        st.metric("Traces", len(traces_b))
        if total_annotated > 0:
            pass_rate = good_count / total_annotated * 100
            st.metric("Pass Rate", f"{pass_rate:.1f}%")
        else:
            st.metric("Pass Rate", "N/A")

    # Sample outputs
    st.divider()
    st.subheader("Sample Outputs")

    col1, col2 = st.columns(2)

    with col1:
        st.caption(f"Version {version_a['version']} samples")
        for trace in traces_a[:3]:
            with st.expander(f"Trace {trace['id'][:8]}..."):
                st.markdown(trace.get("output_content", "No output")[:500])

    with col2:
        st.caption(f"Version {version_b['version']} samples")
        for trace in traces_b[:3]:
            with st.expander(f"Trace {trace['id'][:8]}..."):
                st.markdown(trace.get("output_content", "No output")[:500])


# =============================================================================
# Page 3: Failure Analysis
# =============================================================================
def page_failure_analysis():
    """LLM-powered clustering of failures."""
    st.title("Failure Analysis")

    store = get_store()

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        all_traces = store.get_traces({})
        prompt_names = list(set(t["prompt_name"] for t in all_traces))
        selected_prompt = st.selectbox("Prompt", ["All"] + prompt_names, key="fa_prompt")

    with col2:
        days_back = st.number_input("Days back", min_value=1, max_value=365, value=30)

    with col3:
        min_failures = st.number_input("Min failures to analyze", min_value=1, max_value=100, value=5)

    # Get failed traces with annotations
    filters = {}
    if selected_prompt != "All":
        filters["prompt_name"] = selected_prompt
    filters["start_date"] = datetime.now() - timedelta(days=days_back)

    traces = store.get_traces(filters)

    # Filter to only bad-rated traces
    bad_traces = []
    for trace in traces:
        annotation = store.get_annotation(trace["id"])
        if annotation and annotation["rating"] == "bad":
            trace["annotation"] = annotation
            bad_traces.append(trace)

    st.metric("Total Failures Found", len(bad_traces))

    if len(bad_traces) < min_failures:
        st.warning(f"Not enough failures ({len(bad_traces)}) to analyze. Need at least {min_failures}.")
        return

    st.divider()

    # Manual category summary (from existing annotations)
    st.subheader("Failure Categories (from annotations)")

    categories = {}
    for trace in bad_traces:
        cat = trace["annotation"].get("failure_category", "Uncategorized") or "Uncategorized"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(trace)

    for cat, cat_traces in sorted(categories.items(), key=lambda x: -len(x[1])):
        pct = len(cat_traces) / len(bad_traces) * 100
        with st.expander(f"{cat} ({len(cat_traces)} - {pct:.1f}%)"):
            for trace in cat_traces[:5]:
                st.markdown(f"**Trace {trace['id'][:8]}...** - {trace['annotation'].get('notes', 'No notes')}")
                st.caption(trace.get("output_content", "")[:200])

    st.divider()

    # LLM Analysis button
    st.subheader("LLM-Powered Analysis")
    st.caption("Use an LLM to automatically cluster and categorize failures")

    if st.button("Analyze Failures with LLM", type="primary"):
        st.info("LLM analysis feature coming soon. For now, use manual categorization in annotations.")

        # TODO: Implement LLM-powered clustering
        # This would:
        # 1. Batch failures into chunks
        # 2. Send to LLM with prompt asking to categorize
        # 3. Display clustered results
        # 4. Allow saving categories back to annotations


# =============================================================================
# Main App
# =============================================================================
def main():
    st.set_page_config(
        page_title="LLM Eval Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Sidebar navigation
    st.sidebar.title("LLM Eval")
    st.sidebar.caption("Evaluation & Tracing Dashboard")

    # Database path input
    import os
    default_db = os.environ.get("LLM_EVAL_DB_PATH", "traces.db")
    db_path = st.sidebar.text_input("Database Path", value=default_db, key="db_path_input")

    # Update environment so get_store picks it up
    if db_path:
        os.environ["LLM_EVAL_DB_PATH"] = db_path

    st.sidebar.caption(f"Current: {db_path}")

    st.sidebar.divider()

    page = st.sidebar.radio(
        "Navigation",
        ["Session Explorer", "Version Comparison", "Failure Analysis"],
        label_visibility="collapsed"
    )

    st.sidebar.divider()

    # Database info
    store = get_store()
    sessions = store.get_sessions()
    st.sidebar.metric("Total Sessions", len(sessions))
    st.sidebar.metric("Total Traces", sum(s["trace_count"] for s in sessions))

    # Route to page
    if page == "Session Explorer":
        page_session_explorer()
    elif page == "Version Comparison":
        page_version_comparison()
    elif page == "Failure Analysis":
        page_failure_analysis()


if __name__ == "__main__":
    main()
