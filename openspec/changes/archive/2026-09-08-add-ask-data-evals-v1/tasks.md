## 1. Tasks and Graders

- [x] 1.1 Add strict versioned task contracts and 30 balanced dev/held-out cases; verify invalid contracts are rejected and all reference SQL passes policy.
- [x] 1.2 Implement value-based result comparison and separate status, safety, result, and diagnostic grades; verify equivalent outputs pass and wrong values, duplicate loss, ordering, null, numeric, and unsafe-call mutations fail.

## 2. Execution and Reports

- [x] 2.1 Implement reference calibration, content stability checks, fresh production-agent trials, and explicit live provider mode; verify real Postgres references and scripted malicious/provider-error paths with integration and unit tests.
- [x] 2.2 Add repeats, failure categories, report aggregation, redacted JSON transcripts and Markdown reports; test mixed pass/fail trials, setup errors, secret removal, and output uniqueness.
- [x] 2.3 Expose evals run with split/case/mode/trial selection and exit codes; verify CLI success, failure, and invalid-input behavior.

## 3. Documentation and Validation

- [x] 3.1 Document Anthropic-derived authoring/review practices and commands; update and validate living flow, class, and user action diagrams against actual code.
- [x] 3.2 Add credential-free Postgres reference eval CI; run the full reference suite and inspect passing and failing transcripts, plus a bounded live run if configured, clearly distinguishing evidence.
- [x] 3.3 Run focused tests, full pytest, Ruff, and OpenSpec strict validation; verify secret files and generated reports remain ignored and record evidence without archiving or pushing.
