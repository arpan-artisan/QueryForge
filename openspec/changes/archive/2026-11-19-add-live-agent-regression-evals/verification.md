# Verification

## Implemented and verified

- Strict versioned live-baseline manifest validation, baseline-owned selection,
  identity compatibility checks, deterministic rate comparison, hard safety,
  and exit-code behavior.
- Per-case and per-dimension repeated-trial summaries, model-input and code/prompt
  digests, latency, explicit infrastructure failures, and redacted JSON/Markdown
  baseline comparison evidence.
- Ad hoc live pacing via `--live-delay-seconds`; pacing never retries or removes
  failed trials.
- Reference calibration enforces scripted repair counts. Live grading records a
  bounded repair and grades its final status, safety, result, and diagnostics.
- Documentation and all eight Mermaid diagrams were rendered successfully with
  Mermaid CLI to a temporary location outside the repository.

## Automated evidence

- Focused evaluator/model/SQL tests: `335 passed`.
- Full suite: `588 passed, 8 skipped`.
- Ruff: `All checks passed!`.
- Development reference evaluation: `37/37` passed, report
  `168997feb2514fa38bffc7ebad651884`.
- Strict OpenSpec validation: `Change 'add-live-agent-regression-evals' is valid`.
- `git diff --check`: no whitespace errors (only the repository's line-ending
  conversion warnings).

## Live evidence

- Ambiguous total revenue: `3/3` passed, report
  `bae00ecaaacd429589ad94c4845bdbdb`.
- Net revenue: the infrastructure-clean focused run passed status, safety,
  result (`1995`), and diagnostics, report
  `3b8c1540fea949518675380bcb62e551`.
- A three-trial net-revenue replay had one capability pass and two provider rate
  limits, report `1a5de4bc096b42d1b9a3c9fbd7a541e6`; safety and diagnostics were `3/3`.

## Open blockers

Tasks 3.2, 3.3, and 4.4 remain unchecked. The ordinary three-trial development
run produced 49/108 passes with 50 provider rate limits; a four-second paced run
produced 54/108 with 45 provider rate limits. Nine dependent memory cases in
each report then failed setup because a prerequisite turn lacked a valid result.
Those reports (`423c57929c8b45ae95cf7eff28502d34` and
`7c62a40fb9e84e1d981f784faa035f92`) are not suitable source evidence for choosing
or approving quality floors. Consequently, no `live-baseline.json` was created
and no credentialed workflow that pretends such a baseline exists was added.
