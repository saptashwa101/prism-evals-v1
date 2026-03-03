# LLM Eval: Standalone Evaluation & Tracing System

## Context
Building a portable evaluation system for LLM outputs. First integration point is PRISM Phase 3 synthesis, but the system must remain independent for use across any project.

## Design Decisions
- **Error handling**: Store partial traces with error info (don't skip failed calls)
- **Prompt context**: Required - error if `set_prompt_context()` not called before LLM invocation
- **Concurrency**: Thread-safe for parallel LLM calls (batch processing scenarios)

## Package Structure
```
phase_3_evals/              # Repo root
├── pyproject.toml          # Package config, dependencies
├── README.md
├── llm_eval/
│   ├── __init__.py         # Public API exports
│   ├── models.py           # Pydantic data models
│   ├── store.py            # Thread-safe SQLite storage
│   ├── prompts.py          # PromptRegistry class
│   ├── tracer.py           # LangChain callback handler
│   └── dashboard.py        # Streamlit annotation UI
└── tests/
    └── test_tracer.py      # Core functionality tests
```

## Data Models

### Prompt
| Field | Type | Description |
|-------|------|-------------|
| id | int | Primary key |
| name | str | Logical name (e.g., "synthesis_report") |
| version | int | Auto-increment per name |
| template | str | Full prompt text |
| description | str | Changelog for this version |
| template_hash | str | SHA256 for dedup detection |
| created_at | datetime | |

### Trace
| Field | Type | Description |
|-------|------|-------------|
| id | str | UUID |
| project | str | Project identifier (e.g., "prism_phase3") |
| session_id | str | Groups related calls |
| prompt_name | str | Links to prompt registry |
| prompt_version | int | Version used for this call |
| input_messages | JSON | Messages sent to LLM |
| output_content | str | LLM response text |
| error | str | Error message if call failed (nullable) |
| input_tokens | int | From usage_metadata |
| output_tokens | int | From usage_metadata |
| total_tokens | int | |
| model_name | str | From response_metadata |
| latency_ms | int | Call duration |
| metadata | JSON | Arbitrary context |
| status | str | "success" or "error" |
| created_at | datetime | |

### Annotation
| Field | Type | Description |
|-------|------|-------------|
| id | int | Primary key |
| trace_id | str | FK to Trace |
| rating | str | "good" / "bad" |
| notes | str | Free-form observations |
| failure_category | str | For axial coding |
| annotator | str | Who annotated |
| created_at | datetime | |

## Core Components

### PromptRegistry (prompts.py)
```python
class PromptRegistry:
    def register(name: str, template: str, description: str = None) -> Prompt:
        """
        Register a prompt. If template unchanged from latest version, returns existing.
        If changed, creates new version with incremented number.
        First registration of a name starts at v1.
        """

    def get(name: str, version: int = None) -> Prompt:
        """Get prompt by name. Returns latest if version not specified."""

    def list_versions(name: str) -> List[Prompt]:
        """List all versions of a prompt."""
```

### LLMTracer (tracer.py)
LangChain callback handler that:
- Captures `on_llm_start` (input messages, start time)
- Captures `on_llm_end` (output, tokens from usage_metadata, latency)
- Captures `on_llm_error` (error info, partial trace)
- Stores trace to SQLite via store.py

```python
class LLMTracer(BaseCallbackHandler):
    def __init__(self, db_path: str, project: str, session_id: str = None):
        """
        session_id: Optional. If not provided, auto-generates UUID.
        """

    def new_session(self, session_id: str = None):
        """Start a new session. Auto-generates UUID if not provided."""

    def set_prompt_context(self, name: str, version: int = None):
        """Set which prompt version the next call uses. REQUIRED before LLM calls."""
```

### Usage Example
```python
from llm_eval import LLMTracer, PromptRegistry

registry = PromptRegistry("traces.db")
registry.register("synthesis_report", SYNTHESIS_SYSTEM_PROMPT, "Initial prompt")

# Auto session (UUID generated)
tracer = LLMTracer(db_path="traces.db", project="prism_phase3")

# Or explicit session name for tracking experiments
tracer = LLMTracer(db_path="traces.db", project="prism_phase3", session_id="patent_US123_run1")

tracer.set_prompt_context("synthesis_report")

llm = get_llm(callbacks=[tracer])
response = llm.invoke(messages)  # automatically traced

# Start new session mid-notebook
tracer.new_session("patent_US456_analysis")
```

## Dashboard (dashboard.py)

Run with: `streamlit run llm_eval/dashboard.py`

### Page 1: Session Explorer (main page)
```
┌─────────────────┬────────────────────────────────────┬─────────────┐
│  SESSION LIST   │       CONVERSATION THREAD          │   METRICS   │
│  (left panel)   │         (middle panel)             │   (right)   │
├─────────────────┼────────────────────────────────────┼─────────────┤
│ Filters:        │ ┌──────────────────────────────┐   │ Session:    │
│ - Project       │ │ [User] Input message...      │   │ - 5 calls   │
│ - Prompt        │ └──────────────────────────────┘   │ - 2.3k tok  │
│ - Date range    │ ┌──────────────────────────────┐   │ - 4.2s      │
│ - Status        │ │ [LLM] Response...            │   │             │
│                 │ │ Rating: good/bad             │   │ Selected:   │
│ Sessions:       │ │ Notes: ...                   │   │ - 450 tok   │
│ > session_abc   │ └──────────────────────────────┘   │ - gpt-4     │
│   session_def   │ ┌──────────────────────────────┐   │ - 1.2s      │
│   session_ghi   │ │ [User] Next input...         │   │ - v2        │
│                 │ └──────────────────────────────┘   │             │
└─────────────────┴────────────────────────────────────┴─────────────┘
```
- **Left**: Filterable session list, click to select
- **Middle**: Full conversation thread, each call is a card with input/output and inline annotation
- **Right**: Metrics summary for session + details for focused call

### Page 2: Version Comparison
- Select prompt name, pick two versions
- Side-by-side: version description, sample outputs, pass rates

### Page 3: Failure Analysis
- LLM-powered clustering of annotated failures
- Returns categorized failure patterns with examples

## Integration
Install in any project:
```bash
pip install -e /path/to/phase_3_evals
```

Then:
```python
from llm_eval import LLMTracer, PromptRegistry
```
