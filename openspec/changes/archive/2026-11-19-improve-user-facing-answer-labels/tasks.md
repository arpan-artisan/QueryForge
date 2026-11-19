## 1. Reproduce the label failures

- [x] 1.1 Add focused answer-rendering tests for a generic scalar count, an abbreviated average label, and a generic multi-row entity name; verify the tests reject the current vague output.
- [x] 1.2 Add a provider prompt contract test requiring explicit descriptive output aliases and verify existing provider parsing behavior remains unchanged.

## 2. Improve grounded presentation

- [x] 2.1 Update SQL-generation guidance to request descriptive aliases without changing provider, SQL-safety, or execution contracts; verify the provider tests pass.
- [x] 2.2 Update deterministic answer rendering to expand the reproduced abbreviation and add bounded question context only when returned labels remain generic; verify governed metric explanations, empty results, row previews, and non-generic labels retain their current behavior.
- [x] 2.3 Review the four QF-010 development expectations without weakening them, add only independently valid label synonyms if needed, and verify reference calibration remains 37/37.

## 3. Verify the user-visible fix

- [x] 3.1 Run focused unit, graph, provider, and evaluation-grading tests and verify every affected path passes.
- [x] 3.2 Run focused live trials for `completed-count`, `average-order-value`, `orders-by-status`, and `customer-ranking`; verify correct rows and grounded, direct labels, recording infrastructure failures separately from quality failures.
- [x] 3.3 Update QF-010 and this change's verification record with the observed evidence; verify unresolved limitations remain explicit.
- [x] 3.4 Run Ruff, the full database-backed test suite, development reference evaluation, and strict OpenSpec validation; record the exact results before marking the change complete.
