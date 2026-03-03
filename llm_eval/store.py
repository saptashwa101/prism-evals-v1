"""Thread-safe SQLite storage for LLM traces, prompts, and annotations."""

import json
import sqlite3
import threading
from datetime import datetime
from typing import Any


class TraceStore:
    """Thread-safe SQLite storage for LLM evaluation data.

    Uses threading.Lock for write operations and threading.local() for
    per-thread database connections.
    """

    def __init__(self, db_path: str):
        """Initialize the store and create schema if needed.

        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = db_path
        self._lock = threading.Lock()
        self._local = threading.local()
        self._create_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a per-thread database connection."""
        if not hasattr(self._local, "connection"):
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            self._local.connection = conn
        return self._local.connection

    def _create_schema(self) -> None:
        """Create database tables if they don't exist."""
        conn = self._get_connection()
        with self._lock:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    template TEXT NOT NULL,
                    description TEXT,
                    template_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(name, version)
                );

                CREATE TABLE IF NOT EXISTS traces (
                    id TEXT PRIMARY KEY,
                    project TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    prompt_name TEXT NOT NULL,
                    prompt_version INTEGER NOT NULL,
                    input_messages TEXT NOT NULL,
                    output_content TEXT,
                    error TEXT,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    model_name TEXT,
                    latency_ms INTEGER DEFAULT 0,
                    metadata TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS annotations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL UNIQUE,
                    rating TEXT NOT NULL,
                    notes TEXT,
                    failure_category TEXT,
                    annotator TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (trace_id) REFERENCES traces(id)
                );

                CREATE INDEX IF NOT EXISTS idx_prompts_name ON prompts(name);
                CREATE INDEX IF NOT EXISTS idx_traces_project ON traces(project);
                CREATE INDEX IF NOT EXISTS idx_traces_session ON traces(session_id);
                CREATE INDEX IF NOT EXISTS idx_traces_prompt ON traces(prompt_name);
                CREATE INDEX IF NOT EXISTS idx_traces_created ON traces(created_at);
                CREATE INDEX IF NOT EXISTS idx_annotations_trace ON annotations(trace_id);
            """)
            conn.commit()

    def _row_to_dict(self, row: sqlite3.Row | None) -> dict | None:
        """Convert a sqlite Row to a dictionary."""
        if row is None:
            return None
        return dict(row)

    # -------------------------------------------------------------------------
    # Prompt Methods
    # -------------------------------------------------------------------------

    def save_prompt(self, prompt: dict) -> int:
        """Save a prompt to the database.

        Args:
            prompt: Dictionary with prompt fields (name, version, template,
                   description, template_hash, created_at).

        Returns:
            The prompt ID.
        """
        conn = self._get_connection()
        created_at = prompt.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        elif created_at is None:
            created_at = datetime.utcnow().isoformat()

        with self._lock:
            cursor = conn.execute(
                """
                INSERT INTO prompts (name, version, template, description, template_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    prompt["name"],
                    prompt["version"],
                    prompt["template"],
                    prompt.get("description", ""),
                    prompt["template_hash"],
                    created_at,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_prompt(self, name: str, version: int | None = None) -> dict | None:
        """Get a prompt by name and optional version.

        Args:
            name: The prompt name.
            version: Specific version, or None for latest.

        Returns:
            Prompt dictionary or None if not found.
        """
        conn = self._get_connection()
        if version is not None:
            row = conn.execute(
                "SELECT * FROM prompts WHERE name = ? AND version = ?",
                (name, version),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM prompts WHERE name = ? ORDER BY version DESC LIMIT 1",
                (name,),
            ).fetchone()
        return self._row_to_dict(row)

    def get_latest_prompt(self, name: str) -> dict | None:
        """Get the latest version of a prompt by name.

        Args:
            name: The prompt name.

        Returns:
            Prompt dictionary or None if not found.
        """
        return self.get_prompt(name, version=None)

    def list_prompt_versions(self, name: str) -> list[dict]:
        """List all versions of a prompt.

        Args:
            name: The prompt name.

        Returns:
            List of prompt dictionaries ordered by version descending.
        """
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM prompts WHERE name = ? ORDER BY version DESC",
            (name,),
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    # -------------------------------------------------------------------------
    # Trace Methods
    # -------------------------------------------------------------------------

    def save_trace(self, trace: dict) -> str:
        """Save a trace to the database.

        Args:
            trace: Dictionary with trace fields.

        Returns:
            The trace ID.
        """
        conn = self._get_connection()
        created_at = trace.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        elif created_at is None:
            created_at = datetime.utcnow().isoformat()

        input_messages = trace.get("input_messages", [])
        if not isinstance(input_messages, str):
            input_messages = json.dumps(input_messages)

        metadata = trace.get("metadata", {})
        if not isinstance(metadata, str):
            metadata = json.dumps(metadata)

        with self._lock:
            conn.execute(
                """
                INSERT INTO traces (
                    id, project, session_id, prompt_name, prompt_version,
                    input_messages, output_content, error, input_tokens,
                    output_tokens, total_tokens, model_name, latency_ms,
                    metadata, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace["id"],
                    trace["project"],
                    trace["session_id"],
                    trace["prompt_name"],
                    trace["prompt_version"],
                    input_messages,
                    trace.get("output_content", ""),
                    trace.get("error"),
                    trace.get("input_tokens", 0),
                    trace.get("output_tokens", 0),
                    trace.get("total_tokens", 0),
                    trace.get("model_name", ""),
                    trace.get("latency_ms", 0),
                    metadata,
                    trace.get("status", "success"),
                    created_at,
                ),
            )
            conn.commit()
            return trace["id"]

    def get_trace(self, trace_id: str) -> dict | None:
        """Get a trace by ID.

        Args:
            trace_id: The trace UUID.

        Returns:
            Trace dictionary with parsed JSON fields, or None if not found.
        """
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM traces WHERE id = ?", (trace_id,)
        ).fetchone()
        if row is None:
            return None
        result = self._row_to_dict(row)
        # Parse JSON fields
        if result.get("input_messages"):
            result["input_messages"] = json.loads(result["input_messages"])
        if result.get("metadata"):
            result["metadata"] = json.loads(result["metadata"])
        return result

    def get_traces(self, filters: dict | None = None) -> list[dict]:
        """Get traces with optional filtering.

        Args:
            filters: Optional dictionary with filter criteria:
                - project: Filter by project name
                - session_id: Filter by session ID
                - prompt_name: Filter by prompt name
                - start_date: Filter traces created after this date (inclusive)
                - end_date: Filter traces created before this date (inclusive)
                - status: Filter by status ("success" or "error")

        Returns:
            List of trace dictionaries.
        """
        conn = self._get_connection()
        filters = filters or {}

        query = "SELECT * FROM traces WHERE 1=1"
        params: list[Any] = []

        if "project" in filters:
            query += " AND project = ?"
            params.append(filters["project"])

        if "session_id" in filters:
            query += " AND session_id = ?"
            params.append(filters["session_id"])

        if "prompt_name" in filters:
            query += " AND prompt_name = ?"
            params.append(filters["prompt_name"])

        if "start_date" in filters:
            start = filters["start_date"]
            if isinstance(start, datetime):
                start = start.isoformat()
            query += " AND created_at >= ?"
            params.append(start)

        if "end_date" in filters:
            end = filters["end_date"]
            if isinstance(end, datetime):
                end = end.isoformat()
            query += " AND created_at <= ?"
            params.append(end)

        if "status" in filters:
            query += " AND status = ?"
            params.append(filters["status"])

        query += " ORDER BY created_at DESC"

        rows = conn.execute(query, params).fetchall()
        results = []
        for row in rows:
            result = self._row_to_dict(row)
            if result.get("input_messages"):
                result["input_messages"] = json.loads(result["input_messages"])
            if result.get("metadata"):
                result["metadata"] = json.loads(result["metadata"])
            results.append(result)
        return results

    def get_sessions(self, project: str | None = None) -> list[dict]:
        """Get session summaries.

        Args:
            project: Optional project name to filter by.

        Returns:
            List of session summary dictionaries containing:
                - session_id
                - project
                - trace_count
                - total_tokens
                - first_trace_at
                - last_trace_at
                - success_count
                - error_count
        """
        conn = self._get_connection()

        query = """
            SELECT
                session_id,
                project,
                COUNT(*) as trace_count,
                SUM(total_tokens) as total_tokens,
                MIN(created_at) as first_trace_at,
                MAX(created_at) as last_trace_at,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
            FROM traces
        """
        params: list[Any] = []

        if project is not None:
            query += " WHERE project = ?"
            params.append(project)

        query += " GROUP BY session_id, project ORDER BY last_trace_at DESC"

        rows = conn.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    # -------------------------------------------------------------------------
    # Annotation Methods
    # -------------------------------------------------------------------------

    def save_annotation(self, annotation: dict) -> int:
        """Save an annotation to the database.

        Args:
            annotation: Dictionary with annotation fields (trace_id, rating,
                       notes, failure_category, annotator, created_at).

        Returns:
            The annotation ID.
        """
        conn = self._get_connection()
        created_at = annotation.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        elif created_at is None:
            created_at = datetime.utcnow().isoformat()

        with self._lock:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO annotations
                (trace_id, rating, notes, failure_category, annotator, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    annotation["trace_id"],
                    annotation["rating"],
                    annotation.get("notes", ""),
                    annotation.get("failure_category", ""),
                    annotation.get("annotator", ""),
                    created_at,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_annotation(self, trace_id: str) -> dict | None:
        """Get an annotation by trace ID.

        Args:
            trace_id: The trace UUID.

        Returns:
            Annotation dictionary or None if not found.
        """
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM annotations WHERE trace_id = ?", (trace_id,)
        ).fetchone()
        return self._row_to_dict(row)
