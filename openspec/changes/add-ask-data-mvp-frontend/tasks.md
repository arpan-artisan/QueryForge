## 1. Prerequisite and Scope Guard

- [x] 1.1 Confirm `enforce-live-answer-quality-gate` is fully implemented and verified, and record its completed OpenSpec status plus final verification evidence before making frontend code changes.
- [x] 1.2 Re-read the current CLI-to-`AskDataRuntime` flow, result assembly, semantic-resolution path, and schema context; document the touched files in the implementation notes and verify the web path can reuse them without a second agent workflow.

## 2. Shared Structured Contracts

- [x] 2.1 Replace duplicated schema prose with one typed approved schema catalog that still generates the existing LLM context, and verify focused tests cover all seven approved tables, representative columns, grains, relationships, metric definitions, and the exclusion of unapproved metadata.
- [x] 2.2 Add typed clarification question and candidate fields to the terminal Ask Data result and copy only validated semantic-resolution candidates into clarification-required results; verify focused tests cover candidates present, candidates absent, stable labels/identifiers, and the absence of SQL and rows.
- [x] 2.3 Preserve CLI result compatibility after the additive result-contract changes, and verify existing CLI/runtime contract tests plus a focused clarification serialization test pass.

## 3. Local Web Boundary

- [x] 3.1 Add only the FastAPI and Uvicorn runtime dependencies required by the design, refresh the lockfile, and verify `uv sync` and dependency inspection complete without adding a frontend build toolchain.
- [x] 3.2 Implement explicit browser request/response models and a thin `POST /api/ask` adapter over `AskDataRuntime`; verify endpoint tests cover success, empty input, clarification, blocked/unsupported/invalid outcomes, runtime failure sanitization, bounded rows, trace identity, and omission of full traces and sensitive internals.
- [x] 3.3 Implement `GET /api/schema` from the approved structured catalog without database introspection, and verify endpoint tests return approved descriptions, grains, columns, and relationships while excluding system and unapproved metadata.
- [x] 3.4 Add the local-only `queryforge web` command with loopback binding by default and packaged static-asset serving, and verify a command smoke test confirms the application starts through the documented entry point without changing `queryforge ask` behavior.

## 4. Build-Free Browser Interface

- [x] 4.1 Implement the single-page HTML and CSS layout with the top question form, separate LLM output and scrollable SQL result sections, and right-side schema dropdown; verify the packaged page and assets load successfully and manual inspection matches the approved MVP layout at desktop and narrow widths.
- [x] 4.2 Implement initial, loading, success, empty-result, rejected, and unexpected-failure view states in plain JavaScript; verify manual browser runs prevent empty and duplicate submissions and display answer, SQL, rows, row count, and concise failures without fabricating data.
- [x] 4.3 Implement schema dropdown loading and selected-table details from `/api/schema`; verify manual browser inspection shows the approved description, grain, columns, types, and relationships and a recoverable schema-loading error state.
- [x] 4.4 Implement clarification suggestions plus a free-text explanation path that resubmits an explicit natural-language clarification through `/api/ask`; verify candidate selection, unmatched free text, and still-ambiguous follow-ups all rerun the guarded workflow and never display SQL or rows before resolution.
- [x] 4.5 Keep the page stateless by omitting session storage, local storage, history navigation, and server conversation records; verify a reload clears the visible result and a new top-level question replaces the prior view.

## 5. Documentation and Manual Verification

- [x] 5.1 Update the README with the local web setup/start command, prerequisites, supported MVP behavior, and explicit non-goals; manually verify every documented command from a clean local setup path.
- [x] 5.2 Update `docs/architecture-diagrams.md` with the browser-to-runtime data flow, structured schema source, clarification loop, and unchanged SQL trust boundary; manually compare the diagrams with the implemented code paths.
- [x] 5.3 Run an end-to-end local browser check against the deterministic demo database for a successful question, a scrollable multi-row result, an ambiguous revenue question, a suggested clarification, a free-text clarification, a policy rejection, and a provider/database failure; record outcomes and trace identifiers in the change verification notes without committing secrets.

## 6. Final Validation

- [x] 6.1 Run `uv run ruff check .` and `uv run ruff format --check .`, fix any failures, and record the passing commands.
- [x] 6.2 Run the focused web/contract tests and then `uv run pytest`, fix any regressions, and record the passing test counts.
- [x] 6.3 Run `openspec validate add-ask-data-mvp-frontend --strict`, resolve all findings, and record the passing validation output.
- [x] 6.4 Review the final diff for scope creep, duplicate agent logic, direct query execution, raw trace or secret exposure, unintended session behavior, and committed credentials; record the review result and leave all unrelated user changes untouched.

## 7. Post-verification Regression

- [x] 7.1 Treat an explicit request for approved customer names as a bounded projection rather than clarification or a broad dump; keep full customer records and sensitive fields blocked, and verify the original wording, frontend clarification payload, common paraphrases, guarded graph execution, and one live request.
- [x] 7.2 Treat an explicit request for customers and the orders they placed as a bounded approved relationship projection rather than repeated clarification; keep generic order dumps gated, and verify the original wording, frontend clarification payload, guarded graph execution, and one live request.
