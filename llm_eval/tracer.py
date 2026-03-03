"""LangChain callback handler for tracing LLM calls."""

import threading
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from .models import Trace
from .prompts import PromptRegistry
from .store import TraceStore


@dataclass
class CallContext:
    """Context for a pending LLM call."""

    run_id: str
    prompt_name: str
    prompt_version: int
    input_messages: list[dict[str, Any]]
    start_time: float


class LLMTracer(BaseCallbackHandler):
    """LangChain callback handler that traces LLM calls to SQLite.

    This tracer captures LLM invocations, including inputs, outputs, tokens,
    latency, and errors. All traces are stored via TraceStore for later analysis.

    Usage:
        tracer = LLMTracer(db_path="traces.db", project="my_project")
        tracer.set_prompt_context("my_prompt")
        llm = get_llm(callbacks=[tracer])
        response = llm.invoke(messages)
    """

    def __init__(self, db_path: str, project: str, session_id: str | None = None):
        """Initialize the tracer.

        Args:
            db_path: Path to SQLite database file.
            project: Project identifier for grouping traces.
            session_id: Optional session ID. If not provided, a UUID is generated.
        """
        super().__init__()
        self.db_path = db_path
        self.project = project
        self.session_id = session_id or str(uuid4())

        self._store = TraceStore(db_path)
        self._registry = PromptRegistry(db_path)

        # Thread-safe tracking of pending LLM calls
        self._pending: dict[str, CallContext] = {}
        self._lock = threading.Lock()

        # Current prompt context (must be set before LLM calls)
        self._prompt_name: str | None = None
        self._prompt_version: int | None = None

    def new_session(self, session_id: str | None = None) -> str:
        """Start a new session.

        Args:
            session_id: Optional session ID. If not provided, a UUID is generated.

        Returns:
            The new session ID.
        """
        self.session_id = session_id or str(uuid4())
        return self.session_id

    def set_prompt_context(self, name: str, version: int | None = None) -> None:
        """Set which prompt version the next LLM call uses.

        This method MUST be called before any LLM invocation. If not called,
        on_llm_start will raise an error.

        Args:
            name: The prompt name registered in PromptRegistry.
            version: Specific version number, or None for latest version.
        """
        # Validate that the prompt exists
        prompt = self._registry.get(name, version)
        if prompt is None:
            raise ValueError(f"Prompt '{name}' not found in registry")

        self._prompt_name = name
        self._prompt_version = prompt.version if hasattr(prompt, 'version') else prompt['version']

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Handle the start of an LLM call.

        Records the start time and input messages for later use in on_llm_end.

        Args:
            serialized: Serialized LLM configuration.
            prompts: List of prompt strings sent to the LLM.
            run_id: Unique identifier for this LLM run.
            **kwargs: Additional keyword arguments (may include messages).

        Raises:
            RuntimeError: If set_prompt_context() was not called before this LLM call.
        """
        if self._prompt_name is None or self._prompt_version is None:
            raise RuntimeError(
                "set_prompt_context() must be called before LLM invocation. "
                "No prompt context has been set."
            )

        # Extract input messages from kwargs or prompts
        messages = kwargs.get("messages", [])
        if messages:
            # Convert BaseMessage objects to dicts if needed
            input_messages = []
            for msg in messages:
                if hasattr(msg, "model_dump"):
                    input_messages.append(msg.model_dump())
                elif hasattr(msg, "dict"):
                    input_messages.append(msg.dict())
                elif isinstance(msg, dict):
                    input_messages.append(msg)
                else:
                    input_messages.append({"content": str(msg)})
        else:
            # Fallback to prompts list
            input_messages = [{"role": "user", "content": p} for p in prompts]

        # Create call context and store in pending dict
        run_id_str = str(run_id)
        context = CallContext(
            run_id=run_id_str,
            prompt_name=self._prompt_name,
            prompt_version=self._prompt_version,
            input_messages=input_messages,
            start_time=time.time(),
        )

        with self._lock:
            self._pending[run_id_str] = context
