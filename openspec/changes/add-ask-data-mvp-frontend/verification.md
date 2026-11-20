# Verification Record

## Prerequisite and implementation notes

- `enforce-live-answer-quality-gate` completed 16/16 tasks, passed its final
  baseline replay, and was archived at
  `openspec/changes/archive/2026-11-19-enforce-live-answer-quality-gate/`.
  The completed backend/evaluation snapshot was committed as `3df9148` and
  pushed to `origin/main` before frontend implementation began.
- The prerequisite evidence includes `629 passed, 8 skipped`, Ruff success,
  strict OpenSpec validation, development reference `37/37`, release reference
  `10/10`, and a 37/37-trial infrastructure-clean live baseline replay whose
  hard-safety, baseline-comparison, and final gates passed.
- Existing request flow: `src/queryforge/cli.py` constructs `AgentRequest` and
  calls `AskDataRuntime`; `src/queryforge/runtime.py` delegates to the single
  `AskDataGraph`; `src/queryforge/ask_data_graph.py` owns policy, semantic
  resolution, SQL generation/validation/approval, execution, result assembly,
  and tracing.
- Shared result and clarification contracts live in
  `src/queryforge/models.py`; validated metric candidates are produced by
  `src/queryforge/semantic_resolution.py` and are already present in graph state
  before terminal result assembly.
- Approved schema prompt context is built in `src/queryforge/schema.py` and
  consumed through `src/queryforge/context.py`. The web path will reuse the
  runtime and a single structured schema catalog rather than implement another
  agent or introspect the database.
- Expected implementation touch points are `models.py`, `schema.py`,
  `ask_data_graph.py`, `cli.py`, a small web-adapter module, packaged static
  assets, focused tests, README, and architecture documentation. The web
  adapter must not import or call the query executor directly.

## Validation evidence

- Structured schema and existing runtime-context slice:
  `16 passed` in focused database/runtime tests; focused Ruff lint and format
  checks passed. The catalog contains all seven approved tables, matches the
  SQL query-column contract, retains every approved relationship and metric,
  and excludes `customers.email` and system metadata.
- Clarification/result/CLI slice: `44 passed` across model contracts, graph
  terminal paths, and CLI serialization; focused Ruff lint and format checks
  passed. Semantic ambiguity exposes stable governed IDs and labels, local
  policy clarification exposes no invented candidates, and clarification
  results reject SQL or rows.
- Dependency inspection: `uv add fastapi uvicorn`, `uv sync`, and
  `uv tree --depth 1` succeeded. Runtime additions are FastAPI `0.165.0` and
  Uvicorn `0.54.0`; no Node dependency or frontend build toolchain was added.
- Web adapter, schema endpoint, static serving, and CLI command slice:
  `23 passed`. Browser responses omit the full trace, provider/model, raw
  policy internals, and non-success SQL/rows; runtime exceptions and runtime
  `error` answers are sanitized. The command smoke test proves loopback host
  `127.0.0.1` and the selected port are passed to Uvicorn.
- Packaging verification: `uv build` initially exposed that the wheel omitted
  the static interface. Adding the minimal setuptools package-data declaration
  fixed the defect; a clean rebuild contains exactly
  `queryforge/static/index.html`, `styles.css`, and `app.js`.
- Manual layout inspection passed at desktop and a 500-pixel narrow viewport.
  The question controls stack at the narrow breakpoint, the answer and SQL
  result remain separate, the row area is bounded and scrollable, and the
  schema panel moves below the result without horizontal overflow. A malformed
  responsive `min()` width was corrected to use `calc()`.
- Isolated headless-browser checks loaded all seven schema options and verified
  description, grain, columns, types, and relationships. A simulated schema
  request failure left question entry usable and the retry action restored all
  seven tables.
- Browser state checks verified whitespace rejection, one request for duplicate
  submissions while loading, disabled controls while running, success with an
  explicit empty-result message, concise network failure, and reload back to
  the initial state with zero local/session-storage entries.
- Clarification browser checks verified both suggestion selection and unmatched
  free text use the explicit payload format `Original question: ...` plus
  `User clarification: ...`. A still-ambiguous mocked follow-up rendered a new
  clarification question while SQL stayed `No approved query yet` and rows
  stayed at zero.
- Live deterministic single-trial checks against `queryforge-commerce-v1`:
  completed revenue returned `2040.0` (`qf_af6229aed03e42e7af6c37b2f453064b`);
  ambiguous total revenue stopped with gross/net candidates and no SQL
  (`qf_38e8678c9a8b47e1b49bf023d6b869f1`); suggested gross revenue returned
  `2260.0` (`qf_0a71711ce4ab4aa393e45268ec363660`); free-text net revenue returned
  `1995.0` (`qf_dc1c8e76197d4f56b90c9724ed10e2ae`); completed revenue by product
  returned eight rows (`qf_7fdb0961e8124ec0babbc1956c5a86d5`); and a delete request was blocked
  before SQL (`qf_7dca0585f6dc4c309fd11b71002825a1`).
- For the database-failure browser check, only the QueryForge demo container was
  stopped temporarily. The page returned the sanitized answer `Ask Data could
  not complete the request.`, no SQL, and zero rows
  (`qf_737ebfa3142146a7a391b39117a94eb7`). The container was immediately
  restored and `check-db` reconfirmed the expected fingerprint and facts.
- README commands were exercised through `uv sync`, Docker service startup,
  `queryforge check-db`, loopback `queryforge web --port 8123`, packaged asset
  loading, and live questions. The deterministic initialization/reset contract
  remains covered by the passing database lifecycle integration tests. The
  documented MVP features and non-goals match the observed browser behavior.
- The architecture diagram was compared with `web.py`, `schema.py`,
  `ask_data_graph.py`, and `app.js`: the browser creates a sessionless
  `AgentRequest`, the existing runtime owns all policy/SQL/execution work, the
  approved catalog feeds both prompt prose and schema UI, and clarifications
  re-enter the same guarded endpoint.
- Final validation passed: `uv run ruff check .`; `uv run ruff format --check .`
  (`225 files already formatted`); focused frontend/contract slice
  (`63 passed`); latest post-verification policy/graph slice (`135 passed`);
  full suite after both projection regressions (`656 passed, 8 skipped`); and
  `openspec validate add-ask-data-mvp-frontend --strict`. The only test warning
  is FastAPI's upstream TestClient notice that its current `httpx` compatibility
  path is deprecated.
- Final scope/security review passed. The adapter calls only `AskDataRuntime`,
  never the executor or database directly; response models allowlist browser
  fields; browser rendering uses `textContent`; no raw trace, provider/model,
  prompt, exception, credential, saved session, browser storage, or navigation
  history was added. No credential-like diff was found. Ruff's mechanical
  formatting corrected pre-existing repository drift without behavioral
  changes; the worktree was clean before this frontend change, so no unrelated
  user edits were overwritten.
- Post-verification customer-name regression: manual browser use exposed that
  `List all the names of the customer.` returned `clarify_data_scope`; the
  frontend's explicit clarification payload did the same, and the shorter
  phrase `List all customers` activated the broad-dump block. The deterministic
  policy had aggregate and single-entity lookup categories but no approved
  column-projection category. A narrow `allowed_bounded_projection` decision
  now covers customer `name` requests after all destructive, sensitive, and
  resource-abuse checks. The broad `List all customers` request remains
  blocked, while the resource-abuse regex no longer treats `customer names` as
  full customer records. Focused policy and guarded-graph regressions pass for
  the original wording, the frontend clarification payload, and common
  paraphrases. One live request returned all six deterministic names with
  `SELECT name AS customer_name FROM customers LIMIT 100`, status `ok`, and
  trace `qf_86cba35594be4a0690774d8cd95019ff`.
- Post-verification customer-order regression: `show me what are the orders
  placed by all the unique customers` and its explicit clarification payload
  both returned `clarify_data_scope` because deterministic policy still assumed
  every multi-row request needed an aggregate metric. The bounded projection
  decision now also recognizes the approved `customers` to `orders`
  relationship when the user explicitly asks for orders placed by customers.
  Generic `Show orders` still requires clarification and `List all orders`
  remains blocked. Focused policy and guarded-graph coverage passed `135` tests.
  One live request returned all ten orders across all six customers with bounded
  SQL, status `ok`, and trace `qf_393c2c67c0014ab28e6fb9f316949bda`.
