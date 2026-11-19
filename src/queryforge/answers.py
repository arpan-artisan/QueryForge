from __future__ import annotations

import re

from queryforge.schema import MetricDefinition

MAX_ANSWER_PREVIEW_ROWS = 5
MAX_ANSWER_CONTEXT_CHARS = 120
_GENERIC_COLUMN_NAMES = frozenset({"count", "name"})
_COLUMN_WORDS = {"avg": "average"}


def render_rows_as_answer(
    question: str,
    rows: list[dict[str, object]],
    metric: MetricDefinition | None = None,
) -> str:
    if not rows:
        return "I ran the query successfully, but it returned no rows."

    first = rows[0]
    if len(rows) == 1 and len(first) == 1:
        key, value = next(iter(first.items()))
        if metric is not None:
            return (
                f"{metric.display_name} is {value}. "
                f"Metric definition: {metric.definition}"
            )
        if _is_generic_column_name(key):
            return f'Result for "{_question_context(question)}": {value}.'
        pretty_key = key.replace("_", " ")
        return f"{_format_column_name(pretty_key)} is {value}."

    preview_rows = rows[:MAX_ANSWER_PREVIEW_ROWS]
    lines = [_format_row(index, row) for index, row in enumerate(preview_rows, start=1)]
    if len(rows) > MAX_ANSWER_PREVIEW_ROWS:
        remaining = len(rows) - MAX_ANSWER_PREVIEW_ROWS
        lines.append(f"... {remaining} more row(s) returned.")

    heading = "Results:"
    if any(_is_generic_column_name(key) for row in preview_rows for key in row):
        heading = f'Results for "{_question_context(question)}":'
    return heading + "\n" + "\n".join(lines)


def _format_row(index: int, row: dict[str, object]) -> str:
    if not row:
        return f"{index}. (no columns)"

    values = ", ".join(f"{_format_column_name(key)}: {value}" for key, value in row.items())
    return f"{index}. {values}"


def _format_column_name(column_name: str) -> str:
    words = column_name.replace("_", " ").split()
    return " ".join(_COLUMN_WORDS.get(word.lower(), word).title() for word in words)


def _is_generic_column_name(column_name: str) -> bool:
    return column_name.strip().lower().replace(" ", "_") in _GENERIC_COLUMN_NAMES


def _question_context(question: str) -> str:
    compact = " ".join(question.split())
    context = re.split(r"(?<=[.!?])\s+", compact, maxsplit=1)[0].rstrip(".!?")
    if len(context) > MAX_ANSWER_CONTEXT_CHARS:
        return context[: MAX_ANSWER_CONTEXT_CHARS - 1].rstrip() + "…"
    return context
