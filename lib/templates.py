"""Tiny template renderer with `{{ var }}` and `{% if var %}...{% endif %}`.

We avoid Jinja2 to keep EasyNginx free of Python dependencies — it must work
on a fresh server where only the standard library is guaranteed.
"""

from __future__ import annotations

import re
from pathlib import Path


_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
_BLOCK_RE = re.compile(
    r"\{%\s*if\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*%\}(.*?)\{%\s*endif\s*%\}",
    re.DOTALL,
)


def _truthy(value: object) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, (list, tuple, dict, str)):
        return bool(value)
    return True


def render(template: str, context: dict) -> str:
    """Render a template string against `context`."""

    def block_sub(match: re.Match[str]) -> str:
        var, body = match.group(1), match.group(2)
        return body if _truthy(context.get(var)) else ""

    out = _BLOCK_RE.sub(block_sub, template)

    def var_sub(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            raise KeyError(f"Template variable '{key}' is not set.")
        value = context[key]
        return "" if value is None else str(value)

    out = _VAR_RE.sub(var_sub, out)

    # Collapse any runs of blank lines left behind by removed blocks.
    lines = []
    blanks = 0
    for line in out.splitlines():
        if line.strip() == "":
            blanks += 1
            if blanks <= 1:
                lines.append("")
        else:
            blanks = 0
            lines.append(line)
    return "\n".join(lines).rstrip() + "\n"


def render_file(path: Path, context: dict) -> str:
    return render(path.read_text(encoding="utf-8"), context)
