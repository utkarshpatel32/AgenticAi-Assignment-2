from __future__ import annotations

import json

import pytest

import database
from agent import run_agent
from retrieval.policy_search import search_policy
from tools import student_tools



def test_fee_and_scholarship_tools_are_selected():
    fee = run_agent("What is my current fee status?", "STU1001", save_trace=False)
    scholarship = run_agent("What is my scholarship status?", "STU1001", save_trace=False)
    assert "check_fee_status" in fee["tools_used"]
    assert "fictional demo record" in fee["answer"].lower()
    assert "check_scholarship_status" in scholarship["tools_used"]
    assert "fictional demo record" in scholarship["answer"].lower()


def test_policy_retrieval_selects_relevant_chunk_and_says_when_missing():
    result = run_agent(
        "The payment portal failed. Can I pay on the next working day?",
        "STU1001", save_trace=False,
    )
    assert "search_college_policy" in result["tools_used"]
    assert any(item.startswith("POL-") for item in result["retrieved_evidence"])
    assert "does **not** confirm" in result["answer"]

    missing = run_agent(
        "According to the student policy, what is the late-registration penalty percentage?",
        "STU1001", save_trace=False,
    )
    assert "does not provide enough information" in missing["answer"].lower()
    assert "search_college_policy" in missing["tools_used"]
    assert search_policy("late-registration penalty percentage")["results"] == []


def test_memory_persists_between_requests_without_chat_history():
    saved = run_agent(
        "Remember that my preferred programme is PGDM in Big Data Analytics",
        "STU1001", consent_enabled=True, history=[], save_trace=False,
    )
    recalled = run_agent(
        "What do you remember about my preferred programme?",
        "STU1001", consent_enabled=True, history=[], save_trace=False,
    )
    assert "save_preference" in saved["tools_used"]
    assert "get_saved_preferences" in recalled["tools_used"]
    assert "PGDM in Big Data Analytics" in recalled["answer"]


def test_support_ticket_tool_runs_only_after_explicit_request():
    result = run_agent(
        "Please create a support ticket because I cannot access the student portal.",
        "STU1001", save_trace=False,
    )
    assert "create_support_ticket" in result["tools_used"]
    assert "created a local demo support ticket" in result["answer"].lower()
    assert database.get_tickets(limit=10, student_id="STU1001")


def test_sensitive_statement_is_not_persisted():
    result = run_agent(
        "Remember my OTP is 123456", "STU1001",
        consent_enabled=True, save_trace=True,
    )
    assert "did not store" in result["answer"].lower()
    assert not database.list_memories("STU1001")
    persisted = json.dumps(database.get_traces(limit=20, student_id="STU1001"), ensure_ascii=False)
    assert "123456" not in persisted


def test_tool_error_is_reported_without_fabricating_record(monkeypatch):
    def broken_tool(_student_id, _requested_student_id=None):
        raise RuntimeError("test failure")

    monkeypatch.setattr(student_tools, "check_fee_status", broken_tool)
    result = run_agent("What is my current fee status?", "STU1001", save_trace=False)
    assert result["tool_success"] is False
    assert "tool reported an error" in result["answer"].lower()


def test_assignment1_evaluation_has_one_trace_for_each_scenario():
    from evaluation.runner import run_evaluation

    report = run_evaluation()
    summary = report["summary"]
    assert summary["assignment1_passed"] == 2
    assert summary["assignment1_total"] == 2
    assert summary["assignment2_passed"] == 9
    assert summary["assignment2_total"] == 9
    assert all(row["passed"] for row in report["rows"])
