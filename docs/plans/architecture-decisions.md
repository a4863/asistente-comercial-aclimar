# Architecture Decisions — 2026-09-21

## Status

Approved by user.

These decisions resolve the blockers identified in:

- `docs/plans/architecture-design-analysis.md`

They are authoritative for the next architecture-analysis iteration.

---

## 1. Local UI and execution model

**Decision:** local web application accessed in a browser.

The application runs locally on the user's Windows PC and is accessed through localhost.

No hosted backend, SaaS deployment, or external web server is introduced.

Rationale:

- simplest development and maintenance path;
- consistent with local-only and single-user requirements;
- easier debugging and iteration than a native desktop or hybrid shell;
- does not require cloud deployment.

---

## 2. Persistence and data-access approach

**Decision:** embedded relational persistence with a dedicated data-access layer.

The approved data model is relational and requires:

- integrity constraints;
- provenance;
- audit history;
- lifecycle state;
- idempotency;
- relationships across many assistant-owned entities.

The concrete database engine, ORM/data-access technology, and migration mechanism remain architecture-design choices to document next.

---

## 3. Synchronization and background execution

**Decision:** synchronization runs inside the main application process while the application is running.

Operational constraint approved by the user:

- the Commercial Assistant and the CRM are expected to remain running continuously, 24 hours per day, Monday through Friday;
- they will normally be stopped on Saturdays and Sundays.

Therefore the MVP does not need a second always-on Windows service or separately scheduled background process.

Required behavior:

- periodic synchronization runs while the application process is active;
- IMAP, Calendar, and other approved background reads continue during weekday operation;
- on startup after downtime, including Monday startup after the weekend, incremental synchronization and reconciliation must catch up from the last successful cursor/checkpoint;
- missed weekend activity must be processed incrementally without requiring full historical resynchronization;
- integration-specific failures must not terminate the whole application;
- sync state/checkpoints must be persisted.

A future separate Windows background service remains out of MVP unless later operational evidence justifies it.

---

## 4. Credential storage

**Decision:** use the operating-system secure credential store.

Target environment: Windows.

Credentials for integrations must remain:

- outside source code;
- outside Git;
- outside plaintext application data;
- outside normal logs.

Each integration credential must remain independently manageable and revocable.

Exact Windows secure-storage technology is to be selected and documented in architecture/security design.

---

## 5. AI execution strategy

**Decision:** provider-agnostic AI boundary, initially designed to support remote AI under the approved disclosure limits.

The domain must not depend directly on one AI provider or model family.

Architecture must define an abstraction such as an AI service boundary so a future provider/model can be changed without rewriting business rules.

Before any remote AI integration is implemented:

- `docs/security.md` must define the exact data classes that may leave the device;
- credentials must never be transmitted as model context;
- attachments must not be transmitted automatically;
- whole databases and unrelated commercial data must not be transmitted.

The specific provider/model is not selected by this decision.

---

## Result

The five architectural blockers from the previous analysis are resolved.

Codex should now repeat the architecture analysis against these approved decisions and determine whether the project is `READY FOR APPROVAL` to create `docs/architecture.md`.
