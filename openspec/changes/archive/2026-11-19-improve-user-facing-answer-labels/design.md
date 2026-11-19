## Context

See `proposal.md` for motivation. Successful answer text is currently rendered deterministically from returned column names. Governed scalar metrics already use catalog display names, but non-governed results can expose provider-selected aliases such as `count`, `avg_order_value`, or `name`. The answer renderer receives the original question and rows, so the problem can be corrected without changing the result model or adding a provider call.

## Goals / Non-Goals

**Goals:**

- Keep final answer text deterministic and grounded in executed rows.
- Prefer clear provider-generated result aliases, normalize known analytical abbreviations, and supply bounded question context when an alias remains generic.
- Preserve the existing `AskDataResult` schema and every SQL trust boundary.

**Non-Goals:**

- Generate final prose with an LLM.
- Infer a complete business ontology from arbitrary SQL.
- Reject otherwise safe SQL solely because its presentation alias is imperfect.
- Change row values, ordering, preview limits, statuses, or trace behavior.

## Decisions

### Keep answer rendering deterministic

The existing renderer will remain a pure transformation of the original question, resolved governed metric when present, and returned rows. This avoids a second provider call, added latency, new failure modes, or unvalidated prose. A model-based renderer was rejected because it is larger and can invent claims after safe execution.

### Improve aliases at generation and normalize at presentation

The provider's SQL-generation instruction will request explicit, descriptive result aliases. Rendering will continue to treat returned rows as authoritative and will expand a small reviewed vocabulary of common analytical abbreviations, beginning with the confirmed `avg` failure. Descriptive aliases remain presentation hints, never execution approval.

### Contextualize generic labels with the original question

When the returned projection remains generic, the renderer will add bounded question context so `Count is 7` or a bare `Name` column does not stand alone. This fallback uses the original user text only as a label context; all claimed values still come from returned rows. It avoids brittle table-specific mappings while covering providers that omit or simplify aliases.

### Preserve the existing flow

The ordered flow remains:

1. Resolve intent and governed metric meaning.
2. Generate, validate, approve, and execute SQL.
3. Render returned rows using a governed metric label when available, otherwise a descriptive alias plus question context when needed.
4. Return the unchanged structured result contract.

No architecture diagram update is needed because no node, boundary, model, or interface changes; only generation guidance and deterministic presentation behavior change.

## Risks / Trade-offs

- **[Risk] User questions can be verbose when used as fallback context.** → Bound the displayed context and use it only for generic labels.
- **[Risk] A fixed abbreviation vocabulary cannot cover every future alias.** → Keep it limited to reproduced failures and add entries only with regression evidence.
- **[Risk] Providers may ignore alias guidance.** → The deterministic question-context fallback remains the correctness mechanism.
- **[Risk] Evaluation expectations could be loosened to hide bad output.** → Retain business terms for generic cases and add only independently reviewed synonyms that are already clear to users.
