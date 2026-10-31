from __future__ import annotations

import secrets

import pytest

import database


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    """Give each test an isolated DB and ephemeral local test-account passwords."""
    monkeypatch.setenv("AIDTM_DB_PATH", str(tmp_path / "test_aidtm.sqlite3"))
    monkeypatch.setenv("GROQ_API_KEY", "")
    database.init_db()

    test_student_password = secrets.token_urlsafe(24)
    test_approver_password = secrets.token_urlsafe(24)
    for row in database.list_students():
        database.create_or_update_auth_user(
            username=str(row["student_id"]).lower(),
            password=test_student_password,
            role="student",
            student_id=row["student_id"],
            display_name=row["display_name"],
        )
    database.create_or_update_auth_user(
        username="approver",
        password=test_approver_password,
        role="approver",
        display_name="Test Approver",
    )
    monkeypatch.setenv("AIDTM_TEST_STUDENT_PASSWORD", test_student_password)
    monkeypatch.setenv("AIDTM_TEST_APPROVER_PASSWORD", test_approver_password)
    yield
