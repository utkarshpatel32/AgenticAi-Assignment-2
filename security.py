"""Security helpers shared by the UI, agent and tool implementations."""
from __future__ import annotations

import re
from typing import Any

PRIVATE_DATA_TERMS = (
    "fee status", "fee balance", "scholarship status", "scholarship award", "student record",
    "private record", "personal details", "attendance", "marks", "grades", "payment status",
    "paid fee", "pending fee", "student profile", "contact number", "email address",
)
SECRET_PATTERNS = [
    # A value explicitly assigned to a credential or authentication secret.
    re.compile(r"\b(?:my\s+)?(?:password|passcode|otp|one[- ]time password|verification code|security code|cvv|pin)\s*(?:is|=|:|equals|was)\s*[^\s,;.!?]{3,}", re.I),
    # Explicitly asking the agent to store a secret, including without a colon.
    re.compile(r"\b(?:remember|save|store|memorize)\b.{0,50}\b(?:password|passcode|otp|one[- ]time password|verification code|security code|cvv|pin)\b(?:\s*(?:is|=|:|of)?\s*[^\s,;.!?]{4,})?", re.I),
    re.compile(r"\b(?:otp|passcode|verification code|security code)\b.{0,30}\b\d{4,8}\b", re.I),
]


def contains_sensitive_input(text: str) -> bool:
    """Detect a likely credential/OTP disclosure, not ordinary conceptual questions."""
    value = text or ""
    return any(pattern.search(value) for pattern in SECRET_PATTERNS)


def redact_sensitive_text(text: str) -> str:
    """Mask credential values before writing questions/results into persistent traces."""
    value = text or ""
    value = re.sub(
        r"(\b(?:my\s+)?(?:password|passcode|otp|one[- ]time password|verification code|security code|cvv|pin)\s*(?:is|=|:|equals|was)\s*)[^\s,;.!?]{3,}",
        r"\1[REDACTED]", value, flags=re.I,
    )
    value = re.sub(
        r"(\b(?:remember|save|store|memorize)\b.{0,50}\b(?:password|passcode|otp|one[- ]time password|verification code|security code|cvv|pin)\b)(?:\s*(?:is|=|:|of)?\s*[^\s,;.!?]{4,})?",
        r"\1 [REDACTED]", value, flags=re.I,
    )
    value = re.sub(r"(\b(?:otp|passcode|verification code|security code)\b.{0,30}\b)\d{4,8}\b", r"\1[REDACTED]", value, flags=re.I)
    return value[:4000]


def has_private_data_intent(question: str) -> bool:
    q = (question or "").lower()
    return any(term in q for term in PRIVATE_DATA_TERMS) or bool(re.search(r"\b(?:show|check|fetch|read|tell me)\b.{0,40}\b(?:fee|scholarship|record|profile|marks|attendance|balance)\b", q))


def identify_other_student_target(question: str, actor_student_id: str, students: list[dict[str, Any]]) -> str | None:
    """Return a known foreign student ID when a private-data question names them."""
    q = (question or "").lower()
    if not has_private_data_intent(q):
        return None
    # Explicit general attempt to access a different student's private information.
    if re.search(r"\b(?:another|other|someone else's|somebody else's|a different)\s+(?:student|person|user)\b", q):
        return "OTHER_STUDENT"
    for item in students:
        sid = str(item.get("student_id", ""))
        name = str(item.get("display_name", ""))
        if not sid or sid == actor_student_id:
            continue
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(sid.lower())}(?![A-Za-z0-9])", q):
            return sid
        if name and len(name) > 2 and name.lower() in q:
            return sid
    # Catch explicitly stated unknown student IDs, without disclosing whether they exist.
    explicit_id = re.search(r"\b(?:student\s*(?:id|number|no\.?))\s*[:#-]?\s*([a-z]{2,}\d{3,}|\d{6,})\b", q, re.I)
    if explicit_id:
        candidate = explicit_id.group(1).upper()
        if candidate != actor_student_id.upper():
            return candidate
    return None


def safe_json_value(value: Any) -> Any:
    """Convert common tool inputs to a JSON-safe, redacted value for audit logs."""
    if isinstance(value, dict):
        return {str(k): safe_json_value(v) for k, v in value.items() if str(k).lower() not in {"password", "otp", "passcode", "token", "secret", "api_key"}}
    if isinstance(value, list):
        return [safe_json_value(v) for v in value[:30]]
    if isinstance(value, str):
        return redact_sensitive_text(value)[:1000]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:1000]
