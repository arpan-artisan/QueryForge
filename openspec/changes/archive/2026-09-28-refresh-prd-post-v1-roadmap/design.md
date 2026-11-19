## Context

See `proposal.md` for motivation. The repository now contains a stabilized Ask Data v1 workflow, but `PRD.md` still presents that implementation as future work and names an archived v0 change as the next step. Main OpenSpec requirements already describe the correct staged product direction.

## Goals / Non-Goals

**Goals:**

- Make the PRD accurately distinguish completed, partially completed, and deferred work.
- Preserve the existing two-tool vision and trust boundary.
- Define the next database-adapter change narrowly enough to discuss before implementation.

**Non-Goals:**

- No runtime or architecture changes.
- No adapter interface, Postgres refactor, or MySQL connector yet.
- No claim that Ask Data v1 is production-ready or generally reliable.

## Decisions

### 1. Rewrite stale status sections instead of appending a changelog

The PRD remains the current product-direction document, so obsolete v0 statements will be replaced with the current state. A historical appendix would leave contradictory guidance in place.

### 2. Mark stages by delivery state

Stages 1-4 are complete for the local v1 scope. Stage 5 is partial because session memory exists while persistent corrections, approved examples, and cross-session retrieval remain deferred. Stages 6-9 remain future work.

### 3. Make adapter design the next feature boundary

The next feature will first define the smallest database boundary around dialect identity, schema introspection, SQL-policy hooks, approved execution, readiness, and normalized results while preserving Postgres behavior. A second connector is deferred until that boundary is proven by the existing implementation.

Alternative: add MySQL while extracting the interface. Rejected because simultaneous abstraction and migration would make regressions harder to attribute.

### 4. Leave architecture diagrams unchanged

This change alters product documentation only. Execution flow, classes, contracts, statuses, commands, and user actions do not change, so `docs/architecture-diagrams.md` remains accurate.

## Risks / Trade-offs

- **PRD status can drift again** -> Record concrete completed archives and name only the immediate next feature.
- **The adapter scope can become speculative** -> Require the next OpenSpec exploration to map actual Postgres coupling before defining an interface.
- **“v1 complete” can be read as production-ready** -> Keep explicit reliability, persistent-memory, governance, deployment, and scale limitations.

## Migration Plan

1. Replace stale PRD version, date, current-stage, v0 behavior, roadmap status, success criteria, and next-change sections.
2. Review README and main specs for contradictions; edit only if the PRD refresh reveals one.
3. Validate the documentation-only OpenSpec change and inspect the diff.
4. Archive and push after review. Rollback is a single documentation commit revert.
