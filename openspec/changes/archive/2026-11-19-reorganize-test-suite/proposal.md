## Why

The flat `tests/` directory mixes fast unit checks, Postgres integration checks, and evaluation-harness verification, making it difficult to understand what a test protects or which prerequisites it needs. Reorganizing the existing verification surface will make test intent and execution boundaries visible without changing QueryForge behavior or evaluation grading.

## What Changes

- Group existing tests under clearly named unit, integration, and evaluation-harness directories, with small domain-based subdirectories where they make navigation easier.
- Split oversized test modules by the behavior they verify and give unclear parameterized cases descriptive IDs.
- Keep the development and release evaluation datasets established by `protect-held-out-release-evals` under `evals/`, and generated, ignored reports under `evaluation-results/`, distinct from pytest modules.
- Provide separate local and CI commands for unit tests, Postgres integration tests, evaluation-harness tests, and reference evaluation runs while retaining an aggregate verification path.
- Update affected documentation and architecture references to the new paths and commands.
- Preserve every existing assertion, skip condition, safety check, evaluation grade, dataset value, report format, and runtime behavior.

## Capabilities

### New Capabilities

None. This is a pure verification-layout refactor and `.openspec.yaml` sets `skip_specs: true`.

### Modified Capabilities

None. No product requirement or externally observable runtime behavior changes.

## Impact

- Affected files: pytest modules under `tests/`, pytest configuration in `pyproject.toml` if needed for stable discovery, `.github/workflows/tests.yml`, and test/evaluation documentation.
- Implementation follows `protect-held-out-release-evals` and consumes its `evals/ask-data/development.json`, `evals/ask-data/release.json`, and `--evaluation-set development|release` interface without redefining it.
- Generated reports remain in ignored `evaluation-results/<run-id>/` directories and retain the evidence metadata established by that prerequisite change.
- No production code, public CLI contract, database execution path, safety policy, LLM behavior, evaluation grading logic, dependency, or dataset content changes.

## Non-Goals

- Fixing agent ambiguity, SQL correctness, answer quality, or evaluation coverage gaps.
- Changing evaluation cases, scores, thresholds, report schemas, or the distinction between reference and live modes.
- Defining development/release suite separation, promotion behavior, evidence labels, or release-gate policy; those belong to `protect-held-out-release-evals`.
- Introducing pytest plugins, new test abstractions, shared fixture frameworks, or speculative CI infrastructure.
