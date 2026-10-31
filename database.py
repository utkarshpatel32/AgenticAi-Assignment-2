"""SQLite persistence for the Assignment 2 prototype.

All student information is fictional demo data. Authentication and approval flows are
implemented for coursework demonstration only, not as a production identity system.
"""
from __future__ import annotations

import csv
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from security import contains_sensitive_input, redact_sensitive_text, safe_json_value

ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = ROOT_DIR / "data" / "aidtm_demo.db"
STUDENT_CSV_PATH = ROOT_DIR / "data" / "sample_students.csv"
PBKDF2_ITERATIONS = 240_000
ALLOWED_PROGRAMMES = {"PGDM in Big Data Analytics", "PGDM in AI & Data Science"}


def db_path() -> Path:
    configured = os.getenv("AIDTM_DB_PATH", "").strip()
    path = Path(configured).expanduser() if configured else DEFAULT_DB_PATH
    if not path.is_absolute():
        path = ROOT_DIR / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield a configured SQLite connection and ALWAYS close the file handle.

    ``sqlite3.Connection``'s built-in context manager commits/rolls back but does
    not close the connection. That can keep temporary evaluation databases locked
    on Windows when ``TemporaryDirectory`` tries to remove them (WinError 32).
    All project call sites use ``with get_connection() as conn``, so this wrapper
    preserves that API while guaranteeing closure.
    """
    conn = sqlite3.connect(db_path(), timeout=15)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 15000")
        yield conn
        conn.commit()
    except BaseException:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        raise
    finally:
        conn.close()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, expected = encoded_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _seed_students(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT COUNT(*) FROM students").fetchone()[0] > 0:
        return
    if not STUDENT_CSV_PATH.exists():
        return
    with STUDENT_CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute(
                """INSERT OR IGNORE INTO students
                   (student_id, display_name, programme, total_fee, paid_fee, pending_fee,
                    fee_status, due_date, scholarship_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    row["student_id"], row["display_name"], row["programme"], int(row["total_fee"]),
                    int(row["paid_fee"]), int(row["pending_fee"]), row["fee_status"], row["due_date"],
                    row.get("scholarship_status", "Not available"),
                ),
            )


def _seed_auth_users(conn: sqlite3.Connection) -> None:
    """Do not create public, hard-coded demo passwords.

    Local accounts are provisioned explicitly with scripts/setup_demo_accounts.py.
    The SQLite database is local-only and excluded from Git.
    """
    return


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                programme TEXT NOT NULL,
                total_fee INTEGER NOT NULL,
                paid_fee INTEGER NOT NULL,
                pending_fee INTEGER NOT NULL,
                fee_status TEXT NOT NULL,
                due_date TEXT NOT NULL,
                scholarship_status TEXT NOT NULL DEFAULT 'Not available'
            );
            CREATE TABLE IF NOT EXISTS auth_users (
                username TEXT PRIMARY KEY COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('student', 'approver')),
                student_id TEXT UNIQUE,
                display_name TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(student_id)
            );
            CREATE TABLE IF NOT EXISTS support_tickets (
                ticket_id TEXT PRIMARY KEY,
                student_id TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(student_id)
            );
            CREATE TABLE IF NOT EXISTS memories (
                memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                memory_key TEXT NOT NULL,
                memory_value TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(student_id, memory_key),
                FOREIGN KEY (student_id) REFERENCES students(student_id)
            );
            CREATE TABLE IF NOT EXISTS traces (
                trace_id TEXT PRIMARY KEY,
                student_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                tools_used TEXT NOT NULL,
                tool_success INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                input_tokens INTEGER,
                output_tokens INTEGER,
                retrieved_evidence TEXT NOT NULL,
                mode TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS approval_requests (
                request_id TEXT PRIMARY KEY,
                requester_id TEXT NOT NULL,
                target_student_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                requested_value TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
                approver_id TEXT,
                decision_note TEXT,
                created_at TEXT NOT NULL,
                decided_at TEXT,
                executed_at TEXT,
                result TEXT,
                FOREIGN KEY (requester_id) REFERENCES students(student_id),
                FOREIGN KEY (target_student_id) REFERENCES students(student_id)
            );
            CREATE TABLE IF NOT EXISTS audit_logs (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id TEXT NOT NULL,
                actor_role TEXT NOT NULL,
                action TEXT NOT NULL,
                target_student_id TEXT,
                requested_data TEXT NOT NULL,
                authorization_decision TEXT NOT NULL,
                approval_status TEXT NOT NULL,
                result TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        columns = _table_columns(conn, "students")
        if "scholarship_status" not in columns:
            conn.execute("ALTER TABLE students ADD COLUMN scholarship_status TEXT NOT NULL DEFAULT 'Not available'")
        _seed_students(conn)
        _seed_auth_users(conn)


def list_students() -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT student_id, display_name, programme FROM students ORDER BY student_id").fetchall()
    return [dict(row) for row in rows]


def get_user(username: str) -> dict[str, Any] | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT username, role, student_id, display_name, active, created_at FROM auth_users WHERE username = ? COLLATE NOCASE", (username.strip(),)).fetchone()
    return dict(row) if row else None


def get_user_by_student_id(student_id: str) -> dict[str, Any] | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT username, role, student_id, display_name, active, created_at FROM auth_users WHERE student_id = ?", (student_id,)).fetchone()
    return dict(row) if row else None


def create_or_update_auth_user(
    *, username: str, password: str, role: str,
    student_id: str | None = None, display_name: str | None = None,
) -> dict[str, Any]:
    """Create/update a local demo login using a salted password hash.

    Passwords are supplied interactively by the local operator and are never
    included in source files, sample data, or the public repository.
    """
    username = (username or "").strip()[:80]
    if not username:
        raise ValueError("Username is required.")
    if len(password or "") < 12:
        raise ValueError("Use a local demo password with at least 12 characters.")
    if role not in {"student", "approver"}:
        raise ValueError("Role must be 'student' or 'approver'.")
    init_db()
    if role == "student":
        if not student_id:
            raise ValueError("Student accounts require a student_id.")
        student = get_fee_status(student_id)
        if not student:
            raise ValueError("The selected fictional student record does not exist.")
        display_name = display_name or student.get("display_name") or username
    else:
        student_id = None
        display_name = display_name or "Local Demo Approver"
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO auth_users
               (username, password_hash, role, student_id, display_name, active, created_at)
               VALUES (?, ?, ?, ?, ?, 1, ?)
               ON CONFLICT(username) DO UPDATE SET
                 password_hash=excluded.password_hash,
                 role=excluded.role,
                 student_id=excluded.student_id,
                 display_name=excluded.display_name,
                 active=1""",
            (username, hash_password(password), role, student_id, display_name, utc_now()),
        )
    result = get_user(username)
    if not result:
        raise RuntimeError("The local demo account could not be provisioned.")
    return result


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM auth_users WHERE username = ? COLLATE NOCASE AND active = 1", (username.strip(),)).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        record_audit_event(
            actor_id="anonymous", actor_role="unknown", action="login_attempt", target_student_id=None,
            requested_data={"username": username.strip()[:80]}, authorization_decision="denied",
            approval_status="not_required", result="invalid_credentials",
        )
        return None
    user = {key: row[key] for key in ("username", "role", "student_id", "display_name", "active", "created_at")}
    record_audit_event(
        actor_id=user["username"], actor_role=user["role"], action="login_attempt",
        target_student_id=user["student_id"], requested_data={"username": user["username"]},
        authorization_decision="allowed", approval_status="not_required", result="success",
    )
    return user


def get_fee_status(student_id: str) -> dict[str, Any] | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT student_id, display_name, programme, total_fee, paid_fee, pending_fee, fee_status, due_date FROM students WHERE student_id = ?",
            (student_id,),
        ).fetchone()
    return dict(row) if row else None


def get_scholarship_status(student_id: str) -> dict[str, Any] | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT student_id, programme, scholarship_status FROM students WHERE student_id = ?", (student_id,)).fetchone()
    return dict(row) if row else None


def create_ticket(student_id: str, category: str, description: str) -> dict[str, Any]:
    init_db()
    ticket_id = f"AIDTM-{uuid.uuid4().hex[:8].upper()}"
    created_at = utc_now()
    clean_description = redact_sensitive_text(description)[:450]
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM students WHERE student_id = ?", (student_id,)).fetchone()
        if not exists:
            raise ValueError("The signed-in demo student does not exist.")
        conn.execute(
            "INSERT INTO support_tickets (ticket_id, student_id, category, description, status, created_at) VALUES (?, ?, ?, ?, 'Open', ?)",
            (ticket_id, student_id, category, clean_description, created_at),
        )
    return {"ticket_id": ticket_id, "student_id": student_id, "category": category, "description": clean_description, "status": "Open", "created_at": created_at, "notice": "Saved only in this local demo database; not sent to AIDTM."}


ALLOWED_MEMORY_KEYS = {"programme": "Preferred programme", "preferred_language": "Preferred language", "answer_style": "Answer style"}


def _looks_sensitive(value: str) -> bool:
    import re
    text = value.strip()
    patterns = [
        r"\b\d{10}\b", r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
        r"\b(password|passcode|otp|cvv|card number|bank account|medical|diagnosis|aadhaar|pan number|verification code|security code)\b",
    ]
    return contains_sensitive_input(text) or any(re.search(pattern, text, flags=re.I) for pattern in patterns)


def save_memory(student_id: str, memory_key: str, memory_value: str) -> dict[str, Any]:
    init_db()
    if memory_key not in ALLOWED_MEMORY_KEYS:
        return {"saved": False, "message": "Only programme, preferred_language, or answer_style may be remembered."}
    value = " ".join((memory_value or "").split()).strip()
    if not value or len(value) > 120:
        return {"saved": False, "message": "Preference must contain 1–120 characters."}
    if _looks_sensitive(value):
        record_audit_event(actor_id=student_id, actor_role="student", action="save_memory", target_student_id=student_id, requested_data={"key": memory_key, "value": "[REDACTED]"}, authorization_decision="denied", approval_status="not_required", result="sensitive_value_rejected")
        return {"saved": False, "message": "This value looks sensitive and was not saved."}
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM students WHERE student_id = ?", (student_id,)).fetchone()
        if not exists:
            return {"saved": False, "message": "Unknown signed-in demo student."}
        now = utc_now()
        conn.execute(
            """INSERT INTO memories (student_id, memory_key, memory_value, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?) ON CONFLICT(student_id, memory_key)
               DO UPDATE SET memory_value=excluded.memory_value, updated_at=excluded.updated_at""",
            (student_id, memory_key, value, now, now),
        )
    return {"saved": True, "key": memory_key, "value": value, "message": "Preference saved."}


def list_memories(student_id: str) -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT memory_id, memory_key, memory_value, created_at, updated_at FROM memories WHERE student_id = ? ORDER BY updated_at DESC", (student_id,)).fetchall()
    return [dict(row) for row in rows]


def delete_memory(student_id: str, memory_id: int) -> bool:
    init_db()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM memories WHERE student_id = ? AND memory_id = ?", (student_id, int(memory_id)))
        return cur.rowcount > 0


def get_relevant_memories(student_id: str, query: str) -> list[dict[str, Any]]:
    memories = list_memories(student_id)
    words = {w.lower() for w in __import__("re").findall(r"[a-zA-Z]{3,}", query)}
    key_terms = {"programme": {"programme", "program", "course", "study", "studying", "interested"}, "preferred_language": {"language", "speak", "respond", "reply"}, "answer_style": {"style", "short", "detailed", "format", "explain"}}
    relevant = [item for item in memories if words & key_terms.get(item["memory_key"], set())]
    if not relevant and words & {"remember", "remembered", "previously", "earlier", "told", "recall", "memory"}:
        relevant = memories[:3]
    return relevant[:3]


def record_trace(*, student_id: str, question: str, answer: str, tools_used: list[str], tool_success: bool, latency_ms: float, input_tokens: int | None, output_tokens: int | None, retrieved_evidence: list[str], mode: str) -> str:
    init_db()
    trace_id = f"TRACE-{uuid.uuid4().hex[:10].upper()}"
    # Avoid storing disclosed passwords/OTPs in the trace table.
    safe_question = redact_sensitive_text(question)[:4000]
    safe_answer = redact_sensitive_text(answer)[:8000]
    safe_evidence = "\n".join(redact_sensitive_text(str(x)) for x in retrieved_evidence)[:10000]
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO traces (trace_id, student_id, question, answer, tools_used, tool_success, latency_ms,
               input_tokens, output_tokens, retrieved_evidence, mode, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (trace_id, student_id, safe_question, safe_answer, ", ".join(tools_used) if tools_used else "none", int(tool_success), float(latency_ms), input_tokens, output_tokens, safe_evidence, mode, utc_now()),
        )
    return trace_id


def get_traces(limit: int = 250, student_id: str | None = None) -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        if student_id is None:
            rows = conn.execute("SELECT * FROM traces ORDER BY created_at DESC LIMIT ?", (int(limit),)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM traces WHERE student_id = ? ORDER BY created_at DESC LIMIT ?", (student_id, int(limit))).fetchall()
    return [dict(row) for row in rows]


def get_tickets(limit: int = 100, student_id: str | None = None) -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        if student_id is None:
            rows = conn.execute("SELECT ticket_id, student_id, category, description, status, created_at FROM support_tickets ORDER BY created_at DESC LIMIT ?", (int(limit),)).fetchall()
        else:
            rows = conn.execute("SELECT ticket_id, student_id, category, description, status, created_at FROM support_tickets WHERE student_id = ? ORDER BY created_at DESC LIMIT ?", (student_id, int(limit))).fetchall()
    return [dict(row) for row in rows]


def record_audit_event(*, actor_id: str, actor_role: str, action: str, target_student_id: str | None, requested_data: Any, authorization_decision: str, approval_status: str, result: str) -> int:
    init_db()
    requested = json.dumps(safe_json_value(requested_data), ensure_ascii=False, sort_keys=True)
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO audit_logs (actor_id, actor_role, action, target_student_id, requested_data, authorization_decision, approval_status, result, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (actor_id[:120], actor_role[:40], action[:120], target_student_id, requested[:4000], authorization_decision[:40], approval_status[:40], redact_sensitive_text(result)[:1000], utc_now()),
        )
        return int(cur.lastrowid)


def get_audit_logs(limit: int = 500, actor_id: str | None = None) -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        if actor_id is None:
            rows = conn.execute("SELECT * FROM audit_logs ORDER BY audit_id DESC LIMIT ?", (int(limit),)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM audit_logs WHERE actor_id = ? OR target_student_id = ? OR actor_id IN (SELECT username FROM auth_users WHERE student_id = ?) ORDER BY audit_id DESC LIMIT ?", (actor_id, actor_id, actor_id, int(limit))).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        try:
            item["requested_data"] = json.loads(item["requested_data"])
        except Exception:
            pass
        out.append(item)
    return out


def create_approval_request(*, requester_id: str, action_type: str, requested_value: str, reason: str) -> dict[str, Any]:
    init_db()
    if action_type != "programme_change":
        return {"created": False, "message": "Unsupported sensitive action."}
    normalized_value = "PGDM in Big Data Analytics" if "big data analytics" in requested_value.lower() else "PGDM in AI & Data Science" if ("ai" in requested_value.lower() and "data science" in requested_value.lower()) else ""
    if normalized_value not in ALLOWED_PROGRAMMES:
        return {"created": False, "message": "Choose either PGDM in Big Data Analytics or PGDM in AI & Data Science."}
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM students WHERE student_id = ?", (requester_id,)).fetchone()
        if not exists:
            return {"created": False, "message": "Unknown signed-in student."}
        # Avoid duplicate pending requests for the same field/value.
        duplicate = conn.execute("SELECT request_id FROM approval_requests WHERE requester_id = ? AND action_type = ? AND status = 'pending' LIMIT 1", (requester_id, action_type)).fetchone()
        if duplicate:
            return {"created": False, "request_id": duplicate["request_id"], "message": "You already have a pending programme-change request."}
        request_id = f"APR-{uuid.uuid4().hex[:8].upper()}"
        now = utc_now()
        conn.execute(
            "INSERT INTO approval_requests (request_id, requester_id, target_student_id, action_type, requested_value, reason, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)",
            (request_id, requester_id, requester_id, action_type, normalized_value, redact_sensitive_text(reason)[:500], now),
        )
    owner = get_user_by_student_id(requester_id) or {"username": requester_id}
    record_audit_event(actor_id=owner["username"], actor_role="student", action="request_programme_change", target_student_id=requester_id, requested_data={"requested_programme": normalized_value, "reason": reason}, authorization_decision="allowed", approval_status="pending", result=f"request_created:{request_id};record_unchanged")
    return {"created": True, "request_id": request_id, "status": "pending", "requested_programme": normalized_value, "message": "The request is awaiting human approval. The student record has not been changed."}


def list_approval_requests(status: str | None = None, requester_id: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    init_db()
    where = []
    args: list[Any] = []
    if status:
        where.append("status = ?")
        args.append(status)
    if requester_id:
        where.append("requester_id = ?")
        args.append(requester_id)
    query = "SELECT * FROM approval_requests"
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY created_at DESC LIMIT ?"
    args.append(int(limit))
    with get_connection() as conn:
        rows = conn.execute(query, args).fetchall()
    return [dict(row) for row in rows]


def decide_approval(*, request_id: str, approver_username: str, approve: bool, note: str = "") -> dict[str, Any]:
    init_db()
    actor = get_user(approver_username)
    if not actor or actor.get("role") != "approver" or not actor.get("active"):
        record_audit_event(actor_id=approver_username or "anonymous", actor_role=(actor or {}).get("role", "unknown"), action="decide_approval", target_student_id=None, requested_data={"request_id": request_id, "approve": approve}, authorization_decision="denied", approval_status="not_allowed", result="approver_role_required")
        return {"ok": False, "message": "Only an authenticated approver may decide requests."}
    status = "approved" if approve else "rejected"
    result_text = ""
    request_row: dict[str, Any] | None = None
    now = utc_now()
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM approval_requests WHERE request_id = ?", (request_id,)).fetchone()
        if not row:
            result_text = "request_not_found"
        elif row["status"] != "pending":
            result_text = "request_already_decided"
        else:
            request_row = dict(row)
            if approve and row["action_type"] == "programme_change":
                programme = row["requested_value"]
                if programme not in ALLOWED_PROGRAMMES:
                    result_text = "unsupported_programme_value;not_executed"
                else:
                    conn.execute("UPDATE students SET programme = ? WHERE student_id = ?", (programme, row["target_student_id"]))
                    conn.execute("UPDATE approval_requests SET status='approved', approver_id=?, decision_note=?, decided_at=?, executed_at=?, result=? WHERE request_id=? AND status='pending'", (actor["username"], redact_sensitive_text(note)[:500], now, now, "programme_updated", request_id))
                    result_text = "programme_updated"
            elif approve:
                result_text = "unsupported_action;not_executed"
            else:
                conn.execute("UPDATE approval_requests SET status='rejected', approver_id=?, decision_note=?, decided_at=?, executed_at=NULL, result=? WHERE request_id=? AND status='pending'", (actor["username"], redact_sensitive_text(note)[:500], now, "rejected_no_change", request_id))
                result_text = "rejected_no_change"
            if approve and result_text == "unsupported_action;not_executed":
                conn.execute("UPDATE approval_requests SET status='rejected', approver_id=?, decision_note=?, decided_at=?, result=? WHERE request_id=? AND status='pending'", (actor["username"], redact_sensitive_text(note)[:500], now, result_text, request_id))
    if not request_row:
        record_audit_event(actor_id=actor["username"], actor_role="approver", action="decide_approval", target_student_id=None, requested_data={"request_id": request_id, "approve": approve}, authorization_decision="allowed", approval_status="not_found_or_already_decided", result=result_text)
        return {"ok": False, "message": "Request was not found or has already been decided."}
    decision_status = status if result_text in {"programme_updated", "rejected_no_change"} else "rejected"
    record_audit_event(actor_id=actor["username"], actor_role="approver", action="decide_approval", target_student_id=request_row["target_student_id"], requested_data={"request_id": request_id, "action_type": request_row["action_type"], "requested_value": request_row["requested_value"], "decision_note": note}, authorization_decision="allowed", approval_status=decision_status, result=result_text)
    return {"ok": result_text in {"programme_updated", "rejected_no_change"}, "status": decision_status, "message": result_text, "target_student_id": request_row["target_student_id"]}


def clear_traces() -> None:
    init_db()
    with get_connection() as conn:
        conn.execute("DELETE FROM traces")
