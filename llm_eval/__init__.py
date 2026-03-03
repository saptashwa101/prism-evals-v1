"""LLM Eval - Standalone evaluation and tracing system for LLM outputs.

This package provides:
- Prompt versioning with auto-increment and changelog descriptions
- Trace storage in SQLite for LLM call tracking
- LangChain callback handler for seamless integration
- Streamlit dashboard for viewing traces and annotating outputs

Example:
    >>> from llm_eval import PromptRegistry, LLMTracer, TraceStore
    >>>
    >>> # Register a prompt
    >>> registry = PromptRegistry("traces.db")
    >>> registry.register("my_prompt", "You are a helpful assistant.", "Initial version")
    >>>
    >>> # Create tracer and attach to LLM
    >>> tracer = LLMTracer(db_path="traces.db", project="my_project")
    >>> tracer.set_prompt_context("my_prompt")
    >>> llm = get_llm(callbacks=[tracer])
    >>> response = llm.invoke(messages)
"""

from llm_eval.models import Prompt, Trace, Annotation
from llm_eval.store import TraceStore
from llm_eval.prompts import PromptRegistry
from llm_eval.tracer import LLMTracer

__all__ = [
    "Prompt",
    "Trace",
    "Annotation",
    "TraceStore",
    "PromptRegistry",
    "LLMTracer",
]

__version__ = "0.1.0"
