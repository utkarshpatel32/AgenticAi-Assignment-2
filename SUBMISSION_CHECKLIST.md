# Assignment 2 Submission Checklist

## Working application

- [ ] Node.js server starts with `npm start` and the browser UI opens at `http://127.0.0.1:3000`.
- [ ] Local student and approver accounts have been provisioned using `python scripts/setup_demo_accounts.py`.
- [ ] Own fee and scholarship records are accessible.
- [ ] Cross-student private record access is blocked at the agent and tool/application layers.
- [ ] Programme change creates a pending approval request and does not mutate the record immediately.
- [ ] Student role cannot approve a request.
- [ ] Rejected request leaves the record unchanged.
- [ ] Approved request executes only after an authenticated approver decision.
- [ ] Audit log records actor, action, target, authorization decision, approval status and result.
- [ ] OTP/password input is not stored in persistent memory, traces or audit data.
- [ ] Assignment 1 tools, memory, policy retrieval, context and tracing still work.

## Testing and evidence

- [ ] `python -m pytest -q` passes.
- [ ] `python scripts/run_evaluation.py` regenerates Assignment 1/2 comparison and Assignment 2 evaluation artifacts.
- [ ] Evaluation report explains functional pass rate, latency and offline/live token usage limitations.
- [ ] Sample trace and audit JSON files are included.

## GitHub

- [ ] Repository visibility is Public.
- [ ] Complete source, sample policy/data, tests, README and evaluation evidence are present.
- [ ] `.env`, real API keys, passwords, tokens and private keys are absent.
- [ ] Local database files, logs, caches and virtual environments are absent.
- [ ] `git status` and `git diff --cached` have been reviewed before push.
- [ ] Public repository opens in an incognito window while signed out.

## Explanatory video

- [ ] Architecture, agent flow, tools, memory, retrieval and context are explained.
- [ ] Own-record access and another-student denial are demonstrated.
- [ ] Pending request, student approval denial, rejection and approval are demonstrated.
- [ ] Audit records are shown and explained.
- [ ] Traces, task success, latency, token-usage limitations and retrieved evidence are explained.
- [ ] Source-code walkthrough is included; recording is not only a UI screen capture.
- [ ] No password, API key, `.env` file, token or real student data is visible.
- [ ] Video link is accessible to the evaluator and tested in an incognito window.
