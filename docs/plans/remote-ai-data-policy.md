# Remote AI Data Disclosure Policy — 2026-09-21

## Status

Approved by user.

This document resolves the disclosure-policy blocker identified in:

- `docs/plans/security-design-analysis.md`

It is authoritative for the next security-analysis iteration and for the later `docs/security.md`.

---

## 1. Core principle

Remote AI receives only the minimum context necessary for one concrete analysis operation.

The unit of disclosure is not an entire customer, account, opportunity, mailbox, CRM record set, or database.

The unit of disclosure is the smallest relevant context needed to complete a specific approved analysis task.

No unrelated records may be included.

---

## 2. Email body

**Allowed with minimization.**

Email body text may be sent to a remote AI provider only when needed for a specific task such as:

- summarization;
- question extraction;
- commitment extraction;
- next-step analysis;
- draft preparation;
- meeting preparation;
- commercial-risk analysis.

Prefer:

- the minimum relevant message;
- the minimum relevant excerpt;
- the minimum relevant thread subset.

Do not send unrelated mailbox content.

---

## 3. Email metadata

**Allowed when relevant.**

Permitted fields may include:

- sender;
- relevant recipients;
- subject;
- date/time;
- thread references needed for context.

Unnecessary metadata must be excluded.

---

## 4. Contact and company identity

**Allowed when necessary.**

Identifiable company and contact values may be sent when they materially improve the specific commercial analysis.

Pseudonymization is not required by default.

Do not send unrelated contacts or companies.

---

## 5. Work/project, opportunity and offer context

**Allowed with minimization.**

Permitted context may include:

- work/project identity;
- opportunity identity/status;
- offer identity/status;
- relevant commercial state;
- relevant next step;
- relevant commitment;
- relevant recent activity.

Do not send full historical dossiers when a smaller context is sufficient.

---

## 6. Manual notes

**Allowed when intentionally processed.**

Manual commercial notes may be sent when the user enters, selects, or otherwise requests analysis of that note or when it is specifically required for a concrete assistant workflow.

Only relevant context should accompany it.

---

## 7. Manually pasted WhatsApp text

**Allowed when intentionally processed.**

Manually pasted WhatsApp text may be sent for analysis when the user has supplied it for assistant processing.

Only the relevant pasted content and necessary context may be sent.

No automatic WhatsApp ingestion is authorized by this policy.

---

## 8. Calendar data

**Allowed with minimization.**

Permitted fields may include:

- event title;
- participants;
- date/time;
- relevant description;
- linked commercial context.

Only the data needed for meeting preparation, commitments, scheduling context, or another concrete assistant operation may be sent.

---

## 9. CRM-derived context

**Allowed selectively.**

Permitted CRM-derived context may include, when necessary:

- company name;
- contact name;
- work/project;
- opportunity;
- offer;
- status;
- recent relevant interaction;
- pending commitment;
- next step;
- relevant follow-up context.

The assistant must not send:

- full CRM exports;
- unrelated records;
- whole customer histories when a smaller subset is enough.

---

## 10. Attachments

**Automatic transmission prohibited.**

Attachments must not be transmitted to remote AI automatically.

A future attachment-analysis feature would require:

- explicit separate scope;
- explicit user action/approval;
- security review;
- data-minimization rules.

---

## 11. Credentials, tokens and secrets

**Always prohibited.**

Never transmit:

- passwords;
- IMAP credentials;
- OAuth refresh/access tokens;
- CRM authentication secrets;
- API keys;
- Windows Credential Manager secret values;
- session secrets;
- private keys;
- any other credential material.

---

## 12. Whole databases and bulk exports

**Always prohibited.**

Never transmit:

- complete SQLite databases;
- database dumps;
- bulk CRM exports;
- mailbox exports;
- indiscriminate commercial archives.

---

## 13. Logs and audit data

**Prohibited by default.**

Operational logs and audit records must not be sent to remote AI unless a future explicit policy authorizes a narrowly scoped diagnostic workflow.

Current MVP policy: do not transmit them.

---

## 14. Unrelated records

**Always prohibited.**

Records unrelated to the current analysis task must not be included merely because they are available locally.

---

## 15. Sensitive content minimization

When practical before remote transmission, exclude or redact content that is unnecessary for the task, including:

- passwords;
- tokens;
- banking details not required for the analysis;
- unrelated personal identifiers;
- unnecessary sensitive commercial information.

If removing the data would make the requested analysis impossible, the assistant must still limit disclosure to the smallest necessary subset.

---

## 16. AI output authority

Remote AI has no execution authority.

AI output may only become:

- candidate extracted facts;
- inferences;
- proposals;
- summaries;
- questions;
- commitments;
- tasks;
- next steps;
- response drafts.

AI output cannot itself:

- approve an action;
- send an email;
- move a message;
- create a draft;
- modify Calendar;
- write to CRM;
- change configuration;
- access credentials;
- override application rules.

External mutations still require the approved:

```text
proposal → explicit approval → revalidation → execution → audit
```

flow.

---

## 17. Prompt-injection boundary

All commercial content sent to remote AI remains untrusted source data.

Instructions embedded in:

- email;
- WhatsApp;
- notes;
- Calendar;
- CRM context;
- future attachments

must never be treated as application-level instructions or authorization.

---

## Result

The remote-AI disclosure blocker is resolved.

Codex should now repeat the security analysis using this policy and determine whether the project is `READY FOR APPROVAL` to create `docs/security.md`.
