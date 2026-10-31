"""Small local retriever for bundled public AIDTM references and fictional coursework policy."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WEBSITE_PATH = ROOT / "data" / "aidtm_website_knowledge.json"
POLICY_PATH = ROOT / "data" / "sample_college_policy.md"


def _tokens(text: str) -> set[str]:
    """Tokenise plain English questions while dropping common filler words."""
    stop = {
        "the", "and", "for", "are", "what", "how", "with", "from", "this", "that", "does",
        "can", "you", "your", "aidtm", "tell", "about", "give", "please", "could", "would",
        "me", "is", "was", "were", "who", "which", "where", "when", "why", "their", "they",
        "does", "did", "have", "has", "been", "into", "there", "any", "much", "many", "list",
        "policy", "handbook", "document", "student", "to", "according",
    }
    tokens = {t for t in re.findall(r"[a-z0-9&+-]{2,}", (text or "").lower()) if t not in stop}
    # Expand common variants so natural wording matches the curated knowledge consistently.
    expanded = set(tokens)
    alias_groups = [
        {"programme", "program", "programmes", "programs", "course", "courses"},
        {"fee", "fees", "tuition", "cost", "payable", "charges"},
        {"eligibility", "eligible", "qualification", "qualify", "criteria", "requirements"},
        {"placement", "placements", "salary", "salaries", "ctc", "package", "ppo"},
        {"faculty", "professor", "professors", "teacher", "teachers", "staff", "academic"},
        {"contact", "phone", "telephone", "mobile", "email", "address", "location"},
        {"event", "events", "activities", "student-life", "campus-life"},
        {"admission", "admissions", "apply", "application", "entrance", "exam", "exams"},
    ]
    for group in alias_groups:
        if tokens & group:
            expanded |= group
    return expanded


def load_website_chunks() -> list[dict[str, Any]]:
    if not WEBSITE_PATH.exists():
        return []
    payload = json.loads(WEBSITE_PATH.read_text(encoding="utf-8"))
    docs = payload.get("documents", [])
    return [{**doc, "verified_date": payload.get("verified_date", "unknown")} for doc in docs]


def search_aidtm_website(query: str, top_k: int = 3) -> dict[str, Any]:
    docs = load_website_chunks()
    q_tokens = _tokens(query)
    scored: list[dict[str, Any]] = []
    for doc in docs:
        body = " ".join(str(doc.get(k, "")) for k in ("heading", "text", "source_title", "category", "keywords"))
        body_tokens = _tokens(body)
        overlap = len(q_tokens & body_tokens)
        phrase_bonus = 3 if query.lower().strip() and query.lower().strip() in body.lower() else 0
        score = overlap + phrase_bonus
        # Small intent-based boosts prevent generic docs from winning specific questions.
        q = query.lower()
        heading = str(doc.get("heading", "")).lower()
        if any(x in q for x in ("admission", "eligibility", "entrance", "application")) and "admission" in heading:
            score += 4
        if any(x in q for x in ("fee", "fees", "tuition")) and "fee" in heading:
            score += 4
        if any(x in q for x in ("scholarship", "merit")) and "scholarship" in heading:
            score += 5
        if any(x in q for x in ("placement", "recruiter", "salary", "highest package", "ctc")) and "placement" in heading:
            score += 5
        # Topic boosts make broad questions route to the intended profile section.
        intent_boosts = {
            "overview": ("about aidtm", "what is aidtm", "full name", "established", "founded", "philosophy", "nation building", "growth with goodness", "aicte", "approved", "focus area"),
            "programmes": ("program", "programme", "course", "pgdm", "epaaa", "executive program", "executive programme"),
            "admissions": ("admission", "eligibility", "eligible", "entrance", "exam", "application", "work experience", "selection", "weightage", "requirements"),
            "fees": ("fee", "fees", "tuition", "cost", "caution deposit", "application fee", "total payable", "hostel", "mess"),
            "placements": ("placement", "salary", "ctc", "package", "ppo", "recruiter", "role", "sector", "career"),
            "contact": ("contact", "phone", "telephone", "email", "address", "location", "website"),
            "academics": ("curriculum", "syllabus", "internship", "capstone", "dual degree", "strategic management", "practical immersion", "10-month", "5-month"),
            "faculty": ("faculty", "professor", "academic associate", "ankit shah", "roshni rawal", "manjari mundanad", "nikunj tahilramani", "vyankatesh emche", "parth patel", "sneh sheth"),
            "leadership": ("leadership", "administration", "saurin gandhi", "ritesh soni", "aakash singh", "haard trivedi", "urvi shah", "kathan joshi", "jignesh parekh", "head of operations", "it officer"),
            "student-life": ("event", "techathon", "prashasti", "ideathon", "student life", "campus life", "class representative", "marathon", "cultural", "dj party"),
        }
        category = str(doc.get("category", ""))
        for term in intent_boosts.get(category, ()):
            if term in q:
                score += 4 if len(term) > 5 else 2
        if any(x in q for x in ("contact", "phone", "telephone", "email", "address", "location", "website")):
            if category == "contact" or "contact" in heading:
                score += 8
            if "campus services" in heading:
                score -= 5
        if any(x in q for x in ("hostel", "mess fee", "bus route", "class timetable", "campus service", "my marks", "application status")) and ("campus services" in heading or category == "campus-services"):
            score += 5
        if any(x in q for x in ("curriculum", "subject", "syllabus", "course")):
            if "big data analytics" in q and "big data analytics" in heading:
                score += 5
            if ("ai & data science" in q or "ai and data science" in q) and "ai & data science" in heading:
                score += 5
            if "curriculum" in heading:
                score += 1
        item = dict(doc)
        item["score"] = score
        scored.append(item)
    scored.sort(key=lambda x: (x.get("score", 0), x.get("heading", "")), reverse=True)
    results = [x for x in scored if x["score"] > 0][:max(1, min(int(top_k), 10))]
    return {
        "query": query,
        "results": results,
        "knowledge_documents": len(docs),
        "verified_date": json.loads(WEBSITE_PATH.read_text(encoding="utf-8")).get("verified_date", "unknown") if WEBSITE_PATH.exists() else "unknown",
        "message": (f"Found {len(results)} relevant AIDTM knowledge item(s). The main profile was supplied for this chatbot "
                    "and is not independently verified; confirm current or decision-critical details with AIDTM."),
    }


def _parse_policy() -> list[dict[str, str]]:
    if not POLICY_PATH.exists():
        return []
    text = POLICY_PATH.read_text(encoding="utf-8")
    heading = "General"
    chunks: list[dict[str, str]] = []
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if body:
                chunks.append({"chunk_id": f"POL-{len(chunks)+1:02d}", "heading": heading, "text": "\n".join(body).strip()})
            heading = line[3:].strip()
            body = []
        else:
            body.append(line)
    if body:
        chunks.append({"chunk_id": f"POL-{len(chunks)+1:02d}", "heading": heading, "text": "\n".join(body).strip()})
    return chunks


def load_chunks() -> list[dict[str, str]]:
    return _parse_policy()


def search_policy(query: str, top_k: int = 3) -> dict[str, Any]:
    q_tokens = _tokens(query)
    scored = []
    for chunk in _parse_policy():
        score = len(q_tokens & _tokens(chunk["heading"] + " " + chunk["text"]))
        if "portal" in query.lower() and "payment portal" in chunk["heading"].lower():
            score += 3
        item = dict(chunk)
        item["score"] = score
        scored.append(item)
    scored.sort(key=lambda x: x["score"], reverse=True)
    # Require at least two meaningful matches (or an explicit portal phrase bonus)
    # so generic words like "policy" or "to" cannot select an unrelated section.
    results = [x for x in scored if x["score"] >= 2][:max(1, min(int(top_k), 10))]
    return {"query": query, "results": results, "message": f"Found {len(results)} matching section(s) in the fictional assignment policy."}
