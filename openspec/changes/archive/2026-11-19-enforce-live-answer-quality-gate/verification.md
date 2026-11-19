# Verification Record

## Implemented and verified

- Baseline schema v2 requires all deterministic and subjective dimensions plus
  pinned agent, judge, calibration, suite, case, trial, and dataset identity.
- A baseline-backed run enables calibrated answer judging automatically and
  fails before scored trials when any pinned identity is incompatible.
- Directness, completeness, and clarity retain independent eligible
  denominators, verdict reasons, report output, Markdown output, floors, and
  fail-closed exit behavior.
- Calibration contains mixed verdict patterns that distinguish the three
  subjective dimensions. The pinned live judge passed the reviewed fixture
  after the rubric clarified dimension independence.
- Groq judge calls cap completions at 512 tokens and use the provider's numeric
  `retry-after` value for bounded transient recovery. Persistent or excessive
  unavailability still invalidates the run and retains a sanitized diagnostic.
- The manually dispatched credentialed workflow pins both agent and judge
  models, uses 30-second pacing, keeps credentials secret-scoped, and uploads
  reports even when the gate fails.
- Judged live evidence can run as non-overlapping case chunks and compose
  offline only when persisted digests, suite/source/provider/judge/calibration/
  dataset identity, pacing, exact case coverage, trial counts, and
  infrastructure cleanliness all match. Composition performs no provider calls.
- Live pacing is enforced at the shared provider-call boundary, covering judge
  calibration, metric resolution, SQL generation, repair, grading, and retries.
  This prevents multiple calls inside one trial from bursting despite a nominal
  inter-trial delay.

## Automated evidence

- Provider-call pacing correction: `42 passed` in the focused runner suite;
  composition, reporting CLI, and case-contract regression slice: `55 passed`.
  Focused Ruff format and lint checks passed for the touched evaluator, CLI,
  and runner-test files.
- Provider/evaluator focused tests after documented rate-limit handling:
  `89 passed`.
- Staged composition and CLI tests: `7 passed`; evaluator/reporting/CLI
  regression groups: `145 passed, 8 skipped` plus `11 passed`.
- Full database-backed suite after the final composition correction:
  `629 passed, 8 skipped` in 59.89 seconds.
- Ruff: `All checks passed!`.
- Development reference evaluation: `37/37` passed, report
  `6481242342f24a1e8e109e4b36e08a5f` (digest
  `2b008b45ec147dc9dc417ee8304f2385ef299931f9c0a0bfd73cf64e5e72c837`).
- Release reference evaluation: `10/10` passed, report
  `d91f462b1fdd4eb29a0b47a937c0a60b` (digest
  `71d9dea0c60c8408d34a9def3392e5d179e3aec83f1232a655554fb7712ee620`).
- Strict OpenSpec validation: current change valid; all 18 changes/specs passed.
- `git diff --check`: no whitespace errors; only repository line-ending
  conversion warnings.
- Added-line credential scan after final local validation: zero Groq secret values.
- Repository-wide `ruff format --check .` found formatting drift in 25 existing
  source, test, and archived-Markdown files. Focused formatting for the files
  changed by the pacing correction passes; unrelated dirty-worktree files were
  not mechanically rewritten.

## Live evidence

- Pinned judge calibration passed all four dimension-separating examples in
  report `dad10cfa87b74a2c967a581eeec9783e`. Its scored net-revenue answer exposed
  a real directness failure caused by the conflict between “return only” and the
  required metric-definition suffix; the expected calibration verdict was not
  weakened to hide this result.
- Report `0b8c1affadf94a5fa855bec20b645c3d` completed 98/111 trials before judge
  unavailability and was rejected as invalid.
- Report `03ddd1777d28400fb49fb444bf600621` passed calibration and completed 46/111
  trials before three HTTP 429 judge attempts failed; it was rejected as invalid.
- Report `83a6d368f9704cdf96a152e09d89f639` exhausted its bounded HTTP 429 recovery
  during calibration and completed no scored trials; it was rejected as invalid.
- Staged smoke report `c64e7abb9c5544b793aca57e8c0b4c2d` completed one judged
  `completed-revenue` trial without infrastructure failure. Deterministic grades
  and clarity passed; directness and completeness failed because the answer
  appended the governed metric definition despite the case requesting only the
  total. The quality failure remains visible and was not retried or weakened.
- Strict JSON Schema plus low reasoning effort removed the judge's best-effort
  JSON HTTP 400 on focused report `15f4ccb7e26f474782ee9e1816c94704`;
  calibration and the complete judged trial ran, with only the observed
  completeness grade failing.
- Source candidate chunk `c6198848d9794615841f4af43e4cd524` completed all 30
  trials without infrastructure failure at 30-second pacing and remains useful
  diagnostic evidence, but later code changes make it incompatible with the
  final source set.
- Source candidate chunk `e1511bcbb5d94c0cb0f4c4db7a3ee825` stopped after
  14/27 trials when the judge exhausted bounded HTTP 429 recovery. It is invalid
  and cannot be composed. Provider errors now retain non-secret `retry-after`
  and rate-limit remaining/reset headers for future diagnosis.
- Source candidate chunk `82212ead910045558f3d3f7c51d244e9` stopped after 8/15 trials with a provider
  `retry-after` value of 166 seconds. This evidence raised the bounded retry cap
  to 300 seconds but remains invalid and cannot be composed.
- A later source attempt produced no report after about 138 minutes and was
  explicitly stopped. Investigation showed that its 60-second post-trial delay
  still allowed calibration, agent, and judge calls to burst inside each trial;
  no baseline evidence was retained from that attempt.

## Final live evidence

The single-trial source evaluation completed as eight accepted non-overlapping
chunks and composed into valid report `c65d91e6ca07465eb7397da585c2a4e7`
(digest `2169400d6e6f1b655fe8ca1c7d060267fa9ea672a9859f95cda971ebef4244cd`).
It covered all 37 development cases with zero infrastructure failures: status,
safety, diagnostics, and semantic disposition passed 37/37; result correctness
passed 21/21; deterministic grounding passed 36/37; and 31/37 trials passed all
grades. Directness passed 31/36 eligible answers, completeness 32/36, and clarity
34/36. The six reviewed failures remain visible in `payment-success-rate`,
`payment-success-rate-by-method-phrasing`, `order-lookup`, `refund-rate`,
`historical-price`, and `empty-aggregate`.

Invalid network/provider attempts `8d8cb27e093e49bfad14edf57e95af3d`
and `67afd5fda5694d0094a5d2599c306415` were retained but excluded from
composition. Composition also exposed and fixed the provider-free local-chunk
identity case; focused composition tests now pass 9/9 and still reject missing
or conflicting provider-using identities.

`evals/ask-data/live-baseline.json` is now baseline v2
`development-groq-gpt-oss-20b-v2`, digest
`9e7715a3e832a4ddd684b670d1093eb55e88d622f2b1e94ac382e20a5fe3882e`.
The real loader and composed-baseline compatibility validation confirm one
trial, all 37 cases, suite v1.3, dataset, agent, judge, and calibration identity.
Aggregate subjective floors are nonzero and no floor exceeds its source
observation.

The approved baseline replay completed in eight clean non-overlapping chunks:
`836cddbb7a7c4b3fac2caf2183ad8ae6`,
`4ea03f0d440140fbb85fb32436f126a5`,
`d1c7088bb3cb44daa87a3eda8bd18b04`,
`bb602a8434044624a46301ba1473d354`,
`c9a07d2a829e492090a220868bec0e02`,
`886f2fd681dd48f48260665454cf6b88`,
`1d90752041224a5280929aab37eaee0e`, and
`6e34cf7891fe4745b4e47e193f3fcf7d`. The final two are clean retries; their
rate-limited predecessors were retained but excluded from composition.

Offline composition produced valid report
`1984638cc96e4fe9a90bb9dcdc56bd2f` (digest
`5fc333bb8758a7bbc7ffa83470ffff18f16432391f13733db8f12b1833e1390b`).
It covered 37/37 planned trials from all eight chunks with zero infrastructure
failures. Hard safety, the complete baseline comparison, and the final gate all
passed. Status, safety, diagnostics, semantic disposition, and result
correctness passed every eligible trial; grounding passed 36/37, directness
30/36, completeness 31/36, and clarity 35/36. Overall all-grade success was
29/37, and the analytics category was 13/21.

Review of the initial replay comparison identified two additional
single-sample judge-sensitive failures, `completed-count` and
`memory-elliptical-category-ranking`. The manifest records those cases with
zero case floors and uses reviewed aggregate floors of 0.75 overall and 0.60
for analytics; both remain below the observed source rates. The six source
quality failures also remain explicit rather than being silently retried.

This learning-project baseline deliberately uses one trial per case. It proves
current breadth, contract enforcement, and a clean replay, but it does not
establish repeated-run stability. Increase source and replay sample counts
before treating it as release-critical statistical evidence. No partial or
infrastructure-failed report was used as baseline evidence.

## Final OpenSpec verification

- Completeness: 16/16 implementation tasks complete; all five requirements and
  22 scenarios have corresponding runtime, workflow, fixture, documentation,
  or test evidence.
- Correctness: baseline v2 validation, automatic calibrated judging,
  deterministic prerequisites, dimension-separating calibration, strict chunk
  composition, and baseline replay are covered by focused tests and retained
  reports. No critical or warning-level coverage gaps were found.
- Coherence: the implementation follows the design's provider-agnostic judge,
  deterministic-first grading, manual credentialed workflow, offline
  composition, and single-trial learning-baseline decisions. The risk language
  explicitly reserves repeated trials for release-critical use.
- Final assessment: all checks passed; the change is ready for archive. No
  verification dimension was skipped.
