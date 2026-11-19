## Why

`PRD.md` still describes the initial NL2SQL prototype as future work even though Ask Data v1 has been implemented, stabilized, archived, and pushed. The product roadmap needs an accurate baseline before the next feature is designed.

## What Changes

- Update the PRD to version 0.2 and identify the current stage as stabilized local Ask Data v1.
- Separate completed v1 capabilities from deferred memory, provider, metadata, adapter, governance, dashboard, website, and production work.
- Replace the obsolete `build-nl2sql-cli-v0` follow-up with a narrowly scoped database-adapter design change.
- Keep MySQL as the likely second connector, but require adapter boundaries to be proven around the existing Postgres implementation before adding it.

### Non-Goals

- No runtime, test, dependency, database, CLI, API, or user-visible behavior changes.
- No database adapter implementation or second connector in this change.
- No persistent memory, governance, dashboard, website, or deployment work.

## Capabilities

### New Capabilities

None. This is a documentation-only refresh.

### Modified Capabilities

None. Existing product-direction requirements already define the staged roadmap and remain unchanged.

## Impact

- `PRD.md` becomes an accurate post-v1 source of product direction.
- OpenSpec main capability specs, runtime code, safety boundaries, database execution, LLM behavior, and public interfaces are unchanged.
- The next proposed feature is clearly bounded for later discussion and implementation.
