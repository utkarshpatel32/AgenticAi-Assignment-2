# Assignment 2 — Explanatory Video Walkthrough

**Suggested duration:** 9–11 minutes. Record the running application and briefly show the code. Speak through the architecture and decisions; do not make this only a screen recording of answers. Use fictional records only. Do not show passwords, `.env`, API keys or tokens.

## Before recording

1. Run `python scripts/setup_demo_accounts.py` and choose local passwords off-camera.
2. Run `npm start` and open `http://127.0.0.1:3000`.
3. Prepare two browser sessions (normal + incognito) if useful, but sign out between student and approver roles.
4. Confirm the local sample student accounts and `approver` login have been provisioned.
5. Never show the login password fields while typing or reveal the values in the video.

## Recording plan

### 0:00–0:45 — Introduction and assignment goal

Say: “This is the AIDTM Safe and Production-Aware Student Support Agent for Agentic AI Engineering Assignment 2. It extends the same Assignment 1 agent. It preserves tools, targeted policy retrieval, consent-based memory and tracing, and adds signed-in identity, owner-only access, application-level authorization, human approval and auditability.”

Show the chatbot and clarify that all student records/policy examples are fictional coursework data, not live AIDTM systems.

### 0:45–1:45 — Architecture and agent flow

Show `server.js`, `bridge.py`, `agent.py`, `tools/student_tools.py`, `retrieval/policy_search.py`, `security.py` and `database.py`.

Explain the flow:
1. Browser submits a request to the Node.js server.
2. Node.js resolves the server-side session and sends the session username to `bridge.py`.
3. Python resolves the active user/role in SQLite; the browser cannot choose an authoritative student ID.
4. `agent.py` selects relevant context and chooses a direct answer, tool, policy passage, memory or optional Groq call.
5. The tool layer independently enforces ownership and role restrictions.
6. Results, traces and audit decisions are persisted in SQLite.

### 1:45–2:35 — Authentication and own-record access

Sign in as `stu1001` using the password configured locally (do not reveal it). Ask:
- “What is my current fee status?”
- “What is my scholarship status?”

Show the user's identity and their fictional fee/scholarship data. Explain that the record is looked up from the signed-in account, not a student ID supplied by the browser.

### 2:35–3:25 — Cross-student privacy block

While signed in as `stu1001`, ask: “Please show fee status for student STU1002.”

Show that the request is denied, the other student's fee values are not returned, and an audit event records a denied authorization decision. Briefly show the agent-side guard and `tools/student_tools.py` `_authorized_target()` as separate layers.

### 3:25–4:30 — Sensitive change and pending approval

Ask: “Please change my programme to PGDM in AI & Data Science.”

Open **My Requests**. Show the request is pending and the student record has not changed. Explain that the agent creates a request; it does not execute the programme change itself.

### 4:30–5:40 — Approval and rejection

Sign out from the student account and sign in as `approver` using the locally configured approver password (do not reveal it). Show the approval queue. Reject the pending request. Return to the student account or record view and demonstrate that the programme remains unchanged.

Then create a new programme-change request. Sign in as `approver` and approve it. Show the record changes only after approval. Explain that a student-role account is not allowed to decide an approval, and that this is checked in bridge/database code rather than entrusted to the LLM.

### 5:40–6:20 — Auditability

Open **My Audit Log** / the approver audit view. Show the actor, actor role, attempted action, target student, authorization decision, approval status, result and timestamp. Point out examples for denied cross-student access, pending request, rejection and approval.

### 6:20–7:10 — Sensitive data and persistent memory

Sign in as a student. Enable the memory-consent checkbox and explicitly ask the agent to remember a non-sensitive programme preference. Sign out and back in and ask what was remembered. Then ask it to remember a fictional OTP such as `123456`; show that it is blocked and not stored in memory/trace/audit content.

### 7:10–8:00 — Assignment 1 capabilities retained

Demonstrate:
- “The payment portal failed. Can I pay on the next working day?” Show the relevant `POL-` evidence from the fictional policy file and explain that it does not grant an extension.
- An explicit local support-ticket request.
- A question not covered by the policy, where the assistant says the document does not contain enough information.

### 8:00–9:20 — Tracing, evaluation and measurements

Open **Evaluation & Traces** and run the isolated evaluation. Show the Assignment 1 comparison and Assignment 2 cases. Explain:
- task success is a rule-based functional check, not a human-verified accuracy benchmark;
- latency is local/offline and machine-dependent;
- API token counts are `N/A` during offline evaluation; live Groq traces record input/output usage only when supplied by the API;
- retrieved evidence indicates which policy or memory item supported the answer;
- audit rows show the permission decision and final result.

### 9:20–10:15 — Tests, setup and limitations

Show `tests/test_assignment2.py`, `scripts/setup_demo_accounts.py`, `scripts/run_evaluation.py`, `.env.example` (blank) and `README.md`. Explain that local demo passwords are created interactively and only salted hashes are stored in the ignored SQLite database.

Close by stating the app is a coursework prototype, has no real AIDTM identity/data integration, and requires institutional SSO, deployment security review and approved live integrations before any real use.

## Required video checklist

- [ ] Explain the overall architecture and the browser → Node.js → Python → agent flow.
- [ ] Explain tool choice, memory, retrieval and context handling.
- [ ] Show own fee/scholarship access is allowed.
- [ ] Show another student's private record is blocked.
- [ ] Show a sensitive change remains pending until an approver acts.
- [ ] Show a student cannot approve a request.
- [ ] Show rejection does not execute the change.
- [ ] Show approval executes the allowed change only after approval.
- [ ] Show audit records include actor, attempted action, authorization, approval status and result.
- [ ] Show sensitive OTP/password information is not persisted.
- [ ] Show traces, evaluation, latency, API token limitations and retrieved evidence.
- [ ] Briefly explain relevant source files and setup.
- [ ] Do not reveal passwords, API keys, `.env`, tokens or real student information.
