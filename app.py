import streamlit as st
import base64
import json
import re
from groq import Groq
from PIL import Image
import fitz  # PyMuPDF
import io
import os

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Exam Checker",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Sora:wght@300;400;600;700&display=swap');

:root {
    --teal:       #0D9488;
    --teal-light: #2DD4BF;
    --teal-dark:  #0F766E;
    --cyan:       #06B6D4;
    --cyan-light: #67E8F9;
    --white:      #F8FFFE;
    --off-white:  #E6FAF8;
    --surface:    #F0FDFB;
    --border:     #99F6E4;
    --text:       #134E4A;
    --text-light: #0F766E;
    --shadow:     rgba(13,148,136,0.15);
}

* { font-family: 'Space Grotesk', sans-serif; }

/* ── Global Background ── */
html, body, [data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #E6FAF8 0%, #CCFBF1 40%, #CFFAFE 100%) !important;
    color: var(--text);
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D9488 0%, #0891B2 100%) !important;
    border-right: 2px solid var(--teal-light);
}
[data-testid="stSidebar"] * { color: white !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stNumberInput label { color: #CCFBF1 !important; }

/* ── Hero Header ── */
.hero {
    background: linear-gradient(135deg, #0D9488, #0891B2);
    border-radius: 20px;
    padding: 2.5rem 2rem;
    margin-bottom: 2rem;
    text-align: center;
    box-shadow: 0 8px 32px rgba(13,148,136,0.3);
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute; top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(103,232,249,0.15) 0%, transparent 60%),
                radial-gradient(circle at 70% 30%, rgba(45,212,191,0.1) 0%, transparent 50%);
}
.hero h1 {
    font-family: 'Sora', sans-serif;
    font-size: 2.8rem; font-weight: 700;
    color: white; margin: 0; letter-spacing: -0.02em;
}
.hero p { color: #CCFBF1; font-size: 1.1rem; margin-top: 0.5rem; }

/* ── Cards ── */
.card {
    background: rgba(255,255,255,0.85);
    border: 1.5px solid var(--border);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 16px var(--shadow);
    backdrop-filter: blur(8px);
}
.card h3 {
    color: var(--teal-dark);
    font-size: 1.1rem; font-weight: 600;
    margin-bottom: 1rem;
    display: flex; align-items: center; gap: 0.5rem;
}

/* ── Score Display ── */
.score-big {
    background: linear-gradient(135deg, #0D9488, #06B6D4);
    border-radius: 20px;
    padding: 2rem;
    text-align: center;
    color: white;
    box-shadow: 0 8px 24px rgba(13,148,136,0.4);
}
.score-number {
    font-family: 'Sora', sans-serif;
    font-size: 5rem; font-weight: 700; line-height: 1;
}
.score-label { font-size: 1.2rem; opacity: 0.85; margin-top: 0.5rem; }
.score-percent {
    font-size: 1.8rem; font-weight: 600;
    background: rgba(255,255,255,0.2);
    border-radius: 50px; padding: 0.3rem 1rem;
    display: inline-block; margin-top: 0.8rem;
}

/* ── Result Sections ── */
.result-section {
    background: white;
    border-left: 4px solid var(--teal);
    border-radius: 0 12px 12px 0;
    padding: 1.2rem 1.5rem;
    margin: 1rem 0;
    box-shadow: 0 2px 8px var(--shadow);
}
.result-section.feedback { border-color: var(--cyan); }
.result-section.suggestions { border-color: #F59E0B; }
.result-section.strengths { border-color: #10B981; }

.result-section h4 {
    font-weight: 600; color: var(--teal-dark);
    margin-bottom: 0.6rem; font-size: 1rem;
}

/* ── Progress Bar ── */
.prog-container { margin: 1rem 0; }
.prog-bar {
    height: 12px; border-radius: 6px;
    background: #CCFBF1; overflow: hidden;
}
.prog-fill {
    height: 100%; border-radius: 6px;
    background: linear-gradient(90deg, #0D9488, #06B6D4);
    transition: width 1s ease;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #0D9488, #0891B2) !important;
    color: white !important;
    border: none !important; border-radius: 12px !important;
    font-weight: 600 !important; font-size: 1rem !important;
    padding: 0.7rem 2rem !important;
    box-shadow: 0 4px 12px rgba(13,148,136,0.3) !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(13,148,136,0.45) !important;
}

/* ── Inputs ── */
.stTextInput input, .stNumberInput input, .stSelectbox select, .stTextArea textarea {
    border: 1.5px solid var(--border) !important;
    border-radius: 10px !important;
    background: rgba(255,255,255,0.9) !important;
    color: var(--text) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--teal) !important;
    box-shadow: 0 0 0 3px rgba(13,148,136,0.15) !important;
}

/* ── File Uploader ── */
[data-testid="stFileUploader"] {
    border: 2px dashed var(--teal-light) !important;
    border-radius: 14px !important;
    background: rgba(255,255,255,0.7) !important;
    padding: 1rem !important;
}

/* ── Badge ── */
.badge {
    display: inline-block;
    padding: 0.25rem 0.8rem;
    border-radius: 50px;
    font-size: 0.82rem; font-weight: 600;
    background: linear-gradient(135deg, var(--teal), var(--cyan));
    color: white;
}

/* ── Divider ── */
hr { border-color: var(--border) !important; }

/* ── Warning / Info ── */
.stAlert { border-radius: 12px !important; }
</style>
""", unsafe_allow_html=True)


# ─── Helper: PDF → images ────────────────────────────────────────────────────
def pdf_to_images(pdf_bytes: bytes) -> list[Image.Image]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    return images


def image_to_base64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()


def file_to_images(uploaded_file) -> list[Image.Image]:
    raw = uploaded_file.read()
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        return pdf_to_images(raw)
    else:  # jpg / jpeg / png
        return [Image.open(io.BytesIO(raw))]


# ─── Grading Logic ───────────────────────────────────────────────────────────
def grade_exam(
    client: Groq,
    images: list[Image.Image],
    topic: str,
    total_marks: int,
    marking_scheme: str,
) -> dict:
    """Send images + prompt to Groq vision model and parse response."""

    # Build content list
    content = []
    for img in images:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_to_base64(img)}"},
        })

    scheme_note = f"\nMarking Scheme / Rubric:\n{marking_scheme}" if marking_scheme.strip() else ""

    content.append({
        "type": "text",
        "text": f"""You are an expert, strict-but-fair academic examiner.

Exam Topic: {topic}
Total Marks Available: {total_marks}
{scheme_note}

Please carefully read the student's answer sheet shown in the image(s) above, then:

1. Evaluate the answers based on correctness, completeness, and clarity.
2. Assign marks fairly out of {total_marks}.
3. Return your evaluation ONLY as valid JSON (no markdown fences) with this exact structure:
{{
  "marks_obtained": <integer>,
  "total_marks": {total_marks},
  "percentage": <float rounded to 1 decimal>,
  "grade": "<A+|A|B+|B|C|D|F>",
  "overall_feedback": "<2-3 sentence summary>",
  "strengths": ["<point1>", "<point2>"],
  "areas_for_improvement": ["<point1>", "<point2>"],
  "question_breakdown": [
    {{"question": "<label>", "marks_given": <int>, "max_marks": <int>, "comment": "<brief>"}}
  ]
}}
""",
    })

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": content}],
        max_tokens=1500,
        temperature=0.2,
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown fences if model adds them
    raw = re.sub(r"```json|```", "", raw).strip()
    return json.loads(raw)


# ─── Grade → color ───────────────────────────────────────────────────────────
GRADE_COLORS = {
    "A+": "#0D9488", "A": "#0D9488", "B+": "#06B6D4",
    "B": "#06B6D4",  "C": "#F59E0B", "D": "#F97316", "F": "#EF4444",
}


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    st.markdown("---")

    api_key = st.text_input(
        "🔑 Groq API Key",
        type="password",
        placeholder="gsk_...",
        help="Get your key at console.groq.com",
    )

    st.markdown("---")
    st.markdown("### 📋 Exam Details")

    topic = st.text_input(
        "📚 Exam Topic / Subject",
        placeholder="e.g. Algebra, Python Basics, World War II",
    )

    total_marks = st.number_input(
        "🏆 Total Marks",
        min_value=1, max_value=1000, value=100, step=1,
    )

    marking_scheme = st.text_area(
        "📝 Marking Scheme (optional)",
        placeholder="e.g.\nQ1 – 20 marks: correct formula + working\nQ2 – 30 marks: ...",
        height=130,
    )

    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.markdown(
        "Upload JPG, PNG or PDF answer sheets. The AI will analyze them and "
        "return marks, grade, feedback, and a per-question breakdown."
    )


# ─── Main ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>📝 AI Exam Checker</h1>
  <p>Intelligent answer-sheet grading powered by Groq LLM</p>
</div>
""", unsafe_allow_html=True)

col_upload, col_preview = st.columns([1, 1], gap="large")

with col_upload:
    st.markdown('<div class="card"><h3>📤 Upload Answer Sheet(s)</h3>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Drag & drop or browse",
        type=["jpg", "jpeg", "png", "pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if uploaded_files:
        st.markdown(f'<div class="card"><h3>📄 {len(uploaded_files)} file(s) ready</h3>', unsafe_allow_html=True)
        for f in uploaded_files:
            st.markdown(f'<span class="badge">{f.name}</span> &nbsp;', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

with col_preview:
    if uploaded_files:
        st.markdown('<div class="card"><h3>🖼️ Preview</h3>', unsafe_allow_html=True)
        preview_file = uploaded_files[0]
        preview_imgs = file_to_images(preview_file)
        st.image(preview_imgs[0], caption=f"Page 1 of {preview_file.name}", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# ── Check Button ──
check_col, _ = st.columns([1, 3])
with check_col:
    check = st.button("🚀 Check Exam", use_container_width=True)

# ── Validation + Grading ──
if check:
    errors = []
    if not api_key:
        errors.append("⚠️ Please enter your Groq API key in the sidebar.")
    if not topic.strip():
        errors.append("⚠️ Please enter the exam topic/subject.")
    if not uploaded_files:
        errors.append("⚠️ Please upload at least one answer sheet.")

    for e in errors:
        st.warning(e)

    if not errors:
        with st.spinner("🔍 Analyzing answer sheets with AI…"):
            try:
                client = Groq(api_key=api_key)

                # Collect all images from all files
                all_images: list[Image.Image] = []
                for uf in uploaded_files:
                    all_images.extend(file_to_images(uf))

                result = grade_exam(
                    client=client,
                    images=all_images,
                    topic=topic,
                    total_marks=total_marks,
                    marking_scheme=marking_scheme,
                )

                # ── Results ──
                st.markdown("## 📊 Results")

                r1, r2, r3 = st.columns([1.2, 1, 1])

                pct = result.get("percentage", 0)
                grade = result.get("grade", "N/A")
                grade_color = GRADE_COLORS.get(grade, "#0D9488")

                with r1:
                    st.markdown(f"""
                    <div class="score-big">
                      <div class="score-number">{result['marks_obtained']}</div>
                      <div class="score-label">out of {result['total_marks']} marks</div>
                      <div class="score-percent">{pct}%</div>
                    </div>
                    """, unsafe_allow_html=True)

                with r2:
                    st.markdown(f"""
                    <div class="card" style="text-align:center;padding:2rem 1rem;">
                      <div style="font-size:4rem;font-weight:700;color:{grade_color};
                                  font-family:'Sora',sans-serif;">{grade}</div>
                      <div style="color:#0F766E;font-weight:600;margin-top:0.4rem;">Grade</div>
                    </div>
                    """, unsafe_allow_html=True)

                with r3:
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.markdown("**📈 Score Progress**")
                    st.markdown(f"""
                    <div class="prog-container">
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
                    """, unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                # ── Feedback ──
                st.markdown(f"""
                <div class="result-section feedback">
                  <h4>💬 Overall Feedback</h4>
                  <p>{result.get('overall_feedback','')}</p>
                </div>
                """, unsafe_allow_html=True)

                col_s, col_i = st.columns(2)
                with col_s:
                    strengths = result.get("strengths", [])
                    items = "".join(f"<li>{s}</li>" for s in strengths)
                    st.markdown(f"""
                    <div class="result-section strengths">
                      <h4>✅ Strengths</h4>
                      <ul>{items}</ul>
                    </div>
                    """, unsafe_allow_html=True)

                with col_i:
                    improvements = result.get("areas_for_improvement", [])
                    items = "".join(f"<li>{s}</li>" for s in improvements)
                    st.markdown(f"""
                    <div class="result-section suggestions">
                      <h4>💡 Areas for Improvement</h4>
                      <ul>{items}</ul>
                    </div>
                    """, unsafe_allow_html=True)

                # ── Per-question breakdown ──
                breakdown = result.get("question_breakdown", [])
                if breakdown:
                    st.markdown("### 📋 Question-by-Question Breakdown")
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    header_cols = st.columns([2, 1, 1, 4])
                    for h, c in zip(["Question", "Marks Given", "Max Marks", "Comment"], header_cols):
                        c.markdown(f"**{h}**")
                    st.divider()
                    for row in breakdown:
                        c1, c2, c3, c4 = st.columns([2, 1, 1, 4])
                        c1.write(row.get("question", ""))
                        c2.write(str(row.get("marks_given", "")))
                        c3.write(str(row.get("max_marks", "")))
                        c4.write(row.get("comment", ""))
                    st.markdown("</div>", unsafe_allow_html=True)

            except json.JSONDecodeError:
                st.error("❌ The AI returned an unexpected format. Please try again.")
            except Exception as ex:
                st.error(f"❌ Error: {ex}")
