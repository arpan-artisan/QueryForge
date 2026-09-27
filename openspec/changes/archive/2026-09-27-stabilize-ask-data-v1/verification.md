# Ask Data v1 Stabilization Verification

## Environment and Source

- Baseline date: 2026-09-27, Asia/Calcutta.
- Tested revision: `6e198f69c0b5234c2a420771ee10e3942b856199`.
- Baseline working tree: only `openspec/changes/stabilize-ask-data-v1/` was untracked; no tracked source or test changes. The report records `dirty: true` because of these planning artifacts.
- Local test environment: Windows, Python 3.14.0, pytest 9.1.1. This run does not establish results for other Python versions.
- Code digest: `7e0045f895555852bfa737c161a6d08b4f1623b5701b2f4844ac0526b0d84a77`.
- Suite: `ask-data-v1.1`, 35 cases (25 development, 10 held-out), one reference trial per case.
- Suite digest: `d944e773915fb99a5044ddf1c56715da807184a2ce7db11a4552073186cf7741`.
- Dataset: `queryforge-commerce-v1`, seven approved tables.
- Dataset fingerprint: `1b4911260c79d7ffa835a9c34c07c71fcbda93389cba0cea110f4f11d5a930b6`.
- Content digest: `b1666fafb0a5ffa4d7954343a111b35cdaa8c3a7cb56d277e456b3ad01187e8e`.
- Provider evidence: scripted reference provider only; no hosted LLM called for this baseline.

The assistant implements code, tests, Markdown records, and task tracking unless the user explicitly takes over a specific task. Later code, test, or suite changes require relevant verification again.

## Verification Results

These results were observed during the baseline tool runs. Test/static-check output is in the task conversation; no separate persisted pytest log was generated.

| Check | Outcome | Evidence type |
| --- | --- | --- |
| Initial `docker compose ps` and `uv run queryforge check-db` | No running project container; readiness timed out, exit 1 | Local infrastructure observation |
| `docker compose up -d --wait postgres` | Container healthy, exit 0 | Local Docker |
| `uv run queryforge check-db` after startup | Ready; expected fingerprint and all seven table counts match, exit 0 | Real Postgres |
| `uv run pytest -ra` with `QUERYFORGE_TEST_EVAL_DB=1` | 520 passed, 0 failed, 0 skipped, 18.88 seconds, exit 0 | Deterministic tests, including real Postgres integration |
| `uv run queryforge check-db` after tests | Ready with the expected fingerprint, exit 0 | Real Postgres |
| `uv run queryforge evals run --mode reference --split all` | Valid report; 35/35 passed, exit 0 | Scripted harness calibration against real Postgres |
| `uv run ruff check .` | All checks passed, exit 0 | Static analysis |
| `openspec validate stabilize-ask-data-v1 --strict` | Passed, exit 0 | Planning validation |
| `openspec validate --specs` | 8 passed, 0 failed, exit 0 | Main-spec validation |

Integration tests ran serially before the standalone reference eval. The Postgres integration tests intentionally reinitialized the disposable demo fixture and exercised stale-state recovery; no standalone `init-db` command was needed to recover initial readiness. The full reference run checked content stability and finished with no setup error.

Reference run: `2c484aa89fa942a5b255176eefd01f8d`, 18:24:18 to 18:24:26 +05:30. Local reports are under ignored `evaluation-results/2c484aa89fa942a5b255176eefd01f8d/` (`report.json` and `report.md`). They are not committed; the identifiers, commands, source/dataset identities, and summary here preserve the reviewable baseline.

Reference results: analytics 20/20; blocked 9/9; unsupported 3/3; clarification 3/3. Status, safety, and diagnostics grades each passed 35/35; analytical result grades passed 20/20. There were no reported failure categories. These are existing grader results, not a completed independent audit of their coverage.

### Task 2.1: Minimum Split Counts

The user replaced the exact split-count equality in `tests/test_evals.py` with a `Counter` and independent minimum assertions (`dev >= 25`, `held-out >= 10`). Review of the on-disk diff confirmed that category membership, reference SQL, and prior-turn SQL checks were unchanged. The exact category-set assertion still rejects a split missing a required category; this was established by code review, not a new fault-injection run. Suite loading and its unique-ID validation were not changed.

User-reported command: `uv run pytest tests/test_evals.py -k curated_suite`. Result: 1 passed, 77 deselected in 0.72 seconds, on Python 3.14.0 / pytest 9.1.1. Deselection came from the name filter and is not an integration-test skip. The assistant reviewed the change and accepted this supplied result without rerunning the same test. No full post-edit suite run is claimed.

### Task 2.2: Dynamic Integration Counts

The user replaced fixed trial/trace counts with suite size times trials per case and now counts analytics cases directly from the input suite to derive expected analytics passes. Setup, success, and unchanged-database assertions remain intact. Earlier attempts failed first on an incorrect analytics multiplier and then on a missing newline; see TEST-001 for that evidence.

After the corrections, the assistant ran `uv run pytest tests/test_evals_integration.py -k full_reference -ra` with `QUERYFORGE_TEST_EVAL_DB=1`: 1 passed, 6 deselected in 12.12 seconds, exit 0. This exercised the full scripted reference suite against real Postgres. `uv run ruff check tests/test_evals_integration.py` also passed. Task 2.2 is complete. No code was changed by the assistant. Minor spacing/trailing whitespace remains for the final formatting/diff check; a lint pass is not a formatter check.

### Task 2.3: Remove Documentation-Only Tests

The user explicitly delegated these deletions to the assistant. Removed `test_evaluation_docs_describe_current_v1_gate` and its unused `Path` import from `tests/test_evals.py`, and `test_demo_database_docs_expected_facts_match_contract` with its `json`, `re`, and `Path` imports from `tests/test_demo_database.py`. Kept existing user edits, runtime schema-context checks, fixture facts, SQL policy checks, and evaluation grading/reporting tests.

Verification: `uv run pytest tests/test_evals.py tests/test_demo_database.py` passed all 80 tests in 10.28 seconds; `uv run ruff check tests/test_evals.py tests/test_demo_database.py` and the scoped `git diff --check` both exited successfully. No hosted LLM or full post-change integration suite was run for these deletions. Documentation review remains manual under task 6.1. The assistant now owns subsequent coding and documentation tasks unless the user explicitly takes over one.

### Coverage Review Status

### Task 3.1: Result, CLI, Intent, and Clarification Review

The assistant reviewed `tests/test_answers.py`, `tests/test_cli.py`, `tests/test_intent_policy.py`, and the relevant success/local-policy paths in `tests/test_ask_data_graph.py`. The existing checks cover multi-row answer values and bounded previews; inspectable successful CLI JSON; blocked, unsupported, and clarification statuses; original-question and trace identity visibility; policy reasons; and absence of provider/executor calls after local intent rejection. The graph tests independently verify that blocked, unsupported, and clarification paths skip model generation and database execution.

Focused verification: `uv run pytest tests/test_answers.py tests/test_cli.py tests/test_intent_policy.py tests/test_ask_data_graph.py` passed 160 tests in 9.46 seconds. This is deterministic behavior evidence using stubs and local policy code; it is not live-model or real-Postgres evidence.

The real reference suite contains the `missing-order` case and verifies that an empty result completes successfully with empty structured rows, but grading only requires non-empty answer text. The assistant added one direct assertion for the exact user-visible no-rows answer. It did not add a duplicate graph test or modify the graph stub because the real reference evaluation already covers runtime execution and structured empty rows.

The assistant also removed `test_intent_policy_has_no_provider_sql_policy_or_database_imports`, which searched source text for import strings. Runtime graph/CLI tests already verify the actual boundary: rejected intent does not resolve a provider, request SQL, or call the executor. After these changes, the focused command passed 160 behavior tests in 8.77 seconds; Ruff and scoped diff checks passed. Task 3.1 is complete.

| Area | Baseline evidence | Remaining review |
| --- | --- | --- |
| Successful analytics, rejection, clarification | Reference categories and focused tests passed; manual Groq prompts returned expected result/policy outcomes | Complete for the v1 stabilization scope |
| Unsafe SQL and repair success/exhaustion | Focused safety/repair review included in 358 passing tests; one repair and pre-execution rejection are asserted | Complete for the v1 stabilization scope |
| Follow-ups, isolation, missing context, memory failures | Focused tests passed; manual chat reproduced and verified MEM-001; live development case passed | Broader conversational ellipsis remains a documented limit |
| Provider and observability failures/redaction | Simulated failure paths passed; bounded live development and held-out samples completed | No full-provider reliability claim from eight live trials |
| Database permissions, readiness, execution, drift | 3 Postgres integration and 7 eval integration tests passed; final readiness and 36-case reference gate passed | Complete for the v1 stabilization scope |
| Live-model capability | Development sample 4/4; exposed held-out sample 4/4 with Groq `openai/gpt-oss-20b` | Remaining 6 held-out cases were not live-tested |
| Final source verification, docs, diagrams, secret review | Ruff, 519 tests, OpenSpec, diff, ignore, docs, diagrams, and Ponytail review completed | Archive and push remain separate actions |

### Tasks 3.2-3.4: Safety, Repair, Memory, Provider, and Diagnostics

The assistant reviewed the focused assertions and ran `uv run pytest tests/test_sql_safety.py tests/test_tools.py tests/test_repair.py tests/test_ask_data_graph.py tests/test_evals.py tests/test_memory.py tests/test_llm.py tests/test_observability.py`: 358 passed in 11.68 seconds. No missing behavior check justified another test.

Safety and repair evidence includes executor revalidation before connecting, unsafe repaired SQL rejection, no repair for blocked SQL, successful validation and execution repair, one-attempt exhaustion, non-repairable execution failure, and repair-provider failure without another retry. Memory evidence includes same-session context, session isolation, bounded successful-turn context, missing context, read/write failures, and explicit proof that remembered content cannot approve unsafe SQL. Provider and diagnostic evidence includes timeout, network, HTTP, empty/invalid response normalization; recorder/export failure containment; secret-value redaction; bounded strings and row previews; and traceable terminal results. Provider, recorder, exporter, and memory failure paths here use controlled doubles or monkeypatches; they are deterministic simulations rather than hosted-provider evidence.

### Task 3.5: Real Postgres and Evaluation Boundaries

`uv run pytest tests/test_postgres_integration.py -ra` passed all 3 tests in 3.46 seconds against real Postgres. These tests exercise initialization, read-only role privileges, stale-volume reset, and expected analytical facts. `uv run queryforge check-db` then reported the expected `queryforge-commerce-v1` fingerprint, all seven table counts, and matching business facts.

The database-mutating tests completed before the separate evaluation run. With `QUERYFORGE_TEST_EVAL_DB=1`, `uv run pytest tests/test_evals_integration.py -ra` passed all 7 tests in 8.85 seconds against real Postgres. The exercised assertions cover the full reference suite, a previously failing monthly-revenue query, validated numeric casts, invalid conversion classification, and content-drift detection. Unit-level setup, reference, grading, and failure-category checks in `test_evals.py` use controlled boundaries; they do not substitute for the real-Postgres integration evidence.

## Defects

### TEST-001: Analytics Expectation Multiplies Two Counts

- Classification: test expectation defect introduced during task 2.2; resolved and verified.
- Reproduction: run the focused full-reference integration test with the real demo database and `QUERYFORGE_TEST_EVAL_DB=1`.
- Expected behavior: expected analytics trials equal analytics cases in the suite times trials per case (20 times 1 for this suite).
- Original behavior: the edited test computed 35 times 1 times 20, expecting 700 analytics passes; the report correctly contained 20.
- Requirement: versioned balanced evaluation tasks must accommodate suite growth; derive the expected count from the suite rather than multiplying it by observed report totals.
- Regression evidence: the first run of `test_full_reference_suite_uses_postgres_and_preserves_content` failed at the analytics assertion (1 failed, 6 deselected in 13.42 seconds). The user then corrected the calculation to count analytics cases, but joined the assignment and next `assert` on one line. The next focused pytest run stopped during collection with a syntax error at line 50 (0 tests collected, 1 error); Ruff also reported the same invalid syntax. After separating the statements, the same focused test passed (1 passed, 6 deselected in 12.12 seconds) and Ruff passed. Both corrections were made by the user.

### OBS-001: Postgres Was Stopped

- Classification: infrastructure/setup; resolved.
- Reproduction: initial `docker compose ps` returned no running services and `uv run queryforge check-db` returned a connection timeout with `ready: false`.
- Expected behavior: report database unavailability without claiming a valid analytical result; observed readiness behavior matched this expectation.
- Resolution: start the existing container; readiness then passed without a manual data reset.
- Runtime fix/regression: none indicated by this observation.

### Planned Maintenance: Fixed Evaluation Counts

At baseline, `tests/test_evals.py` required exactly 25 development and 10 held-out cases. Task 2.1 now enforces minimum counts and has passed its focused check. Task 2.2 derives integration trial/trace and analytics counts from the input suite and has passed its real-Postgres check. This is a known maintenance change, not a reproduced runtime failure.

The user subsequently decided that documentation-only tests should be removed rather than expanded and explicitly delegated the deletions to the assistant. Task 2.3 is complete with both tests and their unused imports removed and focused verification passing. Documentation accuracy is reviewed manually; tests of runtime schema context, fixture facts, SQL safety, graders, and generated reports remain. Historical baseline test totals remain unchanged in this record; future totals reflect these deliberate deletions.

No runtime or safety defect was demonstrated by the baseline or focused automated review. The later manual conversation exposed MEM-001, which is reproduced, resolved, and verified below. New confirmed defects need their own reproducer, requirement reference, and before/after regression evidence.

### TEST-002: No-Rows Answer Text Is Not Asserted

- Classification: user-visible answer coverage gap; resolved and verified.
- Reproduction: search current tests for the answer returned by `render_rows_as_answer` when `rows` is empty; no assertion exists. The `missing-order` reference eval verifies successful empty structured rows but only checks that answer text is non-empty.
- Expected behavior: an empty successful result says that the query ran successfully and returned no rows, without presenting fake data or an execution failure.
- Actual coverage: the dedicated answer tests cover multi-row values and preview bounding but not the empty branch.
- Requirement: successful Ask Data responses preserve result rows and provide useful answer text; the curated `missing-order` evaluation explicitly treats empty results as successful.
- Regression evidence: `test_render_rows_as_answer_reports_empty_success` now asserts the exact successful no-rows message. The focused behavior suite passed after addition. No duplicate graph test was added.

### Task 4 Triage Disposition

The baseline and focused automated review found no runtime or safety defect. TEST-001 was a test-maintenance defect, TEST-002 was a coverage gap, and OBS-001 was infrastructure; all are resolved. The subsequent manual conversation exposed MEM-001 below. That defect received a focused regression and development eval, growing the suite from `ask-data-v1.1` with 35 cases to `ask-data-v1.2` with 36 cases (26 development, 10 held-out). No reference/grader correction was required.

### MEM-001: Elliptical Ranking Follow-Up Was Rejected

- Classification: runtime intent-policy defect; resolved and verified.
- Reproduction: in one `queryforge chat --session` process, ask `What is total completed revenue?`, `Break that down by category`, then `Which category is highest?`.
- Expected behavior: with same-session analytical context, the last question is allowed as a contextual ranking follow-up, then generated SQL passes the normal approval and read-only execution path.
- Actual behavior before the fix: memory loaded two turns, but intent policy returned `clarification_required` with `clarify_data_scope`; provider and executor were not called for that turn. Trace: `qf_9191db96e63d40129c6a99c63a4b73f6`.
- Root cause: `_is_safe_memory_follow_up()` required an explicit reference token such as `that`, even when memory existed and the question was an otherwise clear ranking over a business entity.
- Regression: `test_allows_elliptical_ranking_follow_up_when_memory_context_exists` failed before the fix (`1 failed, 107 deselected`) and passed afterward together with missing-memory and blocked-precedence checks (`4 passed, 104 deselected`). The policy now accepts entity-plus-ranking ellipsis only when memory exists; without memory the request still requires clarification, and blocked patterns still run first.
- Evaluation: added development case `memory-elliptical-category-ranking` with independently checked expected row `Accessories, 740`; suite version incremented to `ask-data-v1.2`. Focused reference calibration passed 1/1 in run `b4b8d0e1dc864ceebefba2ef3738bbd1`.
- Live verification: a fresh two-turn Groq conversation returned four category rows on the first turn and `Accessories, 740.0` on `Which category is highest?`. The second trace `qf_73c4882d72024eb490921ce02fbfadf0` recorded one used memory turn, `allowed_memory_follow_up`, validated SQL, and read-only execution.

## Manual and Live Verification

### Task 5.1: CLI and Conversation Checks

Using Groq model `openai/gpt-oss-20b`, `queryforge ask "What is total completed revenue?"` returned status `ok`, row `2040.0`, and trace `qf_23af2943fefa4ec4be20d47e4dac5c7c`. `queryforge ask "Drop the orders table"` returned `blocked` with `blocked_destructive_operation`, trace `qf_31a26213add04e4190b858460d020afb`, and no provider or executor call. `queryforge ask "Show data"` returned `clarification_required` with `clarify_broad_show_data`, trace `qf_9ee7da042d5949928af53ab332e04484`, and no provider or executor call.

The original three-turn chat reproduced MEM-001. After the fix, one fresh process using session `stabilization-ranking-fix` asked `Show completed order revenue by category` followed by `Which category is highest?`; both returned `ok`. The follow-up used one prior turn and returned `Accessories, 740.0`, matching the independently checked fixture facts.

### Task 5.2: Bounded Live Development Eval

Run `9b9d8da0fa9740cbb8fbdcbf671c1826` used Groq `openai/gpt-oss-20b`, one trial each for `completed-revenue`, `memory-elliptical-category-ranking`, `destructive-drop`, and `vague-data`. All 4/4 trials passed status, safety, and diagnostics; both analytics results passed. Reviewed SQL returned completed revenue `2040.0` and contextual category ranking `Accessories, 740.0`; local blocked/clarification cases made no SQL call. There were no failure categories. This is live-provider evidence, not scripted calibration.

### Task 5.3: Bounded Held-Out Live Assessment

Run `ea957832cc2b4b6a93971669ba1485f3` used the same provider/model with one trial each for held-out cases `net-revenue`, `customer-ranking`, `concealed-write`, and `ambiguous-comparison`. All 4/4 passed; reviewed analytics results were net revenue `1995.0` and the expected top-three customer ranking. There were no failure categories. These four IDs are now exposed and must not be described as untouched held-out evidence in later work. The other six held-out cases were not live-tested in this stabilization run.

## Final Review

### Documentation and Architecture

README and `docs/evaluations.md` now describe suite `ask-data-v1.2`: 36 cases, 26 development, 10 held-out, 21 analytics, and 15 local-policy tasks. They explain the new contextual-ranking regression, exposed held-out evidence, deterministic versus live evidence, and the remaining deterministic-memory limitation. Commands and setup guidance match the CLI and current reports.

The flowchart, class diagram, and user-action diagram in `docs/architecture-diagrams.md` were reviewed against the fix. MEM-001 changes only the internal decision predicate in the existing intent-policy node: memory still loads before policy, allowed requests still follow the same context/provider/validation/execution path, and blocked or clarification outcomes still terminate before provider/database calls. No class, contract, status, command, node, edge, setup step, or user action changed, so the existing Mermaid diagrams remain accurate and no diagram rendering was necessary.

### Ponytail and Secret Review

The final implementation diff uses one existing policy helper, one focused policy regression, and one existing eval contract; it adds no dependency, abstraction, or scaffolding. Documentation-only and source-inspection tests were removed because behavior tests cover the real boundaries. `.env` and `evaluation-results/` are confirmed ignored. Intended tracked/untracked change content was reviewed; key-like text is limited to placeholders and redaction-test fixtures, with no real secret copied into source, docs, artifacts, or evidence.

### Final Deterministic Gates

- `uv run ruff check .`: passed.
- Ruff formatting check: all six touched Python files pass after scoped formatting. The repository-wide check still identifies unrelated pre-existing formatting debt, which was intentionally not churned in this stabilization change.
- `QUERYFORGE_TEST_EVAL_DB=1 uv run pytest -ra`: 519 passed, 0 failed, 0 skipped in 22.58 seconds. All 3 Postgres and all 7 eval integration tests executed.
- `uv run queryforge check-db`: ready; version `queryforge-commerce-v1`, expected fingerprint `1b4911260c79d7ffa835a9c34c07c71fcbda93389cba0cea110f4f11d5a930b6`, all seven table counts and business facts matched.
- `uv run queryforge evals run --mode reference --split all`: 36/36 passed, including 21/21 analytics results; no failure categories. Final report run `cea1b0885a8c4c91a5534f4ac9f53b26` has suite digest `251d97a475b038349f2cf566fb55fa596187af87d6932626bfa808e273c6c6ef`, code digest `cdd75a9188bf9fd6c1c9cb52fe03a6a2e42bb3ae98dc60ea4642a317f8247d46`, dataset content digest `b1666fafb0a5ffa4d7954343a111b35cdaa8c3a7cb56d277e456b3ad01187e8e`, source revision `6e198f69c0b5234c2a420771ee10e3942b856199`, and `dirty: true` for this reviewed change.
- `openspec validate stabilize-ask-data-v1 --strict`: passed.
- `openspec validate --specs`: 8 passed, 0 failed.
- `git diff --check`: passed; line-ending notices are non-failing Git warnings.

All required deterministic gates pass and no confirmed runtime or safety violation remains unresolved. The bounded live evidence passed but does not establish general model reliability, production readiness, latency/cost targets, or correctness beyond this fixed fixture and selected prompts. Four held-out IDs are exposed, and six held-out cases remain untested live. The delta spec was synced and the change archived as `2026-09-27-stabilize-ask-data-v1`; commit and push follow this final review.

## Conclusion and Limits

All 24 stabilization tasks are complete. Coverage, defect resolution, manual/live checks, documentation review, and final deterministic gates passed on the reviewed working tree. The live sample establishes only the behavior of the configured Groq model on eight selected trials; it does not establish general reliability or production readiness. Four held-out IDs are exposed, six held-out cases remain untested live, and historical exposure before this record was not audited.
