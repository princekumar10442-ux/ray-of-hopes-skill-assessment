from __future__ import annotations

import csv
import io
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import streamlit as st


APP_NAME = "Ray of Hopes"
LEVELS = {
    "primary": "Primary · Up to class 5",
    "middle": "Middle · Classes 6–8",
    "secondary": "Secondary · Classes 9–10",
    "higher": "Higher secondary · Classes 11–12",
    "graduate": "Graduate & above",
}
SECTIONS = ["Basic Computers", "English", "Aptitude", "Logical Reasoning", "General Awareness"]
CATEGORIES = ["None / other", "Visual", "Hearing", "Locomotor", "Cognitive / intellectual"]
QUESTION_FILE = Path(__file__).parent / "data" / "questions.json"

st.set_page_config(page_title=f"{APP_NAME} · Skills & Opportunity", page_icon="☀️", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { --ink:#173d3b; --muted:#667b77; --teal:#137c70; --mint:#e8f6f0; --orange:#f6a64b; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background:linear-gradient(150deg,#f7fbf7 0%,#f6f8fb 55%,#fff8ed 100%); color:#203a38; }
.block-container { max-width:1120px; padding-top:1.2rem; padding-bottom:3.5rem; }
h1,h2,h3 { font-family:'Manrope',sans-serif!important; color:var(--ink); letter-spacing:-.035em; }
.brandbar { display:flex; align-items:center; gap:14px; padding:12px 0 20px; border-bottom:1px solid #dfeae4; margin-bottom:28px; }
.brandmark { width:48px;height:48px;border-radius:16px;display:grid;place-items:center;background:linear-gradient(145deg,#f6bd61,#ec8f47);color:#fff;font-size:24px;box-shadow:0 7px 20px #e9a35d55; }
.brandname { font:800 20px Manrope,sans-serif;color:#164b45; }
.brandline { color:#72817d;font-size:13px;margin-top:1px; }
.hero { border-radius:28px; padding:clamp(28px,5vw,58px); background:radial-gradient(circle at 90% 5%,#fff5dc 0,transparent 35%),linear-gradient(120deg,#e8f6ef,#eef8f5 60%,#fff); border:1px solid #d9ebe2; position:relative; overflow:hidden; }
.eyebrow { color:#18776c;text-transform:uppercase;letter-spacing:.13em;font-size:11px;font-weight:800; }
.hero h1 { font-size:clamp(34px,5.6vw,60px);line-height:1.08;margin:14px 0;color:#164a43;max-width:700px; }
.hero p { max-width:650px;color:#526c66;font-size:17px;line-height:1.7; }
.statrow { display:flex;gap:10px;flex-wrap:wrap;margin-top:25px; }
.pill { padding:9px 13px;border:1px solid #d7e8de;border-radius:99px;background:#ffffffb8;color:#3b625a;font-size:13px;font-weight:600; }
.panel { background:#fff;border:1px solid #e5ece7;border-radius:22px;padding:24px;box-shadow:0 12px 35px #163e3510;margin:12px 0; }
.small-muted {color:#71817c;font-size:13px;}
.support-note {border-left:4px solid #e9a14a;background:#fff8eb;border-radius:8px;padding:13px 16px;color:#654a2c;font-size:14px;}
div.stButton>button,div.stFormSubmitButton>button {border-radius:12px;border:0;background:linear-gradient(135deg,#177c70,#20665f);color:white;font-weight:700;min-height:44px;box-shadow:0 6px 16px #176d6230;}
div.stButton>button:hover,div.stFormSubmitButton>button:hover {background:linear-gradient(135deg,#126d62,#174f4a);color:white;border:0;transform:translateY(-1px);}
button[kind="secondary"] {background:#fff;color:#28685f;border:1px solid #c8ddd3;box-shadow:none;}
.stProgress>div>div>div>div {background:linear-gradient(90deg,#139385,#f0ab54);}
section[data-testid="stSidebar"] {background:#f0f8f3;}
[data-testid="stMetric"] {background:#fff;border:1px solid #e3ece6;padding:16px;border-radius:15px;}
.footer {text-align:center;color:#80908b;font-size:12px;padding:28px 0 4px;}
@media(max-width:650px){.block-container{padding-left:1rem;padding-right:1rem}.panel{padding:17px}.hero{border-radius:20px}}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_banks() -> dict[str, dict[str, list[dict[str, Any]]]]:
    with QUESTION_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


def init_state() -> None:
    defaults = {
        "page": "home", "student_name": "", "category": CATEGORIES[0], "notes": "", "supports": [],
        "level": "primary", "questions": [], "answers": {}, "question_index": 0, "saved": False,
        "teacher_token": "", "teacher_refresh": "", "teacher_name": "", "teacher_logged_in": False,
        "saved_record": None, "quiz_started": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_assessment() -> None:
    for key, value in {"page": "home", "student_name": "", "category": CATEGORIES[0], "notes": "", "supports": [],
                       "level": "primary", "questions": [], "answers": {}, "question_index": 0, "saved": False,
                       "saved_record": None, "quiz_started": False}.items():
        st.session_state[key] = value


def config() -> tuple[str, str]:
    try:
        url = st.secrets.get("SUPABASE_URL", st.secrets.get("supabase", {}).get("url", ""))
        key = st.secrets.get("SUPABASE_ANON_KEY", st.secrets.get("supabase", {}).get("anon_key", ""))
        return str(url).rstrip("/"), str(key)
    except Exception:
        return "", ""


def db_ready() -> bool:
    url, key = config()
    return url.startswith("https://") and bool(key)


def api_headers(token: str | None = None, prefer: str | None = None) -> dict[str, str]:
    _, key = config()
    headers = {"apikey": key, "Authorization": f"Bearer {token or key}", "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    return headers


def rest_request(method: str, table: str, *, token: str | None = None, params: dict | None = None,
                 payload: Any = None, prefer: str | None = None, timeout: int = 20) -> Any:
    url, _ = config()
    response = requests.request(method, f"{url}/rest/v1/{table}", headers=api_headers(token, prefer), params=params,
                                json=payload, timeout=timeout)
    if not response.ok:
        message = "Database request failed."
        try:
            message = response.json().get("message") or response.json().get("msg") or message
        except ValueError:
            pass
        raise RuntimeError(message)
    return response.json() if response.content else None


def teacher_auth(payload: dict) -> dict:
    url, key = config()
    response = requests.post(f"{url}/functions/v1/teacher-auth", headers={"apikey": key, "Content-Type": "application/json"},
                             json=payload, timeout=20)
    try:
        body = response.json()
    except ValueError:
        body = {}
    if not response.ok:
        raise RuntimeError(body.get("error", "Teacher account service could not complete the request."))
    return body


def brand() -> None:
    st.markdown('<div class="brandbar"><div class="brandmark">☀</div><div><div class="brandname">Ray of Hopes</div><div class="brandline">Skills · Confidence · Opportunity</div></div></div>', unsafe_allow_html=True)


def footer() -> None:
    st.markdown('<div class="footer">Made with care for every learner · Ray of Hopes</div>', unsafe_allow_html=True)


def support_copy() -> str:
    category = st.session_state.category
    supports = st.session_state.supports
    if "Larger text" in supports or category == "Visual":
        return "We’ll keep the page clear and comfortable to read. You can also use your device’s built-in screen reader."
    if "One question at a time" in supports or category == "Cognitive / intellectual":
        return "We’ll show one question at a time with simple, clear instructions. Take a break whenever you need."
    if category == "Hearing":
        return "All instructions and feedback are shown as text. You won’t need to hear audio to complete the assessment."
    if category == "Locomotor":
        return "The assessment works with a keyboard and assistive switches. Use the Previous, Skip, and Next controls to move around."
    return "Choose any display or reading supports that make this assessment more comfortable. Supports never change your questions or score."


def build_assessment(level: str) -> list[dict[str, Any]]:
    bank = load_banks().get(level, {})
    database_questions: dict[str, list[dict[str, Any]]] = {}
    if db_ready():
        try:
            rows = rest_request("GET", "questions", params={"select": "*", "education_level": f"eq.{level}", "is_active": "eq.true", "limit": "2000"}) or []
            for row in rows:
                section = row.get("section")
                options = row.get("options")
                correct = row.get("correct_index")
                if isinstance(options, str):
                    options = json.loads(options)
                if section in SECTIONS and isinstance(options, list) and len(options) >= 2 and isinstance(correct, int) and 0 <= correct < len(options):
                    database_questions.setdefault(section, []).append({**row, "options": options, "correctIndex": correct})
        except Exception:
            # A missing/temporarily unavailable question table should not block an assessment.
            database_questions = {}
    questions = []
    for section in SECTIONS:
        db_pool = database_questions.get(section, [])
        # Prefer teacher-curated questions once the database has enough to fill the section.
        pool = list(db_pool if len(db_pool) >= 4 else bank.get(section, []))
        random.shuffle(pool)
        questions.extend({**item, "section": section} for item in pool[:4])
    random.shuffle(questions)
    return questions


def section_results() -> dict[str, dict[str, int]]:
    result = {section: {"correct": 0, "total": 0} for section in SECTIONS}
    for i, question in enumerate(st.session_state.questions):
        section = question["section"]
        result[section]["total"] += 1
        if st.session_state.answers.get(i) == int(question["correctIndex"]):
            result[section]["correct"] += 1
    return result


def recommendation(breakdown: dict, pct: int) -> str:
    best = max(SECTIONS, key=lambda name: breakdown[name]["correct"] / max(1, breakdown[name]["total"]))
    level = st.session_state.level
    basic = level in ("primary", "middle")
    advanced = level in ("higher", "graduate")
    if pct < 30:
        return "Foundational Skills Refresher — build confidence in literacy, numeracy and computer basics with a supportive learning plan."
    routes = {
        "Basic Computers": "Computer Operations & Office Tools — build practical typing, office software, email and internet skills.",
        "English": "Communication & Customer Support — practise spoken communication, customer care, email and front-desk skills.",
        "Aptitude": "Bookkeeping & Small Business Skills — explore numbers through budgeting, billing, bookkeeping and business basics.",
        "Logical Reasoning": "Inventory & Office Administration — develop organisation, record-keeping and practical problem-solving skills.",
        "General Awareness": "Community Outreach & Service Support — use your everyday knowledge in community programmes and public-facing roles.",
    }
    route = routes[best]
    if basic:
        route += " Start with a beginner-friendly, hands-on course and learn at your own pace."
    elif advanced:
        route += " Consider an advanced course or a work placement to deepen your strengths."
    return route


def save_result() -> tuple[bool, str]:
    if st.session_state.saved:
        return True, "Your result has already been saved."
    if not db_ready():
        return False, "Your result is ready, but online saving is not configured. Ask your teacher to set up Supabase."
    breakdown = section_results()
    correct = sum(1 for i, q in enumerate(st.session_state.questions) if st.session_state.answers.get(i) == int(q["correctIndex"]))
    notes = [st.session_state.notes.strip()] if st.session_state.notes.strip() else []
    if st.session_state.supports:
        notes.append("Selected supports: " + ", ".join(st.session_state.supports))
    record = {
        "full_name": st.session_state.student_name,
        "category": st.session_state.category,
        "accommodation_notes": " | ".join(notes),
        "education_level": st.session_state.level,
        "score": correct,
        "total_questions": len(st.session_state.questions),
        "section_breakdown": breakdown,
        "recommended_pathway": recommendation(breakdown, round(correct / max(1, len(st.session_state.questions)) * 100)),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        rest_request("POST", "assessments", payload=record, prefer="return=minimal")
        st.session_state.saved = True
        return True, "Your result was saved securely for your teacher."
    except Exception as exc:
        return False, f"Could not save online: {exc}"


def home_page() -> None:
    st.markdown('<div class="hero"><div class="eyebrow">A brighter path starts here</div><h1>Every learner deserves a chance to shine.</h1><p>Discover your strengths with a friendly skills assessment and find a confident next step toward learning and work.</p><div class="statrow"><span class="pill">✦ Accessible by design</span><span class="pill">◷ Untimed · your own pace</span><span class="pill">♡ Support for every learner</span></div></div>', unsafe_allow_html=True)
    st.write("")
    left, right = st.columns(2, gap="large")
    with left:
        with st.container(border=True):
            st.markdown("### ✍️ Student space")
            st.write("Take a welcoming, untimed assessment and explore a training pathway shaped around your strengths.")
            if st.button("Start as a student →", key="student_home", use_container_width=True):
                st.session_state.page = "student_details"
                st.rerun()
    with right:
        with st.container(border=True):
            st.markdown("### 📋 Teacher space")
            st.write("Review learner submissions, scores, accessibility supports and recommended pathways.")
            if st.button("Open teacher portal →", key="teacher_home", use_container_width=True):
                st.session_state.page = "teacher"
                st.rerun()
    st.write("")
    with st.expander("What happens in the assessment?"):
        cols = st.columns(3)
        for col, title, desc in zip(cols, ["Tell us a little about yourself", "Choose your learning level", "Explore your next step"], ["Share your name and choose any support that helps you.", "Questions are selected to suit your education level.", "See your results and a suggested learning pathway."]):
            with col:
                st.markdown(f"**{title}**")
                st.caption(desc)
    st.caption("🔒 Student information and results are shared with authorised Ray of Hopes teachers.")


def student_details_page() -> None:
    st.markdown("## Your assessment starts here")
    st.write("A few details help us make the experience comfortable for you.")
    with st.form("student_details"):
        name = st.text_input("Your full name *", value=st.session_state.student_name, max_chars=120, placeholder="e.g. Asha Kumar")
        category = st.selectbox("Accessibility support category (optional)", CATEGORIES, index=CATEGORIES.index(st.session_state.category) if st.session_state.category in CATEGORIES else 0)
        notes = st.text_area("Anything else that would help? (optional)", value=st.session_state.notes, max_chars=500, placeholder="For example: I use a screen reader or need short breaks.")
        submitted = st.form_submit_button("Continue to support options →", use_container_width=True)
    if submitted:
        if len(name.strip()) < 2:
            st.error("Please enter your name so your teacher can recognise your result.")
        else:
            st.session_state.student_name = name.strip()
            st.session_state.category = category
            st.session_state.notes = notes.strip()
            st.session_state.page = "student_support"
            st.rerun()
    if st.button("← Back to home", key="back_home_details", type="secondary"):
        st.session_state.page = "home"
        st.rerun()


def student_support_page() -> None:
    st.markdown("## Make this assessment work for you")
    st.info(support_copy(), icon="💛")
    options = ["Larger text", "High contrast", "One question at a time", "Plain-language instructions", "Keyboard-friendly navigation"]
    recommended = {"Visual": ["Larger text", "High contrast"], "Hearing": [], "Locomotor": ["Keyboard-friendly navigation"], "Cognitive / intellectual": ["One question at a time", "Plain-language instructions"]}.get(st.session_state.category, [])
    st.caption("Choose any options you like. They affect how the page is displayed, not the questions or score.")
    selected = st.multiselect("Display and navigation supports", options, default=[x for x in recommended if x in options], label_visibility="collapsed")
    st.session_state.supports = selected
    st.write("")
    cols = st.columns([1, 2])
    with cols[0]:
        if st.button("← Back", key="support_back", type="secondary", use_container_width=True):
            st.session_state.page = "student_details"
            st.rerun()
    with cols[1]:
        if st.button("Choose your learning level →", key="support_next", use_container_width=True):
            st.session_state.page = "student_level"
            st.rerun()


def student_level_page() -> None:
    st.markdown("## Choose your learning level")
    st.caption("We’ll choose questions that match the level you select. You can take your time.")
    level = st.selectbox("Education level", list(LEVELS), format_func=lambda key: LEVELS[key], index=list(LEVELS).index(st.session_state.level))
    st.info("20 questions · 5 skill areas · Untimed", icon="🌿")
    left, right = st.columns([1, 2])
    with left:
        if st.button("← Back", key="level_back", type="secondary", use_container_width=True):
            st.session_state.page = "student_support"
            st.rerun()
    with right:
        if st.button("Begin my assessment →", key="begin_quiz", use_container_width=True):
            st.session_state.level = level
            st.session_state.questions = build_assessment(level)
            st.session_state.answers = {}
            st.session_state.question_index = 0
            st.session_state.saved = False
            st.session_state.quiz_started = True
            st.session_state.page = "quiz"
            st.rerun()


def quiz_page() -> None:
    questions = st.session_state.questions
    if not questions:
        st.session_state.page = "student_level"
        st.rerun()
    index = max(0, min(st.session_state.question_index, len(questions) - 1))
    question = questions[index]
    size_css = "" if "Larger text" not in st.session_state.supports else "<style>[data-testid='stMarkdownContainer'] p{font-size:1.18rem!important}</style>"
    contrast_css = "" if "High contrast" not in st.session_state.supports else "<style>.stApp{filter:contrast(1.15)}.stApp{color:#000}</style>"
    st.markdown(size_css + contrast_css, unsafe_allow_html=True)
    st.markdown(f"## Question {index + 1} of {len(questions)}")
    st.progress((index + 1) / len(questions), text=f"{question['section']} · {sum(1 for i in range(len(questions)) if i in st.session_state.answers)} answered")
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f"### {question['question']}")
    if "Plain-language instructions" in st.session_state.supports:
        st.caption("Choose one answer. If you’re unsure, you can skip and come back later.")
    previous = st.session_state.answers.get(index)
    selected = st.radio("Choose one answer", question["options"], index=previous if previous is not None else None, key=f"answer_{index}", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
    if "Visual" == st.session_state.category and selected is not None:
        st.caption("Your selected answer is highlighted. You may use your device’s built-in screen reader.")
    # Persist selected value immediately so Previous / Skip never lose an answer.
    if selected is not None:
        st.session_state.answers[index] = question["options"].index(selected)
    nav = st.columns(4)
    with nav[0]:
        if st.button("← Previous", key="quiz_prev", disabled=index == 0, type="secondary", use_container_width=True):
            st.session_state.question_index -= 1
            st.rerun()
    with nav[1]:
        if st.button("Skip question", key="quiz_skip", disabled=index >= len(questions) - 1, type="secondary", use_container_width=True):
            st.session_state.question_index += 1
            st.rerun()
    with nav[2]:
        if index < len(questions) - 1:
            if st.button("Save & next →", key="quiz_next", use_container_width=True):
                st.session_state.question_index += 1
                st.rerun()
        else:
            if st.button("Review my answers →", key="quiz_review", use_container_width=True):
                st.session_state.page = "review"
                st.rerun()
    with nav[3]:
        if st.button("⌂ Home", key="quiz_home", type="secondary", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()
    with st.expander("Jump to a question"):
        grid = st.columns(5)
        for i in range(len(questions)):
            with grid[i % 5]:
                label = f"✓ {i+1}" if i in st.session_state.answers else (f"● {i+1}" if i == index else f"{i+1}")
                if st.button(label, key=f"jump_{i}", use_container_width=True):
                    st.session_state.question_index = i
                    st.rerun()


def review_page() -> None:
    st.markdown("## Review your answers")
    unanswered = [i for i in range(len(st.session_state.questions)) if i not in st.session_state.answers]
    if unanswered:
        st.warning(f"{len(unanswered)} question(s) are unanswered. They will count as incorrect, but you can still go back.")
    for i, q in enumerate(st.session_state.questions):
        answer = st.session_state.answers.get(i)
        with st.expander(f"{'✓' if answer is not None else '○'} Question {i+1} · {q['section']}", expanded=False):
            st.write(q["question"])
            st.write(f"Your answer: {q['options'][answer] if answer is not None else 'Skipped / unanswered'}")
            if st.button("Change answer", key=f"edit_{i}"):
                st.session_state.question_index = i
                st.session_state.page = "quiz"
                st.rerun()
    left, right = st.columns(2)
    with left:
        if st.button("← Back to questions", key="review_back", type="secondary", use_container_width=True):
            st.session_state.page = "quiz"
            st.rerun()
    with right:
        if st.button("Finish assessment", key="finish_assessment", use_container_width=True):
            st.session_state.page = "results"
            st.rerun()


def results_page() -> None:
    questions = st.session_state.questions
    if not questions:
        st.session_state.page = "home"
        st.rerun()
    correct = sum(1 for i, q in enumerate(questions) if st.session_state.answers.get(i) == int(q["correctIndex"]))
    pct = round(correct / len(questions) * 100)
    breakdown = section_results()
    st.markdown(f"## Well done, {st.session_state.student_name.split()[0]}! 🌟")
    st.write("You completed your skills assessment. Here’s a snapshot of your strengths and a suggested next step.")
    metrics = st.columns(3)
    metrics[0].metric("Your score", f"{correct} / {len(questions)}")
    metrics[1].metric("Overall result", f"{pct}%")
    metrics[2].metric("Learning level", LEVELS[st.session_state.level].split(" ·")[0])
    st.markdown("### Your skill areas")
    for section, score in breakdown.items():
        value = round(score["correct"] / max(1, score["total"]) * 100)
        st.progress(value / 100, text=f"{section} · {score['correct']}/{score['total']} ({value}%)")
    st.markdown("### A pathway to explore")
    st.info(recommendation(breakdown, pct), icon="🧭")
    if st.session_state.supports:
        st.caption("Supports used: " + ", ".join(st.session_state.supports))
    saved, message = save_result()
    if saved:
        st.success(message)
    else:
        st.warning(message)
        if db_ready() and st.button("Retry saving result", key="retry_save"):
            st.rerun()
    if not db_ready():
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["Name", "Education level", "Score", "Total", "Percentage", "Recommendation"])
        writer.writerow([st.session_state.student_name, LEVELS[st.session_state.level], correct, len(questions), f"{pct}%", recommendation(breakdown, pct)])
        st.download_button("Download my result", data=csv_buffer.getvalue(), file_name="ray-of-hopes-result.csv", mime="text/csv")
    if st.button("⌂ Return to home", key="results_home", type="secondary"):
        reset_assessment()
        st.rerun()


def teacher_page() -> None:
    st.markdown("## Teacher portal")
    if not db_ready():
        st.warning("Connect Supabase to enable teacher registration, sign-in and result storage. Student assessments still work offline.")
        st.code("[supabase]\nurl = \"https://your-project.supabase.co\"\n\n# Put the publishable/anon key in Streamlit secrets, never a service-role key.\nanon_key = \"your-publishable-key\"", language="toml")
        if st.button("⌂ Back to home", key="teacher_home_offline", type="secondary"):
            st.session_state.page = "home"
            st.rerun()
        return
    if st.session_state.teacher_logged_in:
        teacher_dashboard()
        return
    login_tab, register_tab = st.tabs(["Sign in", "Register teacher"])
    with login_tab:
        with st.form("teacher_login"):
            username = st.text_input("Username", placeholder="your.teacher.name")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
        if submitted:
            try:
                result = teacher_auth({"action": "login", "username": username.strip(), "password": password})
                st.session_state.teacher_token = result["access_token"]
                st.session_state.teacher_refresh = result.get("refresh_token", "")
                st.session_state.teacher_name = username.strip()
                st.session_state.teacher_logged_in = True
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with register_tab:
        st.caption("Teacher account registration is protected by the private key configured on your Supabase Edge Function.")
        with st.form("teacher_register"):
            username = st.text_input("Create username", help="3–32 letters, numbers, dots, underscores or hyphens")
            phone = st.text_input("Phone number with country code", placeholder="+919876543210")
            password = st.text_input("Create password", type="password", help="At least 8 characters")
            key = st.text_input("Teacher registration key", type="password")
            submitted = st.form_submit_button("Create teacher account", use_container_width=True)
        if submitted:
            try:
                teacher_auth({"action": "register", "username": username.strip(), "phone": phone.strip(), "password": password, "key": key})
                st.success("Teacher account created. Sign in with your username and password.")
            except Exception as exc:
                st.error(str(exc))
    if st.button("⌂ Back to home", key="teacher_home_login", type="secondary"):
        st.session_state.page = "home"
        st.rerun()


def teacher_dashboard() -> None:
    st.markdown(f"Welcome, **{st.session_state.teacher_name}**")
    top = st.columns([4, 1])
    with top[1]:
        if st.button("Sign out", key="teacher_logout", type="secondary", use_container_width=True):
            for key in ["teacher_token", "teacher_refresh", "teacher_name", "teacher_logged_in"]:
                st.session_state[key] = "" if key != "teacher_logged_in" else False
            st.rerun()
    results_tab, questions_tab = st.tabs(["📊 Student results", "📝 Question bank"])
    with results_tab:
        render_results_dashboard()
    with questions_tab:
        render_question_manager()


def render_results_dashboard() -> None:
    token = st.session_state.teacher_token
    a, b, c = st.columns([2, 1, 1])
    with a:
        name_filter = st.text_input("Search student", placeholder="Type a name")
    with b:
        level_filter = st.selectbox("Education level", ["All levels", *LEVELS.values()])
    with c:
        st.write("")
        refresh = st.button("↻ Refresh", key="refresh_results", type="secondary", use_container_width=True)
    try:
        records = rest_request("GET", "assessments", token=token,
                               params={"select": "*", "order": "created_at.desc", "limit": "1000"}) or []
        if name_filter:
            records = [r for r in records if name_filter.casefold() in str(r.get("full_name", "")).casefold()]
        if level_filter != "All levels":
            level_key = list(LEVELS)[list(LEVELS.values()).index(level_filter)]
            records = [r for r in records if r.get("education_level") == level_key]
        count = len(records)
        average = round(sum((int(r.get("score") or 0) / max(1, int(r.get("total_questions") or 0))) * 100 for r in records) / count) if count else 0
        best = max((int(r.get("score") or 0) / max(1, int(r.get("total_questions") or 0)) * 100 for r in records), default=0)
        m1, m2, m3 = st.columns(3)
        m1.metric("Assessments", count)
        m2.metric("Average score", f"{average}%")
        m3.metric("Highest score", f"{round(best)}%")
        if not records:
            st.info("No student assessments match these filters yet.")
            return
        rows = []
        for record in records:
            total = int(record.get("total_questions") or 0)
            score = int(record.get("score") or 0)
            rows.append({"Date": (record.get("created_at") or "")[:10], "Student": record.get("full_name", ""),
                         "Level": LEVELS.get(record.get("education_level"), record.get("education_level", "")),
                         "Support": record.get("category", ""), "Score": f"{score}/{total} ({round(score / max(1,total)*100)}%)",
                         "Suggested pathway": record.get("recommended_pathway", "")})
        st.dataframe(rows, use_container_width=True, hide_index=True)
        csv_buffer = io.StringIO()
        columns = list(rows[0])
        writer = csv.DictWriter(csv_buffer, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
        st.download_button("Download filtered results (CSV)", csv_buffer.getvalue(), "ray-of-hopes-assessments.csv", "text/csv")
        st.markdown("### Assessment details")
        labels = [f"{r.get('full_name','Student')} · {r.get('created_at','')[:10]} · {r.get('score',0)}/{r.get('total_questions',0)}" for r in records]
        selected = st.selectbox("Choose an assessment to review", range(len(labels)), format_func=lambda i: labels[i])
        record = records[selected]
        st.write("**Accessibility support:**", record.get("category", "None recorded"))
        st.write("**Additional notes:**", record.get("accommodation_notes") or "None recorded")
        st.write("**Recommended pathway:**", record.get("recommended_pathway", ""))
        breakdown = record.get("section_breakdown") or {}
        if isinstance(breakdown, dict):
            for section, values in breakdown.items():
                if isinstance(values, dict):
                    st.caption(f"{section}: {values.get('correct', 0)}/{values.get('total', 0)}")
    except Exception as exc:
        st.error(f"Could not load student results: {exc}")
        st.caption("Check that setup.sql has been applied and this teacher account is authorised.")


def render_question_manager() -> None:
    token = st.session_state.teacher_token
    a, b = st.columns(2)
    with a:
        level = st.selectbox("Question level", list(LEVELS), format_func=lambda key: LEVELS[key], key="manage_level")
    with b:
        section = st.selectbox("Skill area", SECTIONS, key="manage_section")
    try:
        questions = rest_request("GET", "questions", token=token, params={"select": "*", "education_level": f"eq.{level}", "section": f"eq.{section}", "order": "created_at.desc", "limit": "300"}) or []
    except Exception as exc:
        st.error(f"Could not load questions: {exc}")
        return
    active = [q for q in questions if q.get("is_active", True)]
    st.caption(f"{len(active)} active questions · {len(questions)} total in this area")
    with st.expander("Add a question"):
        with st.form("add_question"):
            prompt = st.text_area("Question", max_chars=1000)
            choices = [st.text_input(f"Answer option {i+1}", key=f"new_opt_{i}") for i in range(4)]
            correct = st.radio("Correct answer", [0, 1, 2, 3], format_func=lambda i: f"Option {i+1}", horizontal=True)
            submit = st.form_submit_button("Add to question bank")
        if submit:
            if not prompt.strip() or any(not choice.strip() for choice in choices):
                st.error("Add a question and all four answer options.")
            else:
                try:
                    rest_request("POST", "questions", token=token, prefer="return=minimal", payload={"education_level": level, "section": section, "question": prompt.strip(), "options": [x.strip() for x in choices], "correct_index": correct, "is_active": True})
                    st.success("Question added.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not add question: {exc}")
    for i, question in enumerate(questions):
        label = ("✓ " if question.get("is_active") else "⏸ ") + str(question.get("question", ""))
        with st.expander(label):
            options = question.get("options") or []
            for j, option in enumerate(options):
                st.write(f"{'✅' if j == question.get('correct_index') else '▫️'} {option}")
            left, right = st.columns([1, 4])
            with left:
                if st.button("Disable" if question.get("is_active") else "Enable", key=f"toggle_q_{question['id']}", type="secondary"):
                    try:
                        rest_request("PATCH", "questions", token=token, params={"id": f"eq.{question['id']}"}, payload={"is_active": not question.get("is_active")}, prefer="return=minimal")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not update question: {exc}")


def main() -> None:
    init_state()
    brand()
    page = st.session_state.page
    if page == "home":
        home_page()
    elif page == "student_details":
        student_details_page()
    elif page == "student_support":
        student_support_page()
    elif page == "student_level":
        student_level_page()
    elif page == "quiz":
        quiz_page()
    elif page == "review":
        review_page()
    elif page == "results":
        results_page()
    elif page == "teacher":
        teacher_page()
    else:
        st.session_state.page = "home"
        st.rerun()
    footer()


main()
