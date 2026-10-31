"""High-recall, deterministic answers from the AIDTM profile supplied for this project.

These answers are deliberately preferred for clear institutional questions, so the
chatbot does not depend on an LLM guessing the right topic from weak keyword overlap.
The supplied profile is not independently verified; answers link to AIDTM's site for
confirmation of time-sensitive or decision-critical details.
"""
from __future__ import annotations

import re
from typing import Any

BASE = "https://www.aidtm.ac.in/"
ADMISSION = "https://www.aidtm.ac.in/admission"
PLACEMENT = "https://www.aidtm.ac.in/placement"
CONTACT = "https://www.aidtm.ac.in/contactus"

PROVENANCE = (
    "\n\n*Note: This answer uses the AIDTM information supplied for this chatbot. "
    "Admissions, fees, staff and placement details may change; confirm them on the "
    f"[official AIDTM website]({BASE}) or [contact page]({CONTACT}).*"
)


def _has(q: str, *terms: str) -> bool:
    """Match whole words/phrases, avoiding false matches like `mission` in `admission`."""
    for term in terms:
        term = term.strip().lower()
        if not term:
            continue
        # Permit ordinary plurals while keeping the start/end of the phrase bounded.
        escaped = re.escape(term)
        if re.search(r"(?<![a-z0-9])" + escaped + r"(?:s|es)?(?![a-z0-9])", q):
            return True
    return False


def _matches(q: str, pattern: str) -> bool:
    return bool(re.search(pattern, q, flags=re.IGNORECASE))


def answer_aidtm_question(question: str) -> dict[str, Any] | None:
    """Return a deterministic answer for a recognisable AIDTM question, or None.

    Personal student records and actions are intentionally excluded; those must keep
    going through the authenticated tool and approval paths in agent.py.
    """
    q = " ".join((question or "").lower().replace("’", "'").split())
    if not q:
        return None

    # Never treat personal/demo records or state-changing requests as public FAQ.
    if _has(q, "my fee status", "my fee balance", "pending fee", "fees paid", "payment status",
            "my scholarship status", "my scholarship", "my marks", "my application status",
            "my ticket", "my current fee", "my payment"):
        return None
    if _matches(q, r"\b(create|raise|open|log|submit|make)\b.*\b(ticket|support request|complaint)\b"):
        return None
    if _matches(q, r"\b(remember|save|store|recall|what do you remember|what did i tell)\b"):
        return None
    if _matches(q, r"\b(change|switch|transfer|update)\s+(my\s+)?(programme|program|course)\b") and not _matches(q, r"\b(how|process|procedure|steps|can i)\b"):
        return None
    if _has(q, "portal failed", "payment portal", "portal failure", "next working day", "deadline extension"):
        return None

    chunk = "AIDTM-OVERVIEW"
    source = BASE
    answer = ""

    # Contact is prioritised so a contact question doesn't get mixed with campus services.
    if _has(q, "phone", "telephone", "mobile number", "contact", "email", "e-mail", "address", "where is aidtm", "location", "website", "url"):
        chunk, source = "AIDTM-CONTACT", CONTACT
        if _has(q, "phone", "telephone", "mobile number"):
            answer = ("AIDTM contact numbers provided for this chatbot are **+91-6358975111**, "
                      "**+91-6358975222**, and **+91-6358975333**. The admissions email is "
                      "**admissions@aidtm.ac.in**."
                      "\n\n**Campus address:** Plot No. 225, Opp. Maharaj Hotel Lane, Jamiyatpura Road, "
                      "Sarkhej-Gandhinagar Highway, Gandhinagar – 382423, Gujarat.")
        elif _has(q, "email", "e-mail"):
            answer = ("The admissions email provided is **admissions@aidtm.ac.in**. "
                      "The contact numbers are +91-6358975111, +91-6358975222 and +91-6358975333.")
        elif _has(q, "address", "where is", "location"):
            answer = ("AIDTM is located at **Plot No. 225, Opp. Maharaj Hotel Lane, Jamiyatpura Road, "
                      "Sarkhej-Gandhinagar Highway, Gandhinagar – 382423, Gujarat, India**.")
        elif _has(q, "website", "url"):
            answer = f"AIDTM's website is [{BASE}]({BASE}). For admissions, see the [admission page]({ADMISSION})."
        else:
            answer = ("**AIDTM contact details**\n\n- **Phone:** +91-6358975111 / +91-6358975222 / +91-6358975333\n"
                      "- **Admissions email:** admissions@aidtm.ac.in\n"
                      "- **Address:** Plot No. 225, Opp. Maharaj Hotel Lane, Jamiyatpura Road, "
                      "Sarkhej-Gandhinagar Highway, Gandhinagar – 382423, Gujarat\n"
                      f"- **Website:** [{BASE}]({BASE})")

    elif _has(q, "faculty", "professor", "associate professor", "assistant professor", "academic associate", "marketing", "statistics", "soft skills", "computer vision", "geospatial", "remote sensing") or _matches(q, r"\b(dr\.? ankit shah|dr\.? roshni rawal|dr\.? manjari mundanad|dr\.? nikunj tahilramani|vyankatesh emche|parth patel|sneh sheth)\b"):
        chunk = "AIDTM-FACULTY"
        people = {
            "dr. ankit shah": "**Dr. Ankit Shah** — Professor specialising in Big Data Analytics.",
            "ankit shah": "**Dr. Ankit Shah** — Professor specialising in Big Data Analytics.",
            "dr. roshni rawal": "**Dr. Roshni Rawal** — Associate Professor specialising in Soft Skills & Communication.",
            "roshni rawal": "**Dr. Roshni Rawal** — Associate Professor specialising in Soft Skills & Communication.",
            "dr. manjari mundanad": "**Dr. Manjari Mundanad** — Assistant Professor specialising in Marketing and Statistics.",
            "manjari mundanad": "**Dr. Manjari Mundanad** — Assistant Professor specialising in Marketing and Statistics.",
            "dr. nikunj tahilramani": "**Dr. Nikunj Tahilramani** — Assistant Professor.",
            "nikunj tahilramani": "**Dr. Nikunj Tahilramani** — Assistant Professor.",
            "vyankatesh emche": "**Mr. Vyankatesh Emche** — Assistant Professor.",
            "parth patel": "**Mr. Parth Patel** — Academic Associate specialising in Data Science, AI/ML, computer vision, geospatial analytics and remote sensing; supports curriculum enhancement, lab sessions and student projects.",
            "sneh sheth": "**Mr. Sneh Sheth** — Academic Associate.",
        }
        matched = [v for k, v in people.items() if k in q]
        if matched:
            answer = matched[0]
        elif _has(q, "marketing", "statistics"):
            answer = "**Dr. Manjari Mundanad** is listed as Assistant Professor specialising in Marketing and Statistics."
        elif _has(q, "soft skills", "communication"):
            answer = "**Dr. Roshni Rawal** is listed as Associate Professor specialising in Soft Skills & Communication."
        elif _has(q, "computer vision", "geospatial", "remote sensing", "curriculum enhancement", "lab sessions"):
            answer = "**Mr. Parth Patel**, Academic Associate, is listed as specialising in Data Science, AI/ML, computer vision, geospatial analytics and remote sensing; he supports curriculum enhancement, lab sessions and student projects."
        elif _has(q, "big data analytics"):
            answer = "**Dr. Ankit Shah** is listed as Professor specialising in Big Data Analytics."
        else:
            answer = ("The faculty and academic staff listed in the supplied AIDTM profile are:\n\n"
                      "- **Dr. Ankit Shah** — Professor, Big Data Analytics\n"
                      "- **Dr. Roshni Rawal** — Associate Professor, Soft Skills & Communication\n"
                      "- **Dr. Manjari Mundanad** — Assistant Professor, Marketing and Statistics\n"
                      "- **Dr. Nikunj Tahilramani** — Assistant Professor\n"
                      "- **Mr. Vyankatesh Emche** — Assistant Professor\n"
                      "- **Mr. Parth Patel** — Academic Associate, Data Science, AI/ML, computer vision, geospatial analytics and remote sensing\n"
                      "- **Mr. Sneh Sheth** — Academic Associate")

    elif _has(q, "leadership", "administration", "head of operations", "operations head", "operations", "admission manager", "program manager", "executive education manager", "manager executive education", "it officer", "system security", "smart classroom", "social media manager", "graphic designer", "associate vice president", "corporate relations", "saurin gandhi", "ritesh soni", "aakash singh", "haard trivedi", "urvi shah", "kathan joshi", "jignesh parekh"):
        chunk = "AIDTM-LEADERSHIP"
        leaders = {
            "saurin gandhi": "**Mr. Saurin Gandhi** — Associate Vice President, Adani Group; a key contributor in building institutions across the Adani portfolio.",
            "ritesh soni": "**Mr. Ritesh Soni** — Head of Operations, with over 16 years of experience in EPC projects, institutional administration and industry collaborations.",
            "aakash singh": "**Mr. Aakash Singh** — Manager, Executive Education.",
            "haard trivedi": "**Mr. Haard Trivedi** — Admission Manager.",
            "urvi shah": "**Ms. Urvi Shah** — Program Manager, handling institutional administration and corporate relations.",
            "kathan joshi": "**Mr. Kathan Joshi** — Graphic Designer and Social Media Manager.",
            "jignesh parekh": "**Mr. Jignesh Parekh** — IT Officer responsible for system security and Smart Classroom technical support.",
        }
        matched = [v for k, v in leaders.items() if k in q]
        if matched:
            answer = matched[0]
        elif _has(q, "head of operations", "operations head", "operations"):
            answer = "**Mr. Ritesh Soni** is listed as Head of Operations, with over 16 years of experience across EPC projects, institutional administration and industry collaborations."
        elif _has(q, "admission manager", "admissions manager"):
            answer = "**Mr. Haard Trivedi** is listed as Admission Manager."
        elif _has(q, "corporate relations", "institutional administration", "program manager", "programme manager"):
            answer = "**Ms. Urvi Shah** is listed as Program Manager, handling institutional administration and corporate relations."
        elif _has(q, "system security", "smart classroom", "it officer"):
            answer = "**Mr. Jignesh Parekh** is listed as IT Officer, responsible for system security and Smart Classroom technical support."
        elif _has(q, "executive education manager", "manager executive education"):
            answer = "**Mr. Aakash Singh** is listed as Manager, Executive Education."
        elif _has(q, "graphic designer", "social media"):
            answer = "**Mr. Kathan Joshi** is listed as Graphic Designer and Social Media Manager."
        else:
            answer = ("The leadership and administration roles listed in the supplied profile are:\n\n"
                      "- **Mr. Saurin Gandhi** — Associate Vice President, Adani Group\n"
                      "- **Mr. Ritesh Soni** — Head of Operations; 16+ years in EPC, institutional administration and industry collaborations\n"
                      "- **Mr. Aakash Singh** — Manager, Executive Education\n"
                      "- **Mr. Haard Trivedi** — Admission Manager\n"
                      "- **Ms. Urvi Shah** — Program Manager, institutional administration and corporate relations\n"
                      "- **Mr. Kathan Joshi** — Graphic Designer and Social Media Manager\n"
                      "- **Mr. Jignesh Parekh** — IT Officer, system security and Smart Classroom support")

    elif _has(q, "event", "techathon", "prashasti", "ideathon", "class representative", "batch representative", "student life", "campus life", "extracurricular", "marathon", "dj party", "cultural", "sports", "startup pitch"):
        chunk = "AIDTM-EVENTS"
        answer = ("The supplied profile describes several student activities:\n\n"
                  "- **Techathon:** annual technical event, noted for January\n"
                  "- **Prashasti:** annual cultural event, noted for January/February\n"
                  "- **Ideathons:** students pitch startup and innovation ideas to judging panels\n"
                  "- **Student leadership:** nomination and voting for Batch Class Representatives\n"
                  "- **Community and social activities:** participation in events such as the Ahmedabad Marathon, cultural gatherings and DJ parties.\n\n"
                  "Event names and dates should be checked with the institute for the current year.")

    elif _has(q, "placement", "salary", "salary package", "average package", "highest package", "ctc", "package", "ppo", "pre-placement", "recruiter", "recruit", "company", "companies", "role", "career", "sector", "industry", "career outcome", "earn"):
        chunk, source = "AIDTM-PLACEMENTS", PLACEMENT
        if _has(q, "role", "job", "career") and not _has(q, "placement", "salary", "ctc", "package", "ppo", "recruiter", "sector"):
            answer = ("Roles listed in the supplied profile include **Data Analyst, Data Scientist, Business Analyst, "
                      "Management Trainee (Digital Transformation), AI Strategies Manager, and Project Management Coordinator**. "
                      "Career outcomes depend on the student, market and hiring organisation.")
        elif _has(q, "sector", "industry"):
            answer = ("The recruiting sectors listed are **IT & Technology, Consulting, Ports & Logistics, Manufacturing, "
                      "Healthcare, Financial Services, and FMCG**.")
        elif _has(q, "recruiter", "company", "companies"):
            answer = ("The supplied profile describes recruiting sectors including IT & Technology, Consulting, Ports & Logistics, "
                      "Manufacturing, Healthcare, Financial Services and FMCG. For a current company-wise recruiter list, check "
                      f"the [official placement page]({PLACEMENT}).")
        else:
            answer = ("The placement figures in the supplied profile are **100% placement track record**, **₹20 LPA highest CTC**, "
                      "**₹8 LPA average CTC**, and **90% pre-placement offers (PPOs)** through the five-month summer internship/capstone. "
                      "These are supplied figures, not a guarantee of an individual outcome or a future batch result. Check the "
                      f"[official placement page]({PLACEMENT}) for current reporting.")

    elif _has(q, "scholarship", "merit award", "tuition waiver"):
        chunk, source = "AIDTM-SCHOLARSHIP", ADMISSION
        answer = ("The AIDTM profile you supplied for this chatbot does not include scholarship thresholds or award amounts, "
                  "so I don't want to guess. Please check the current scholarship information with the [official admission page](%s) "
                  "or contact admissions@aidtm.ac.in. This is different from checking a student's personal scholarship status, "
                  "which uses the signed-in fictional demo record." % ADMISSION)

    elif _has(q, "application fee", "form fee", "registration application"):
        chunk, source = "AIDTM-FEES", ADMISSION
        answer = "The application fee listed in the supplied profile is **₹1,500**, and it is **non-refundable**. Confirm the current amount on the [official admission page](%s)." % ADMISSION
    elif _has(q, "fee", "fees", "tuition", "cost", "caution deposit", "payable", "hostel", "mess", "living expense", "included", "inclusion", "exclusion"):
        chunk, source = "AIDTM-FEES", ADMISSION
        if _has(q, "hostel", "mess", "living expense", "excluded"):
            answer = ("**Hostel, mess and living expenses are excluded** from the PGDM fee in the supplied profile. "
                      "The same profile lists ₹10,00,000 as the two-year programme fee and a refundable ₹50,000 caution deposit. "
                      f"Confirm current charges with AIDTM via the [admission page]({ADMISSION}).")
        elif _has(q, "included", "inclusion", "what does the fee cover"):
            answer = ("The supplied profile says the PGDM fee includes **study materials, books, library and internet charges**. "
                      "Hostel, mess and living expenses are excluded. See the [official admission page]({ADMISSION}) to confirm the current structure.")
        elif _has(q, "caution deposit", "refundable deposit"):
            answer = ("The supplied profile lists a **₹50,000 refundable caution deposit**. Along with the ₹10,00,000 two-year programme fee, "
                      "the total payable to the institute is listed as ₹10,50,000. Confirm current details on the [admission page](%s)." % ADMISSION)
        elif _has(q, "total payable", "total amount", "total fee", "how much", "fee structure", "tuition", "cost", "fees", "fee"):
            answer = ("The supplied PGDM fee structure is:\n\n- **Two-year programme fee:** ₹10,00,000\n"
                      "- **Refundable caution deposit:** ₹50,000\n- **Total payable to the institute:** ₹10,50,000\n"
                      "- **Application fee:** ₹1,500 (non-refundable)\n- **Included:** study materials, books, library and internet charges\n"
                      "- **Excluded:** hostel, mess and living expenses\n\n"
                      f"Confirm current amounts and due dates on the [official admission page]({ADMISSION}).")
        else:
            answer = ("The supplied profile lists ₹10,00,000 for the two-year PGDM, plus a refundable ₹50,000 caution deposit, making "
                      "₹10,50,000 payable to the institute. Hostel, mess and living expenses are excluded. "
                      f"Confirm details on the [official admission page]({ADMISSION}).")

    elif _has(q, "weightage", "selection criteria", "selection process", "selection score", "personal interview", "pi round", "interview marks"):
        chunk, source = "AIDTM-ADMISSIONS", ADMISSION
        answer = ("The selection weightage in the supplied profile is:\n\n- **Personal Interview (PI): 40%**\n"
                  "- **Entrance exam score: 20%**\n- **Academic performance: 20%**\n- **Work experience: 10%**\n"
                  "- **Extracurriculars: 10%**")
        if _has(q, "entrance exam", "entrance exams", "exam", "cat", "xat", "cmat", "mat", "atma", "gmat"):
            answer += "\n\nAccepted entrance exams listed in the supplied profile are **CAT, XAT, CMAT, MAT, ATMA and GMAT**."
        answer += f"\n\nCheck the [official admission page]({ADMISSION}) for the current selection policy."
    elif _has(q, "exam", "entrance exam", "entrance exams", "entrance test", "which exam", "accepted exam", "exams accepted", "cat", "xat", "cmat", "mat", "atma", "gmat") and _has(q, "exam", "entrance", "admission", "eligib", "accept", "score", "test", "cat", "xat", "cmat", "mat", "atma", "gmat"):
        chunk, source = "AIDTM-ADMISSIONS", ADMISSION
        answer = ("The entrance exams listed in the supplied profile are **CAT, XAT, CMAT, MAT, ATMA and GMAT**. "
                  f"Verify the exams accepted for the target batch on the [official admission page]({ADMISSION}).")
    elif _has(q, "eligibility", "eligible", "qualification", "qualify", "education", "degree", "b.sc", "bsc", "bca", "mca", "m.sc", "msc", "b.tech", "btech", "minimum marks", "minimum percentage", "50%", "45%", "reserved category", "work experience", "final year"):
        chunk, source = "AIDTM-ADMISSIONS", ADMISSION
        if _has(q, "work experience", "work exp", "experience required"):
            answer = ("Work experience is **not mandatory** according to the supplied profile, although relevant experience carries weight in selection (10%).")
        elif _has(q, "final year"):
            answer = ("According to the supplied profile, **final-year students may apply**. Applicants should verify the current qualification and document rules on the [official admission page](%s)." % ADMISSION)
        else:
            answer = ("The eligibility criteria in the supplied profile are:\n\n- A recognised bachelor's degree such as **BE/B.Tech, B.Sc, BCA, MCA or M.Sc**\n"
                      "- Minimum **50% marks** (or **45% for reserved categories**)\n- **Final-year students can apply**\n"
                      "- Entrance exams listed: **CAT, XAT, CMAT, MAT, ATMA and GMAT**\n- Work experience is **not mandatory**, but relevant experience carries weight.\n\n"
                      f"Verify current batch-specific requirements on the [official admission page]({ADMISSION}).")

    elif _has(q, "apply", "application process", "admission process", "admission policy", "admission criteria", "how to get admission", "how can i join", "admission steps"):
        chunk, source = "AIDTM-ADMISSIONS", ADMISSION
        answer = ("Based on the supplied profile, applicants should confirm they meet the degree/marks criteria, have an accepted entrance-exam score (CAT, XAT, CMAT, MAT, ATMA or GMAT), and prepare for the Personal Interview. "
                  "Selection weightage is PI 40%, entrance test 20%, academics 20%, work experience 10% and extracurriculars 10%. "
                  f"Start with the [official AIDTM admission page]({ADMISSION}) and confirm the current process.")

    elif _has(q, "executive program", "executive programme", "epaaa", "working professional", "executive education"):
        chunk = "AIDTM-PROGRAMS"
        if _has(q, "duration", "how long", "how many years", "years long"):
            answer = ("The supplied profile describes EPAAA as an executive programme for working professionals, but it does not specify its duration. Please confirm the current schedule with AIDTM via the [official website](%s)." % BASE)
        else:
            answer = ("AIDTM offers **EPAAA — Executive Program in AI, Analytics & Automation** for working professionals who want to solve real-world problems using advanced data methodologies, AI, analytics and automation. "
                      f"For current details, check the [official AIDTM website]({BASE}).")

    elif _has(q, "dual degree", "diploma in strategic management", "strategic management diploma", "additional diploma"):
        chunk = "AIDTM-ACADEMICS"
        answer = ("The supplied profile describes a dual-degree advantage: the PGDM programmes are integrated with a **Diploma in Strategic Management** (for example, PGDM Big Data Analytics plus the Diploma in Strategic Management). "
                  f"Confirm the award wording and current structure with AIDTM via the [official website]({BASE}).")

    elif _has(q, "internship", "capstone", "classroom phase", "classroom duration", "program duration", "programme duration", "course duration", "program structure", "programme structure", "course structure", "structure", "how long", "how many years", "years long", "2-year", "two-year", "5-month", "five-month", "10-month", "ten-month", "experiential learning"):
        chunk = "AIDTM-ACADEMICS"
        answer = ("The supplied profile describes the PGDMs as **two-year, full-time programmes** with a **five-month classroom phase** and a **five-month internship/capstone project**. It also describes an extensive **10-month continuous practical immersion** across internship and capstone work alongside classroom modules. Confirm the exact timetable for your batch on the [official AIDTM website](%s)." % BASE)

    elif _has(q, "curriculum", "syllabus", "subjects", "what do they teach", "what will i learn", "topics taught", "course content", "study in pgdm", "course content", "academic structure"):
        chunk = "AIDTM-PROGRAMS"
        bda = _has(q, "big data analytics", "bda", "data analytics pgdm")
        aids = _has(q, "ai & data science", "ai and data science", "ai/ ds", "pgdm ai", "artificial intelligence and data science", "ai ds")
        if bda and not aids:
            chunk, source = "AIDTM-BDA-SNAPSHOT", "https://www.aidtm.ac.in/academics/pgdm-big-data-analytics"
            answer = ("**PGDM (Big Data Analytics)** focuses on **Data Sciences, Statistical Learning, Data Visualisation, SQL, Python and data-driven decision-making**. The prior indexed subject snapshot also lists: **Data Analysis using SQL, Enterprise Data Visualisation, HR Analytics, Fundamentals of Finance, Introduction to Big Data Analytics, Statistical Learning, Introduction to Machine Learning, Python for Data Science, Deep Learning, Statistics for Data Analytics using Excel, Image Processing using Python, Cloud Computing, Networking/Cyber Security/Fraud Detection analytics, Data Exploration & Visualisation using Python, and NoSQL Database** (along with communication, management and marketing subjects). This detailed list comes from the project's previous page snapshot; check the current [programme page](%s) for your batch." % source)
        elif aids and not bda:
            chunk, source = "AIDTM-AIDS-SNAPSHOT", "https://www.aidtm.ac.in/academics/pgdm-ai-data-science"
            answer = ("**PGDM (AI & Data Science)** focuses on **Machine Learning, IoT, Cloud Computing, Generative AI, RPA, NLP and Data Engineering**. The prior indexed subject snapshot also lists: **Mathematical Foundations for AI & DS, Reinforcement Learning, Data Science and Big Data Technologies, Natural Language Processing, Foundation AI & ML, Computer Vision, Statistical Learning, IoT, Exploratory Data Analysis, Data Analysis Tools, Machine Learning, Business Management, Deep Learning, Cloud Computing Essentials, Gen-AI & Large Language Models, Prompt Engineering, Data Engineering, Speech Recognition, and Data Intelligence and Analytics** (plus Professional Communicative English). This detailed list comes from the project's previous page snapshot; check the current [programme page](%s) for your batch." % source)
        else:
            answer = ("AIDTM offers two PGDM programmes:\n\n- **PGDM (Big Data Analytics):** Data Sciences, Statistical Learning, Data Visualisation, SQL, Python and data-driven decision-making.\n"
                      "- **PGDM (AI & Data Science):** Machine Learning, IoT, Cloud Computing, Generative AI, RPA, NLP and Data Engineering.\n\n"
                      f"Both are described as two-year, full-time programmes with practical internship/capstone work. See the [official website]({BASE}) for the current subject list.")

    elif _has(q, "program", "programme", "course", "pgdm", "what does aidtm offer", "courses offered", "bda", "ai ds"):
        chunk = "AIDTM-PROGRAMS"
        answer = ("AIDTM's programmes listed in the supplied profile are:\n\n- **PGDM (Big Data Analytics):** Data Science, Statistical Learning, Data Visualisation, SQL, Python and data-driven decision-making.\n"
                  "- **PGDM (AI & Data Science):** Machine Learning, IoT, Cloud Computing, Generative AI, RPA, NLP and Data Engineering.\n"
                  "- **EPAAA:** Executive Program in AI, Analytics & Automation for working professionals.\n\n"
                  f"The PGDM programmes are two-year, full-time programmes. See the [official AIDTM website]({BASE}) for current details.")

    elif _has(q, "established", "founded", "when did", "establishment", "started in"):
        chunk = "AIDTM-OVERVIEW"
        answer = "The information supplied for this chatbot says that the Adani Institute of Digital Technology Management (AIDTM) was established in **2020**."
    elif _has(q, "aicte", "approved", "approval"):
        chunk = "AIDTM-OVERVIEW"
        answer = "The information supplied for this chatbot describes AIDTM as an **AICTE-approved private institute**. For formal/current confirmation, check the [official AIDTM website](%s) or contact the institute." % BASE
    elif _has(q, "complete information", "all about aidtm", "full details about aidtm", "tell me everything about aidtm"):
        chunk = "AIDTM-OVERVIEW"
        answer = """**AIDTM at a glance**

- **Full name:** Adani Institute of Digital Technology Management
- **Established:** 2020
- **Location:** Gandhinagar, Gujarat
- **Focus:** Big Data, AI and Data Science
- **Programmes:** PGDM (Big Data Analytics), PGDM (AI & Data Science), and EPAAA for working professionals
- **PGDM duration:** two years, with a classroom phase and internship/capstone immersion
- **Fee listed in the supplied profile:** ₹10,00,000 programme fee plus refundable ₹50,000 caution deposit; ₹1,500 non-refundable application fee
- **Selection:** PI 40%, entrance exam 20%, academics 20%, work experience 10%, extracurriculars 10%
- **Placement highlights supplied:** ₹8 LPA average CTC, ₹20 LPA highest CTC, 90% PPOs, 100% placement track record
- **Contact:** admissions@aidtm.ac.in; +91-6358975111 / +91-6358975222 / +91-6358975333

These are the details supplied for this chatbot; verify current official information before applying or making payments."""
    elif _has(q, "philosophy", "nation building", "growth with goodness", "mission", "vision", "core focus", "focus area", "what is aidtm about", "about aidtm", "overview", "full name", "stands for", "what is aidtm", "private institute", "private college"):
        chunk = "AIDTM-OVERVIEW"
        answer = ("**AIDTM** stands for **Adani Institute of Digital Technology Management**. The supplied profile says it was established in **2020** in **Gandhinagar, Gujarat**, is an **AICTE-approved private institute**, and follows the Adani Group philosophy of **“Nation Building”** and **“Growth with Goodness.”** Its focus is connecting innovative ideas with disruptive technologies, especially **Big Data, AI and Data Science**.")

    else:
        # When the question is clearly about AIDTM, fail helpfully instead of allowing
        # the offline chatbot to silently guess from a vaguely related document.
        institutional_terms = (
            "aidtm", "adani institute", "pgdm", "big data analytics", "ai & data science", "education", "degree", "qualification",
            "ai and data science", "admission", "eligibility", "entrance exam", "fee", "fees",
            "placement", "scholarship", "faculty", "professor", "campus", "hostel", "timetable",
            "application status", "executive program", "executive programme", "epaaa", "techathon",
            "prashasti", "ideathon", "student life", "selection criteria", "admission criteria",
        )
        if not any(term in q for term in institutional_terms):
            return None
        chunk = "AIDTM-OVERVIEW"
        source = BASE
        answer = ("I don't have that specific detail in the AIDTM profile currently loaded into this chatbot, "
                  "so I won't guess. Please confirm it with AIDTM through the [official website](%s) or "
                  "[contact page](%s). If you share the missing information, it can be added to the chatbot's knowledge base." % (BASE, CONTACT))

    return {
        "answer": answer + PROVENANCE,
        "chunk_id": chunk,
        "source_url": source,
        "mode": "curated_knowledge",
    }
