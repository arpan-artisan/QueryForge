# Verification

## Implemented behavior

- SQL-generation guidance requests explicit descriptive aliases for calculated
  values and otherwise generic projected columns.
- Deterministic rendering expands `avg` to `average`, contextualizes generic
  scalar `count` and tabular `name` labels with a bounded first-question
  sentence, and preserves governed metric explanations and structured rows.
- Development suite `ask-data-development-v1.3` accepts the independently clear
  phrases `completed order count` and `order count`; no result, status, safety,
  diagnostic, or other grounding requirement was weakened.

## Focused evidence

- The new reproductions initially failed in all four expected places: three
  rendering cases and the missing provider prompt contract.
- Answer and provider tests after implementation: `27 passed`; the additional
  bounded-context answer test also passes.
- Unit agent, provider, and evaluation-grading tests: `146 passed`.
- Evaluation case-contract and grading tests after the reviewed vocabulary
  correction: `81 passed`.
- Development reference calibration: `37/37` passed, report
  `2b2d1d8329464c418d90d8b547b37e48`.

## Live evidence

- The first focused live run returned correct rows for all four cases. Two
  outputs passed immediately; `Completed Order Count` and `Order Count` exposed
  missing valid synonyms in the expectation vocabulary, report
  `5f4d4a8297254a938b1c60f6eab0cc0a`.
- After adding only those reviewed synonyms and recalibrating, the repeated live
  run passed `completed-count`, `average-order-value`, `orders-by-status`, and
  `customer-ranking`: 4/4 trials, status, safety, diagnostics, result, and answer
  grounding all 4/4, report `af4228f1ae994f0cbad67b4ffae3a0cd`.

## Remaining boundary

The existing approved baseline pins development suite v1.2. Replacing it for
v1.3 and enforcing calibrated subjective answer-quality dimensions belongs to
the next focused live-quality-gate change; this change does not claim that gate
is complete.

## Final repository validation

- Ruff: `All checks passed!`.
- Full database-backed suite: `619 passed`.
- Final development reference evaluation: `37/37` passed, report
  `737acf86815346439d760c67d28d910c`.
- Strict OpenSpec validation: passed.
- `git diff --check`: no whitespace errors; only the repository's existing
  line-ending conversion warnings were emitted.
