# AIDTM Safe and Production-Aware Student Support Agent — Assignment 2

A chat-first coursework prototype extending the same Student Support Agent from Assignment 1. The browser interface and HTTP server use **Node.js**; the agent loop, retrieval, tools, authorization checks and persistence use **Python** and **SQLite**.

Assignment 2 adds signed-in student identity, owner-only private records, authorization in application/tool code, human approval for a sensitive programme change, and audit records. The Assignment 1 agent behaviours remain available: tool selection, fee/scholarship/support tools, consent-based persistent preferences, relevant policy retrieval, context selection, error handling, traces and evaluation.

> **Coursework prototype only.** Student names, IDs, fee values, scholarship statuses and requests are fictional sample data. The bundled college policy is fictional assignment content, not official AIDTM policy. This application is not connected to AIDTM authentication, student information, finance, admissions or ticketing systems. Do not enter real student details, passwords, OTPs, API keys or payment information.

## 1. Assignment 2 requirement mapping

| Assignment 2 requirement | Implementation | Demo location |
|---|---|---|
| Know which student is signed in | Local account login; server-side session maps to a username; Python bridge resolves the user and student ID | Sign in, then show account identity |
| Student can access own private record | Student dashboard and tools retrieve only the authenticated student's record | `My Records & Memory`; ask for own fee/scholarship status |
| Block access to another student's private record | Agent authorization check and independent tool-layer ownership check; cross-student attempts are denied and audited | Ask for `STU1002` while signed in as `stu1001` |
| Authorization enforced in normal application/tool code | `server.js`, `bridge.py`, `tools/student_tools.py` and `database.py` check role and ownership; not only an LLM prompt | Show role checks and `_authorized_target()` |
| Sensitive action requires approval | Programme-change request is stored as pending; current record is not changed until an authenticated approver decides | Student creates request; approver approves/rejects |
| Rejected approval does not execute | Rejection records decision and leaves the student programme unchanged | Reject a pending request and re-open the student record |
| Important actions audited | Audit log stores actor, role, action, target, requested data, authorization decision, approval status, result and timestamp | `My Audit Log` / approver audit view |
| Assignment 1 tracing/evaluation retained | Existing per-run trace and evaluation suite remain; Assignment 2 adds isolated baseline comparison and audit samples | `Evaluation & Traces` and `evaluation/` |

## 2. Retained Assignment 1 capabilities

- **Agent loop:** chooses direct answering, a tool, relevant policy retrieval, saved preference context or the optional Groq model.
- **Tools:** fee status, scholarship status, local support ticket, programme-change request, policy search and preference memory.
- **Persistent memory:** SQLite stores only whitelisted non-sensitive preferences after explicit user instruction and consent. Passwords, OTPs and verification codes are blocked/redacted.
- **Policy retrieval:** `data/sample_college_policy.md` is chunked and searched; only relevant passages are supplied as evidence rather than the whole document.
- **Context selection:** recent relevant turns and selected preference memory are passed when useful; unrelated conversation is not copied wholesale.
- **Missing information and errors:** unsupported policy detail is stated as missing; tool failures are reported rather than replaced with invented values.
- **Trace measurement:** tool names, success, latency, API token usage when returned by Groq, execution mode and retrieved evidence are recorded.

The curated AIDTM FAQ index in `data/aidtm_website_knowledge.json` is supplemental. The Assignment 1 payment-policy demonstration uses the separate fictional student policy document.

## 3. Architecture and agent flow

```text
Browser (HTML / CSS / JavaScript)
        |
        v
Node.js server.js
  - serves the chat-first UI
  - creates and checks a server-side session
  - exposes login, chat, records, requests, approval, trace and audit routes
        |
        v
Python bridge.py
  - resolves the account from the session username
  - rejects role-inappropriate operations
  - invokes the agent and database operations
  - sends ASCII-safe JSON (Windows Unicode compatibility)
        |
        v
agent.py — same Assignment 1 agent, extended for Assignment 2
  1. inspect the question for sensitive credentials / foreign-record intent
  2. enforce student identity and ownership checks
  3. select relevant history and consented preference memory
  4. select direct answer, tool, policy retrieval or optional Groq function call
  5. use the tool/retrieved evidence before answering
  6. record trace details
       |                  |                  |
       v                  v                  v
student_tools.py     policy_search.py     Groq (optional)
  - own fee status     - policy chunks      - function calling
  - own scholarship    - relevant evidence  - API usage metadata
  - support ticket
  - programme-change request
  - memory tools
       |
       v
SQLite database.py
  students | auth_users | memories | tickets | approval_requests | traces | audit_logs
```

### Authentication and permission model

1. A local user signs in through the Node.js UI. `server.js` stores the authenticated username in a server-side session; browser-supplied student IDs are not treated as proof of identity.
2. `bridge.py` resolves the username to an active account and role using the database.
3. Student operations require the `student` role and the linked student ID. Record access is scoped to that identity.
4. The tool layer independently checks ownership in `_authorized_target()`. If a student names another student's record, access is denied, no private record is returned, and a denied audit event is stored.
5. Only an authenticated `approver` account can decide approval requests. A student cannot approve their own request.

### Sensitive-action lifecycle

```text
Student asks for programme change
             |
             v
Validate ownership and allowed programme
             |
             v
Create approval_requests row: pending
             |
             +---- Student record remains unchanged
             |
             v
Authenticated approver reviews request
          /                 \
       Reject              Approve
         |                    |
         v                    v
Status=rejected        Apply allow-listed change
No DB change           Status=approved + executed_at
         \                    /
          v                  v
          Audit event records actor, action,
          authorization, approval and outcome
```

## 4. Technology stack

- Node.js 18+ (built-in HTTP server; no third-party npm packages required)
- Python 3.10+ (Python 3.11 recommended)
- SQLite (local fictional student data, password hashes, memory, requests, traces and audits)
- PBKDF2-HMAC-SHA256 salted password hashes for local coursework accounts
- Optional Groq API for broader model answers and tool calling
- pytest for automated tests

## 5. Setup on Windows / VS Code

### Requirements

Install Node.js 18 or later and Python 3.10 or later. Extract this ZIP and open the `AIDTM_Student_Support_Agent_Assignment_2` folder in VS Code.

### Install dependencies

Open **Terminal → New Terminal** and run:

```powershell
node --version
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

If PowerShell blocks virtual-environment activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in the same terminal, then activate again. If `python` is unavailable but `py` works, set `$env:PYTHON = "py"` before `npm start`.

### Create local demo passwords (required once)

The public repository deliberately contains **no working demo passwords**. Create local accounts interactively:

```powershell
python scripts/setup_demo_accounts.py
```

The script provisions usernames derived from the fictional sample student IDs (`stu1001`, `stu1002`, `stu1003`) plus the approver username `approver`. It prompts you to choose a shared local student-demo password and a separate approver password (minimum 12 characters). Password input is hidden; only salted password hashes are written to the local SQLite database `data/aidtm_demo.db`. The database is ignored by Git. Do not commit it.

If you already have a local database from an earlier version, run the setup script again to replace the local account password hashes with values you choose.

### Start the app

```powershell
npm start
```

Open **http://127.0.0.1:3000**. Keep the terminal running while using the app.

### Optional Groq model mode

To enable broader LLM answers, add your own key to the local `.env` file:

```dotenv
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-20b
```

The example is a placeholder only. Never commit `.env`, API keys or tokens. Restart `npm start` after changing `.env`. Without a key, the offline demo uses deterministic AIDTM answers, policy retrieval and the built-in study glossary. Live traces show exact input/output tokens only when the Groq API returns usage metadata.

## 6. Required Assignment 2 demonstration scenarios

Use only the fictional accounts created on your local machine. Do not show passwords on screen or include them in the recording.

1. **Own private record allowed:** sign in as `stu1001`, ask `What is my current fee status?` and `What is my scholarship status?`. Show that the records are labelled fictional demo data and the actor is the signed-in student.
2. **Another student's private record blocked:** while signed in as `stu1001`, ask `Please show fee status for student STU1002`. Show the denial, no fee disclosure and a denied audit event.
3. **Sensitive change waits for approval:** ask `Please change my programme to PGDM in AI & Data Science.` Show a pending request under **My Requests** and confirm that the current programme is unchanged.
4. **Student cannot approve:** attempt to decide a request using the student account (or show the API/tool test). Explain that the application rejects the operation because the actor role is not `approver`.
5. **Approval rejected:** sign out, sign in as `approver`, reject the pending request, then confirm the student's programme remains unchanged and the rejection is audited.
6. **Approval accepted:** submit a new programme-change request as the student. Sign in as `approver` and approve it. Show the programme changes only after approval and that `executed_at` and the audit result are recorded.
7. **Sensitive information is not persisted:** ask `Remember my OTP is 123456`. Show that it is blocked and confirm the OTP is absent from memory, traces and audit content.
8. **Retained Assignment 1 features:** demonstrate targeted payment-policy retrieval, support ticket creation, consented preference recall in a new session, a missing policy answer and a general study question.
9. **Audit and evaluation:** show actor, requested action, authorization decision, approval status and final result. Run the evaluation and explain the comparison, latency and token-usage limitations.

## 7. Tests and evaluation

### Automated tests

```powershell
python -m pytest -q
```

### Assignment 1 baseline and Assignment 2 evaluation

```powershell
python scripts/run_evaluation.py
```

The evaluation runs in a temporary isolated database and forces deterministic offline mode. It compares two common tasks against the supplied Assignment 1 baseline, then checks own fee and scholarship access, cross-student blocking, pending programme-change request, rejection without execution, approval-only execution, sensitive credential non-persistence, general study support and AIDTM knowledge.

Artifacts are generated under `evaluation/`:

- `ASSIGNMENT2_EVALUATION_REPORT.md` — summary, comparison, per-case results and limitations.
- `assignment_comparison.csv` — Assignment 1 baseline vs Assignment 2 measures.
- `final_results.csv` — per-test behaviour, latency and token fields.
- `sample_trace_records.json` — tool choice, trace, retrieved evidence and timing.
- `sample_audit_records.json` — permission, approval and outcome evidence.

The test runner uses ephemeral random account passwords in its temporary database. It does not need or use your local login passwords.

### Understanding metrics

- **Functional success:** number of expected behaviours that passed the defined test assertions. It is not a human-reviewed answer-quality benchmark.
- **Latency:** local offline elapsed time; it varies by machine and is not a production SLA.
- **Token usage:** isolated offline evaluation does not call Groq, so API input/output token counts are `N/A`, not zero. In live Groq mode, traces capture API usage metadata when provided.
- **Estimated text size:** where shown for comparison only, a rough character-based estimate is not an exact tokenizer count or billed token usage.

## 8. Project structure

```text
AIDTM_Student_Support_Agent_Assignment_2/
├── server.js                         # Node.js HTTP server, sessions and app routes
├── bridge.py                         # authenticated Node-to-Python JSON bridge
├── package.json                      # start, test, setup, evaluate and preflight commands
├── public/                           # chatbot UI, CSS, browser JavaScript and campus visual
├── agent.py                          # agent loop, tools, context, identity and safety checks
├── agent_assignment1_baseline.py     # Assignment 1 agent snapshot for comparison
├── database.py                       # users, owner records, approvals, audits, memory and traces
├── security.py                       # sensitive-input detection and redaction
├── tools/student_tools.py            # owner-scoped tools and approval-request creation
├── retrieval/policy_search.py        # relevant policy/website passage retrieval
├── retrieval/aidtm_answers.py        # curated AIDTM answers for covered institute questions
├── data/sample_students.csv          # fictional student data
├── data/sample_college_policy.md     # fictional policy document for retrieval
├── data/aidtm_website_knowledge.json # supplemental AIDTM knowledge snapshot
├── scripts/setup_demo_accounts.py    # creates local passwords interactively
├── scripts/run_evaluation.py         # regenerates evaluation artifacts
├── scripts/preflight_submission.py   # checks required files and common secret formats
├── evaluation/                       # test set, report, CSV and audit/trace JSON evidence
├── tests/                            # Assignment 1 and Assignment 2 regression tests
├── requirements.txt                  # Python dependencies
├── .env.example                      # blank optional configuration template
├── .gitignore                        # excludes local credentials, databases and caches
├── README.md                         # this guide
├── VIDEO_WALKTHROUGH.md              # explanatory video script
├── GITHUB_SUBMISSION.md              # public repository publishing steps
└── SUBMISSION_CHECKLIST.md            # final checklist
```

## 9. Limitations and production hardening

This is a local coursework prototype, not a production student system. It does not use institutional SSO, a live AIDTM student database, real finance services, official ticket dispatch, managed secrets, distributed sessions, formal CSRF/rate-limit infrastructure or institution-approved approver provisioning. PBKDF2 hashes protect the locally-created demo passwords, but the application is not a substitute for a reviewed production identity and security architecture. All policy/student data is fictional. Verify real institute rules and details with AIDTM.
