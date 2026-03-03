"""Prompt registry for managing versioned prompt templates."""

import hashlib

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

    def _hash_template(self, template: str) -> str:
        """Compute SHA256 hash of a template string."""
        return hashlib.sha256(template.encode()).hexdigest()

    def register(
        self, name: str, template: str, description: str | None = None
    ) -> Prompt:
        """Register a prompt template.

        If the template is unchanged from the latest version, returns the existing
        prompt. If changed or new, creates a new version with auto-incremented
        version number.

        Args:
            name: Logical name for the prompt (e.g., "synthesis_report").
            template: Full prompt text.
            description: Optional changelog for this version.

        Returns:
            The registered Prompt (existing or newly created).
        """
        template_hash = self._hash_template(template)

        # Check if this name already exists
        latest = self._store.get_latest_prompt(name)

        if latest is not None:
            # If hash matches, return the existing prompt
            if latest["template_hash"] == template_hash:
                return Prompt(**latest)

            # Different template - create new version
            new_version = latest["version"] + 1
        else:
            # First version for this name
            new_version = 1

        prompt = Prompt(
            name=name,
            version=new_version,
            template=template,
            description=description or "",
            template_hash=template_hash,
        )

        prompt_id = self._store.save_prompt(prompt.model_dump())
        prompt.id = prompt_id

        return prompt
