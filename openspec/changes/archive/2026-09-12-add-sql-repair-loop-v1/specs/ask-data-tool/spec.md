## ADDED Requirements

### Requirement: Bounded SQL repair loop
The Ask Data tool SHALL allow at most one SQL repair attempt after an allowed analytical request produces SQL that fails due to a repairable validation or execution problem. A repaired candidate MUST pass the same active SQL safety policy and approved-query execution boundary before database execution.

#### Scenario: Repairable validation failure succeeds
- **WHEN** an allowed analytical request produces candidate SQL with a repairable validation failure such as an unknown approved-context column, missing join, bad alias, or parseable syntax mistake
- **THEN** Ask Data may request one repaired SQL candidate and execute it only if the repaired SQL passes the active SQL safety policy and approval boundary

#### Scenario: Repairable execution failure succeeds
- **WHEN** an approved query reaches read-only execution but fails due to a repairable generated-SQL mistake such as an ambiguous column reference, missing relation alias, invalid grouping shape, or type-compatible expression error
- **THEN** Ask Data may request one repaired SQL candidate and execute it only if the repaired SQL passes the active SQL safety policy and approval boundary

#### Scenario: Repair attempt fails
- **WHEN** the repair attempt is unavailable, fails to produce SQL, produces invalid SQL, or produces SQL that still cannot be approved or executed
- **THEN** Ask Data returns a non-successful result with the original question, trace identity, generated SQL when available, validation or execution reason, and without attempting another repair

#### Scenario: One repair attempt only
- **WHEN** an Ask Data request has already used its repair attempt
- **THEN** any later validation or execution failure returns a terminal non-successful result without requesting another repaired SQL candidate

### Requirement: Non-repairable failures remain blocked
The Ask Data tool SHALL NOT request SQL repair for failures that indicate unsafe intent, policy bypass, non-analytical requests, mutation, prohibited database access, prohibited functions, prohibited objects, multi-statement SQL, resource abuse, or any other active policy violation.

#### Scenario: Unsafe intent is not repaired
- **WHEN** the user's original question violates the active intent policy
- **THEN** Ask Data returns the policy result without requesting initial SQL, repair SQL, or database execution

#### Scenario: Unsafe generated SQL is not repaired
- **WHEN** generated SQL attempts mutation, multiple statements, prohibited system metadata access, prohibited functions, forbidden clauses, unapproved objects, or another active SQL policy violation
- **THEN** Ask Data blocks the candidate and does not request a repaired SQL candidate

#### Scenario: Repaired SQL cannot bypass policy
- **WHEN** a repair candidate changes the query in a way that violates intent policy, SQL policy, approved-object rules, function policy, row-bound policy, or read-only execution rules
- **THEN** Ask Data rejects the repaired candidate and does not execute it
