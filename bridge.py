"""JSON bridge between the Node.js web UI and the existing Python agent/safety layer.

The browser never supplies a student ID as authority. Each operation resolves the
account again from the authenticated username that the Node server passes from its
server-side session. Run this module only via server.js for the coursework demo.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _safe_user(username: str) -> dict[str, Any] | None:
    import database
    user = database.get_user(username)
    if not user or not user.get("active"):
        return None
    return user


def dispatch(request: dict[str, Any]) -> dict[str, Any]:
    import database
    from security import redact_sensitive_text, safe_json_value

    database.init_db()
    op = str(request.get("op", ""))

    if op == "login":
        username = str(request.get("username", "")).strip()[:80]
        password = str(request.get("password", ""))[:500]
        user = database.authenticate(username, password) if username and password else None
        if not user:
            return {"ok": False, "error": "Sign-in failed. Check the demo username and password."}
        return {"ok": True, "user": user}

    username = str(request.get("username", "")).strip()[:80]
    user = _safe_user(username) if username else None
    if op == "me":
        if not user:
            return {"ok": False, "error": "Session expired. Please sign in again."}
        return {"ok": True, "user": user}

    if not user:
        return {"ok": False, "error": "Authentication required."}

    role = user.get("role")
    student_id = user.get("student_id")

    if op == "chat":
        if role != "student" or not student_id:
            return {"ok": False, "error": "Student chat is available to student accounts only."}
        from agent import run_agent
        question = str(request.get("question", ""))[:4000].strip()
        if not question:
            return {"ok": False, "error": "Please enter a question."}
        history = request.get("history", [])
        if not isinstance(history, list):
            history = []
        cleaned_history = []
        for item in history[-8:]:
            if isinstance(item, dict) and item.get("role") in {"user", "assistant"}:
                cleaned_history.append({"role": item["role"], "content": redact_sensitive_text(str(item.get("content", "")))[:1500]})
        result = run_agent(
            question=question,
            student_id=student_id,
            consent_enabled=bool(request.get("consent", False)),
            history=cleaned_history,
        )
        result["display_question"] = redact_sensitive_text(question)
        return {"ok": True, "result": result}

    if op == "dashboard":
        if role != "student" or not student_id:
            return {"ok": False, "error": "Student records are available to student accounts only."}
        database.record_audit_event(
            actor_id=user["username"], actor_role="student", action="view_own_private_records",
            target_student_id=student_id, requested_data={"field_group": "fee_and_scholarship_status"},
            authorization_decision="allowed", approval_status="not_required", result="own_record_dashboard_accessed",
        )
        fee = database.get_fee_status(student_id)
        scholarship = database.get_scholarship_status(student_id)
        return {"ok": True, "user": user, "fee": fee, "scholarship": scholarship,
                "memories": database.list_memories(student_id),
                "tickets": database.get_tickets(limit=100, student_id=student_id),
                "requests": database.list_approval_requests(requester_id=student_id, limit=100)}

    if op == "approvals":
        if role == "approver":
            requests = database.list_approval_requests(limit=200)
        elif role == "student" and student_id:
            requests = database.list_approval_requests(requester_id=student_id, limit=100)
        else:
            return {"ok": False, "error": "Not authorized."}
        return {"ok": True, "requests": requests}

    if op == "decide_approval":
        if role != "approver":
            database.record_audit_event(actor_id=user["username"], actor_role=role or "unknown", action="decide_approval", target_student_id=None,
                                        requested_data={"request_id": str(request.get("request_id", "")), "approve": bool(request.get("approve"))},
                                        authorization_decision="denied", approval_status="not_allowed", result="approver_role_required")
            return {"ok": False, "error": "Only an authenticated approver may decide requests."}
        result = database.decide_approval(
            request_id=str(request.get("request_id", ""))[:80],
            approver_username=user["username"],
            approve=bool(request.get("approve", False)),
            note=redact_sensitive_text(str(request.get("note", "")))[:500],
        )
        return {"ok": bool(result.get("ok")), "result": result}

    if op == "audit":
        logs = database.get_audit_logs(limit=500, actor_id=None if role == "approver" else user["username"])
        return {"ok": True, "logs": logs}

    if op == "traces":
        traces = database.get_traces(limit=300, student_id=student_id if role == "student" else None)
        return {"ok": True, "traces": traces}

    if op == "knowledge_search":
        from retrieval.policy_search import load_website_chunks, search_aidtm_website
        query = str(request.get("query", "")).strip()[:300]
        result = search_aidtm_website(query, top_k=6) if query else None
        return {"ok": True, "documents": load_website_chunks(), "result": result}

    if op == "policy_search":
        from retrieval.policy_search import load_chunks, search_policy
        query = str(request.get("query", "")).strip()[:300]
        result = search_policy(query, top_k=3) if query else None
        return {"ok": True, "chunks": load_chunks(), "result": result}

    if op == "evaluation":
        from evaluation.runner import run_evaluation
        return {"ok": True, "report": run_evaluation()}

    if op == "save_memory":
        if role != "student" or not student_id:
            return {"ok": False, "error": "Only students may save their own preferences."}
        from tools.student_tools import save_preference
        key = str(request.get("key", ""))[:80]
        value = str(request.get("value", ""))[:300]
        consent = request.get("consent") is True
        result = save_preference(student_id, key, value, consent_enabled=consent)
        return {"ok": bool(result.get("saved")), "result": result}

    if op == "delete_memory":
        if role != "student" or not student_id:
            return {"ok": False, "error": "Only students may manage their own preferences."}
        memory_id = request.get("memory_id")
        try:
            memory_id = int(memory_id)
        except (TypeError, ValueError):
            return {"ok": False, "error": "Invalid preference ID."}
        removed = database.delete_memory(student_id, memory_id)
        database.record_audit_event(actor_id=user["username"], actor_role="student", action="delete_memory", target_student_id=student_id,
                                    requested_data={"memory_id": memory_id}, authorization_decision="allowed" if removed else "denied",
                                    approval_status="not_required", result="deleted" if removed else "not_found")
        return {"ok": removed, "message": "Preference deleted." if removed else "Preference not found."}

    return {"ok": False, "error": "Unknown operation."}


def _json_protocol_line(payload: dict[str, Any]) -> str:
    """Serialize the bridge response to ASCII-only JSON.

    ASCII escaping is important on Windows, where the console code page may not
    support characters such as ₹. Node.js JSON.parse restores Unicode characters.
    """
    return json.dumps(payload, ensure_ascii=True, default=str)


def _write_protocol(payload: dict[str, Any]) -> None:
    """Write JSON as ASCII bytes, bypassing the Windows console encoder entirely."""
    wire = (_json_protocol_line(payload) + "\n").encode("ascii", errors="strict")
    binary_stdout = getattr(sys.stdout, "buffer", None)
    if binary_stdout is not None:
        binary_stdout.write(wire)
        binary_stdout.flush()
    else:
        # Test-friendly fallback; wire is ASCII so legacy encodings can handle it.
        sys.stdout.write(wire.decode("ascii"))
        sys.stdout.flush()


def _write_debug_error(exc: BaseException) -> None:
    """Write a local UTF-8 diagnostic with traceback locations, not request contents."""
    try:
        log_path = Path(ROOT) / "data" / "bridge_errors.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        frames = traceback.extract_tb(exc.__traceback__)
        frame_text = "\n".join(
            f"  File {frame.filename}, line {frame.lineno}, in {frame.name}"
            for frame in frames
        )
        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"{type(exc).__name__}: {str(exc)}\n{frame_text}\n\n")
    except Exception:
        # Error logging must never interfere with the one-line JSON protocol.
        pass


def main() -> None:
    # Set stream encoding before importing the agent or any optional dependencies.
    # The Node server additionally launches Python in UTF-8 mode; ASCII-byte output
    # below remains safe even if Windows ignores one of these settings.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except (AttributeError, OSError, ValueError):
            pass

    try:
        raw = sys.stdin.read(200_000)
        req = json.loads(raw or "{}")
        if not isinstance(req, dict):
            req = {}
        # Redirect accidental prints from libraries so stdout contains only JSON.
        captured_out = io.StringIO()
        captured_err = io.StringIO()
        with contextlib.redirect_stdout(captured_out), contextlib.redirect_stderr(captured_err):
            response = dispatch(req)
        _write_protocol(response)
    except BaseException as exc:
        _write_debug_error(exc)
        # The response protocol contains only ASCII bytes, even when error text has ₹.
        _write_protocol({"ok": False, "error": f"Backend error: {type(exc).__name__}: {exc}"})
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()
