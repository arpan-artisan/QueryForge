from __future__ import annotations

MAX_ANSWER_PREVIEW_ROWS = 5


def render_rows_as_answer(question: str, rows: list[dict[str, object]]) -> str:
    if not rows:
        return "I ran the query successfully, but it returned no rows."

    first = rows[0]
    if len(rows) == 1 and len(first) == 1:
        key, value = next(iter(first.items()))
        pretty_key = key.replace("_", " ")
        return f"{pretty_key.title()} is {value}."

    preview_rows = rows[:MAX_ANSWER_PREVIEW_ROWS]
    lines = [_format_row(index, row) for index, row in enumerate(preview_rows, start=1)]
    if len(rows) > MAX_ANSWER_PREVIEW_ROWS:
        remaining = len(rows) - MAX_ANSWER_PREVIEW_ROWS
        lines.append(f"... {remaining} more row(s) returned.")

    return "Results:\n" + "\n".join(lines)


def _format_row(index: int, row: dict[str, object]) -> str:
    if not row:
        return f"{index}. (no columns)"

    values = ", ".join(f"{_format_column_name(key)}: {value}" for key, value in row.items())
    return f"{index}. {values}"


def _format_column_name(column_name: str) -> str:
    return column_name.replace("_", " ").title()
