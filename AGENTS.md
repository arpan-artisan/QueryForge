# QueryForge Agent Instructions

## Code Quality

- Use the `ponytail` skill or ponytail principles for every coding change: read the touched flow first, then choose the smallest correct implementation.
- Prefer deletion, existing code, standard library, native platform behavior, and already-installed dependencies before adding new abstractions or packages.
- Do not add speculative interfaces, factories, config, scaffolding, or files for future features.
- Keep trust-boundary code explicit. Do not simplify away input validation, SQL safety, intent policy, approved-query enforcement, read-only execution, secret handling, error handling that prevents data loss, observability needed for debugging, or tests for non-trivial logic.
- Add or keep the smallest useful test for non-trivial branches, parsers, policy checks, database behavior, and security-sensitive paths.
- If a deliberately simple shortcut has a known ceiling, mark it with a `ponytail:` comment that names the ceiling and upgrade path.

## OpenSpec

- Specs describe observable behavior, not internal class shapes.
- For pure refactors, use `skip_specs: true` instead of inventing requirements.
- Proposal, design, and tasks should explicitly prefer the smallest behavior-preserving change that satisfies the current scope.
