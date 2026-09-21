# Phase 2A Implementation Review

**Status:** CHANGES REQUIRED

## Scope Lock

**PASS for versioned implementation files.** Commit `db9ae5b` changes the eight authorized files. No integration, credential, Phase 2B entity, route, or dependency was added.

## Test result

Executed `python -m pytest`.

Result: **5 collection errors; suite not green.** Pytest cannot read five residual `test/tmp*` directories left by failed Windows SQLite cleanup, so it cannot collect the full suite. This fails the Phase 2A Definition of Done.

## Findings

### Critical

None.

### Major

1. **Migration `0002` is not historical or bounded.** `alembic/versions/0002_phase_2a_persistent_foundation.py` calls `Base.metadata.create_all()` and `drop_all()`. Future model changes alter this old migration's behaviour, and downgrade can drop every table registered in metadata rather than only Phase 2A tables. This violates the approved explicit/reversible migration scope.
2. **Required repository boundaries and guards are absent.** `app/persistence/repositories.py` implements only `SourceRepository` and `AuditRepository`; the planned Provenance and Derivation boundaries, typed support validation, CRM-context validation, correction handling, checkpoint methods, and audit-history safeguards are missing.
3. **Identity and context invariants are incomplete.** There is no partial unique constraint for one active confirmed `IdentityLink`; `CRMContextLink` allows a non-confirmed row with `confirmed_at`; polymorphic record/support references are unconstrained and unvalidated.
4. **Append-only/history semantics are not implemented.** Observations, corrections and audit rows have no repository-level mutation prevention beyond missing convenience methods; `mark_retention()` mutates a source without retaining a transition/audit event. This does not satisfy the model's history-preserving requirement.
5. **Required test coverage is materially incomplete.** Tests omit mandatory checkpoint, CRM-context, identity-correction, evidence/support, unsafe-audit, migration constraints/table-set, and negative repository validations. The fixture creates metadata directly, which can conceal Alembic migration defects.
6. **Relevant suite is not green.** Residual inaccessible temporary directories cause collection failure, a regression of the Windows temporary-path requirement.

### Minor

1. `SourceObservation` uses a nullable-column `UniqueConstraint`; SQLite permits multiple null version markers, which is acceptable for observations but is not directly tested.

### Observation

1. `SourceRecord` uses SQLite's normal nullable unique constraint rather than the plan's partial index. SQLite's multiple-NULL semantics satisfy manual-source identity, but the exact planned physical constraint was not implemented.

## Coverage of required invariants

Implemented only partially: physical 2A table declarations, scoped source uniqueness, manual/WhatsApp one-to-one FKs, conversation source uniqueness, separate fact/inference/proposal tables, and basic idempotency uniqueness. All other mandatory invariants above remain unproven or incomplete.

## Required corrections

- Replace metadata-driven migration with explicit `op.create_table`, constraints/indexes and reverse-only-2A `op.drop_*` operations.
- Implement the planned provenance/derivation repositories and all invariant guards.
- Add identity/context/support validation and append-only history behaviour.
- Add the required isolated tests and repair controlled temporary-directory cleanup so the full suite is green.

## External systems

No IMAP/SMTP, Calendar, CRM, AI, keyring, credentials, network access, or production mutation was found or performed.

## Final verdict

**CHANGES REQUIRED**
