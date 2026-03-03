"""Prompt registry for managing versioned prompt templates."""

from .models import Prompt
from .store import TraceStore


class PromptRegistry:
    """Registry for managing versioned prompt templates.

    Uses TraceStore internally for persistence. Provides automatic version
    management with SHA256-based deduplication.
    """

    def __init__(self, db_path: str):
        """Initialize the prompt registry.

        Args:
            db_path: Path to SQLite database file.
        """
        self._store = TraceStore(db_path)
