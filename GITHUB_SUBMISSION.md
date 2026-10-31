# Public GitHub Submission Guide — Assignment 2

The submission must be a **public GitHub repository** with the complete runnable source, a clear README, sample data/policy, tests and evaluation evidence. No passwords, API keys, tokens, local databases or real student information may be committed.

## 1. Prepare the project locally

From the project root in VS Code:

```powershell
python -m pytest -q
python scripts/run_evaluation.py
python scripts/preflight_submission.py
```

Create your local logins with `python scripts/setup_demo_accounts.py`. The script prompts for local passwords and stores only salted hashes in the local SQLite database. The database is Git-ignored. The repository includes no default working passwords.

## 2. Review the files before staging

Run:

```powershell
git status --short
```

Confirm that none of the following are staged:

- `.env` or any real environment file;
- API keys, tokens, passwords or private keys;
- `data/aidtm_demo.db`, SQLite files or sidecars;
- `.venv/`, `venv/`, `node_modules/`, `__pycache__/` or cache directories;
- real student information or screenshots containing credentials.

The `.env.example` file is safe to commit because its API key field is blank. Inspect the staged diff (`git diff --cached`) before every push. A preflight script is a helper, not a guarantee that all possible secrets are detected.

## 3. Create the public repository

1. Sign in at https://github.com/.
2. Select **New repository**.
3. Use a name such as `aidtm-safe-student-support-agent-assignment-2`.
4. Select **Public**.
5. Leave “Add a README”, `.gitignore` and license unchecked because this project already has these files.
6. Create the repository.

## 4. Push from VS Code terminal

Run these commands in the project root (replace the username and repository URL):

```powershell
git init
git add .
git status
git diff --cached
git commit -m "Submit AIDTM Safe Student Support Agent Assignment 2"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/aidtm-safe-student-support-agent-assignment-2.git
git push -u origin main
```

If a Git repository or remote already exists, inspect `git status` and `git remote -v` instead of adding a duplicate remote.

## 5. Verify public access

- Open the repository in a private/incognito browser window while signed out of GitHub.
- Confirm `README.md`, source code, sample policy, sample data, tests, evaluation outputs and video script are visible.
- Confirm `.env`, local database, local credentials and generated cache/logs are absent.
- Clone the public repository into a separate temporary folder and follow the README from a clean environment.
- Run the tests and demo-account setup in that clean clone.

## 6. Publish the explanatory video

Record the working app using `VIDEO_WALKTHROUGH.md`. Explain the code and agent flow and demonstrate privacy, authorization, pending/rejected/approved changes, and auditability. Upload the recording to the platform accepted by the instructor, grant access to the evaluator and test the link in an incognito browser. The script is not a recorded video and does not create a video link.

Submit both the public repository URL and the accessible video URL. Verify both immediately before submission.
