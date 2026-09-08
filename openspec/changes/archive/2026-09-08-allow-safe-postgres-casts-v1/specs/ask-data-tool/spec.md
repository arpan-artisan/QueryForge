## ADDED Requirements

### Requirement: Restricted built-in scalar conversions
Ask Data SHALL allow standard PostgreSQL `CAST(expression AS type)` and `expression::type` conversions to unquoted, unqualified built-in DATE, TIMESTAMP, TIMESTAMPTZ, BOOLEAN, SMALLINT, INTEGER, BIGINT, NUMERIC/DECIMAL, REAL, DOUBLE PRECISION, TEXT, VARCHAR, and CHAR targets, including their parser-recognized unquoted built-in aliases. Numeric precision SHALL be limited to 1-38 with optional scale 0-precision; character length SHALL be limited to 1-1024; timestamp fractional precision SHALL be limited to 0-6. Type modifiers MUST be literal integers and SHALL be rejected on other targets.

#### Scenario: Monthly revenue uses a date cast
- **WHEN** otherwise approved SQL groups completed-order revenue using `DATE_TRUNC('month', order_date)::date`
- **THEN** the SQL passes cast validation and returns the expected monthly values through normal read-only execution

#### Scenario: Rounded aggregates are normalized
- **WHEN** SQL normalization inserts an approved decimal cast into a rounded aggregate
- **THEN** executor revalidation accepts the same conversion

#### Scenario: Unsupported cast target
- **WHEN** SQL casts to an array, quoted, custom or schema-qualified type, domain, catalog identifier such as REGCLASS, or any other target outside the approved set
- **THEN** the system blocks it with `cast_type_not_allowed` before database execution

#### Scenario: Unsupported cast modifiers
- **WHEN** SQL uses dynamic, excessive, negative, or otherwise unsupported type modifiers
- **THEN** the system blocks it with `cast_modifier_not_allowed` before database execution

#### Scenario: Nonstandard cast syntax
- **WHEN** a parsed conversion uses TRY_CAST, formatting clauses, or other unsupported conversion options
- **THEN** the system blocks it with `cast_syntax_not_allowed`

### Requirement: Conversions preserve recursive safety checks
Allowing a cast SHALL NOT approve its operand or nested expressions. Existing column, source, function, statement, row-bound, and executor checks MUST continue to apply throughout the query.

#### Scenario: Dangerous operand hidden in a cast
- **WHEN** a permitted text cast wraps `pg_read_file`, a restricted column, or a nested unapproved cast
- **THEN** the underlying policy violation remains blocked or unsupported before execution

#### Scenario: Conversion fails on data
- **WHEN** a permitted conversion cannot convert an actual database value
- **THEN** Ask Data returns its normal database execution error without claiming success
