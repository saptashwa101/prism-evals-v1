# Dashboard V2 Design

**Date**: 2026-03-04
**Status**: Approved
**Author**: Claude

## Overview

Create `llm_eval/dashboard_v2.py` - a new Streamlit dashboard with dark editorial theme for the LLM evaluation framework. Frontend-only implementation with three pages.

## Requirements

1. **Page 1: Session Explorer**
   - View all sessions with filtering (project, prompt, status)
   - Chat-style vertical conversation view per session
   - Show system prompts (collapsed), user inputs, assistant outputs
   - Inline metrics per trace (tokens, latency, model, version)
   - Inline annotation controls (good/bad buttons + notes input)
   - Session-level aggregate metrics

2. **Page 2: Version Comparison**
   - Select prompt name from dropdown
   - Side-by-side comparison of two versions
   - Show: description, template, usage stats (traces, good/bad counts, pass rate)
   - Sample outputs from each version

3. **Page 3: Failure Analysis**
   - Filter failures by prompt and date range
   - List all traces rated "bad" with checkboxes
   - "Analyze with LLM" button (stub implementation)
   - Display categorized failure patterns (placeholder data)

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | Single-file | Simple, matches existing pattern, 3 pages don't warrant multi-file |
| Theme | Dark editorial | User preference, easier on eyes for annotation work |
| Layout | Chat-style vertical | Familiar, scannable for conversation review |
| Annotations | Inline per-message | Quick annotation as you review |
| LLM integration | Stub/placeholder | User will wire up real LLM later |

## Design

### Page 1: Session Explorer Layout

```
┌──────────────────┬────────────────────────────────────────────────────┐
│ SIDEBAR          │ MAIN: Session abc123...                            │
│                  │                                                     │
│ ◉ LLM Eval v2   │ ┌──────────────────────────────────────────────┐   │
│ [Database path]  │ │ METRICS: 5 calls | 2.3k tok | 4.2s | gpt-4  │   │
│                  │ └──────────────────────────────────────────────┘   │
│ FILTERS:         │                                                     │
│ Project [▼]      │ [SYSTEM] You are... (collapsed)                    │
│ Prompt  [▼]      │                                                     │
│ Status  [▼]      │ ┌──────────────────────────────────────────────┐   │
│                  │ │ [USER] Please summarize this text...         │   │
│ SESSIONS:        │ └──────────────────────────────────────────────┘   │
│ > abc123 (5)     │                                                     │
│   def456 (3)     │ ┌──────────────────────────────────────────────┐   │
│   ghi789 (7)     │ │ [ASSISTANT] Here is the summary...           │   │
│                  │ │ in:450 | out:120 | 1.2s | v2                 │   │
│ Stats: 15/45     │ │ [👍 Good] [👎 Bad] [Notes...______] [Save]   │   │
│                  │ └──────────────────────────────────────────────┘   │
│ PAGES:           │                                                     │
│ ◉ Sessions      │                                                     │
│ ○ Versions      │                                                     │
│ ○ Failures      │                                                     │
└──────────────────┴────────────────────────────────────────────────────┘
```

### Page 2: Version Comparison Layout

```
┌───────────────────────────────────────────────────────────────────────┐
│ Prompt: [summarize ▼]                                                  │
│                                                                        │
│ ┌─────────────────────────────┐ ┌─────────────────────────────┐       │
│ │ VERSION A [v1 ▼]            │ │ VERSION B [v2 ▼]            │       │
│ ├─────────────────────────────┤ ├─────────────────────────────┤       │
│ │ "Basic summarization"       │ │ "Improved with persona"     │       │
│ │                             │ │                             │       │
│ │ Template:                   │ │ Template:                   │       │
│ │ ┌─────────────────────────┐ │ │ ┌─────────────────────────┐ │       │
│ │ │ Summarize the...        │ │ │ │ You are an expert...    │ │       │
│ │ └─────────────────────────┘ │ │ └─────────────────────────┘ │       │
│ │                             │ │                             │       │
│ │ Traces: 12                  │ │ Traces: 8                   │       │
│ │ Good: 10 | Bad: 2           │ │ Good: 7 | Bad: 1            │       │
│ │ Pass: 83%                   │ │ Pass: 87%                   │       │
│ └─────────────────────────────┘ └─────────────────────────────┘       │
│                                                                        │
│ SAMPLE OUTPUTS (expandable)                                            │
└───────────────────────────────────────────────────────────────────────┘
```

### Page 3: Failure Analysis Layout

```
┌───────────────────────────────────────────────────────────────────────┐
│ FAILURE ANALYSIS                                                       │
│                                                                        │
│ Prompt: [All ▼]  Days: [30]  [🔍 Analyze with LLM]                    │
│                                                                        │
│ Found: 8 failures                                                      │
│                                                                        │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │ FAILURES TO ANALYZE                                              │   │
│ │ ☑ abc123 - "Output too verbose" - summarize v1                  │   │
│ │ ☑ def456 - "Missed key info" - qa v2                            │   │
│ │ ☐ ghi789 - "Hallucinated" - classify v1                         │   │
│ └─────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │ ANALYSIS RESULTS                                                 │   │
│ │                                                                  │   │
│ │ VERBOSITY (3, 38%) - Over-explains simple requests               │   │
│ │ INCOMPLETENESS (2, 25%) - Missing context extraction             │   │
│ └─────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────┘
```

## Theme: Dark Editorial

```css
/* Color palette */
--bg-base: #0a0a0a;        /* Near black background */
--bg-card: #18181b;        /* Dark zinc cards */
--bg-elevated: #27272a;    /* Elevated surfaces */
--bg-user: #172554;        /* Dark blue for user messages */
--bg-assistant: #14532d;   /* Dark green for assistant messages */
--bg-system: #1c1c1e;      /* Dark gray for system messages */

--text-primary: #fafafa;   /* White text */
--text-secondary: #d4d4d8; /* Light gray */
--text-muted: #71717a;     /* Muted gray */

--accent-blue: #3b82f6;    /* Primary accent */
--accent-green: #22c55e;   /* Good/success */
--accent-red: #ef4444;     /* Bad/error */

--border: #27272a;         /* Subtle borders */
```

## Components

### MessageBubble
Renders a single message (system/user/assistant) with role indicator and content.

### TraceCard
Wraps messages for a trace with:
- System prompt (collapsed expander)
- User message bubble
- Assistant message bubble
- Metrics bar (tokens, latency, model, version)
- Annotation controls (good/bad, notes, save button)

### SessionList
Sidebar list of sessions with:
- Click to select
- Show trace count per session
- Highlight selected

### FilterPanel
Dropdowns for project, prompt name, status filters.

### MetricsBar
Compact inline display of trace/session metrics.

## Data Flow

```
TraceStore (SQLite)
     │
     ├──▶ get_sessions() ──▶ SessionList
     │
     ├──▶ get_traces(session_id) ──▶ TraceCard[]
     │
     ├──▶ get_annotation(trace_id) ──▶ Annotation controls
     │
     ├──▶ save_annotation() ◀── User interaction
     │
     └──▶ list_prompt_versions() ──▶ Version Comparison
```

## Implementation Notes

1. **No new dependencies** - Uses only Streamlit, which is already in pyproject.toml
2. **Reuses existing store** - TraceStore and models from llm_eval package
3. **CSS in markdown** - Custom theme via st.markdown with unsafe_allow_html
4. **Stub for LLM** - `analyze_failures()` function returns placeholder data

## File Structure

```
llm_eval/
├── dashboard.py      # Existing (ignore)
├── dashboard_v2.py   # NEW - this design
├── models.py
├── store.py
├── prompts.py
└── tracer.py
```

## Usage

```bash
# Run the new dashboard
streamlit run llm_eval/dashboard_v2.py

# With custom database
LLM_EVAL_DB_PATH=/path/to/db.db streamlit run llm_eval/dashboard_v2.py
```
