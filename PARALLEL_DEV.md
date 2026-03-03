# Parallel Development Setup

## Worktree Locations
All worktrees are inside `phase_3_evals/.worktrees/`:
```
Main repo:     phase_3_evals/                    (branch: main)
Models:        phase_3_evals/.worktrees/models   (branch: feature/models)
Store:         phase_3_evals/.worktrees/store    (branch: feature/store)
```

## Wave 1: Run these two in parallel

### Terminal 1: Models
```bash
cd /Users/L122739/Library/CloudStorage/OneDrive-EliLillyandCompany/Desktop/evals/phase_3_evals/.worktrees/models
claude
```
Then paste:
```
Implement llm_eval/models.py based on DESIGN.md.

Create Pydantic models for:
1. Prompt - with fields: id (int), name (str), version (int), template (str), description (str), template_hash (str), created_at (datetime)
2. Trace - with fields: id (str/UUID), project (str), session_id (str), prompt_name (str), prompt_version (int), input_messages (list), output_content (str), error (str|None), input_tokens (int), output_tokens (int), total_tokens (int), model_name (str), latency_ms (int), metadata (dict), status (str: "success"|"error"), created_at (datetime)
3. Annotation - with fields: id (int), trace_id (str), rating (str: "good"|"bad"), notes (str), failure_category (str), annotator (str), created_at (datetime)

Use Pydantic v2 syntax. Add sensible defaults where appropriate.
Commit when done with message describing what was implemented.
```

### Terminal 2: Store
```bash
cd /Users/L122739/Library/CloudStorage/OneDrive-EliLillyandCompany/Desktop/evals/phase_3_evals/.worktrees/store
claude
```
Then paste:
```
Implement llm_eval/store.py based on DESIGN.md.

Create a TraceStore class with thread-safe SQLite storage:
- Use threading.Lock for write operations
- Use threading.local() for per-thread connections
- Auto-create schema on init (tables for prompts, traces, annotations)

Methods needed:
- __init__(self, db_path: str)
- save_prompt(prompt: dict) -> int
- get_prompt(name: str, version: int = None) -> dict | None
- get_latest_prompt(name: str) -> dict | None
- list_prompt_versions(name: str) -> list[dict]
- save_trace(trace: dict) -> str
- get_trace(trace_id: str) -> dict | None
- get_traces(filters: dict) -> list[dict]  # filter by project, session_id, prompt_name, date range
- get_sessions(project: str = None) -> list[dict]  # return session summaries
- save_annotation(annotation: dict) -> int
- get_annotation(trace_id: str) -> dict | None

For now, use raw dicts for input/output (the models will be merged later).
Commit when done with message describing what was implemented.
```

---

## After Wave 1: Merge and setup Wave 2

```bash
# From main repo
cd /Users/L122739/Library/CloudStorage/OneDrive-EliLillyandCompany/Desktop/evals/phase_3_evals
git merge feature/models
git merge feature/store

# Create Wave 2 worktrees
git worktree add -b feature/prompts .worktrees/prompts main
git worktree add -b feature/tracer .worktrees/tracer main
```

## Wave 2: Run these two in parallel

### Terminal 1: Prompts
```bash
cd /Users/L122739/Library/CloudStorage/OneDrive-EliLillyandCompany/Desktop/evals/phase_3_evals/.worktrees/prompts
claude
```
Then paste:
```
Implement llm_eval/prompts.py based on DESIGN.md.

Create PromptRegistry class:
- __init__(self, db_path: str) - uses TraceStore internally
- register(name: str, template: str, description: str = None) -> Prompt
  - Hash template with SHA256
  - If hash matches latest version, return existing
  - If different or new, create new version (auto-increment)
- get(name: str, version: int = None) -> Prompt
  - Returns latest if version not specified
- list_versions(name: str) -> list[Prompt]

Import from .models import Prompt and from .store import TraceStore.
Commit when done.
```

### Terminal 2: Tracer
```bash
cd /Users/L122739/Library/CloudStorage/OneDrive-EliLillyandCompany/Desktop/evals/phase_3_evals/.worktrees/tracer
claude
```
Then paste:
```
Implement llm_eval/tracer.py based on DESIGN.md.

Create LLMTracer class extending langchain_core.callbacks.BaseCallbackHandler:
- __init__(self, db_path: str, project: str, session_id: str = None)
  - Auto-generate UUID for session_id if not provided
  - Uses TraceStore internally
- new_session(self, session_id: str = None) - start new session
- set_prompt_context(self, name: str, version: int = None) - REQUIRED before LLM calls

Implement callbacks:
- on_llm_start(serialized, prompts, run_id, ...) - store start time, input messages
- on_llm_end(response, run_id, ...) - extract output, tokens from usage_metadata, calculate latency, save trace
- on_llm_error(error, run_id, ...) - save partial trace with error info

Use thread-safe dict to track pending calls by run_id: {run_id: CallContext}
Raise error if prompt context not set when on_llm_start fires.

Import from .models, .store, .prompts as needed.
Commit when done.
```

---

## After Wave 2: Merge and setup Wave 3

```bash
cd /Users/L122739/Library/CloudStorage/OneDrive-EliLillyandCompany/Desktop/evals/phase_3_evals
git merge feature/prompts
git merge feature/tracer

git worktree add -b feature/dashboard .worktrees/dashboard main
```

## Wave 3: Dashboard

```bash
cd /Users/L122739/Library/CloudStorage/OneDrive-EliLillyandCompany/Desktop/evals/phase_3_evals/.worktrees/dashboard
claude
```
Then paste:
```
Implement llm_eval/dashboard.py - a Streamlit app.

Page 1: Session Explorer (main page, 3-column layout)
- Left (st.sidebar or column): Filters (project, prompt, date range, annotation status) + session list
- Middle: Conversation thread for selected session - each trace as a card showing input/output with inline annotation form
- Right: Metrics panel (session totals + selected trace details)

Page 2: Version Comparison
- Dropdown to select prompt name
- Two version selectors
- Side-by-side comparison with pass rates

Page 3: Failure Analysis
- Filter controls
- Button to trigger LLM analysis of failures
- Display clustered failure categories

Use st.set_page_config(layout="wide"). Import from .store import TraceStore.
Commit when done.
```

---

## Cleanup: After all waves complete

```bash
cd /Users/L122739/Library/CloudStorage/OneDrive-EliLillyandCompany/Desktop/evals/phase_3_evals

# Merge final branch
git merge feature/dashboard

# Remove worktrees
git worktree remove .worktrees/models
git worktree remove .worktrees/store
git worktree remove .worktrees/prompts
git worktree remove .worktrees/tracer
git worktree remove .worktrees/dashboard

# Delete feature branches (now merged)
git branch -d feature/models feature/store feature/prompts feature/tracer feature/dashboard

# Update __init__.py with exports
```

Final `llm_eval/__init__.py`:
```python
from .models import Prompt, Trace, Annotation
from .store import TraceStore
from .prompts import PromptRegistry
from .tracer import LLMTracer

__all__ = ["Prompt", "Trace", "Annotation", "TraceStore", "PromptRegistry", "LLMTracer"]
```
