## Context

See [proposal.md](proposal.md) for motivation. QueryForge currently has 17 pytest modules directly under `tests/`. Most are isolated unit tests, two use a real Postgres database, and two verify the evaluation harness. This refactor is implemented only after `protect-held-out-release-evals`, whose resulting evaluation inputs are separate at `evals/ask-data/development.json` and `evals/ask-data/release.json`; generated reports remain in the ignored `evaluation-results/<run-id>/` directory.

The post-dependency state is the preservation baseline. This refactor must retain pytest discovery behavior, opt-in database skip behavior, evaluation case IDs and provenance, grading logic, evidence-labeled report schema, `--evaluation-set development|release` behavior, and the aggregate `uv run pytest` command. Production modules under `src/queryforge/` are outside the implementation scope.

## Goals / Non-Goals

**Goals:**

- Make the kind and dependency level of each verification file clear from its path.
- Make large test modules readable by separating distinct behaviors without changing assertions.
- Expose focused commands for fast unit checks, Postgres integration checks, evaluation-harness checks, and actual reference evaluations.
- Prove that collection and results are preserved after the move.

**Non-Goals:**

- Reclassifying reference calibration as a live quality evaluation.
- Adding or changing agent behavior, evaluation cases, graders, thresholds, reports, dependencies, or pytest plugins.
- Moving `evals/ask-data/development.json`, `evals/ask-data/release.json`, or `evaluation-results/`; those paths already provide the required dataset/report separation.
- Implementing suite separation, held-out promotion/replacement, evidence classification, or release policy; this change only consumes the completed `protect-held-out-release-evals` interface.
- Creating a generalized test utility framework. Shared fixtures stay local to the smallest directory that uses them.

## Decisions

### 1. Use three pytest roots under `tests/`

The target layout is:

```text
tests/
├── unit/
│   ├── agent/
│   ├── contracts/
│   ├── database/
│   ├── interfaces/
│   ├── policy/
│   ├── providers/
│   └── telemetry/
├── integration/
│   └── database/
└── eval_harness/
```

`unit/` contains tests that use fakes, monkeypatching, or in-memory values and do not require an external service. `integration/database/` contains tests that provision or connect to Postgres. `eval_harness/` contains tests of case contracts, graders, runners, report generation, and the opt-in full reference suite.

The datasets remain at `evals/ask-data/development.json` and `evals/ask-data/release.json`; they are inputs to evaluation runs, not pytest code. Reports remain at `evaluation-results/<run-id>/`; they are generated evidence and stay git-ignored.

Alternative considered: keep one flat file per production module. That is smaller mechanically, but it preserves the unclear distinction between ordinary tests, external-service integration, evaluation-harness verification, and actual evaluation inputs.

### 2. Move focused files and split only the modules that currently mix distinct behaviors

Existing focused modules move intact into the closest unit domain, with descriptive renames where the current filename hides its responsibility:

- Agent: answers, memory, repair, runtime architecture.
- Contracts: result/model contracts.
- Database: demo dataset contract, Postgres configuration/readiness with fakes, and query executor boundary with fakes.
- Interfaces: CLI behavior with injected collaborators.
- Policy: intent and SQL safety.
- Providers: LLM provider parsing/configuration/error normalization.
- Telemetry: observability configuration, trace contracts, recording, and exporter behavior.
- Integration/database: the current `test_postgres_integration.py` becomes `test_demo_database_lifecycle.py`.
- Eval harness: the current `test_evals_integration.py` becomes `test_reference_suite_with_postgres.py` and keeps its existing `QUERYFORGE_TEST_EVAL_DB` opt-in guard.

Only these large mixed modules are split:

- `test_ask_data_graph.py` into success/memory, local-policy stops, and failure/repair flows under `unit/agent/`.
- `test_sql_safety.py` into allowlist, prohibited constructs, normalization/limits, and cast handling under `unit/policy/`.
- `test_observability.py` into configuration, trace/redaction contracts, and recorder/exporter behavior under `unit/telemetry/`.
- `test_evals.py` into case contracts, grading, runner behavior, and reporting/CLI behavior under `eval_harness/`.

Existing helper classes and fixtures move with their consumers. When a helper is used by more than one resulting file, place only that helper in the nearest local `conftest.py`; do not introduce a repository-wide test utility module.

Alternative considered: split every file to a fixed line limit. A line-count rule would create arbitrary files and more navigation, so splitting is limited to modules that contain multiple recognizable responsibilities.

### 3. Improve names without changing evaluated inputs or assertions

Test function names should state the condition and observable outcome. Parameterized tests whose collected IDs are currently raw values or generated indexes receive explicit, stable `pytest.param(..., id="...")` labels. Existing evaluation case IDs in `development.json` and `release.json` are not renamed because they identify report history, provenance, and evaluation evidence.

No assertion may be weakened or removed as part of a rename or split. Content changes discovered during implementation belong to the separate agent/evaluation correctness changes.

Alternative considered: add docstrings to every test. Descriptive file, function, and parameter IDs provide clearer collection output with less duplicated prose.

### 4. Keep aggregate discovery and add explicit verification commands

`pyproject.toml` keeps `testpaths = ["tests"]`, so `uv run pytest` remains the aggregate command. Documentation and CI expose these boundaries:

```powershell
uv run pytest tests/unit
uv run pytest tests/integration
uv run pytest tests/eval_harness
$env:QUERYFORGE_TEST_EVAL_DB = "1"; uv run pytest tests/eval_harness/test_reference_suite_with_postgres.py
uv run queryforge evals run --mode reference --evaluation-set development
uv run queryforge evals run --mode reference --evaluation-set release
```

Routine CI keeps the post-dependency Postgres provisioning and development reference-evaluation behavior, using `--evaluation-set development`, but runs the pytest groups as separately named steps so failures identify the responsible layer. Release verification remains an explicit command and is not added to routine CI. This change does not add a live-model CI gate.

Alternative considered: custom pytest markers. Directories already express the selection boundary and require no plugin, registration, or duplicated marker maintenance.

### 5. Verify preservation before removing old paths

After `protect-held-out-release-evals` is implemented and before moving files, capture the post-dependency collected count and full-suite result. After the move:

1. Run collection for each new pytest root and for the aggregate suite.
2. Confirm all pre-existing test functions and parameter cases are represented; path changes and explicitly improved IDs are the only collection-name differences.
3. Run unit, integration, evaluation-harness, aggregate pytest, Ruff, development reference evaluation, and explicit release reference evaluation under the same Postgres prerequisites as the post-dependency baseline.
4. Confirm report location, evidence classification, provenance, grades, and summaries are unchanged relative to that baseline.

Git history preserves rollback: revert the refactor commit if collection or behavior differs. There is no data migration.

### 6. Update documentation, not runtime architecture

Update `README.md`, `docs/evaluations.md`, and CI path references to the new commands and module locations. `docs/architecture-diagrams.md` does not need a semantic diagram change because agent execution, trust boundaries, evaluation flow, dataset flow, and report generation are unchanged; only stale file-path references, if any, should be corrected.

The LLM-output-to-validator-to-approved-query-to-database trust boundary remains exactly as implemented. Moving its tests must not simplify or bypass those checks.

## Risks / Trade-offs

- [Tests are lost while splitting large modules] → Record pre-move collection, use an explicit source-to-destination checklist, and compare aggregate collection and results before deleting old files.
- [Imports or fixture visibility break after nesting] → Keep production imports absolute and place shared pytest fixtures in the nearest common `conftest.py` only when multiple files need them.
- [Database tests run in the wrong stage] → Classify by actual external dependency, retain existing skip/readiness behavior, and exercise focused commands in CI.
- [A readability edit silently changes behavior] → Limit edits to moves, names, IDs, and fixture placement; keep assertions, inputs, environment gates, development/release dataset content, evidence metadata, and grading code unchanged relative to the completed prerequisite.
- [The refactor is applied before its evaluation dependency] → Do not begin implementation until `protect-held-out-release-evals` is implemented and verified; capture preservation evidence only from that resulting state.
- [More directories add navigation cost] → Use only seven stable unit domains and avoid mirroring the full production package tree.
- [The cleaner layout is mistaken for improved eval quality] → Document that reference calibration and live quality evaluation remain separate concerns; this refactor changes organization only.
