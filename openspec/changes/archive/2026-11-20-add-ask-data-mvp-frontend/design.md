## Context

See `proposal.md` for motivation and scope. QueryForge currently exposes `AskDataRuntime` through a CLI and returns a structured `AskDataResult`. The runtime already owns intent policy, semantic metric resolution, SQL generation, validation, approval, read-only execution, answer rendering, tracing, and row bounds. Clarification details exist inside the graph's metric-resolution decision, but the terminal result currently exposes only the clarification text through `answer`. Schema context is maintained as prompt text plus a structured revenue metric catalog, so the browser cannot yet consume the approved table metadata without duplicating or parsing prose.

This change crosses the result contract, schema context, local application boundary, static interface, tests, commands, and architecture documentation. It is therefore designed as an additive interface over the existing runtime, not as a separate agent.

## Goals / Non-Goals

**Goals:**

- Add the smallest local web boundary that can run Ask Data and return browser-safe structured results.
- Keep the existing runtime as the only path from natural-language input to database execution.
- Make approved schema metadata and clarification candidates structured, typed, and reusable.
- Use a build-free frontend so local development requires no Node toolchain.
- Preserve request traceability while excluding internal trace payloads and secrets from normal browser responses.

**Non-Goals:**

- A stable public API or versioning commitment for third-party integrations.
- Server-side sessions, a conversation model, result storage, or durable frontend state.
- A frontend framework, component library, JavaScript build pipeline, or generalized design system.
- Direct database introspection from the browser-facing path.
- A second implementation of intent, generation, validation, execution, or answer rendering.

## Decisions

### 1. Gate implementation on the answer-quality change

Implementation starts only after `enforce-live-answer-quality-gate` is complete and verified. This is an execution dependency, not a runtime coupling: this change will consume the completed Ask Data behavior without importing evaluation code into the web path.

**Alternatives considered:** Implement both changes concurrently. Rejected because it would make failures harder to attribute and could expose an answer path whose regression gate is still unfinished.

### 2. Add one local web command backed by a thin FastAPI application

Add a `queryforge web` command that starts a local-only server bound to `127.0.0.1` by default. The application serves the static interface and two UI-facing endpoints:

- `POST /api/ask` accepts a bounded natural-language question and returns a sanitized Ask Data response.
- `GET /api/schema` returns the approved structured schema catalog used by the active Ask Data context.

FastAPI and Uvicorn are the only planned runtime additions. Pydantic is already used for contracts and `httpx` is already available for in-process endpoint tests. The endpoints are an internal local UI boundary and are not documented as a public integration API.

**Alternatives considered:**

- Python's `http.server`: avoids dependencies but requires hand-written JSON validation, routing, error mapping, async lifecycle handling, and static-file safeguards. That produces more trust-boundary code than the two small dependencies remove.
- React, Next.js, or another frontend framework: rejected because one page with a form, dropdown, and result table does not justify a build system or client framework.
- A second CLI process invoked by the browser server: rejected because it duplicates serialization and loses the direct typed runtime boundary.

### 3. Keep the browser response smaller than the internal result

The UI response includes only the fields the page needs: request and trace identifiers, terminal status, answer or concise reason, generated SQL when approved, bounded rows, row count, and structured clarification data. It does not return the full trace, provider prompts, credentials, raw exceptions, or unrelated policy internals. Domain outcomes such as `ok`, `blocked`, `unsupported`, `clarification_required`, `invalid`, and runtime failure remain explicit in the JSON body; malformed HTTP input uses a client error and unexpected adapter failures use a sanitized server error.

The web adapter constructs the same `AgentRequest` and calls the same `AskDataRuntime` used by the CLI. It cannot accept raw SQL and cannot call the query tool directly.

**Alternatives considered:** Return `AskDataResult.model_dump()` unchanged. Rejected because the browser does not need the complete trace and widening the exposed boundary increases accidental disclosure and coupling.

### 4. Promote clarification details into the terminal Ask Data contract

Add typed clarification fields to `AskDataResult`: the user-facing clarification question and a bounded collection of candidates with stable governed identifiers and display labels. The graph copies these fields from the validated semantic-resolution decision only for clarification-required results. SQL and rows remain absent for that status.

The UI displays candidate buttons and a free-text explanation input. A candidate selection or explanation is converted into a new explicit natural-language question that contains the original question and the user's clarification, then submitted to the same stateless endpoint. The semantic resolver and all downstream policy stages run again. The UI does not treat a candidate button as approval to execute SQL.

**Alternatives considered:**

- Keep candidates only in trace metadata: rejected because normal interfaces should not depend on internal observability payloads.
- Execute a preselected metric directly after a button click: rejected because it would bypass semantic resolution and the normal intent boundary.
- Add server sessions solely for clarification: rejected because the original question plus explicit clarification is sufficient for the MVP and preserves statelessness.

### 5. Make schema metadata structured once, then render existing prompt context from it

Introduce a typed, immutable schema catalog for the approved demo tables, their descriptions/grains, columns/types, and relationships. Generate both the LLM's schema text and the browser schema response from this catalog. Existing metric definitions and safety rules remain part of the same governed context. The schema endpoint reads this catalog; it does not introspect Postgres or system catalogs.

This removes drift between what the model is told and what the user sees. Tests will protect the prompt/schema contract and verify that only approved metadata is exposed.

**Alternatives considered:**

- Parse `SCHEMA_CONTEXT`: rejected because prose is not a reliable data format.
- Maintain a second frontend-only schema file: rejected because the two descriptions would drift.
- Query `information_schema`: rejected because it would expose a wider metadata surface and could disagree with the explicitly approved agent context.

### 6. Use a build-free single page with progressive result states

Serve plain HTML, CSS, and a small JavaScript module from package assets. The page has:

1. A top question form.
2. An LLM output card.
3. A SQL result card containing SQL and a bounded scrollable table.
4. A right-side table dropdown and schema detail panel.

JavaScript owns only view state: initial, loading, success, clarification, failure, and schema-loading failure. A new top-level submission replaces the displayed result. No question or result is written to local storage. Controls use native labeled form elements and remain keyboard operable.

**Alternatives considered:** A chat transcript UI. Rejected because the approved MVP intentionally removes sessions and history.

### 7. Verify behavior at the narrowest useful boundaries

Automated tests cover:

- Sanitized `POST /api/ask` mappings for success, clarification, policy rejection, empty input, and unexpected failures.
- Proof that the adapter calls `AskDataRuntime` and never the query executor directly.
- Clarification fields reaching `AskDataResult` and remaining incompatible with SQL/rows on unresolved ambiguity.
- Structured schema output and alignment with the generated LLM context.
- Static page and asset serving without adding snapshot tests for wording or visual styling.

Manual verification covers browser layout, keyboard use, horizontal/vertical result scrolling, responsive behavior at a narrow viewport, candidate selection, free-text clarification, and safe failure presentation. Existing runtime, safety, database, and eval suites continue to verify the reused agent path.

### Data flow

```text
Browser question
    -> POST /api/ask (validated natural-language input)
    -> existing AskDataRuntime
    -> intent + semantic resolution
       -> clarification_required -> sanitized clarification response -> browser choice/text -> new POST /api/ask
       -> allowed -> LLM candidate SQL -> SQL validation -> approved query -> read-only Postgres
    -> answer rendering + bounded rows + trace identity
    -> sanitized browser response

Browser schema dropdown
    -> GET /api/schema
    -> approved structured schema catalog
    -> selected table description, grain, columns, and relationships
```

The trust boundary remains unchanged: browser input and LLM output are untrusted; only QueryForge's policy and approved-query boundary can authorize database execution.

## Risks / Trade-offs

- **[Risk] A local HTTP endpoint is mistaken for a supported public API** -> Keep it loopback-bound by default, document it as an MVP UI adapter, and avoid public API versioning or deployment claims.
- **[Risk] Structured schema and prompt context drift** -> Generate both from one approved catalog and test representative tables, fields, relationships, and exclusions.
- **[Risk] Clarification text changes the user's meaning** -> Show the submitted clarification, rerun semantic resolution, and never make a suggestion executable authority.
- **[Risk] A large bounded result still strains the browser** -> Preserve the current execution row cap and render only returned rows inside an overflow container; do not add client-side full-dataset loading.
- **[Risk] Provider and database latency makes the page appear stuck** -> Show a loading state, disable duplicate submission, and surface the runtime's terminal failure without adding streaming complexity.
- **[Risk] Browser responses leak internals** -> Use explicit response models, sanitize unexpected errors, omit raw traces/prompts, and retain only request/trace identifiers for debugging.
- **[Trade-off] Plain JavaScript is less scalable than a component framework** -> Accept this for one page; reconsider only when a concrete second complex screen creates repeated state or component behavior.
- **[Trade-off] Stateless clarification repeats context in a new request** -> Accept the small repetition to avoid premature session infrastructure.
- **[Risk] Architecture documentation becomes stale** -> Update `docs/architecture-diagrams.md` with the local web path and schema/clarification flow in the same implementation change.

## Migration Plan

1. Complete and verify `enforce-live-answer-quality-gate`; record the evidence before checking off this change's prerequisite task.
2. Add the structured schema and clarification result contracts while preserving current CLI serialization compatibility.
3. Add the local web adapter, static page, focused tests, and documentation.
4. Run static checks, targeted tests, the full test suite, strict OpenSpec validation, and manual local browser verification.
5. Roll back by removing the `web` command, adapter, assets, and web-only dependencies. Additive clarification fields and the structured schema catalog may remain because they preserve existing CLI behavior and improve the core contract.
