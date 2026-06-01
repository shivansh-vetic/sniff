"""Server-level instructions advertised to MCP clients.

These are sent to every Claude session that connects to the gateway, so the
LLM gets Vetic-specific analyst context (schema map, time conventions, PII
rules, query budgets) without the user having to paste anything.

Markdown files in this directory hold the actual content — edit them as
plain markdown, no Python required. To swap which file is loaded, change
the constant below.
"""

from pathlib import Path

_HERE = Path(__file__).parent
_DEFAULT_CONTEXT = "analyst_context.md"


def load_instructions(name: str = _DEFAULT_CONTEXT) -> str:
    """Read a markdown file from this directory and return its contents."""
    return (_HERE / name).read_text(encoding="utf-8")
