"""Pydantic data models for the LLM evaluation framework."""

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Prompt(BaseModel):
    """Represents a versioned prompt template in the registry."""

    id: int | None = None
    name: str
    version: int = 1
    template: str
    description: str = ""
    template_hash: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


class Trace(BaseModel):
    """Represents a single LLM invocation trace."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    project: str
    session_id: str
    prompt_name: str
    prompt_version: int
    input_messages: list[dict[str, Any]] = Field(default_factory=list)
    output_content: str = ""
    error: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model_name: str = ""
    latency_ms: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: Literal["success", "error"] = "success"
    created_at: datetime = Field(default_factory=datetime.now)


class Annotation(BaseModel):
    """Represents a human annotation on a trace."""

    id: int | None = None
    trace_id: str
    rating: Literal["good", "bad"]
    notes: str = ""
    failure_category: str = ""
    annotator: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
