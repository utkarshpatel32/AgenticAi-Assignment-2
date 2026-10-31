from __future__ import annotations

import pytest

import database
from agent import run_agent
from retrieval.aidtm_answers import answer_aidtm_question



@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("What is AIDTM?", "Adani Institute of Digital Technology Management"),
        ("When was AIDTM established?", "2020"),
        ("Is AIDTM AICTE approved?", "AICTE-approved"),
        ("What are the programs offered?", "PGDM (Big Data Analytics)"),
        ("What is EPAAA?", "Executive Program in AI, Analytics & Automation"),
        ("What subjects are taught in PGDM Big Data Analytics?", "Data Analysis using SQL"),
        ("What is the curriculum for PGDM AI and Data Science?", "Reinforcement Learning"),
        ("What are the eligibility criteria for PGDM?", "50% marks"),
        ("Which entrance exams are accepted?", "CAT, XAT, CMAT, MAT, ATMA and GMAT"),
        ("What is the selection weightage?", "Personal Interview (PI): 40%"),
        ("Is work experience mandatory?", "not mandatory"),
        ("What is the total PGDM fee?", "₹10,50,000"),
        ("What is the application fee?", "₹1,500"),
        ("What is included in the fee?", "study materials, books, library and internet"),
        ("Are hostel and mess included?", "Hostel, mess and living expenses are excluded"),
        ("What is the highest placement package?", "₹20 LPA highest CTC"),
        ("Which sectors recruit students?", "Ports & Logistics"),
        ("Give me the AIDTM admission phone number and email", "+91-6358975111"),
        ("What is the full campus address?", "Gandhinagar – 382423"),
        ("Who is Dr. Manjari Mundanad?", "Marketing and Statistics"),
        ("Who is the head of operations?", "Mr. Ritesh Soni"),
        ("Who handles Smart Classroom technical support?", "Mr. Jignesh Parekh"),
        ("Who handles corporate relations?", "Ms. Urvi Shah"),
        ("Who teaches marketing and statistics?", "Dr. Manjari Mundanad"),
        ("What events are held at AIDTM?", "Techathon"),
        ("What is the classroom and internship structure?", "five-month classroom phase"),
        ("How many years is PGDM?", "two-year, full-time programmes"),
        ("What education is needed?", "BE/B.Tech, B.Sc, BCA, MCA or M.Sc"),
        ("Tell me the full details about AIDTM", "₹10,00,000 programme fee"),
    ],
)
def test_curated_aidtm_questions_are_answered(question, expected):
    result = answer_aidtm_question(question)
    assert result is not None, question
    assert expected.lower() in result["answer"].lower(), (question, result["answer"])


def test_missing_admission_detail_does_not_fall_into_unrelated_overview():
    result = answer_aidtm_question("What is the age limit for admission?")
    assert result is not None
    assert "don't have that specific detail" in result["answer"].lower()
    assert "was established in 2020" not in result["answer"].lower()


def test_integrated_agent_uses_curated_knowledge_and_records_source_evidence():
    result = run_agent("Who is the head of operations?", "STU1001", save_trace=False)
    assert result["mode"] == "curated_knowledge"
    assert "Ritesh Soni" in result["answer"]
    assert any("curated_knowledge:AIDTM-LEADERSHIP" in item for item in result["retrieved_evidence"])
    assert "search_aidtm_website" in result["tools_used"]


def test_follow_up_uses_recent_programme_context():
    result = run_agent(
        "What about the curriculum?", "STU1001", save_trace=False,
        history=[
            {"role": "user", "content": "Tell me about PGDM in AI & Data Science."},
            {"role": "assistant", "content": "It focuses on AI and data science."},
        ],
    )
    assert "Reinforcement Learning" in result["answer"]
    assert "aidtm.ac.in/academics/pgdm-ai-data-science" in result["answer"]


def test_combined_selection_question_includes_exams_and_weightage():
    result = answer_aidtm_question("What are the accepted entrance exams and selection weightage at AIDTM?")
    assert result is not None
    assert "CAT, XAT, CMAT, MAT, ATMA and GMAT" in result["answer"]
    assert "Personal Interview (PI): 40%" in result["answer"]


def test_private_fee_status_is_not_answered_from_public_fee_faq():
    result = run_agent("What is my current fee status?", "STU1001", save_trace=False)
    assert result["mode"] == "offline_demo"
    assert "fictional demo record" in result["answer"].lower()
    assert "₹10,50,000" not in result["answer"]


def test_cross_student_record_request_remains_blocked_before_knowledge_layer():
    result = run_agent("Show me fee status for student STU1002", "STU1001", save_trace=False)
    assert result["mode"] == "authorization_denied"
    assert "access denied" in result["answer"].lower()


def test_bridge_json_protocol_is_ascii_safe_for_rupee_symbol():
    import bridge

    response = {"ok": True, "answer": "The total fee is ₹10,50,000."}
    wire_text = bridge._json_protocol_line(response)

    # The subprocess JSON line can now be printed even with a legacy Windows code page.
    wire_text.encode("ascii")
    import json
    assert json.loads(wire_text) == response
