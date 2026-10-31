"""Application tools with server-side ownership checks and audit logging."""
from __future__ import annotations

from typing import Any

import database
from retrieval.policy_search import search_aidtm_website, search_policy
from security import redact_sensitive_text


def _record_actor(student_id: str) -> tuple[str, bool]:
    user = database.get_user_by_student_id(student_id)
    if not user or user.get("role") != "student" or not user.get("active"):
        return "unknown", False
    return user["username"], True


def _deny(actor_id: str, action: str, target: str, requested: dict[str, Any]) -> dict[str, Any]:
    actor, valid = _record_actor(actor_id)
    database.record_audit_event(
        actor_id=actor if valid else (actor_id or "unknown"), actor_role="student" if valid else "unknown",
        action=action, target_student_id=target, requested_data=requested,
        authorization_decision="denied", approval_status="not_required", result="cross_student_access_blocked",
    )
    return {"error": "Access denied: students can access only their own private records.", "found": False, "message": "Cross-student data access is blocked by the application authorization layer."}


def _authorized_target(actor_student_id: str, requested_student_id: str | None, action: str) -> tuple[bool, dict[str, Any] | None]:
    _, valid_actor = _record_actor(actor_student_id)
    if not valid_actor:
        return False, {"error": "An authenticated student identity is required."}
    target = (requested_student_id or actor_student_id).strip()
    if target != actor_student_id:
        return False, _deny(actor_student_id, action, target, {"requested_student_id": target})
    return True, None


def check_fee_status(student_id: str, requested_student_id: str | None = None) -> dict[str, Any]:
    allowed, denied = _authorized_target(student_id, requested_student_id, "read_fee_status")
    if not allowed:
        return denied or {"error": "Access denied"}
    row = database.get_fee_status(student_id)
    username, _ = _record_actor(student_id)
    database.record_audit_event(actor_id=username, actor_role="student", action="read_fee_status", target_student_id=student_id, requested_data={"field_group": "fee_status"}, authorization_decision="allowed", approval_status="not_required", result="success" if row else "record_not_found")
    if not row:
        return {"found": False, "message": "No fee record was found for the signed-in demo student."}
    return {"found": True, **row, "total_fee_inr": row["total_fee"], "paid_fee_inr": row["paid_fee"], "pending_fee_inr": row["pending_fee"], "note": "Fictional demonstration data, not an AIDTM finance-system record."}


def check_scholarship_status(student_id: str, requested_student_id: str | None = None) -> dict[str, Any]:
    allowed, denied = _authorized_target(student_id, requested_student_id, "read_scholarship_status")
    if not allowed:
        return denied or {"error": "Access denied"}
    row = database.get_scholarship_status(student_id)
    username, _ = _record_actor(student_id)
    database.record_audit_event(actor_id=username, actor_role="student", action="read_scholarship_status", target_student_id=student_id, requested_data={"field_group": "scholarship_status"}, authorization_decision="allowed", approval_status="not_required", result="success" if row else "record_not_found")
    return {"found": bool(row), **(row or {}), "note": "Fictional demo status only. This is not an official scholarship decision."}


def create_support_ticket(student_id: str, category: str, description: str) -> dict[str, Any]:
    allowed, denied = _authorized_target(student_id, student_id, "create_support_ticket")
    if not allowed:
        return denied or {"error": "Access denied"}
    try:
        result = database.create_ticket(student_id, category, redact_sensitive_text(description))
        username, _ = _record_actor(student_id)
        database.record_audit_event(actor_id=username, actor_role="student", action="create_support_ticket", target_student_id=student_id, requested_data={"category": category, "description": description}, authorization_decision="allowed", approval_status="not_required", result=f"created_local_demo_ticket:{result['ticket_id']}")
        return {"created": True, **result}
    except Exception as exc:
        return {"created": False, "error": f"{type(exc).__name__}: {exc}"}


def request_programme_change(student_id: str, requested_programme: str, reason: str) -> dict[str, Any]:
    allowed, denied = _authorized_target(student_id, student_id, "request_programme_change")
    if not allowed:
        return denied or {"error": "Access denied"}
    return database.create_approval_request(requester_id=student_id, action_type="programme_change", requested_value=requested_programme, reason=reason)


def get_admission_information(programme: str) -> dict[str, Any]:
    result = search_aidtm_website(f"admission eligibility programme {programme}", top_k=3)
    return {**result, "programme": programme}


def search_aidtm_website_tool(query: str) -> dict[str, Any]:
    return search_aidtm_website(query, top_k=3)


def search_college_policy_tool(query: str) -> dict[str, Any]:
    return search_policy(query, top_k=3)


def get_saved_preferences(student_id: str) -> dict[str, Any]:
    allowed, denied = _authorized_target(student_id, student_id, "read_saved_preferences")
    if not allowed:
        return denied or {"error": "Access denied"}
    username, _ = _record_actor(student_id)
    prefs = database.list_memories(student_id)
    database.record_audit_event(actor_id=username, actor_role="student", action="read_saved_preferences", target_student_id=student_id, requested_data={"count": len(prefs)}, authorization_decision="allowed", approval_status="not_required", result="success")
    return {"preferences": [{"key": x["memory_key"], "value": x["memory_value"]} for x in prefs]}


def save_preference(student_id: str, key: str, value: str, consent_enabled: bool = False) -> dict[str, Any]:
    allowed, denied = _authorized_target(student_id, student_id, "save_memory")
    if not allowed:
        return denied or {"saved": False, "error": "Access denied"}
    if not consent_enabled:
        database.record_audit_event(actor_id=student_id, actor_role="student", action="save_memory", target_student_id=student_id, requested_data={"key": key}, authorization_decision="denied", approval_status="not_required", result="consent_not_enabled")
        return {"saved": False, "message": "Memory consent is disabled. Enable consent and explicitly ask to remember a supported non-sensitive preference."}
    result = database.save_memory(student_id, key, value)
    username, _ = _record_actor(student_id)
    database.record_audit_event(actor_id=username, actor_role="student", action="save_memory", target_student_id=student_id, requested_data={"key": key, "value": value if result.get("saved") else "[not saved]"}, authorization_decision="allowed" if result.get("saved") else "denied", approval_status="not_required", result="saved" if result.get("saved") else result.get("message", "rejected"))
    return result
