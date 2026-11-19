## Context

See [proposal.md](proposal.md) for motivation. The current `evals/ask-data/cases.json` contains 26 `dev` and 10 `held-out` cases, while selection is implemented by a per-case `split` field. The CLI defaults to development but accepts `--split all`, and routine CI currently runs reference mode with that combined selection. Reports record the selected split but do not distinguish regression evidence from release evidence or identify promoted release cases.

The existing loader, runner, graders, reference/live modes, report writers, and `--suite` override are sufficient. This change only needs to make the evidence boundary explicit in those existing paths. The term "unexposed" means a case has not been used to diagnose or tune an implementation change; committed evaluation data is not secret and this design does not add access control.

## Goals / Non-Goals

**Goals:**

- Make routine commands unable to select release cases accidentally.
- Make the evidence class of every report mechanically inspectable.
- Preserve a development regression when a release failure informs a fix without shrinking the active release gate.
- Keep the implementation inside the existing evaluation contracts, runner, CLI, reports, tests, and documentation.

**Non-Goals:**

- Establishing model-quality baselines, score thresholds, schedules, or credentialed CI.
- Changing case grading, trial execution, agent prompts, runtime behavior, or SQL safety.
- Preventing repository readers from viewing committed release cases.
- Adding a promotion command, registry service, database, or automatic suite mutation.

## Decisions

### 1. Replace the mixed suite with two single-purpose suite files

Use these default paths:

- `evals/ask-data/development.json`
- `evals/ask-data/release.json`

Add a required suite-level `purpose` field with values `development` or `release`, and remove the redundant per-case `split` field. Keep all other suite and case fields unchanged. The default loader resolves the file from the requested evaluation set. Loading either default suite also validates the companion suite sufficiently to reject overlapping active case IDs. A custom `--suite` file still uses the same schema and must declare the purpose requested by the CLI.

This is smaller and less error-prone than retaining a per-case split inside two files: file membership and suite purpose become the same fact. A separate manifest or registry was considered, but it would duplicate the JSON suites and add another synchronization point.

The development suite has a minimum of 25 cases. The release suite has a minimum of 10 cases. Category-balance checks remain suite-level. These checks belong in the existing evaluation contract validation rather than a new service.

### 2. Select exactly one evidence set

Replace `--split dev|held-out|all` with:

```text
--evaluation-set development|release
```

The default is `development`. `release` is explicit. There is no `all` equivalent. `--case` continues to narrow the selected suite, `--suite` continues to replace its default path, and reference/live mode plus trial behavior remain unchanged. A purpose mismatch or empty selection is a setup error before provider or executor calls.

The runner accepts `evaluation_set` instead of `split`, resolves the default suite before loading, and writes the requested and declared purpose into the report. No new selector abstraction is needed beyond two path constants and the existing load/select functions.

Alternative considered: preserve `--split all` for reference calibration. That would keep accidental release selection in the routine path and allow one score to mix evidence classes, which is the defect this change removes.

### 3. Represent promotion as case provenance, not a workflow engine

Add one optional case field:

```json
"promoted_from_release": {
  "suite_version": "<release-suite-version>",
  "case_digest": "<sha256-of-evaluation-fields>"
}
```

It is valid only in the development suite. The digest covers the case's evaluation behavior fields while excluding provenance, allowing validation to detect accidental changes to the promoted question, oracle, or comparison rules. Release cases must not carry promotion metadata.

Promotion is a reviewed dataset edit:

1. Move the exposed case from `release.json` to `development.json` without changing its ID or evaluation fields.
2. Add its release suite version and pre-move case digest.
3. Add an independently reviewed replacement to `release.json` so the active count remains at least 10.
4. Increment both suite versions, validate both suites together, and reference-calibrate each separately.

This deliberately avoids an automatic mutation command. Promotion is infrequent, affects reviewed benchmark data, and must remain visible in a normal code review. If an oracle is demonstrably wrong, correct it in a separate documented evaluation-data correction rather than disguising the correction as promotion.

The first migration moves all 36 currently visible cases into `development.json`; it does not relabel the current held-out cases as fresh release evidence. `release.json` is populated with at least 10 newly reviewed cases that have not informed agent implementation. This preserves existing regression coverage and avoids overstating the status of cases that routine CI already selected.

### 4. Label evidence in JSON and Markdown reports

Replace the top-level `split` report field with:

- `evaluation_set`: `development` or `release`;
- `evidence_class`: `development_regression` or `release_assessment`;
- existing suite version and digest;
- ordered selected case IDs;
- per-selected-case provenance, which is `native_development`, `promoted_release`, or `active_release` and includes bounded promotion metadata when applicable.

Both JSON and Markdown display these fields. Summary rates and all existing trial details remain unchanged. A single report directory contains one evidence class only.

Alternative considered: infer evidence type later from file paths. Explicit report fields are stable when reports are moved and make incorrect claims testable.

### 5. Keep routine CI development-only and release execution explicit

Change the existing workflow command to run reference mode with the development default. It continues uploading the report artifact, whose metadata now proves that it is development regression evidence. Do not add a hosted-model job or an automatic release job in this change. Document separate reference and live release commands for a release reviewer.

Update the evaluation code-flow and user-action diagrams because suite selection and the CLI command change. No agent execution or trust-boundary diagram changes are required: LLM output still passes through the same intent, SQL-validation, approval, and read-only execution boundaries.

## Risks / Trade-offs

- [Committed release cases are visible] -> Define release integrity as non-use during iterative tuning, not secrecy; use access-controlled external suites later only if the project adopts a trusted evaluation service.
- [Maintainers forget to promote a case that informed a fix] -> Document the trigger, expose provenance in reports, and require promotion plus replacement in review tasks; this change does not pretend local tooling can infer human use.
- [New release cases are lower quality than promoted cases] -> Require the same strict schema, independent expected results, category balance, reference calibration, and review used for development cases.
- [The CLI rename breaks saved commands] -> Treat it as an explicit local-tool breaking change, update every repository command and test in one implementation, and return argparse usage errors for removed values.
- [Two suites drift to duplicate IDs or incompatible dataset identity] -> Validate the default pair together before execution and cover overlap and purpose mismatches with focused tests.
- [Other in-flight evaluation changes mention the old mixed path or `--split`] -> Rebase their artifacts or implementation onto the two-suite contract; do not add compatibility branches that restore combined evidence.
- [LLM cost, latency, unsafe SQL, or schema drift changes] -> This change does not alter model calls or execution. Existing modes, trial bounds, readiness checks, SQL policy, and report diagnostics remain authoritative.

## Migration Plan

1. Add the suite-purpose and promotion-provenance contracts plus paired-suite validation with focused negative tests.
2. Convert all current cases into `development.json`, create and independently review at least 10 new release cases in `release.json`, and verify disjoint IDs and dataset identity.
3. Replace CLI/runner split selection and report metadata, then update focused CLI, runner, and report tests.
4. Update routine CI, evaluation documentation, README commands, and evaluation diagrams.
5. Run Ruff, focused tests, the full test suite, and separate reference calibration for development and release; inspect both reports for correct evidence labels.

Rollback restores the single `cases.json`, per-case split field, old CLI argument, CI command, and documentation together. Generated reports require no migration because each report directory is immutable evidence from its own schema version.
