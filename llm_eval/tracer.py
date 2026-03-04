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

    def _normalize_message(self, msg: Any) -> dict[str, Any]:
        """Convert a message to dict with standard 'role' field.

        LangChain uses 'type' field (system, human, ai) while the dashboard
        expects 'role' field (system, user, assistant). This method normalizes
        the message format.

        Args:
            msg: A message object (LangChain BaseMessage, dict, or string).

        Returns:
            Dictionary with 'role' and 'content' fields.
        """
        if hasattr(msg, "model_dump"):
            d = msg.model_dump()
        elif hasattr(msg, "dict"):
            d = msg.dict()
        elif isinstance(msg, dict):
            d = dict(msg)
        else:
            return {"role": "user", "content": str(msg)}

        # Map LangChain 'type' to standard 'role' if needed
        if "type" in d and "role" not in d:
            type_to_role = {"system": "system", "human": "user", "ai": "assistant"}
            d["role"] = type_to_role.get(d["type"], "user")

        return d

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
            # Convert BaseMessage objects to dicts with normalized 'role' field
            input_messages = [self._normalize_message(msg) for msg in messages]
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

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Handle the completion of an LLM call.

        Extracts output content, token usage, and model info from the response,
        calculates latency, and saves the complete trace to storage.

        Args:
            response: The LLM response containing generations and metadata.
            run_id: Unique identifier matching the on_llm_start call.
            **kwargs: Additional keyword arguments.
        """
        run_id_str = str(run_id)

        # Retrieve and remove the pending context
        with self._lock:
            context = self._pending.pop(run_id_str, None)

        if context is None:
            # This shouldn't happen in normal operation
            return

        # Calculate latency
        latency_ms = int((time.time() - context.start_time) * 1000)

        # Extract output content from response
        output_content = ""
        if response.generations and response.generations[0]:
            generation = response.generations[0][0]
            if hasattr(generation, "text"):
                output_content = generation.text
            elif hasattr(generation, "message") and hasattr(generation.message, "content"):
                output_content = generation.message.content

        # Extract token usage from llm_output or generation metadata
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        model_name = ""

        # Try llm_output first (common location for token usage)
        if response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})
            if token_usage:
                input_tokens = token_usage.get("prompt_tokens", 0)
                output_tokens = token_usage.get("completion_tokens", 0)
                total_tokens = token_usage.get("total_tokens", 0)
            model_name = response.llm_output.get("model_name", "")

        # Try usage_metadata on the generation (LangChain chat models)
        if response.generations and response.generations[0]:
            generation = response.generations[0][0]
            if hasattr(generation, "message"):
                msg = generation.message
                # usage_metadata is common in newer LangChain versions
                if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                    usage = msg.usage_metadata
                    input_tokens = getattr(usage, "input_tokens", 0) or usage.get("input_tokens", 0) if isinstance(usage, dict) else getattr(usage, "input_tokens", 0)
                    output_tokens = getattr(usage, "output_tokens", 0) or usage.get("output_tokens", 0) if isinstance(usage, dict) else getattr(usage, "output_tokens", 0)
                    total_tokens = input_tokens + output_tokens
                # response_metadata may contain model info
                if hasattr(msg, "response_metadata") and msg.response_metadata:
                    if not model_name:
                        model_name = msg.response_metadata.get("model_name", "") or msg.response_metadata.get("model", "")

        # Create and save the trace
        trace = Trace(
            project=self.project,
            session_id=self.session_id,
            prompt_name=context.prompt_name,
            prompt_version=context.prompt_version,
            input_messages=context.input_messages,
            output_content=output_content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            model_name=model_name,
            latency_ms=latency_ms,
            status="success",
        )

        self._store.save_trace(trace.model_dump())

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Handle an error during an LLM call.

        Saves a partial trace with error information and status="error".
        Per design decision, we store partial traces with error info rather than
        skipping failed calls.

        Args:
            error: The exception that occurred during the LLM call.
            run_id: Unique identifier matching the on_llm_start call.
            **kwargs: Additional keyword arguments.
        """
        run_id_str = str(run_id)

        # Retrieve and remove the pending context
        with self._lock:
            context = self._pending.pop(run_id_str, None)

        if context is None:
            # This shouldn't happen in normal operation
            return

        # Calculate latency up to the error
        latency_ms = int((time.time() - context.start_time) * 1000)

        # Create and save partial trace with error info
        trace = Trace(
            project=self.project,
            session_id=self.session_id,
            prompt_name=context.prompt_name,
            prompt_version=context.prompt_version,
            input_messages=context.input_messages,
            output_content="",
            error=str(error),
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            model_name="",
            latency_ms=latency_ms,
            status="error",
        )

        self._store.save_trace(trace.model_dump())
