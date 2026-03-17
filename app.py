import streamlit as st
import base64
import json
import re
import hashlib
import os
from groq import Groq
from PIL import Image
import fitz  # PyMuPDF
import io

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Exam Checker",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Sora:wght@300;400;600;700&display=swap');

:root {
    --teal:       #0D9488;
    --teal-light: #2DD4BF;
    --teal-dark:  #0F766E;
    --cyan:       #06B6D4;
    --border:     #99F6E4;
    --text:       #134E4A;
    --shadow:     rgba(13,148,136,0.15);
}

* { font-family: 'Space Grotesk', sans-serif; }

html, body, [data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #E6FAF8 0%, #CCFBF1 40%, #CFFAFE 100%) !important;
    color: var(--text);
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D9488 0%, #0891B2 100%) !important;
    border-right: 2px solid var(--teal-light);
}
[data-testid="stSidebar"] * { color: white !important; }

.hero {
    background: linear-gradient(135deg, #0D9488, #0891B2);
    border-radius: 20px;
    padding: 2.2rem 2rem;
    margin-bottom: 1.5rem;
    text-align: center;
    box-shadow: 0 8px 32px rgba(13,148,136,0.3);
    position: relative; overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute; top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(103,232,249,0.15) 0%, transparent 60%);
}
.hero h1 {
    font-family: 'Sora', sans-serif;
    font-size: 2.4rem; font-weight: 700;
    color: white; margin: 0;
}
.hero p { color: #CCFBF1; font-size: 1rem; margin-top: 0.4rem; }

.card {
    background: rgba(255,255,255,0.85);
    border: 1.5px solid var(--border);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 16px var(--shadow);
}
.card h3 { color: var(--teal-dark); font-size: 1.05rem; font-weight: 600; margin-bottom: 1rem; }

.score-big {
    background: linear-gradient(135deg, #0D9488, #06B6D4);
    border-radius: 20px; padding: 2rem;
    text-align: center; color: white;
    box-shadow: 0 8px 24px rgba(13,148,136,0.4);
}
.score-number { font-family: 'Sora', sans-serif; font-size: 5rem; font-weight: 700; line-height: 1; }
.score-label { font-size: 1.1rem; opacity: 0.85; margin-top: 0.4rem; }
.score-percent {
    font-size: 1.6rem; font-weight: 600;
    background: rgba(255,255,255,0.2);
    border-radius: 50px; padding: 0.25rem 1rem;
    display: inline-block; margin-top: 0.6rem;
}

.result-section {
    background: white;
    border-left: 4px solid var(--teal);
    border-radius: 0 12px 12px 0;
    padding: 1.2rem 1.5rem; margin: 1rem 0;
    box-shadow: 0 2px 8px var(--shadow);
}
.result-section.feedback  { border-color: var(--cyan); }
.result-section.strengths { border-color: #10B981; }
.result-section.improve   { border-color: #F59E0B; }
.result-section h4 { font-weight: 600; color: var(--teal-dark); margin-bottom: 0.5rem; }

.prog-bar { height: 12px; border-radius: 6px; background: #CCFBF1; overflow: hidden; }
.prog-fill { height: 100%; border-radius: 6px; background: linear-gradient(90deg, #0D9488, #06B6D4); }

.stButton > button {
    background: linear-gradient(135deg, #0D9488, #0891B2) !important;
    color: white !important; border: none !important;
    border-radius: 12px !important; font-weight: 600 !important;
    font-size: 1rem !important; padding: 0.65rem 2rem !important;
    box-shadow: 0 4px 12px rgba(13,148,136,0.3) !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(13,148,136,0.45) !important;
}

.stTextInput input, .stNumberInput input, .stTextArea textarea {
    border: 1.5px solid var(--border) !important;
    border-radius: 10px !important;
    background: rgba(255,255,255,0.9) !important;
    color: var(--text) !important;
}

[data-testid="stFileUploader"] {
    border: 2px dashed var(--teal-light) !important;
    border-radius: 14px !important;
    background: rgba(255,255,255,0.7) !important;
}

.badge {
    display: inline-block; padding: 0.25rem 0.8rem;
    border-radius: 50px; font-size: 0.82rem; font-weight: 600;
    background: linear-gradient(135deg, var(--teal), var(--cyan));
    color: white;
}

hr { border-color: var(--border) !important; }
</style>
""", unsafe_allow_html=True)


# ─── User Storage ─────────────────────────────────────────────────────────────
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def register_user(name, email, password, api_key):
    users = load_users()
    if email in users:
        return False, "Email already registered."
    users[email] = {"name": name, "password": hash_pw(password), "api_key": api_key}
    save_users(users)
    return True, "Account created!"

def login_user(email, password):
    users = load_users()
    if email not in users:
        return False, None, "Email not found."
    if users[email]["password"] != hash_pw(password):
        return False, None, "Incorrect password."
    return True, users[email], "Login successful!"

def update_api_key(email, new_key):
    users = load_users()
    if email in users:
        users[email]["api_key"] = new_key
        save_users(users)


# ─── Session Defaults ─────────────────────────────────────────────────────────
for k, v in {"logged_in": False, "user_email": "", "user_name": "",
             "user_api_key": "", "auth_mode": "login"}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─── Auth Screen ──────────────────────────────────────────────────────────────
def show_auth():
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown("""
        <div style="text-align:center;margin:2rem 0 1.5rem;">
          <div style="font-size:3rem;">📝</div>
          <h1 style="font-family:'Sora',sans-serif;font-size:2.2rem;font-weight:700;
                     background:linear-gradient(135deg,#0D9488,#06B6D4);
                     -webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0;">
            AI Exam Checker
          </h1>
          <p style="color:#0F766E;font-size:0.95rem;margin-top:0.3rem;">
            Smart grading for teachers — powered by Groq LLM
          </p>
        </div>
        """, unsafe_allow_html=True)

        # Tab switcher
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔑  Login", use_container_width=True, key="tab_login"):
                st.session_state.auth_mode = "login"
        with c2:
            if st.button("✏️  Sign Up", use_container_width=True, key="tab_signup"):
                st.session_state.auth_mode = "signup"

        st.markdown("<br>", unsafe_allow_html=True)

        # ── LOGIN ──
        if st.session_state.auth_mode == "login":
            st.markdown('<div class="card"><h3>🔑 Teacher Login</h3>', unsafe_allow_html=True)
            email    = st.text_input("📧 Email", placeholder="teacher@school.com", key="li_email")
            password = st.text_input("🔒 Password", type="password", key="li_pass")
            if st.button("Login →", use_container_width=True, key="login_btn"):
                if not email or not password:
                    st.warning("Please fill in all fields.")
                else:
                    ok, data, msg = login_user(email, password)
                    if ok:
                        st.session_state.logged_in    = True
                        st.session_state.user_email   = email
                        st.session_state.user_name    = data["name"]
                        st.session_state.user_api_key = data["api_key"]
                        st.success(f"Welcome back, {data['name']}! 🎉")
                        st.rerun()
                    else:
                        st.error(msg)
            st.markdown("</div>", unsafe_allow_html=True)

        # ── SIGNUP ──
        else:
            st.markdown('<div class="card"><h3>✏️ Create Teacher Account</h3>', unsafe_allow_html=True)
            name    = st.text_input("👤 Full Name", placeholder="e.g. Mr. Ahmed", key="su_name")
            email   = st.text_input("📧 Email", placeholder="teacher@school.com", key="su_email")
            password = st.text_input("🔒 Password (min 6 chars)", type="password", key="su_pass")
            confirm  = st.text_input("🔒 Confirm Password", type="password", key="su_confirm")
            api_key  = st.text_input(
                "🔑 Groq API Key",
                type="password", placeholder="gsk_...",
                help="Enter once — saved to your account. No need to enter again!",
                key="su_api",
            )
            st.caption("🔗 Get your free Groq key at [console.groq.com](https://console.groq.com)")

            if st.button("Create Account →", use_container_width=True, key="signup_btn"):
                if not all([name, email, password, confirm, api_key]):
                    st.warning("Please fill in all fields.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    ok, msg = register_user(name, email, password, api_key)
                    if ok:
                        st.success(msg + " Please login now.")
                        st.session_state.auth_mode = "login"
                        st.rerun()
                    else:
                        st.error(msg)
            st.markdown("</div>", unsafe_allow_html=True)


# ─── Image Helpers ────────────────────────────────────────────────────────────
def pdf_to_images(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    imgs = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        imgs.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
    return imgs

def image_to_b64(img):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()

def file_to_images(uf):
    uf.seek(0)
    raw = uf.read()
    if uf.name.lower().endswith(".pdf"):
        return pdf_to_images(raw)
    return [Image.open(io.BytesIO(raw))]


# ─── Grading ──────────────────────────────────────────────────────────────────
def grade_exam(client, images, topic, total_marks, scheme):
    content = [
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_to_b64(img)}"}}
        for img in images
    ]
    scheme_note = f"\nMarking Scheme:\n{scheme}" if scheme.strip() else ""
    content.append({"type": "text", "text": f"""You are an expert academic examiner.

Exam Topic: {topic}
Total Marks: {total_marks}{scheme_note}

Read the student answer sheet and evaluate it.
Return ONLY valid JSON (no markdown fences):
{{
  "marks_obtained": <int>,
  "total_marks": {total_marks},
  "percentage": <float 1 decimal>,
  "grade": "<A+|A|B+|B|C|D|F>",
  "overall_feedback": "<2-3 sentences>",
  "strengths": ["<pt>", "<pt>"],
  "areas_for_improvement": ["<pt>", "<pt>"],
  "question_breakdown": [
    {{"question": "<label>", "marks_given": <int>, "max_marks": <int>, "comment": "<brief>"}}
  ]
}}"""})

    resp = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": content}],
        max_tokens=1500, temperature=0.2,
    )
    raw = re.sub(r"```json|```", "", resp.choices[0].message.content.strip()).strip()
    return json.loads(raw)

GRADE_COLORS = {
    "A+":"#0D9488","A":"#0D9488","B+":"#06B6D4",
    "B":"#06B6D4","C":"#F59E0B","D":"#F97316","F":"#EF4444",
}


# ─── Main App ─────────────────────────────────────────────────────────────────
def show_main_app():
    with st.sidebar:
        st.markdown(f"## 👋 {st.session_state.user_name}")
        st.markdown(f"📧 `{st.session_state.user_email}`")
        st.markdown("---")
        st.markdown("### 📋 Exam Details")
        topic        = st.text_input("📚 Topic / Subject", placeholder="e.g. Computer Security")
        total_marks  = st.number_input("🏆 Total Marks", min_value=1, max_value=1000, value=100, step=1)
        marking_scheme = st.text_area("📝 Marking Scheme (optional)",
                                      placeholder="Q1 – 20 marks...\nQ2 – 30 marks...", height=110)
        st.markdown("---")
        st.markdown("### ⚙️ Update API Key")
        new_key = st.text_input("Groq API Key", type="password",
                                value=st.session_state.user_api_key, key="sidebar_key")
        if st.button("💾 Save Key", use_container_width=True):
            update_api_key(st.session_state.user_email, new_key)
            st.session_state.user_api_key = new_key
            st.success("✅ Key saved!")
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            for k in ["logged_in","user_email","user_name","user_api_key"]:
                st.session_state[k] = False if k == "logged_in" else ""
            st.rerun()

    st.markdown(f"""
    <div class="hero">
      <h1>📝 AI Exam Checker</h1>
      <p>Welcome, {st.session_state.user_name} — Groq LLM powered grading</p>
    </div>""", unsafe_allow_html=True)

    col_up, col_prev = st.columns([1, 1], gap="large")

    with col_up:
        st.markdown('<div class="card"><h3>📤 Upload Answer Sheet(s)</h3>', unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "Drag & drop or browse",
            type=["jpg","jpeg","png","pdf"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
        st.markdown("</div>", unsafe_allow_html=True)
        if uploaded_files:
            st.markdown(f'<div class="card"><h3>📄 {len(uploaded_files)} file(s) ready</h3>', unsafe_allow_html=True)
            for f in uploaded_files:
                st.markdown(f'<span class="badge">{f.name}</span> &nbsp;', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    with col_prev:
        if uploaded_files:
            st.markdown('<div class="card"><h3>🖼️ Preview</h3>', unsafe_allow_html=True)
            imgs = file_to_images(uploaded_files[0])
            st.image(imgs[0], caption=f"Page 1 — {uploaded_files[0].name}", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    btn_col, _ = st.columns([1, 3])
    with btn_col:
        check = st.button("🚀 Check Exam", use_container_width=True)

    if check:
        errors = []
        if not st.session_state.user_api_key:
            errors.append("⚠️ No Groq API key. Add it in the sidebar.")
        if not topic.strip():
            errors.append("⚠️ Please enter the exam topic.")
        if not uploaded_files:
            errors.append("⚠️ Please upload at least one file.")
        for e in errors:
            st.warning(e)

        if not errors:
            with st.spinner("🔍 Analyzing with AI…"):
                try:
                    client = Groq(api_key=st.session_state.user_api_key)
                    all_imgs = []
                    for uf in uploaded_files:
                        uf.seek(0)
                        all_imgs.extend(file_to_images(uf))

                    result = grade_exam(client, all_imgs, topic, total_marks, marking_scheme)

                    st.markdown("## 📊 Results")
                    pct   = result.get("percentage", 0)
                    grade = result.get("grade", "N/A")
                    gc    = GRADE_COLORS.get(grade, "#0D9488")

                    c1, c2, c3 = st.columns([1.2, 1, 1])
                    with c1:
                        st.markdown(f"""
                        <div class="score-big">
                          <div class="score-number">{result['marks_obtained']}</div>
                          <div class="score-label">out of {result['total_marks']} marks</div>
                          <div class="score-percent">{pct}%</div>
                        </div>""", unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"""
                        <div class="card" style="text-align:center;padding:2rem 1rem;">
                          <div style="font-size:4rem;font-weight:700;color:{gc};
                                      font-family:'Sora',sans-serif;">{grade}</div>
                          <div style="color:#0F766E;font-weight:600;">Grade</div>
                        </div>""", unsafe_allow_html=True)
                    with c3:
                        st.markdown(f"""
                        <div class="card">
                          <strong>📈 Score Progress</strong>
                          <div style="margin:0.8rem 0;">
                            <div style="display:flex;justify-content:space-between;
                                        font-size:0.85rem;color:#0F766E;margin-bottom:4px;">
                              <span>0</span><span>{result['total_marks']}</span>
                            </div>
                            <div class="prog-bar">
                              <div class="prog-fill" style="width:{pct}%;"></div>
                            </div>
                            <div style="text-align:right;font-size:0.85rem;
                                        color:#0D9488;margin-top:4px;">{pct}%</div>
                          </div>
                        </div>""", unsafe_allow_html=True)

                    st.markdown(f"""
                    <div class="result-section feedback">
                      <h4>💬 Overall Feedback</h4>
                      <p>{result.get('overall_feedback','')}</p>
                    </div>""", unsafe_allow_html=True)

                    cs, ci = st.columns(2)
                    with cs:
                        items = "".join(f"<li>{s}</li>" for s in result.get("strengths",[]))
                        st.markdown(f'<div class="result-section strengths"><h4>✅ Strengths</h4><ul>{items}</ul></div>', unsafe_allow_html=True)
                    with ci:
                        items = "".join(f"<li>{s}</li>" for s in result.get("areas_for_improvement",[]))
                        st.markdown(f'<div class="result-section improve"><h4>💡 Areas for Improvement</h4><ul>{items}</ul></div>', unsafe_allow_html=True)

                    breakdown = result.get("question_breakdown", [])
                    if breakdown:
                        st.markdown("### 📋 Question Breakdown")
                        st.markdown('<div class="card">', unsafe_allow_html=True)
                        h1,h2,h3,h4 = st.columns([2,1,1,4])
                        for h,col in zip(["Question","Marks Given","Max Marks","Comment"],[h1,h2,h3,h4]):
                            col.markdown(f"**{h}**")
                        st.divider()
                        for row in breakdown:
                            c1,c2,c3,c4 = st.columns([2,1,1,4])
                            c1.write(row.get("question",""))
                            c2.write(str(row.get("marks_given","")))
                            c3.write(str(row.get("max_marks","")))
                            c4.write(row.get("comment",""))
                        st.markdown("</div>", unsafe_allow_html=True)

                except json.JSONDecodeError:
                    st.error("❌ AI returned unexpected format. Please try again.")
                except Exception as ex:
                    st.error(f"❌ Error: {ex}")


# ─── Router ───────────────────────────────────────────────────────────────────
if st.session_state.logged_in:
    show_main_app()
else:
    show_auth()
