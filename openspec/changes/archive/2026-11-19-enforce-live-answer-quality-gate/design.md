## Context

See `proposal.md` for motivation. QueryForge already has a provider-agnostic answer judge, strict JSON verdicts, a versioned calibration fixture, and opt-in directness, completeness, and clarity grades. The current baseline schema contains only deterministic dimensions, and baseline-backed runs do not request the judge. Development suite v1.3 also makes the committed v1.2 baseline incompatible.

## Goals / Non-Goals

**Goals:**

- Make subjective answer quality an explicit, comparable part of approved live evidence.
- Pin every variable that materially affects subjective comparison: judge provider, judge model, calibration version, and calibration digest.
- Fail closed before scored trials when baseline or judge compatibility is absent.
- Keep deterministic safety, correctness, diagnostics, and grounding authoritative.

**Non-Goals:**

- Treat an LLM judge as a safety control or ground truth for returned values.
- Expose or grade hidden model reasoning.
- Add a second judge implementation, service, dependency, or automatic PR trigger.
- Change normal unjudged reference runs or ad-hoc live runs that do not use a baseline.

## Decisions

### Replace the baseline manifest with version 2

The baseline dimension contract will require `directness`, `completeness`, and `clarity`, and a small judge identity object will record provider, model, calibration version, and calibration digest. Supporting optional subjective fields in v1 was rejected because it would allow an apparently approved baseline to omit the exact quality goal this change is meant to enforce.

### Baseline selection automatically requires the judge

Supplying `--baseline` will enable the existing calibrated judge path even when `--judge-answers` is absent. Ad-hoc runs retain the current explicit flag. Judge construction and calibration occur before scored trials; the active judge and calibration identities are compared to the manifest before proceeding.

Ordered baseline flow:

1. Load and structurally validate the v2 manifest.
2. Validate suite, cases, trials, agent provider/model, and database identity.
3. Construct and calibrate the answer judge.
4. Validate judge provider/model plus calibration version/digest.
5. Run trials; apply deterministic grades first and subjective grades only to eligible trials.
6. Compare every approved floor, hard safety, infrastructure failures, and per-case rates.
7. Persist redacted JSON and Markdown evidence and return the gate exit code.

### Keep subjective grades downstream of deterministic grades

The existing prerequisite rule remains: the judge runs only when status, safety, result, diagnostics, and grounding pass. This prevents fluent prose from hiding an incorrect or unsafe answer and gives subjective rates an explicit eligible-trial denominator in the report.

### Strengthen the existing calibration fixture

The same versioned fixture will gain reviewed dimension-separating examples. The loader will reject a fixture that has no expected verdict pattern in which the dimensions differ. This is smaller than adding a new benchmark system and demonstrates that the judge can apply the three rubrics independently.

### Pin the workflow judge model

The credentialed workflow will set `QUERYFORGE_EVAL_JUDGE_MODEL` explicitly and continue using the baseline-owned case selection and trial count. The workflow remains manually dispatched, secret-scoped, fail-closed, and artifact-retaining.

### Update the evaluation architecture diagram

The evaluation flow changes materially because baseline loading now requires calibration and subjective comparison before a pass. The existing evaluation diagram and documentation will be updated; the agent runtime diagram and public result contract do not change.

### Compose staged case chunks instead of requiring one large provider run

The existing `--case` selection will execute non-overlapping chunks with the same trial count and pacing. A small offline composition command will load the persisted JSON reports, verify their stored digests and pinned identities, require exact full-suite case coverage with no duplicates, recompute the summary from retained trials, and write one composed report that lists every source report. Provider-using chunks must agree on one agent provider/model; local-policy-only chunks that correctly make no agent call inherit that effective identity while retaining their own explicit judge identity. When an approved baseline is supplied, composition will apply the existing baseline comparison to the composed trials.

Composition performs no provider calls and cannot turn an invalid, infrastructure-failed, partial, identity-mismatched, or duplicate chunk into evidence. Source chunks remain individually reviewable. The learning-project baseline runs one trial for every case. Chunks contain at most five cases and use 60-second provider-call pacing so calibration, agent, repair, judge, and retry calls do not burst within one trial under the active 8,000-token-per-minute account limit. Stages may span quota-reset periods; every source chunk still uses identical code and settings.

One trial preserves full case breadth at practical cost but does not measure run-to-run stability. Raising both source and replay evidence to at least three trials per case is the explicit upgrade path before release-critical use; the baseline contract keeps the trial count pinned so source and replay cannot silently use different confidence levels.

Adding resumable in-process state was rejected because it introduces mutable checkpoint semantics into the evaluator. Hand-merging reports was rejected because it would not provide reproducible validation or source digests.

## Risks / Trade-offs

- **[Risk] Judge verdicts can vary even at temperature zero.** → Pin judge and calibration identity, preserve verdict reasons, set reviewed floors no higher than clean source observations, and explicitly require repeated trials before release-critical use.
- **[Risk] The agent model may also be the judge model.** → Treat semantic grades as regression signals only; deterministic grounding and result checks remain authoritative and the identity is explicit in evidence.
- **[Risk] Extra calls increase runtime, quota use, and rate-limit exposure.** → Keep the gate manual, retain pacing, classify judge/provider failures separately, and never discard them from evidence.
- **[Risk] Skipped subjective grades could hide deterministic failures.** → Trial pass still requires deterministic grades, and baseline comparison separately enforces deterministic dimensions, per-case floors, hard safety, and zero infrastructure failures.
- **[Risk] A new baseline could normalize known defects.** → Require an infrastructure-clean source report, manual transcript review, nonzero subjective floors, exact suite identity, and recorded approval rationale.
- **[Risk] Chunk composition could hide missing or incompatible evidence.** → Require exact case coverage, identical pinned identities, verified report digests, full trial counts, retained source identifiers, and the existing hard-safety/infrastructure checks before composition succeeds.

## Migration Plan

1. Add and test the v2 contract and mandatory baseline judge behavior.
2. Strengthen and validate the calibration fixture.
3. Update workflow, documentation, and evaluation diagram.
4. Run the single-trial judged development v1.3 evaluation as non-overlapping chunks of at most five cases with 60-second provider-call pacing and compose them only after strict compatibility and coverage validation.
5. Review chunk transcripts and the composed report, then author the v2 manifest from observed rates without raising floors above evidence.
6. Replay the one-trial v2 baseline as new non-overlapping chunks with the same size and pacing, compose them with the approved baseline, and retain the final gate report reference.

Rollback requires reverting evaluator code, workflow/documentation, calibration fixture, and baseline manifest together. The v1 baseline must not be silently accepted by v2 code.
