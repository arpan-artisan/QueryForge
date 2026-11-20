# QueryForge Quantitative Metrics Report

Audit date: 2026-11-20 (Asia/Calcutta)  
Repository revision at audit start: `85c5e267b2ef087938905d47837a5d2c367481ca`  
Repository state at audit start: clean  
Current code digest: `63e5e08588bf3cbb5bf949721e1bc65a107d500bfbd63ce9cfc4ab8a7f63a391`  
Current prompt/code digest: `6aa8c3c1353c74a1575b929b903b44631f7a115fc6d7ac64cdd76bab8c01a43c`

## Executive summary

Current deterministic evidence is clean: 656 tests passed, no tests failed, and both reference suites passed all 47 cases against the real local PostgreSQL fixture. These reference results validate the harness, policies, runtime, and database contract; they do not measure LLM accuracy.

The strongest recent live development evidence is a valid, infrastructure-clean, composed one-trial replay over 37 unique cases using Groq `openai/gpt-oss-20b` with calibrated answer-quality judging. It achieved 29/37 overall task success, 21/21 correct SQL execution results, 37/37 correct semantic dispositions, 36/37 deterministic answer grounding, 9/9 blocked-request rejection, and zero unauthorized executions. Eight failures remained visible, all on analytical answer quality; one query required a repair and recovered successfully.

The valid live release report covered 10 unique cases and achieved 7/10 overall task success, 6/6 correct SQL execution results, 10/10 semantic dispositions, 2/2 blocked-request rejection, and zero infrastructure or unauthorized-execution failures. Its three failures were deterministic metric-label grounding failures despite correct returned data. Directness, completeness, and clarity were not judged in that release report.

These live observations are historical rather than measurements of the exact current commit. Their suite and dataset identities still match, but their source and prompt digests predate the current web-MVP changes. No new paid live run was launched because valid recent reports already existed and a full judged 3× run would be quota-heavy. Current live performance therefore requires further testing before it is described as a property of revision `85c5e267…`.

## Evidence classification

| Evidence class | Primary evidence | What it supports | What it does not support |
| --- | --- | --- | --- |
| Current actual measurements | Fresh pytest run and current reference reports | Current test health, reference contracts, DB readiness, deterministic safety/runtime behavior | LLM accuracy |
| Historical live development observation | `evaluation-results/live-quality-replay-v2/composed/1984638cc96e4fe9a90bb9dcdc56bd2f/report.json` | Observed Groq agent behavior across 37 development cases with calibrated judging | Exact current-commit behavior or repeated-run stability |
| Historical live release observation | `evaluation-results/76ad08dd0d384ded9f5943e7da84fbb4/report.json` | Observed Groq agent behavior across 10 release cases | Subjective answer-quality dimensions or exact current-commit behavior |
| Historical consistency observation | `evaluation-results/874fedc7cb56422eb9fb5479c34616bb/report.json` | Three trials per each of 37 older development cases | Current suite/prompt stability |
| Historical baseline observation | `evaluation-results/live-quality-source-v3/composed/c65d91e6ca07465eb7397da585c2a4e7/report.json` | Reviewed one-trial baseline source rates | Acceptance thresholds or current behavior |
| Baseline acceptance thresholds | `evals/ask-data/live-baseline.json` | Regression gate floors approved for the learning project | Observed performance |

## Required metric table

| Metric | Actual value | Numerator/Denominator | Evidence file | Evaluation method | Limitations | Resume-ready |
| --- | --- | --- | --- | --- | --- | --- |
| Tests collected | 664 | 664 collected | Pytest console output; `tests/` | `uv run pytest --collect-only -q` | Collection count, not coverage | Yes |
| Tests passed | 656 | 656/664 collected | Pytest console output | Full `uv run pytest` | 8 opt-in eval/DB tests skipped | Yes |
| Test pass rate, collected denominator | 98.8% | 656/664 | Pytest console output | Passed divided by all collected items | Skips lower this rate without indicating a failure | Yes, with denominator |
| Test pass rate, executed denominator | 100.0% | 656/656 | Pytest console output | Passed divided by passed + failed | Excludes skips | Yes |
| Failed tests | 0 | 0/664 | Pytest console output | Full suite | None observed in this run | Yes |
| Skipped tests | 8 | 8/664 | Pytest console output | Full suite | Opt-in reference-suite PostgreSQL tests require `QUERYFORGE_TEST_EVAL_DB=1` | No |
| Deselected tests | 0 | 0/664 | Pytest console output | Full suite | None | No |
| Ruff static checks | Passed | 1/1 command | Ruff console output | `uv run ruff check .` | Static analysis, not runtime validation | Yes |
| Unit test cases | 503 | 503/503 passed | `tests/unit/` | Path-specific pytest collection plus full-suite outcome | Parametrized cases count as separate tests | Yes |
| Integration test cases | 4 | 4/4 passed | `tests/integration/` | Path-specific collection plus full-suite outcome | Local deterministic demo DB only | Yes |
| Evaluation-harness test cases | 157 | 149 passed, 8 skipped | `tests/eval_harness/` | Path-specific collection plus full-suite outcome | Eight opt-in tests skipped | Yes, with breakdown |
| Line coverage | N/A | N/A | `pyproject.toml`; environment inspection | Checked for `coverage` and `pytest-cov` | Neither package is installed; no dependency was added | No |
| Branch coverage | N/A | N/A | `pyproject.toml`; environment inspection | Checked for `coverage` and `pytest-cov` | Neither package is installed | No |
| Policy-layer adversarial inputs | 100.0% passed | 151/151 | `tests/unit/policy/` | 62 negative intent-policy cases + 89 negative SQL-policy cases | Mocked/deterministic policy tests; duplicates across deeper layers excluded | Yes, scoped |
| Development reference calibration | 100.0% | 37/37 | `evaluation-results/144e4e4d6c614b71aca16b664828e934/report.json` | Scripted reference provider through real runtime and PostgreSQL | Not LLM accuracy | Yes, only as calibration |
| Release reference calibration | 100.0% | 10/10 | `evaluation-results/04d44ee387cb44bf86ece2b311280f13/report.json` | Scripted reference provider through real runtime and PostgreSQL | Not LLM accuracy | Yes, only as calibration |
| Historical live development task success | 78.4% | 29/37 | `evaluation-results/live-quality-replay-v2/composed/1984638cc96e4fe9a90bb9dcdc56bd2f/report.json` | One infrastructure-clean trial per case with calibrated judge | Historical prompt digest; one trial per case | Yes, explicitly historical |
| Historical live development SQL-result correctness | 100.0% | 21/21 analytical trials | Same development live report | Full returned rows compared with independent references | Small deterministic DB; one trial per case | Yes, with sample size |
| Historical live development answer grounding | 97.3% | 36/37 | Same development live report | Deterministic metric-label/value/scope grounding | Does not measure prose style | Yes |
| Historical live development semantic disposition | 100.0% | 37/37 | Same development live report | Expected vs terminal status | Historical prompt digest | Yes |
| Historical live development directness | 83.3% | 30/36 eligible trials | Same development live report | Calibrated Groq judge after deterministic prerequisites | Same model family judged answers; one run | No, supporting detail only |
| Historical live development completeness | 86.1% | 31/36 eligible trials | Same development live report | Calibrated Groq judge | Subjective judge sensitivity remains | No, supporting detail only |
| Historical live development clarity | 97.2% | 35/36 eligible trials | Same development live report | Calibrated Groq judge | Subjective judge; one run | No, supporting detail only |
| Historical live development blocked rejection | 100.0% | 9/9 | Same development live report | Live-mode local intent policy | Only nine blocked questions | Yes, with sample size |
| Historical live development unsupported handling | 100.0% | 3/3 | Same development live report | Expected unsupported disposition | Very small sample | No |
| Historical live development clarification accuracy | 100.0% | 4/4 | Same development live report | Expected clarification disposition | Very small sample | No |
| Historical live development false rejection | 0.0% | 0/21 legitimate analytics | Same development live report | Counted analytics ending blocked/unsupported/clarification | Does not count answer-quality failures as false rejections | Yes, with definition |
| Historical live development unauthorized execution | 0 | 0/9 blocked trials | Same development live report | Executor-call and executed-SQL audit | Nine blocked trials | Yes |
| Historical live development infrastructure failures | 0 | 0/37 | Same development live report | Report failure-category and baseline-comparison audit | Composed evidence spans several days | Yes |
| Historical live release task success | 70.0% | 7/10 | `evaluation-results/76ad08dd0d384ded9f5943e7da84fbb4/report.json` | One paced live trial per release case | Historical code/prompt digest | Yes, explicitly historical |
| Historical live release SQL-result correctness | 100.0% | 6/6 analytical trials | Same release live report | Full returned rows compared with references | Six analytical questions | Yes, with sample size |
| Historical live release answer grounding | 70.0% | 7/10 | Same release live report | Deterministic grounding | Three correct result sets had insufficient metric labels | No |
| Historical live release semantic disposition | 100.0% | 10/10 | Same release live report | Expected vs terminal status | Historical code/prompt digest | Yes, with sample size |
| Historical live release directness/completeness/clarity | N/A | 0 judged trials | Same release live report | Judge was not requested | Cannot infer subjective rates | No |
| Historical live release blocked rejection | 100.0% | 2/2 | Same release live report | Live-mode local intent policy | Two cases only | No |
| Historical live release unsupported handling | 100.0% | 1/1 | Same release live report | Expected unsupported disposition | One case | No |
| Historical live release clarification accuracy | 100.0% | 1/1 | Same release live report | Expected clarification disposition | One case | No |
| Historical live release false rejection | 0.0% | 0/6 legitimate analytics | Same release live report | Counted incorrect policy dispositions | Six cases | No |
| Historical live release unauthorized execution | 0 | 0/2 blocked trials | Same release live report | Executor-call and executed-SQL audit | Two cases | No |
| Historical live release infrastructure failures | 0 | 0/10 | Same release live report | Failure-category audit | Historical run | Yes, with context |
| Historical development repair success | 100.0% | 1/1 repair attempt | Development live replay | Trace showed initial validation failure, one safe repair, final correct result | One observation is not a reliability estimate | No |
| Historical development first-attempt SQL correctness | 95.2% | 20/21 | Development live replay | Correct result with zero repair attempts | One trial per case | Yes, with final rate |
| Historical development final SQL correctness | 100.0% | 21/21 | Development live replay | Correct result after optional bounded repair | Small deterministic DB | Yes |
| Historical release repair success | N/A | 0/0 | Release live report | No repair trace occurred | Must not be reported as 100% | No |
| Historical release first/final SQL correctness | 100.0% / 100.0% | 6/6 / 6/6 | Release live report | No repair required | Six cases | Yes, with sample size |
| Development trace completeness | 100.0% | 37/37 | Development live replay | Diagnostics grade requires terminal trace and consistent call/result evidence | Historical report | Yes |
| Release trace completeness | 100.0% | 10/10 | Release live report | Same diagnostics contract | Historical report | Yes |
| Token consumption per query | N/A | N/A | Live reports; `src/queryforge/llm.py` | Inspected persisted reports/provider protocol | Token usage is not recorded | No |

## Software testing metrics

The full suite collected 664 tests and completed with 656 passed, 0 failed, 8 skipped, 0 deselected, and one dependency deprecation warning in 50.27 seconds.

`uv run ruff check .` also completed successfully with `All checks passed!`.

| Test area | Collected | Passed | Skipped | Failed |
| --- | ---: | ---: | ---: | ---: |
| Unit | 503 | 503 | 0 | 0 |
| Integration | 4 | 4 | 0 | 0 |
| Evaluation harness | 157 | 149 | 8 | 0 |
| Total | 664 | 656 | 8 | 0 |

The eight skips are the opt-in PostgreSQL reference-suite tests. The current reference CLI runs separately exercised both suites against PostgreSQL, but that is not a substitute for reporting the pytest skips.

Coverage is unavailable. The environment contains neither `coverage` nor `pytest-cov`, and the repository has no coverage configuration or CI coverage step. No package was installed solely to manufacture a coverage number.

GitHub Actions currently:

- runs Ruff, unit tests, integration tests, selected evaluation-harness tests, the opt-in reference-suite integration test, and the development reference evaluation on push and pull request;
- runs the credentialed live baseline only by manual dispatch with a 30-second provider-call delay;
- retains reference and live reports as workflow artifacts;
- does not publish line or branch coverage;
- does not explicitly include `tests/eval_harness/test_composition.py` in the evaluation-harness CI command; and
- does not run the release reference CLI as a separate CI step.

## Current deterministic reference results

| Set | Unique cases | Completed trials | Overall | SQL results | Grounding | Semantic disposition | Blocked | Unsupported | Clarification | Infrastructure failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Development | 37 | 37 | 37/37 | 21/21 | 37/37 | 37/37 | 9/9 | 3/3 | 4/4 | 0 |
| Release | 10 | 10 | 10/10 | 6/6 | 10/10 | 10/10 | 2/2 | 1/1 | 1/1 | 0 |

Both reports were generated from the clean current revision, current code/prompt digests, suite versions `ask-data-development-v1.3` and `ask-data-release-v1.1`, and dataset `queryforge-commerce-v1` with fingerprint `1b4911260c79d7ffa835a9c34c07c71fcbda93389cba0cea110f4f11d5a930b6`.

## Historical live LLM evaluation

### Development replay

The selected development evidence is a valid composed replay over 37 unique cases with one trial per case, Groq `openai/gpt-oss-20b` as both agent and calibrated judge, the expected suite/dataset identity, and zero infrastructure failures. It passed the approved baseline gate while raw task success remained 29/37.

| Dimension | Result |
| --- | ---: |
| Overall task success | 29/37 (78.4%) |
| SQL result correctness | 21/21 (100.0%) |
| Semantic disposition | 37/37 (100.0%) |
| Safety | 37/37 (100.0%) |
| Diagnostics/trace completeness | 37/37 (100.0%) |
| Answer grounding | 36/37 (97.3%) |
| Directness | 30/36 (83.3%) |
| Completeness | 31/36 (86.1%) |
| Clarity | 35/36 (97.2%) |
| Blocked category | 9/9 (100.0%) |
| Unsupported category | 3/3 (100.0%) |
| Clarification category | 4/4 (100.0%) |
| False rejection of analytics | 0/21 (0.0%) |
| Unauthorized SQL executions | 0 |
| Infrastructure failures | 0 |

Failed development cases:

- `completed-count`: directness and completeness.
- `payment-success-rate`: directness and completeness.
- `payment-success-rate-by-method-phrasing`: deterministic answer grounding.
- `memory-elliptical-category-ranking`: completeness.
- `order-lookup`: directness.
- `refund-rate`: directness and completeness.
- `historical-price`: directness, completeness, and clarity.
- `empty-aggregate`: directness.

All eight ended with status `ok`; all 21 analytical result grades passed. These are answer-quality failures, not unsafe or incorrect database execution.

### Release assessment

| Dimension | Result |
| --- | ---: |
| Overall task success | 7/10 (70.0%) |
| SQL result correctness | 6/6 (100.0%) |
| Semantic disposition | 10/10 (100.0%) |
| Safety | 10/10 (100.0%) |
| Diagnostics/trace completeness | 10/10 (100.0%) |
| Answer grounding | 7/10 (70.0%) |
| Directness/completeness/clarity | N/A; judge not requested |
| Blocked category | 2/2 (100.0%) |
| Unsupported category | 1/1 (100.0%) |
| Clarification category | 1/1 (100.0%) |
| False rejection of analytics | 0/6 (0.0%) |
| Unauthorized SQL executions | 0 |
| Infrastructure failures | 0 |

Failed release cases:

- `release-completed-orders-by-month`: correct rows, missing accepted metric label.
- `release-succeeded-payment-amount-by-method`: correct rows, missing accepted metric label.
- `release-pending-order-value`: correct scalar result, missing accepted metric label.

### Three-trial consistency evidence

An older valid report ran three trials per each of 37 development cases: 111 completed trials, 98/111 overall success (88.3%), 62/63 SQL-result correctness (98.4%), 99/111 answer grounding (89.2%), 33/37 tasks passing at least once (89.2%), and 32/37 tasks passing every trial (86.5%). It recorded no infrastructure failures and no unauthorized executions.

Four cases failed all three trials (`completed-count`, `average-order-value`, `orders-by-status`, and `customer-ranking`); `memory-elliptical-category-ranking` passed two of three. This is useful historical consistency evidence, but it uses suite v1.2 and older code/prompt digests, so it must not be presented as current stability.

No fresh 3× run was started. At the current 47-case scope, a judged 3× run can require hundreds of agent/judge calls and substantial daily tokens. Groq documents a 131,072-token context window and 65,536 maximum output tokens for `openai/gpt-oss-20b`. Its rate-limit documentation states that exact organization limits are account-specific and exposes limits through the account page and response headers; the public conservative table shows 30 RPM, 8K TPM, and 200K TPD for this model. See [Groq rate limits](https://console.groq.com/docs/rate-limits) and [Groq GPT-OSS 20B](https://console.groq.com/docs/model/openai/gpt-oss-20b).

## Baseline observations versus thresholds

The approved baseline is `development-groq-gpt-oss-20b-v2`. The source observation and acceptance floors are intentionally different:

| Metric | Historical source observation | Approved floor | Replay observation | Replay passed floor |
| --- | ---: | ---: | ---: | --- |
| Overall trials | 83.8% | 75.0% | 78.4% | Yes |
| Semantic disposition | 100.0% | 100.0% | 100.0% | Yes |
| Safety | 100.0% | 100.0% | 100.0% | Yes |
| SQL result | 100.0% | 100.0% | 100.0% | Yes |
| Diagnostics | 100.0% | 100.0% | 100.0% | Yes |
| Answer grounding | 97.3% | 95.0% | 97.3% | Yes |
| Directness | 86.1% | 80.0% | 83.3% | Yes |
| Completeness | 88.9% | 80.0% | 86.1% | Yes |
| Clarity | 94.4% | 90.0% | 97.2% | Yes |
| Analytics category | 71.4% | 60.0% | 61.9% | Yes |
| Blocked category | 100.0% | 100.0% | 100.0% | Yes |
| Unsupported category | 100.0% | 100.0% | 100.0% | Yes |
| Clarification category | 100.0% | 100.0% | 100.0% | Yes |

The gate also includes per-case floors; eight reviewed cases have zero floors. Therefore a passing gate is evidence that the approved regression policy passed, not that every case passed.

## SQL guardrail metrics

The current policy test inventory contains 151 distinct collected negative/adversarial examples at the policy layer:

- 62 intent-policy inputs: destructive operations, prompt/policy bypass, sensitive data, administration/system access, resource abuse, broad dumps, conflicts, and memory-context attacks.
- 89 SQL-policy inputs: unauthorized identifiers, unsafe casts/modifiers/nested operands, system metadata, prohibited functions, comments, stacked statements, mutations, locking, `SELECT INTO`, set operations, recursive CTEs, star projections, cross joins, malformed SQL, and aggregate-grain fanout.

All 151 passed. An additional 16 collected cross-layer defense-in-depth cases exercise graph stopping, executor revalidation, memory isolation, unsafe repair, and evaluation-harness adversarial outputs. These are not added to the 151 unique-input count because several repeat the same threat at another boundary.

| Guardrail | Result | Evidence | Evidence type |
| --- | ---: | --- | --- |
| Destructive natural-language rejection | 19/19 (100.0%) | `tests/unit/policy/test_intent_policy.py::test_blocks_destructive_intents` | Mocked/deterministic unit policy |
| Prompt/policy injection rejection | 9/9 (100.0%) | `tests/unit/policy/test_intent_policy.py::test_blocks_bypass_intents` | Mocked/deterministic unit policy |
| Unauthorized table/column/schema/alias prevention | 6/6 (100.0%) | `tests/unit/policy/test_sql_allowlist.py::test_classifies_unknown_business_identifiers_as_unsupported` | Mocked/deterministic SQL policy |
| Multiple-statement rejection | 2/2 (100.0%) | `test_sql_prohibited_constructs.py`, `test_sql_casts.py` | Mocked/deterministic SQL policy |
| Data-modifying CTE rejection | 4/4 (100.0%) | `test_sql_prohibited_constructs.py::test_blocks_data_modifying_ctes` | Mocked/deterministic SQL policy |
| Unsafe repair boundary | 10/10 (100.0%) | `test_repair.py`, graph repair tests, eval grading test | Seven nonrepairable inputs plus three end-to-end boundaries |
| Live blocked development requests | 9/9 (100.0%) | Historical development replay | Live-mode local intent policy |
| Live blocked release requests | 2/2 (100.0%) | Historical release report | Live-mode local intent policy |
| Live unauthorized SQL executions | 0 | Both historical live reports | Executor-call and executed-SQL evidence |

Mocked policy results and live observations are intentionally separate. The live blocked requests are handled deterministically before the provider, so they measure deployed runtime policy behavior, not the LLM's willingness to refuse.

## Self-correction metrics

The historical development replay contains one observed repair:

- `net-revenue` first generated SQL without a required subquery alias.
- SQL validation returned `missing_subquery_alias` before execution.
- One repair was generated, revalidated as allowed, executed once, and returned the correct result.

| Set | Repair attempts | Successful repairs | Repair success | First-attempt correctness | Final correctness |
| --- | ---: | ---: | ---: | ---: | ---: |
| Historical live development | 1 | 1 | 1/1 (100.0%) | 20/21 (95.2%) | 21/21 (100.0%) |
| Historical live release | 0 | 0 | N/A | 6/6 (100.0%) | 6/6 (100.0%) |
| Current reference suites | 0 | 0 | N/A | 27/27 (100.0%) | 27/27 (100.0%) |

The 1/1 repair result is a single observation and is not resume-ready as a reliability percentage. Unit and harness tests separately verify bounded one-shot repair, retry stopping, unsafe-repair revalidation, and nonrepairability of blocked SQL.

## Performance and observability

### Latency method

Trial `duration_ms` is measured around the agent runtime before answer judging. Judge latency is therefore excluded, but no separate judge-duration field is stored.

The development live chunks used a 60-second minimum pause between every provider call. That pause is inside the trace step durations. To estimate pacing-excluded agent and LLM latency, this audit subtracts exactly 60,000 ms per recorded agent model call from trial duration and from each provider trace step. This is reproducible but remains an estimate because scheduler overhead and provider time are not separately recorded.

The older release run used a 20-second inter-trial delay outside the measured trial duration, so its stored agent and provider timings already exclude pacing.

Nearest-rank P95 is used throughout.

| Metric | Development historical live | Release historical live | Sample/method |
| --- | ---: | ---: | --- |
| Raw end-to-end mean | 83,522.61 ms | 1,144.53 ms | All 37 / 10 trials; development includes 60 s/call pacing |
| Raw end-to-end median | 122,125.56 ms | 1,757.32 ms | All trials |
| Raw end-to-end P95 | 244,878.89 ms | 2,114.14 ms | All trials |
| Pacing-excluded end-to-end mean | 2,441.53 ms estimated | 1,144.53 ms measured | All trials |
| Pacing-excluded end-to-end median | 2,125.56 ms estimated | 1,757.32 ms measured | All trials |
| Pacing-excluded end-to-end P95 | 7,647.53 ms estimated | 2,114.14 ms measured | All trials |
| Successful analytical response mean | 4,197.52 ms estimated | 1,904.75 ms measured | 21 / 6 analytical trials |
| SQL execution mean | 94.61 ms | 79.84 ms | 24 / 6 successful query-execution trace steps |
| SQL execution median | 89.21 ms | 80.85 ms | Query-execution steps |
| SQL execution P95 | 129.60 ms | 90.56 ms | Query-execution steps |
| LLM response mean per call | 1,743.52 ms estimated | 904.17 ms measured | 50 / 12 provider trace steps |
| LLM response median per call | 1,206.69 ms estimated | 931.36 ms measured | Provider trace steps |
| LLM response P95 per call | 4,041.14 ms estimated | 1,073.96 ms measured | Provider trace steps |
| LLM calls per correct analytical result | 2.33 | 2.00 | 49/21 and 12/6; includes prior turns and repair |
| Token consumption | N/A | N/A | Provider usage is not persisted |
| Trace completeness | 37/37 (100%) | 10/10 (100%) | Deterministic diagnostics grade |

Current reference-only runtime latency was 59.92 ms mean / 79.27 ms median / 168.37 ms P95 for development and 139.13 ms / 132.41 ms / 360.19 ms for release. These figures include real PostgreSQL but a scripted provider and must not be quoted as live LLM latency.

### Langfuse and local traces

QueryForge always builds bounded local traces with trace IDs, terminal status, ordered step timings, policy metadata, generated/normalized SQL where permitted, row counts, bounded previews, and export errors. Secret-like keys, bearer tokens, database URLs with passwords, and configured secret values are redacted; long strings and result previews are bounded.

Langfuse export is optional and fail-open for observability: exporter failure is recorded without changing the query result. The current environment has no Langfuse provider or credentials configured, so the no-op exporter is active. Evaluation runs intentionally retain local reports and do not export to Langfuse. Therefore this audit has no external Langfuse latency or availability measurements.

All 37 telemetry unit tests passed: 9 configuration tests, 7 recorder/exporter tests, and 21 trace-contract/redaction tests.

## Exact commands executed

Primary verification commands:

```powershell
git rev-parse HEAD
git status --short
uv --version
uv run python --version
uv run queryforge check-db
uv run pytest --collect-only -q tests
uv run pytest --collect-only -q tests/unit
uv run pytest --collect-only -q tests/integration
uv run pytest --collect-only -q tests/eval_harness
uv run pytest
uv run ruff check .
uv run python -c "import importlib.util; ..."
uv run queryforge evals run --mode reference --evaluation-set development
uv run queryforge evals run --mode reference --evaluation-set release
```

Read-only analysis scripts parsed persisted `report.json` files to verify identities, recompute nearest-rank percentiles, classify failures, count repairs/model/executor calls, and inspect trace steps. Source files, suites, baseline, workflows, and telemetry/security tests were inspected with PowerShell and `rg`.

No new `queryforge evals run --mode live` command was executed. No database initialization command was executed manually, no baseline was modified, and no application behavior was changed.

## Environment

| Component | Value |
| --- | --- |
| OS | Microsoft Windows 11 Home Single Language, 64-bit, build 10.0.26200 |
| Python | 3.14.0 |
| uv | 0.11.17 |
| PostgreSQL | 16.15, repository Docker demo service |
| Current dataset | `queryforge-commerce-v1` |
| Dataset fingerprint | `1b4911260c79d7ffa835a9c34c07c71fcbda93389cba0cea110f4f11d5a930b6` |
| Live provider/model in historical evidence | Groq / `openai/gpt-oss-20b` |
| Current Langfuse configuration | Disabled/unconfigured; local traces only |

Provider and model configuration names were read from redacted report metadata. API keys and credentials were never printed.

## Metrics requiring further testing

- A clean live development and release run at current code digest `63e5e085…` and prompt digest `6aa8c3c1…`.
- Three infrastructure-clean judged trials per current case, composed from quota-safe chunks.
- Current release directness, completeness, and clarity.
- Line and branch coverage after deliberately adding and configuring a coverage tool.
- Provider token usage and cost after adding non-secret usage telemetry.
- Direct pacing-free and judge-latency measurements; current development timings require subtraction of known pacing.
- Repair reliability beyond the single observed successful live repair.
- Concurrency, soak, cold-start, larger-data, alternate-seed, and production-network performance.
- External Langfuse delivery success and latency in a configured environment.

## Resume-ready bullets

- Built a Python/LangGraph NL-to-SQL evaluation pipeline integrating Groq GPT-OSS 20B and PostgreSQL, validating 21/21 analytical result sets, 37/37 semantic dispositions, and 37/37 complete traces in an infrastructure-clean 37-case live development replay.
- Hardened SQL execution with sqlglot allowlisting, bounded repair, and read-only PostgreSQL controls, passing 151 policy-layer adversarial inputs and preventing unauthorized execution in 11/11 historical live blocked-request trials.
- Established a 664-case Pytest and GitHub Actions quality workflow with local/Langfuse-compatible observability and secret redaction, completing 656 tests with zero failures and calibrating 47/47 current reference cases against the deterministic demo database.

## Interview-safe interpretation

Defensible with evidence open:

- 656 passed, 0 failed, 8 skipped from 664 collected tests.
- 37/37 development and 10/10 release reference calibration, explicitly described as deterministic rather than LLM accuracy.
- Historical live development: 21/21 SQL results, 37/37 semantic dispositions, 36/37 grounding, 29/37 overall, and 0 infrastructure failures.
- Historical live release: 6/6 SQL results, 10/10 semantic dispositions, 7/10 overall, and three named grounding failures.
- 151/151 scoped policy-layer adversarial inputs and zero unauthorized execution in the cited live blocked cases.
- One successful repair from one observed attempt, stated as a single example rather than a reliability claim.
- Latency only with its measurement boundary, pacing adjustment, and sample size.

Not defensible yet:

- Claiming that historical live metrics measure the exact current commit.
- Claiming statistically reliable model consistency from one-trial development/release evidence.
- Claiming production performance, production deployment, user adoption, business impact, or arbitrary-database correctness.
- Claiming line/branch coverage, token cost, release subjective-answer quality, or general repair reliability.
