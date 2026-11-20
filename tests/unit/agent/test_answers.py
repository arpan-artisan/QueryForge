from queryforge.answers import render_rows_as_answer
from queryforge.schema import REVENUE_METRIC_DEFINITIONS


def test_render_rows_as_answer_reports_empty_success() -> None:
    assert render_rows_as_answer("Show order 999", []) == (
        "I ran the query successfully, but it returned no rows."
    )


def test_render_rows_as_answer_explains_a_governed_scalar() -> None:
    metric = next(item for item in REVENUE_METRIC_DEFINITIONS if item.metric_id == "net_revenue")

    answer = render_rows_as_answer(
        "Ignore this conflicting wording",
        [{"completed_revenue": 1995}],
        metric,
    )

    assert answer == ("Net revenue is 1995. Metric definition: gross revenue minus refund amount.")


def test_render_rows_as_answer_preserves_scalar_alias_fallback_without_metric() -> None:
    assert render_rows_as_answer("What is revenue?", [{"total_revenue": 2260}]) == (
        "Total Revenue is 2260."
    )


def test_render_rows_as_answer_contextualizes_generic_scalar_label() -> None:
    answer = render_rows_as_answer(
        "Count completed orders. Return only the count.",
        [{"count": 7}],
    )

    assert answer == 'Result for "Count completed orders": 7.'


def test_render_rows_as_answer_bounds_generic_label_context() -> None:
    answer = render_rows_as_answer("Show " + "very " * 40 + "long context", [{"count": 7}])

    assert answer.startswith('Result for "Show very very')
    assert '…": 7.' in answer


def test_render_rows_as_answer_expands_average_abbreviation() -> None:
    answer = render_rows_as_answer(
        "What is the average order value?",
        [{"avg_order_value": 291.43}],
    )

    assert answer == "Average Order Value is 291.43."


def test_render_rows_as_answer_does_not_explain_non_scalar_results() -> None:
    metric = REVENUE_METRIC_DEFINITIONS[0]

    answer = render_rows_as_answer(
        "Completed revenue by channel",
        [{"channel": "web", "revenue": 500}],
        metric,
    )

    assert "Metric definition:" not in answer
    assert answer == "Results:\n1. Channel: web, Revenue: 500"


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


def test_render_rows_as_answer_contextualizes_generic_tabular_label() -> None:
    answer = render_rows_as_answer(
        "Show the top 3 customers by completed order revenue. Return customer name and revenue.",
        [{"name": "Aarav Mehta", "revenue": 580}],
    )

    assert answer == (
        'Results for "Show the top 3 customers by completed order revenue":\n'
        "1. Name: Aarav Mehta, Revenue: 580"
    )


def test_render_rows_as_answer_limits_large_multi_row_preview() -> None:
    answer = render_rows_as_answer(
        "Show orders",
        [{"id": index} for index in range(1, 8)],
    )

    assert "1. Id: 1" in answer
    assert "5. Id: 5" in answer
    assert "6. Id: 6" not in answer
    assert "... 2 more row(s) returned." in answer
