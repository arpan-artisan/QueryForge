from queryforge.answers import render_rows_as_answer


def test_render_rows_as_answer_includes_multi_row_values() -> None:
    answer = render_rows_as_answer(
        "Top products by revenue",
        [
            {"product": "Keyboard", "revenue": 1200.5},
            {"product": "Mouse", "revenue": 650},
        ],
    )

    assert "Results:" in answer
    assert "Product: Keyboard, Revenue: 1200.5" in answer
    assert "Product: Mouse, Revenue: 650" in answer


def test_render_rows_as_answer_limits_large_multi_row_preview() -> None:
    answer = render_rows_as_answer(
        "Show orders",
        [{"id": index} for index in range(1, 8)],
    )

    assert "1. Id: 1" in answer
    assert "5. Id: 5" in answer
    assert "6. Id: 6" not in answer
    assert "... 2 more row(s) returned." in answer
