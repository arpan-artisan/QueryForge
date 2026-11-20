# QueryForge Quality Findings

This is the durable evidence log for agent and evaluation defects discovered
during manual use. A finding stays open until its product behavior, automated
coverage, and verification evidence are all complete. OpenSpec changes may
reference this log, but reorganizing files or passing reference calibration does
not close a finding.

## Status legend

- **Confirmed**: reproduced or directly supported by code and output evidence.
- **Planned**: assigned to an OpenSpec change with approved tasks.
- **Resolved**: implementation and focused regression coverage are complete.
- **Verified**: focused tests, full tests, and the applicable live evaluation pass.

## QF-001: Ambiguous revenue request is incorrectly allowed

- **Status:** Verified
- **Priority:** Critical
- **Observed input:** `What is total revenue?`
- **Observed behavior:** Intent policy returns `allowed_aggregate`, so the LLM and
  database execute instead of asking what revenue definition the user means.
- **Evidence:** Repeated runs returned `1995.0`, `2260.0`, and `1950.0` for the
  same question. The current intent-policy unit test explicitly expects this
  exact question to be allowed.
- **Root cause:** Clarification rules cover broad data requests, missing metrics
  or dimensions, vague time ranges, ambiguous entities, and incomplete
  comparisons. They do not recognize a named metric with multiple business
  definitions. The allow rule treats `revenue` as sufficient analytical intent.
- **Impact:** QueryForge silently selects among completed revenue, gross revenue,
  and net revenue while presenting the result as an unqualified fact.
- **Expected behavior:** Until QueryForge has a governed canonical revenue
  definition, the request must return `clarification_required` and must not call
  the LLM or database. The response should ask the user to choose completed,
  gross, or net revenue.
- **Required coverage:** Intent-policy unit case, workflow short-circuit case,
  CLI result case, and an evaluation golden for the ambiguous wording.
- **Verification evidence:** The governed semantic resolver returns
  `clarification_required` before SQL generation or execution. The development
  reference suite passes the promoted regression, and live report
  `bae00ecaaacd429589ad94c4845bdbdb` passed all three ambiguity trials.

## QF-002: Required evaluation gate does not measure live model behavior

- **Status:** Verified
- **Priority:** Critical
- **Observed behavior:** CI runs all 36 cases in `reference` mode. Analytics cases
  receive scripted reference SQL; normal pytest also uses fake providers.
- **Impact:** Prompt, model, schema-context, and SQL-generation regressions can
  ship while the required evaluation gate remains green.
- **What the current gate proves:** Case contracts, expected rows, workflow,
  guardrails, read-only execution, traces, and deterministic grading work with
  known-good SQL.
- **What it does not prove:** The configured LLM consistently chooses the right
  metric definition or generates semantically correct SQL.
- **Expected behavior:** Keep deterministic reference calibration, but add a
  separately reported live-model regression gate with a pinned dataset,
  provider/model/prompt identity, repeated trials where appropriate, approved
  thresholds, and comparison with an accepted baseline.
- **Verification evidence:** The strict baseline contract, compatibility checks,
  comparator, reports, and gate exit semantics are implemented and covered by
  deterministic tests. Infrastructure-clean live report
  `874fedc7cb56422eb9fb5479c34616bb` is the reviewed source for
  `evals/ask-data/live-baseline.json`. A subsequent baseline-owned run retained
  all 111 trials, identified 59 provider/dependent infrastructure failures,
  failed the applicable floors and hard-safety comparison, and returned exit
  `1` rather than silently passing.

## QF-003: Generated net-revenue SQL double-counts refunds

- **Status:** Verified
- **Priority:** Critical
- **Observed input:** `What is total revenue?`
- **Observed SQL shape:** `orders` joined to `order_items`, then directly joined
  to `refunds`, followed by `SUM(r.amount)` grouped by order.
- **Observed result:** `1950.0`.
- **Correct fixture values:** Gross revenue is `2260`; refunds are `265`; net
  revenue is `1995`.
- **Root cause:** A refund row is repeated for each matching order item, so the
  query summed `310` of refunds instead of `265`. SQL policy correctly allowed
  the statement because it is read-only and structurally safe; policy is not a
  semantic SQL correctness checker.
- **Impact:** QueryForge can confidently return a numerically wrong answer from
  safe, executable SQL.
- **Expected behavior:** Explicit net-revenue questions must aggregate order
  lines and refund events independently before subtraction.
- **Required coverage:** A live evaluation must compare returned rows with the
  expected `1995`. Reference mode alone cannot demonstrate model competence.
- **Resolution evidence:** SQL validation now rejects reading `order_items` and
  `refunds` in the same query scope as `aggregate_grain_mismatch`, while allowing
  independently aggregated derived results to be combined. The focused live
  run `3b8c1540fea949518675380bcb62e551` passed status, safety, result (`1995`),
  and diagnostics. A three-trial repeat produced the same capability pass when
  the provider responded, but two other trials were rate-limited.

## QF-004: Final answers omit metric definitions and are not quality-graded

- **Status:** Resolved
- **Priority:** High
- **Observed behavior:** The final answer is produced by a deterministic row
  formatter, for example `Total Revenue is 2260.0.` It does not disclose included
  statuses, refund treatment, time scope, currency, or calculation semantics.
- **Impact:** A response can be faithful to its result row yet misleading or
  incomplete for the user's actual question.
- **Current grading gap:** Evals grade terminal status, execution safety, result
  rows, and diagnostic consistency. They do not grade directness, completeness,
  clarity, or unsupported claims in the user-facing answer.
- **Expected behavior:** Define grounded answer behavior before adding a quality
  judge. Deterministic correctness and safety remain hard gates; any semantic
  judge must receive the question, expected facts, returned rows, and final
  answer, and must never override a wrong numerical result.
- **Implementation progress:** Governed scalar answers now state their validated
  metric name and definition. All 47 development/release cases declare reviewed
  answer expectations, and every normal evaluation has an authoritative
  `answer_grounding` grade for metric labels, required values/scope, and
  unsupported scalar claims. Development reference passes 37/37 and release
  reference passes 10/10 with grounding at 100%. Subjective directness,
  completeness, and clarity judging is now an explicit calibrated option and
  remains subordinate to deterministic grades. A credentialed judged
  `net-revenue` reference run passed all three dimensions; this focused result
  is evidence for that case, not a general quality baseline.

## QF-009: Empty successful results need a distinct answer benchmark

- **Status:** Resolved
- **Priority:** Medium
- **Discovery:** Requiring every successful analytics case to name a metric and
  repeat a value from `expected_rows` is impossible when the correct result is
  an empty row set.
- **Resolution:** The strict expectation contract has an explicit
  `expect_empty_result` branch. It forbids invented metric/value requirements,
  requires an empty-result message, and still rejects unsupported scalar claims.
  This keeps `missing-order` meaningful without fabricating a zero or weakening
  nonempty analytics validation.

## QF-005: Ambiguity detection is lexical rather than semantic

- **Status:** Verified
- **Priority:** Critical
- **Observed behavior:** Intent ambiguity is determined by hard-coded terms,
  regular expressions, and narrow helpers for missing metrics, dimensions,
  time ranges, entities, and comparison targets.
- **Evidence:** `What is total revenue?` contains a recognized metric and
  business term, misses every clarification pattern, and is explicitly expected
  by a unit test to return `allowed_aggregate`.
- **Impact:** The policy can identify missing words but cannot determine that a
  present business metric has several legitimate meanings. Adding more phrases
  would expand coverage but remain brittle and schema-specific.
- **Expected behavior:** Keep deterministic blocking and execution-safety
  policy, but resolve analytical intent through governed metric definitions and
  a structured semantic decision before SQL generation. When context cannot
  resolve one definition, return `clarification_required`; model output must not
  itself authorize database execution.
- **Required coverage:** Metric-definition contract tests, structured intent
  decision tests, ambiguous and explicit revenue workflow cases, and live evals
  that verify the real model does not silently choose among valid definitions.
- **Verification evidence:** Deterministic policy still screens prohibited
  requests first; a structured model decision now resolves governed metrics and
  is validated before generation. Unknown, malformed, or unresolved decisions
  fail closed. The ambiguity live case passed three of three trials.

## QF-006: Metric definitions are present but excluded from ambiguity resolution

- **Status:** Verified
- **Priority:** Critical
- **Observed behavior:** The schema context already defines completed revenue,
  gross revenue, refund amount, and net revenue. Intent policy decides whether a
  request is allowed before the context builder and SQL provider use those
  definitions.
- **Evidence:** The SQL-generation prompt receives all metric definitions but is
  instructed to return exactly one `SELECT` statement unless the schema cannot
  answer the question. It has no structured clarification outcome, so an
  ambiguous but answerable request is forced into SQL generation.
- **Impact:** QueryForge possesses the evidence needed to recognize multiple
  revenue meanings but does not use it at the decision point. The model silently
  chooses a definition, while deterministic policy sees only lexical patterns.
- **Expected behavior:** After deterministic safety screening, a semantic intent
  resolver must receive the question, governed schema/metric context, and
  relevant bounded memory. It must return a structured allowed, unsupported, or
  clarification decision. Deterministic code must validate any resolved metric
  identifier against the governed definitions before SQL generation.
- **Required coverage:** Verify that ambiguous metric context reaches the
  resolver, malformed or unknown metric decisions cannot authorize generation,
  unresolved candidates skip SQL generation and execution, and explicit metric
  definitions proceed through the normal validation boundary.
- **Verification evidence:** The immutable metric catalog renders both schema
  context and the resolver contract. The validated resolution and exact metric
  definition then flow into SQL generation and repair; focused tests and the
  three-trial live ambiguity run cover the boundary.

## QF-007: Provider throttling prevents approval of a live baseline

- **Status:** Resolved
- **Priority:** High
- **Observed behavior:** The unpaced development run passed 49 of 108 trials
  with 50 `provider_rate_limit` failures; a four-second paced run passed 54 of
  108 with 45 rate-limit failures. Nine dependent memory turns in each run then
  failed setup because their prerequisite turn had no valid result.
- **Evidence:** Live reports `423c57929c8b45ae95cf7eff28502d34` and
  `7c62a40fb9e84e1d981f784faa035f92`.
- **Impact:** These reports cannot support reviewed floors or an approved
  development baseline. Treating the low aggregate rate as agent quality would
  conflate provider availability with semantic capability.
- **Required next step:** Obtain an infrastructure-clean three-trial development
  run with suitable provider quota, manually inspect failures and sample passes,
  then author and review the baseline manifest. Do not auto-retry, discard, or
  approve throttled trials.
- **Resolution evidence:** A 20-second inter-trial delay produced the complete
  infrastructure-clean report `874fedc7cb56422eb9fb5479c34616bb`: 111 of 111
  trials completed with no provider, network, timeout, rate-limit, or harness
  failures. The reviewed manifest pins that report's exact observed rates.
  A later baseline run encountered generic provider failures; the live gate
  retained and classified them and failed closed, so provider availability
  remains an operational limitation rather than a missing baseline control.

## QF-010: Correct rows can still produce weak or mismatched answer labels

- **Status:** Verified
- **Priority:** High
- **Observed behavior:** The infrastructure-clean live baseline run returned
  correct rows but failed deterministic answer grounding for `completed-count`,
  `average-order-value`, `orders-by-status`, and `customer-ranking`. Examples
  include `Count is 7.`, `Avg Order Value is 291.43.`, `Order Count`, and a bare
  `Name` column where the reviewed expectations require clearer business labels.
- **Impact:** The numerical result can be right while the user-facing prose is
  abbreviated, under-specified, or judged against a label contract that does not
  recognize an acceptable synonym.
- **Resolution:** SQL generation now requests descriptive output aliases, while
  deterministic rendering expands the reproduced `avg` abbreviation and adds
  bounded question context when a provider still returns a generic `count` or
  `name` label. Review also confirmed that `completed order count` and `order
  count` are clear synonyms for the existing expectations; those exact phrases
  were added without weakening value, status, safety, or other grounding rules.
  Development suite `ask-data-development-v1.3` calibrates at 37/37. A focused
  live rerun passed all four affected cases with correct results and 4/4 answer
  grounding in report `af4228f1ae994f0cbad67b4ffae3a0cd`.
- **Remaining boundary:** The approved live baseline still identifies suite
  v1.2 and must be replaced through the separate live-quality-gate change before
  it can gate the updated suite.

## QF-012: Approved customer-name projection loops through clarification

- **Status:** Verified
- **Priority:** High
- **Observed input:** `List all the names of the customer.`
- **Observed behavior:** The initial request and an explicit clarification both
  returned `clarify_data_scope`. A shorter retry such as `List all customers`
  then activated `blocked_resource_abuse`.
- **Root cause:** Deterministic intent policy recognized aggregates and bounded
  single-entity lookups but not a bounded projection of one approved column.
  The broad-dump regex also treated the prefix `list all customer` in
  `list all customer names` as a request for full customer records.
- **Impact:** A clear, safe question over the approved `customers.name` column
  could not reach SQL generation, and repeated clarification made the product
  appear inconsistent.
- **Resolution:** Added a narrow `allowed_bounded_projection` decision for
  customer-name requests after all safety blocks. Customer emails, raw records,
  and full customer dumps remain blocked. The resource-abuse rule excludes only
  the explicit `name` projection from its customer prefix match.
- **Coverage:** Intent-policy regressions cover the original wording, common
  paraphrases, the frontend clarification payload, and the unchanged broad-dump
  block. Guarded graph tests prove both original and clarified inputs reach SQL
  validation and bounded execution. Live trace
  `qf_86cba35594be4a0690774d8cd95019ff` returned all six fixture names.
- **Verification evidence:** Focused policy and guarded-graph coverage passed
  `129` tests. The full repository suite passed `650` tests with `8` expected
  skips; Ruff lint, Ruff formatting, and strict OpenSpec validation also pass.
- **Evaluation gap:** Development suite v1.3 has no plain approved-column
  projection case. Promote this wording when the live baseline is next reviewed;
  changing the 37-case suite alone would intentionally invalidate the current
  baseline and require another full provider run.

## QF-011: Approved baseline omits subjective answer quality

- **Status:** In progress
- **Priority:** High
- **Observed behavior:** Directness, completeness, and clarity are available only
  through the optional `--judge-answers` path. The committed v1 baseline records
  no subjective dimensions, and a baseline-backed run does not require the judge.
- **Impact:** An agent version can preserve rows, safety, and grounding while
  making answers less direct, incomplete, or harder to understand without failing
  the approved regression gate.
- **Reproduction:** The v1 manifest loads without judge or calibration identity,
  and `baseline_rates` excludes all three prose-quality dimensions.
- **Current work:** Baseline v2 requires pinned judge/calibration identity and
  non-optional directness, completeness, and clarity floors. The expanded
  calibration exposed and corrected a judge rubric defect that conflated
  incompleteness with indirectness. A judged net-revenue check then surfaced a
  real contract tension between `Return only the net total` and the governed
  metric-definition suffix; that outcome remains visible for full-run review.
  Invalid reports `0b8c1affadf94a5fa855bec20b645c3d` (98/111 trials) and
  `03ddd1777d28400fb49fb444bf600621` (46/111 trials) proved the gate fails
  closed when the judge becomes unavailable. Report
  `83a6d368f9704cdf96a152e09d89f639` failed during calibration. The provider
  returned HTTP 429 under its documented 8,000-token-per-minute and
  200,000-token-per-day limits. The judge now caps completion output, honors
  Groq's bounded `retry-after` value, retains sanitized failure diagnostics, and
  still rejects persistent unavailability. Live evidence now runs as smaller
  non-overlapping case chunks; offline composition requires identical pinned
  identities, full trial coverage, and zero infrastructure failures before it
  can produce a baseline source or gate report.
- **Required next step:** Complete and compose the infrastructure-clean judged
  development chunks, approve a v2 manifest from reviewed observations, and
  replay the gate as new chunks before changing this finding to verified.

## QF-013: Explicit customer-order relationship loops through clarification

- **Status:** Verified
- **Priority:** High
- **Observed input:** `show me what are the orders placed by all the unique customers`
- **Observed behavior:** The original question and an explicit explanation to
  show each customer with the orders they placed repeatedly returned
  `clarify_data_scope`.
- **Root cause:** Deterministic intent routing still assumed that a multi-row
  request needed an aggregate metric or single-entity lookup. It did not
  recognize an explicit projection over the approved `customers.id` to
  `orders.customer_id` relationship.
- **Resolution:** The bounded approved-projection decision now recognizes
  customer-order wording with an explicit `placed by` relationship. It still
  runs after destructive, sensitive, administrative, and resource-abuse blocks.
  Generic `Show orders` remains clarification-required and `List all orders`
  remains blocked.
- **Coverage:** Policy and guarded graph tests cover both the original wording
  and the frontend clarification payload. Live trace
  `qf_393c2c67c0014ab28e6fb9f316949bda` returned ten bounded order rows covering
  all six customers.
- **Verification evidence:** The focused policy and guarded-graph slice passed
  `135` tests. The full suite passed `656` tests with `8` expected skips; Ruff
  lint, Ruff formatting, and strict OpenSpec validation also pass.
- **Evaluation gap:** Like QF-012, development suite v1.3 has no non-aggregate
  approved-relationship projection. Promote a representative case during the
  next reviewed live-baseline refresh instead of invalidating the current
  manifest without complete replacement evidence.

## QF-014: Named-customer order lookup and requested limit are not resolved

- **Status:** Confirmed
- **Priority:** High
- **Observed input:** `could you list the orders placed by kabir maximum limit of 1000`
- **Observed behavior:** The browser returned `clarify_data_scope` even though
  the request identifies the order entity, a customer-name filter, and a
  requested limit. Trace: `qf_25398005e44e47a8a9d4607e253ee9d3`.
- **Root cause:** Deterministic intent policy cannot infer that `Kabir` is a
  value of the approved `customers.name` field when the word `customer` is not
  present. The request contract also has no structured distinction between the
  user's requested limit (`1000`) and QueryForge's enforced maximum (`100`).
- **Expected behavior:** Resolve the named customer through approved schema
  context, query that customer's orders, enforce the system row cap, and tell
  the user that the requested limit was capped. Clarification is appropriate
  only when the name matches multiple customers or another material meaning is
  genuinely unresolved.
- **Required next step:** Replace phrase-by-phrase allow rules with a dedicated
  schema-grounded semantic request decision covering entities, attributes,
  relationships, filters, requested/effective limits, and specific ambiguity.
  Preserve deterministic safety checks before execution and add systematic
  projection/join/filter/limit regressions plus representative live evals.

## QF-008: Live diagnostics required the reference suite's exact repair count

- **Status:** Verified
- **Priority:** High
- **Observed behavior:** A live net-revenue trial produced safe repaired SQL and
  the correct `1995` result, but diagnostics failed because the case's reference
  script expected zero repairs.
- **Root cause:** One diagnostic condition was serving two different purposes:
  proving that the deterministic reference repair fixture took its scripted path
  and judging the quality of stochastic live behavior.
- **Resolution:** Reference mode still enforces the exact scripted repair count.
  Live mode records the bounded repair count but grades the final status, safety,
  result correctness, and trace evidence. Focused tests cover both contracts;
  live report `3b8c1540fea949518675380bcb62e551` passes after the separation.

## Gate before the next product stage

Do not treat Ask Data as stable enough for the next product stage until:

1. Ambiguous business metrics either resolve through a governed semantic
   definition or require clarification before generation.
2. The observed refund fan-out failure has focused regression coverage and live
   evaluation evidence.
3. Reference calibration and live model evaluation are reported as different
   kinds of evidence.
4. Agent-affecting changes are compared with an approved live baseline.
5. User-facing answer quality has an explicit contract and grading strategy.

## Prioritized remediation sequence

### Phase 1: Restore agent semantic correctness

1. Move metric definitions into one structured, governed source of truth and
   render the model-facing context from it.
2. Keep deterministic blocking for destructive, sensitive, administrative,
   resource-abuse, and policy-bypass requests before any model call.
3. Add a structured semantic intent resolver that receives the question,
   governed schema and metric definitions, and relevant bounded memory.
4. Validate resolver output deterministically. Unknown metrics, malformed
   decisions, or unresolved multiple definitions must not authorize SQL
   generation.
5. Return `clarification_required` without calling SQL generation or the
   database when one governed interpretation cannot be selected.
6. Pass the resolved metric identifier and definition to SQL generation so the
   model does not reinterpret the business metric a second time.
7. Preserve normal SQL policy and approved-query enforcement after generation.
8. Add focused regression coverage for ambiguous revenue, explicit completed,
   gross, and net revenue, bounded memory disambiguation, malformed resolver
   output, and refund join fan-out.

### Phase 2: Make evaluations protect real agent quality

1. Keep reference mode as harness calibration and label it as such.
2. Add live semantic-intent and SQL-generation evaluation runs using the real
   configured model.
3. Add the observed ambiguous-revenue and refund fan-out failures as development
   goldens.
4. Record provider, model, prompt/code revision, dataset version, per-case
   grades, repeated-trial consistency, latency, and failure categories.
5. Establish an approved live baseline and fail agent-affecting changes on hard
   safety/correctness regressions or an approved quality-threshold regression.
6. Keep genuinely unexposed cases for release evaluation and move exposed
   failures into the development regression set.

### Phase 3: Improve grounded user-facing answers

1. Define the answer contract: metric name and definition, value, relevant
   scope, refund/status treatment, time range, and uncertainty when applicable.
2. Ensure every factual statement is grounded in validated result rows and the
   resolved metric definition.
3. Add deterministic answer checks for required facts and unsupported values.
4. Add a calibrated semantic judge only for relevance, completeness, clarity,
   and unsupported claims; it must never override failed deterministic grades.
5. Compare answer-quality results with an approved baseline across agent
   versions.

### Phase 4: Reorganize the verification surface

1. Separate unit tests, Postgres integration tests, eval-harness tests, actual
   evaluation datasets, and generated reports.
2. Split oversized files by behavior and give parameterized cases readable IDs.
3. Expose unit, integration, reference-calibration, and live-evaluation results
   as distinct CI stages.
4. Document local commands, report locations, evidence types, and stage gates.
