# Verification

## Completed evidence

- Both purpose-declared suites have strict reviewed answer expectations:
  development `ask-data-development-v1.2` (37 cases) and release
  `ask-data-release-v1.1` (10 cases).
- Deterministic grounding covers metric labels, required values and terms,
  unsupported scalar claims, explicit empty results, and bounded number,
  currency, percent, ISO date/time, boolean, and null normalization.
- Presentation list ordinals and the bounded preview remainder counter are not
  misclassified as database claims.
- The semantic judge uses a separate provider-agnostic boundary, strict JSON,
  temperature zero, bounded reasons, and evaluator-only inputs. It must exactly
  reproduce the versioned calibration fixture before trial verdicts count.
- Default runs remain credential-free and report semantic judging as
  `not_requested`; deterministic grades remain authoritative.

## Test and run evidence

- Focused evaluator tests: `131 passed`; evaluator plus provider tests:
  `146 passed`.
- Development reference with answer grounding: `37/37`, report
  `7bf9710bdd5d4a38b6a7b25e7c929f26`.
- Release reference with answer grounding: `10/10`, report
  `9223448079044f4eb435728764e21e08`.
- Credentialed judged development case `net-revenue`: calibration passed exactly;
  grounding, directness, completeness, and clarity all passed, report
  `a1ed42ac6d854559aa82608f6a1f650e`.

## Final repository validation

- Full suite: `607 passed, 8 skipped`; the skips are the documented opt-in
  Postgres evaluation integration tests.
- Ruff: `All checks passed!`.
- Strict OpenSpec validation: passed.
- All eight Mermaid diagrams rendered successfully to a temporary directory
  outside the repository.
- Calibration agreement, disagreement, malformed output, missing configuration,
  deterministic skip, subjective failure, and post-calibration unavailability
  paths have focused regression coverage.
