## 1. Establish the Preservation Baseline

- [x] 1.1 Verify `protect-held-out-release-evals` is implemented and validated first, including `evals/ask-data/development.json`, `evals/ask-data/release.json`, and `--evaluation-set development|release`; do not start this refactor against the obsolete mixed-suite interface.
- [x] 1.2 Record the post-dependency `uv run pytest --collect-only -q` total and source-to-destination module checklist, and verify every existing pytest module and collected case is represented before moving files.
- [x] 1.3 Run the post-dependency aggregate pytest suite with its documented Postgres prerequisites and record pass/skip/fail totals so the reorganized suite can be compared under the same environment.

## 2. Organize Unit Tests

- [x] 2.1 Create the `tests/unit/{agent,contracts,database,interfaces,policy,providers,telemetry}` layout, move focused fake/in-memory test modules into their owning domains, and verify `uv run pytest tests/unit --collect-only -q` discovers each moved test.
- [x] 2.2 Split `test_ask_data_graph.py` into success/memory, local-policy-stop, and failure/repair modules under `tests/unit/agent/`, retaining every helper, input, assertion, and test case; verify the focused agent tests pass.
- [x] 2.3 Split `test_sql_safety.py` into allowlist, prohibited-construct, normalization/limit, and cast modules under `tests/unit/policy/`, retaining all safety assertions and parameter cases; verify the focused policy tests pass.
- [x] 2.4 Split `test_observability.py` into configuration, trace/redaction contract, and recorder/exporter modules under `tests/unit/telemetry/`, keeping credential redaction and exporter-failure coverage unchanged; verify the focused telemetry tests pass.
- [x] 2.5 Add explicit descriptive IDs only to parameterized unit cases whose collected names do not explain the scenario, and verify collection output is readable without changing parameter inputs or expected outcomes.

## 3. Separate Integration and Evaluation-Harness Verification

- [x] 3.1 Move the real-Postgres lifecycle coverage to `tests/integration/database/test_demo_database_lifecycle.py`, retain its readiness/privilege/reset behavior, and verify `uv run pytest tests/integration` passes against the initialized demo database.
- [x] 3.2 Split the existing evaluation-harness unit coverage into case-contract, grading, runner, and reporting/CLI modules under `tests/eval_harness/`, retaining every grader, failure-category, redaction, and exit-code assertion; verify `uv run pytest tests/eval_harness` passes with the database-gated reference suite skipped when not opted in.
- [x] 3.3 Move the opt-in full reference-suite coverage to `tests/eval_harness/test_reference_suite_with_postgres.py`, preserve the `QUERYFORGE_TEST_EVAL_DB` guard and database-content checks, and verify it passes when explicitly enabled against the initialized demo database.
- [x] 3.4 Confirm `evals/ask-data/development.json`, `evals/ask-data/release.json`, and the `evaluation-results/<run-id>/` output convention were not moved or semantically edited by this refactor, and verify development and release reference runs still write evidence-labeled `report.json` and `report.md` files under separate unique run directories.

## 4. Expose the Verification Boundaries

- [x] 4.1 Keep aggregate pytest discovery rooted at `tests/` and verify `uv run pytest --collect-only -q` includes the same pre-existing cases, allowing only path changes and explicitly improved parameter IDs.
- [x] 4.2 Update `.github/workflows/tests.yml` to use separately named unit, Postgres integration, evaluation-harness, opt-in reference-suite, and development reference-evaluation steps with `--evaluation-set development`, while preserving the post-dependency database setup, evidence-labeled report upload, and cleanup behavior; verify the workflow contains no routine release selection and its commands run locally under equivalent prerequisites.
- [x] 4.3 Update `README.md` and `docs/evaluations.md` with the new directory purposes, focused commands, `development.json` and `release.json` locations, generated-report location, routine development command, explicit release command, and the distinction between pytest harness verification and actual reference/live evaluation; manually verify no old test path or mixed-suite command remains.
- [x] 4.4 Review `docs/architecture-diagrams.md` for stale test paths and update only those references if present; record that no diagram flow changes are required because runtime, trust boundaries, grading, and report generation are unchanged.

## 5. Validate the Refactor

- [x] 5.1 Run `uv run ruff check .` and resolve only organization-related lint/import issues.
- [x] 5.2 Run `uv run pytest tests/unit`, `uv run pytest tests/integration`, and `uv run pytest tests/eval_harness` under their documented prerequisites and verify all pre-existing behavior remains covered.
- [x] 5.3 Run the aggregate `uv run pytest` with `QUERYFORGE_TEST_EVAL_DB=1`, compare its collection and pass/skip/fail totals with the baseline, and resolve any lost, duplicated, or unexpectedly executed cases.
- [x] 5.4 Run `uv run queryforge evals run --mode reference --evaluation-set development` and `uv run queryforge evals run --mode reference --evaluation-set release`; verify each uses only its requested suite and preserves the post-dependency grades, summaries, provenance, evidence classification, and JSON/Markdown report contract.
- [x] 5.5 Run `openspec validate reorganize-test-suite --strict`, verify planning/implementation evidence supports every completed checkbox, and confirm this refactor did not change `src/queryforge/` runtime behavior, development/release suite content, selection semantics, evidence metadata, or grading logic.
