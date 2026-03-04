"""CLI entry points for llm_eval package."""

import subprocess
import sys
from pathlib import Path


def run_dashboard():
    """Run the Streamlit dashboard."""
    dashboard_path = Path(__file__).parent / "dashboard_v2.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(dashboard_path)] + sys.argv[1:])


if __name__ == "__main__":
    run_dashboard()
