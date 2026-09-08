## 1. Policy and Regression Tests

- [x] 1.1 Add a built-in cast target/modifier validator without bypassing recursive safety; verify valid casts, both syntaxes, normalization, unsupported targets, modifiers, and unsafe nested operands with focused tests.
- [x] 1.2 Update the calibration regression and add real Postgres tests for the failed monthly SQL, rounded aggregates, and conversion errors; run focused eval/integration tests.

## 2. Documentation and Verification

- [x] 2.1 Update README, current eval limitations, and the validation diagram; retain historical reports and render diagrams to validate syntax.
- [x] 2.2 Run full pytest, reference evals, bounded live monthly eval, Ruff, and strict OpenSpec; record evidence and remaining limitations, without archiving or pushing.
