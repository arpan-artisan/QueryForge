## Why

QueryForge currently keeps development and held-out cases in one routinely selected file, so `--split all` and ordinary CI exercise the supposed release set and make its results easy to use for iterative tuning. A release failure that becomes a development regression also reduces the remaining untouched release evidence because the suite has no enforceable promotion and replacement contract.

## What Changes

- Store routine development cases and release-assessment cases in separate versioned evaluation suites, with the suite purpose declared and validated at load time.
- Make development the only default selection; require an explicit release selection, and remove the combined `all` selection so one run cannot accidentally mix evidence classes.
- Label reports as development-regression or release-assessment evidence and include the selected suite purpose, version, digest, and case provenance.
- Define promotion as moving a release case that informed development into the development suite, preserving its identity and oracle, recording its release origin, and adding a new release case before the release suite can satisfy its minimum gate.
- Keep ordinary pull-request CI on the development reference suite; release-suite execution remains an explicit release action using the existing reference/live modes and graders.
- **BREAKING**: replace the public `--split dev|held-out|all` selection with `--evaluation-set development|release`; existing commands using `held-out` or `all` must choose one evidence set explicitly.

### Non-Goals

- Adding or comparing live-model baselines, thresholds, schedules, or credentialed CI.
- Adding answer-quality judges or changing status, safety, result, or diagnostics grading.
- Changing agent intent resolution, SQL generation, SQL safety, execution, or answers.
- Hiding committed files through access control or claiming that repository-visible cases are secret; "unexposed" means not used as iterative development evidence.
- Reorganizing pytest or the rest of the repository test tree.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ask-data-evaluations`: Separate development regression evidence from explicit release assessment evidence, define report labels and selection behavior, and require promoted release cases to be replaced.

## Impact

- Evaluation contracts and selection in `src/queryforge/eval_cases.py`, the runner/report metadata in `src/queryforge/evals.py`, and CLI arguments in `src/queryforge/cli.py`.
- Evaluation data under `evals/ask-data/`, focused eval/CLI tests, routine CI commands, and evaluation documentation.
- No runtime agent behavior, database execution policy, LLM behavior, dependency, or production interface changes.
