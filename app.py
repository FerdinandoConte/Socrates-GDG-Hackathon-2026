import json
from pathlib import Path

# pyrefly: ignore [missing-import]
import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True)

from agent.semantic_analyzer import semantic_analyzer_node
from agent.session_analyzer import session_analyzer_node, build_knowledge_map
from agent.orchestrator import orchestrator_node
from agent.tutor import tutor_node
from agent.evaluator import (
    generate_question,
    evaluate_answer_internal,
    evaluate_voice_answer_internal,
    update_knowledge_map,
    generate_final_feedback,
    should_continue_session,
    is_non_answer,
    generate_hint,
)
from agent.speech import transcribe_audio
from agent.peer_matcher import peer_matcher_node
from agent.state import MasteryZone
from agent.schemas import StudentGoal

MASTERY_EMOJI = {
    MasteryZone.UNEXPLORED: "⬜",
    MasteryZone.SKIMMED: "🟡",
    MasteryZone.STUDIED: "🟢",
    MasteryZone.STRUGGLING: "🔴",
    MasteryZone.CONSOLIDATING: "🔵",
    MasteryZone.MASTERED: "⭐",
}

LEVEL_ICON = {"strong": "✅", "adequate": "⚠️", "weak": "❌"}
GOAL_LABELS = {"exam": "📝 Exam", "study": "📚 Study", "work": "💼 Work"}
DIFFICULTY_LABELS = {
    "recognition": "🟢 Recognition",
    "recall": "🔵 Recall",
    "recall_angled": "🟠 Different angle",
    "application": "🔴 Application",
    "transfer": "⭐ Transfer",
}

ACTION_META = {
    "quiz_topic":            {"icon": "🏛️", "label": "Socratic Debate",       "color": "#74b9ff"},
    "introduce_topic":       {"icon": "📖", "label": "New Topic",              "color": "#55efc4"},
    "review_prerequisites":  {"icon": "🔍", "label": "Review Prerequisites",   "color": "#fdcb6e"},
    "fill_gap":              {"icon": "🩹", "label": "Fill Gap",               "color": "#fd79a8"},
    "peer_match":            {"icon": "🤝", "label": "Peer Match",             "color": "#a29bfe"},
}

def _get_avatar_b64():
    import base64
    p = Path(__file__).resolve().parent / "data" / "socrates_avatar.png"
    if p.exists():
        with open(p, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""
SOCRATES_AVATAR = f'<img src="data:image/png;base64,{_get_avatar_b64()}" style="width:28px;height:28px;border-radius:50%;object-fit:cover;vertical-align:middle;margin-right:6px;border:1px solid #a29bfe;"/>'
SOCRATES_AVATAR_HEADER = f'<img src="data:image/png;base64,{_get_avatar_b64()}" style="width:48px;height:48px;border-radius:50%;object-fit:cover;vertical-align:middle;margin-right:10px;border:2px solid #a29bfe;box-shadow:0 0 10px rgba(162,155,254,0.4);"/>'

st.set_page_config(page_title="Socrates", page_icon="🏛️", layout="wide")

# ── Custom CSS for WhatsApp-style chat ───────────────────────────────────────
st.markdown("""
<style>
    /* Hide Deploy button and menu */
    .stDeployButton {display: none;}
    [data-testid="stToolbar"] {display: none;}
    
    /* Hide loading animation and Streamlit default bar */
    [data-testid="stDecoration"] {display: none;}
    [data-testid="stStatusWidget"] {display: none;}
    [data-testid="stHeader"] {background: transparent;}

    /* Add a nicer animated loading bar at the top */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 4px;
        background: linear-gradient(90deg, #a29bfe, #74b9ff, #55efc4, #fdcb6e, #ff7675, #a29bfe);
        background-size: 200% 100%;
        animation: gradientMove 2s linear infinite;
        z-index: 999999;
    }

    @keyframes gradientMove {
        0% { background-position: 200% 0; }
        100% { background-position: 0% 0; }
    }
    .lp-hero {
      display: flex;
      flex-direction: column; /* Stack elements vertically */
      align-items: center;    /* Center elements horizontally */
      text-align: center;     /* Ensure text inside elements is centered */
    }
    .chat-container {
        max-width: 720px;
        margin: 0 auto;
        padding: 1rem 0;
    }
    .chat-bubble {
        padding: 0.75rem 1rem;
        border-radius: 16px;
        margin-bottom: 0.5rem;
        max-width: 80%;
        line-height: 1.5;
        font-size: 0.95rem;
        word-wrap: break-word;
    }
    .agent-bubble {
        background: linear-gradient(135deg, #2d2d3a, #3a3a4a);
        color: #e8e8e8;
        border-bottom-left-radius: 4px;
        margin-right: auto;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    .user-bubble {
        background: linear-gradient(135deg, #0b93f6, #0078d4);
        color: white;
        border-bottom-right-radius: 4px;
        margin-left: auto;
        box-shadow: 0 2px 8px rgba(11,147,246,0.3);
    }
    .voice-bubble {
        background: linear-gradient(135deg, #6c5ce7, #a29bfe);
        color: white;
        border-bottom-right-radius: 4px;
        margin-left: auto;
        box-shadow: 0 2px 8px rgba(108,92,231,0.3);
    }
    .bubble-row {
        display: flex;
        margin-bottom: 0.25rem;
    }
    .bubble-row-agent { justify-content: flex-start; }
    .bubble-row-user { justify-content: flex-end; }
    .bubble-label {
        font-size: 0.7rem;
        color: #888;
        margin-bottom: 2px;
        padding: 0 0.25rem;
    }
    .feedback-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid #2a2a4a;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    }
    .category-row {
        display: flex;
        align-items: center;
        padding: 0.5rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.05);
    }
    .category-row:last-child { border-bottom: none; }
    .category-icon { font-size: 1.2rem; margin-right: 0.75rem; }
    .category-name { font-weight: 600; color: #e0e0e0; flex: 1; }
    .category-level {
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .level-strong { background: rgba(46,204,113,0.2); color: #2ecc71; }
    .level-adequate { background: rgba(241,196,15,0.2); color: #f1c40f; }
    .level-weak { background: rgba(231,76,60,0.2); color: #e74c3c; }
    .category-comment {
        color: #aaa;
        font-size: 0.85rem;
        margin-top: 0.25rem;
        padding-left: 2rem;
    }
    .weakest-highlight {
        background: linear-gradient(135deg, rgba(231,76,60,0.1), rgba(192,57,43,0.1));
        border: 1px solid rgba(231,76,60,0.3);
        border-radius: 12px;
        padding: 1rem;
        margin-top: 1rem;
    }
    .session-status {
        text-align: center;
        padding: 0.5rem;
        color: #888;
        font-size: 0.85rem;
    }
    .voice-banner {
        background: linear-gradient(135deg, rgba(108,92,231,0.15), rgba(162,155,254,0.15));
        border: 1px solid rgba(108,92,231,0.3);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin: 0.75rem 0;
    }
    .voice-banner-title {
        font-weight: 600;
        color: #a29bfe;
        font-size: 1rem;
        margin-bottom: 0.25rem;
    }
    .voice-banner-desc {
        color: #bbb;
        font-size: 0.85rem;
    }
    .hint-bubble {
        background: linear-gradient(135deg, rgba(253,203,110,0.12), rgba(253,203,110,0.06));
        border: 1px solid rgba(253,203,110,0.35);
        color: #ffeaa7;
        border-bottom-left-radius: 4px;
        margin-right: auto;
        box-shadow: 0 2px 8px rgba(253,203,110,0.1);
    }
</style>
""", unsafe_allow_html=True)



# ── Helper to render chat bubbles ────────────────────────────────────────────

def _render_chat_bubbles(session: list[dict]):
    """Render the Socratic dialogue as WhatsApp-style chat bubbles."""
    for msg in session:
        if msg["role"] == "agent":
            bubble_class = "hint-bubble" if msg.get("_hint") else "agent-bubble"
            icon = "💡" if msg.get("_hint") else SOCRATES_AVATAR
            st.markdown(f"""
                <div class="bubble-row bubble-row-agent">
                    <div class="chat-bubble {bubble_class}">{icon} {msg['content']}</div>
                </div>
            """, unsafe_allow_html=True)
        elif msg.get("is_voice"):
            st.markdown(f"""
                <div class="bubble-row bubble-row-user">
                    <div class="chat-bubble voice-bubble">🎙️ {msg['content']}</div>
                </div>
            """, unsafe_allow_html=True)
        elif msg.get("_non_answer"):
            st.markdown(f"""
                <div class="bubble-row bubble-row-user">
                    <div class="chat-bubble user-bubble" style="opacity:0.6;font-style:italic;">{msg['content']} 👤</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="bubble-row bubble-row-user">
                    <div class="chat-bubble user-bubble">{msg['content']} 👤</div>
                </div>
            """, unsafe_allow_html=True)


def _process_answer(state, action, current_q, answer_text, turn, is_voice=False, transcription=None):
    """Process a student answer (text or voice) through the evaluation pipeline.
    Returns the updated state."""
    state["current_action"] = action

    # Add Q&A to session history
    session = list(state.get("socratic_session", []))
    session.append({"role": "agent", "content": current_q})
    user_msg = {"role": "user", "content": answer_text}
    if is_voice:
        user_msg["is_voice"] = True
    session.append(user_msg)
    state["socratic_session"] = session

    # Internal evaluation (voice-aware or standard)
    if is_voice and transcription:
        evaluation = evaluate_voice_answer_internal(state, current_q, transcription)
        state["voice_used_in_session"] = True
    else:
        evaluation = evaluate_answer_internal(state, current_q, answer_text)

    # Store evaluation data in the user's last message
    session[-1]["_evaluation"] = {
        "overall_understanding": evaluation.overall_understanding,
        "internal_score": evaluation.internal_score,
    }
    state["socratic_session"] = session

    # Update knowledge map (softer penalty for voice)
    state["knowledge_map"] = update_knowledge_map(state, evaluation, is_voice=is_voice)

    # Update difficulty based on new mastery
    from agent.evaluator import _get_current_mastery, _difficulty_for_mastery
    new_mastery = _get_current_mastery(state, action.target_topic_id)
    state["current_difficulty"] = _difficulty_for_mastery(new_mastery)

    # Increment turn
    state["socratic_turn"] = turn + 1

    # Check if session should continue
    if should_continue_session(state, evaluation):
        st.session_state["current_question"] = evaluation.follow_up_question
    else:
        final = generate_final_feedback(state)
        st.session_state["final_feedback"] = final
        st.session_state["session_finished"] = True

    return state


def _handle_non_answer(state, action, current_q, answer_text, turn):
    """Handle a non-answer (e.g. 'I don't know'): generate a hint and a simpler follow-up.
    Mastery is not changed and no evaluation score is recorded."""
    state["current_action"] = action

    session = list(state.get("socratic_session", []))
    session.append({"role": "agent", "content": current_q})
    session.append({"role": "user", "content": answer_text, "_non_answer": True})
    state["socratic_session"] = session

    hint_resp = generate_hint(state, current_q)

    session.append({"role": "agent", "content": hint_resp.hint, "_hint": True})
    state["socratic_session"] = session
    state["socratic_turn"] = turn + 1

    st.session_state["current_question"] = hint_resp.follow_up_question
    return state


@st.cache_data(persist="disk")
def load_peer_profiles():
    path = Path(__file__).resolve().parent
    file_path = path / "data" / "metadata_peer.json"

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    state = {
        "raw_metadata": data,
        "messages": [],
        "difficulty_level": "medium",
        "peer_match": None,
        "current_action": None,
        "pending_actions": [],
        "document_domain": "",
        "topic_list": [],
        "dependency_graph": {},
        "session_timeline": [],
        "behavioral_patterns": [],
        "knowledge_map": [],
        "current_question": None,
        "socratic_session": [],
        "socratic_turn": 0,
        "current_difficulty": "recall",
        "session_topic_id": None,
        "student_goal": "study",
        "voice_used_in_session": False,
    }
    state = semantic_analyzer_node(state)
    state = session_analyzer_node(state)

    return {
        "marco": {
            "name": "Marco R.",
            "knowledge_map": state["knowledge_map"],
            "status": "online"
        }
    }

peer_profiles = load_peer_profiles()

# ── Landing page (shown only before file is uploaded) ───────────────────────
if "agent_state" not in st.session_state:
    st.markdown("""
<style>
.lp-hero { text-align:center; padding:3.5rem 1rem 2rem; }
.lp-logo { font-size:3.5rem; line-height:1; margin-bottom:0.75rem; }
.lp-title {
    font-size:2.8rem; font-weight:800; letter-spacing:-0.03em;
    background:linear-gradient(135deg,#a29bfe 0%,#74b9ff 60%,#55efc4 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    background-clip:text; margin:0;
}
.lp-sub { font-size:1.05rem; color:#9ca3af; margin-top:0.75rem;
          max-width:480px; margin-left:auto; margin-right:auto; line-height:1.6; text-align:center; }
.lp-card {
    background:linear-gradient(145deg,#1e1e2e,#16213e);
    border:1px solid rgba(162,155,254,0.18);
    border-radius:16px; padding:1.5rem; text-align:center; height:210px;
    display:flex; flex-direction:column; justify-content:center; align-items:center;
}
.lp-card-icon { font-size:1.8rem; margin-bottom:0.6rem; }
.lp-card-title { font-weight:700; color:#e0e0e0; font-size:0.95rem; margin-bottom:0.4rem; }
.lp-card-desc { color:#9ca3af; font-size:0.82rem; line-height:1.55; }
.lp-upload-wrap {
    background:linear-gradient(135deg,rgba(108,92,231,0.07),rgba(116,185,255,0.07));
    border:1px solid rgba(162,155,254,0.28); border-radius:20px;
    padding:2rem 2rem 1.25rem; margin-top:2rem;
}
.lp-upload-label { font-size:1rem; font-weight:600; color:#e0e0e0; margin-bottom:0.25rem; }
.lp-upload-hint { font-size:0.82rem; color:#9ca3af; margin-bottom:1rem; }
.lp-step { display:flex; align-items:flex-start; gap:0.75rem; margin-bottom:0.6rem; }
.lp-step-num {
    width:22px; height:22px; border-radius:50%; flex-shrink:0;
    background:rgba(162,155,254,0.2); border:1px solid rgba(162,155,254,0.4);
    font-size:0.7rem; font-weight:700; color:#a29bfe;
    display:flex; align-items:center; justify-content:center;
}
.lp-step-text { font-size:0.83rem; color:#9ca3af; line-height:1.45; padding-top:2px; }
</style>
""", unsafe_allow_html=True)

    st.markdown(f"""
<div class="lp-hero" style="display:flex; flex-direction:column; align-items:center;">
  <img src="data:image/png;base64,{_get_avatar_b64()}" style="width:110px;height:110px;border-radius:50%;object-fit:cover;margin-bottom:16px;border:4px solid #a29bfe;box-shadow:0 0 25px rgba(162,155,254,0.6);"/>
  <div class="lp-logo" style="margin-bottom:0;">Socrates</div>
  <p class="lp-sub" style="margin-top:1rem;">Agentic AI Braynr extension for active learning — turns your study data into a personalised coaching session.</p>
</div>
""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3, gap="medium")
    for col, icon, title, desc in [
        (col1, "📊", "Knowledge Map", "See which topics you've truly mastered and where you're still struggling at a glance."),
        (col2, "🏛️", "Socratic Debate", "Engage in targeted debates generated from your own notes and flashcards — no generic content."),
        (col3, "🤝", "Peer Match", "Get matched with a peer who has already mastered what you're struggling with."),
    ]:
        with col:
            st.markdown(f"""
<div class="lp-card">
  <div class="lp-card-icon">{icon}</div>
  <div class="lp-card-title">{title}</div>
  <div class="lp-card-desc">{desc}</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        up_col1, up_col2 = st.columns([1.5, 1], gap="large", vertical_alignment="center")
        with up_col1:
            st.markdown("""
<div style="padding: 0.5rem;">
  <div class="lp-upload-label" style="font-size:1.1rem; margin-bottom:0.4rem;">Upload your session data</div>
  <div class="lp-upload-hint" style="margin-bottom:1rem;">Export <code>metadata.json</code> from the Braynr app.</div>
  <div class="lp-step"><div class="lp-step-num">1</div><div class="lp-step-text">Open Braynr → Settings → Export data</div></div>
  <div class="lp-step"><div class="lp-step-num">2</div><div class="lp-step-text">Save the <code>metadata.json</code> file to your device</div></div>
  <div class="lp-step"><div class="lp-step-num">3</div><div class="lp-step-text">Upload it using the widget to the right</div></div>
</div>
""", unsafe_allow_html=True)
        with up_col2:
            st.info("⏱️ Analysis takes ~20 seconds")
            uploaded = st.file_uploader("Upload metadata.json", type="json", label_visibility="collapsed")

    if uploaded:
        raw = json.load(uploaded)
        with st.spinner("🏛️ Analyzing your study session with AI… (this may take ~20 s)"):
            state: dict = {
                "raw_metadata": raw,
                "peer_pool": [peer_profiles] if peer_profiles else [],
                "messages": [],
                "difficulty_level": "medium",
                "peer_match": None,
                "current_action": None,
                "pending_actions": [],
                "document_domain": "",
                "topic_list": [],
                "dependency_graph": {},
                "session_timeline": [],
                "behavioral_patterns": [],
                "knowledge_map": [],
                "current_question": None,
                "socratic_session": [],
                "socratic_turn": 0,
                "current_difficulty": "recall",
                "session_topic_id": None,
                "student_goal": "study",
                "voice_used_in_session": False,
            }
            state = semantic_analyzer_node(state)
            state = session_analyzer_node(state)
            state = orchestrator_node(state)
        st.session_state["agent_state"] = state
        st.rerun()

    st.stop()

state: dict = st.session_state["agent_state"]

# ── Persistent top header ─────────────────────────────────────────────────────
st.markdown("""
<style>
.app-header-brand {
    display:flex; align-items:center; gap:0.6rem; padding:0.4rem 0;
}
.app-header-logo { font-size:1.5rem; line-height:1; }
.app-header-title {
    font-size:1.2rem; font-weight:800; letter-spacing:-0.02em;
    background:linear-gradient(135deg,#a29bfe 0%,#74b9ff 60%,#55efc4 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    background-clip:text;
}
</style>
""", unsafe_allow_html=True)

_hcol_brand, _hcol_btn = st.columns([5, 1], vertical_alignment="center")
with _hcol_brand:
    st.markdown(f"""
<div class="app-header-brand">
  <span class="app-header-logo">{SOCRATES_AVATAR_HEADER}</span>
  <span class="app-header-title">Socrates</span>
</div>""", unsafe_allow_html=True)
with _hcol_btn:
    if st.button("← New file", help="Go back to home and load a different file", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
st.divider()

# ── Debug mode (activate via ?debug=1 in URL) ────────────────────────────────
DEBUG_MODE = st.query_params.get("debug") == "1"
force_voice = False
if DEBUG_MODE:
    with st.sidebar:
        st.markdown("### 🔧 Debug")
        force_voice = st.toggle(
            "Force voice mode",
            value=False,
            help="Show the voice banner from turn 1.",
        )

# ── Overview metrics banner ──────────────────────────────────────────────────
_km = state.get("knowledge_map", [])
if _km:
    _total = len(_km)
    _explored = sum(1 for t in _km if t.mastery_zone != MasteryZone.UNEXPLORED)
    _mastered = sum(1 for t in _km if t.mastery_zone == MasteryZone.MASTERED)
    _consolidating = sum(1 for t in _km if t.mastery_zone == MasteryZone.CONSOLIDATING)
    _struggling = sum(1 for t in _km if t.mastery_zone == MasteryZone.STRUGGLING)
    _studied = sum(1 for t in _km if t.mastery_zone == MasteryZone.STUDIED)
    _skimmed = sum(1 for t in _km if t.mastery_zone == MasteryZone.SKIMMED)
    _unexplored = _total - _explored
    _strong_pct = int((_mastered + _consolidating) / _total * 100) if _total else 0

    # progress bar segments (widths as percentages of total)
    def _seg(n): return f"{n / _total * 100:.1f}%" if _total else "0%"

    st.markdown("""
<style>
.ov-wrap {
    display:flex; gap:0.75rem; margin-bottom:1.25rem; flex-wrap:wrap;
}
.ov-stat {
    flex:1; min-width:110px;
    background:linear-gradient(145deg,#1e1e2e,#16213e);
    border:1px solid rgba(162,155,254,0.15);
    border-radius:14px; padding:0.9rem 1rem 0.7rem;
    text-align:center;
}
.ov-stat-val {
    font-size:1.7rem; font-weight:800; line-height:1;
    margin-bottom:0.2rem;
}
.ov-stat-label { font-size:0.72rem; color:#9ca3af; letter-spacing:0.04em; text-transform:uppercase; }
.ov-bar-wrap {
    background:rgba(255,255,255,0.06); border-radius:8px; overflow:hidden;
    height:10px; display:flex; margin-bottom:0.4rem;
}
.ov-bar-seg { height:100%; transition:width 0.4s; }
.ov-bar-legend {
    display:flex; gap:1rem; flex-wrap:wrap;
    font-size:0.72rem; color:#9ca3af; margin-bottom:1rem;
}
.ov-leg-dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:4px; vertical-align:middle; }
</style>
""", unsafe_allow_html=True)

    st.markdown(f"""
<div class="ov-wrap">
  <div class="ov-stat">
    <div class="ov-stat-val" style="color:#a29bfe;">{_total}</div>
    <div class="ov-stat-label">Total Topics</div>
  </div>
  <div class="ov-stat">
    <div class="ov-stat-val" style="color:#55efc4;">{_strong_pct}%</div>
    <div class="ov-stat-label">Mastery Rate</div>
  </div>
  <div class="ov-stat">
    <div class="ov-stat-val" style="color:#ffeaa7;">⭐ {_mastered}</div>
    <div class="ov-stat-label">Mastered</div>
  </div>
  <div class="ov-stat">
    <div class="ov-stat-val" style="color:#74b9ff;">🔵 {_consolidating}</div>
    <div class="ov-stat-label">Consolidating</div>
  </div>
  <div class="ov-stat">
    <div class="ov-stat-val" style="color:#ff7675;">🔴 {_struggling}</div>
    <div class="ov-stat-label">Struggling</div>
  </div>
  <div class="ov-stat">
    <div class="ov-stat-val" style="color:#636e72;">⬜ {_unexplored}</div>
    <div class="ov-stat-label">Unexplored</div>
  </div>
</div>
<div class="ov-bar-wrap">
  <div class="ov-bar-seg" style="width:{_seg(_mastered)};background:#ffeaa7;"></div>
  <div class="ov-bar-seg" style="width:{_seg(_consolidating)};background:#74b9ff;"></div>
  <div class="ov-bar-seg" style="width:{_seg(_studied)};background:#55efc4;"></div>
  <div class="ov-bar-seg" style="width:{_seg(_skimmed)};background:#fdcb6e;"></div>
  <div class="ov-bar-seg" style="width:{_seg(_struggling)};background:#ff7675;"></div>
  <div class="ov-bar-seg" style="width:{_seg(_unexplored)};background:#2d3436;"></div>
</div>
<div class="ov-bar-legend">
  <span><span class="ov-leg-dot" style="background:#ffeaa7;"></span>Mastered</span>
  <span><span class="ov-leg-dot" style="background:#74b9ff;"></span>Consolidating</span>
  <span><span class="ov-leg-dot" style="background:#55efc4;"></span>Studied</span>
  <span><span class="ov-leg-dot" style="background:#fdcb6e;"></span>Skimmed</span>
  <span><span class="ov-leg-dot" style="background:#ff7675;"></span>Struggling</span>
  <span><span class="ov-leg-dot" style="background:#2d3436;"></span>Unexplored</span>
</div>
""", unsafe_allow_html=True)

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📋 Timeline", "🗺️ Knowledge Map", "🎯 Actions"])

# ─── Tab 1: Timeline ─────────────────────────────────────────────────────────
with tab1:
    st.subheader("Study Timeline")
    timeline = state.get("session_timeline", [])
    if timeline:
        import pandas as pd
        df = pd.DataFrame([
            {"When": e["datetime"], "": e["icon"], "Type": e["type"], "Content": e.get("text", "")[:90], "Page": e.get("page") or "—"}
            for e in timeline
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No timeline events found.")

    patterns = state.get("behavioral_patterns", [])
    if patterns:
        st.subheader("Detected Patterns")
        for p in patterns:
            icon = {"deep_dive": "🔍", "topic_skip": "⏭️", "long_pause": "⏸️", "spaced_repetition_struggle": "🔁"}.get(p.pattern_type, "▪️")
            st.markdown(f"{icon} **{p.pattern_type.replace('_', ' ').title()}** — {p.details}")

# ─── Tab 2: Knowledge Map ────────────────────────────────────────────────────
with tab2:
    st.subheader("Knowledge Map")
    st.caption(f"Document domain: **{state.get('document_domain', '—').upper()}**")
    km = state.get("knowledge_map", [])
    if km:
        import pandas as pd
        df = pd.DataFrame([
            {
                "Topic": MASTERY_EMOJI.get(tm.mastery_zone, "") + "  " + tm.topic_name,
                "Pages": f"{tm.page_range[0]}–{tm.page_range[1]}",
                "Keywords": tm.keywords_count,
                "Notes": tm.notes_count,
                "Flashcard reps": tm.fsrs_total_reps,
                "Avg difficulty": tm.fsrs_avg_difficulty if tm.fsrs_avg_difficulty else 0.0,
                "Mastery": tm.mastery_zone,
            }
            for tm in km
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("**Legend:** ⬜ Unexplored · 🟡 Skimmed · 🟢 Studied · 🔴 Struggling · 🔵 Consolidating · ⭐ Mastered")
    else:
        st.info("No knowledge map available yet.")

# ─── Tab 3: Actions ──────────────────────────────────────────────────────────
with tab3:
    pending = state.get("pending_actions", [])

    # ══════════════════════════════════════════════════════════════════════════
    # SOCRATIC SESSION UI
    # ══════════════════════════════════════════════════════════════════════════

    socratic_active = st.session_state.get("socratic_active", False)
    session_finished = st.session_state.get("session_finished", False)

    # ── Final feedback display ───────────────────────────────────────────────
    if session_finished and "final_feedback" in st.session_state:
        feedback = st.session_state["final_feedback"]
        topic_name = st.session_state.get("socratic_topic_name", "Topic")
        goal_label = GOAL_LABELS.get(state.get("student_goal", "study"), "📚 Study")

        st.divider()
        st.subheader(f"📊 Debate Summary — \"{topic_name}\"")
        st.caption(f"Goal: {goal_label}")

        # Show conversation history
        session_history = state.get("socratic_session", [])
        if session_history:
            with st.expander("💬 View full debate", expanded=False):
                _render_chat_bubbles(session_history)

        # Category feedback card
        st.markdown('<div class="feedback-card">', unsafe_allow_html=True)
        for cat in feedback.category_feedback:
            icon = LEVEL_ICON.get(cat.level, "▪️")
            if cat.category.lower() == "oral exposition":
                icon = "🎙️" if cat.level == "strong" else icon
            level_class = f"level-{cat.level}"
            st.markdown(f"""
                <div class="category-row">
                    <span class="category-icon">{icon}</span>
                    <span class="category-name">{cat.category}</span>
                    <span class="category-level {level_class}">{cat.level.upper()}</span>
                </div>
                <div class="category-comment">{cat.comment}</div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Weakest category highlight
        st.markdown(f"""
            <div class="weakest-highlight">
                <strong>💡 Most critical area: {feedback.weakest_category}</strong><br>
                <span style="color: #ccc;">{feedback.recommendation}</span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown(f"**📝 Summary:** {feedback.overall_summary}")

        if st.button("🔄 Back to actions", type="primary"):
            st.session_state.pop("socratic_active", None)
            st.session_state.pop("session_finished", None)
            st.session_state.pop("final_feedback", None)
            st.session_state.pop("socratic_topic_name", None)
            st.session_state.pop("current_question", None)
            st.session_state.pop("quiz_action", None)
            st.session_state.pop("pinned_response", None)
            st.session_state.pop("goal_selector_action_id", None)
            st.session_state.pop("show_goal_selector", None)
            state["socratic_session"] = []
            state["socratic_turn"] = 0
            state["session_topic_id"] = None
            state["voice_used_in_session"] = False
            state = orchestrator_node(state)
            st.session_state["agent_state"] = state
            st.rerun()

        st.divider()

    # ── Active Socratic dialogue ─────────────────────────────────────────────
    elif socratic_active and "current_question" in st.session_state:
        action = st.session_state["quiz_action"]
        topic_list = state.get("topic_list", [])
        topic = next((t for t in topic_list if t["id"] == action.target_topic_id), None)
        topic_name = topic["name"] if topic else action.target_topic_id
        st.session_state["socratic_topic_name"] = topic_name
        goal_label = GOAL_LABELS.get(state.get("student_goal", "study"), "📚 Study")
        turn = state.get("socratic_turn", 0)
        difficulty = state.get("current_difficulty", "recall")
        st.divider()
        st.subheader(f"🏛️ Socratic Debate — \"{topic_name}\"")

        col_info1, col_info2, col_info3 = st.columns(3)
        col_info1.caption(f"Goal: {goal_label}")
        col_info2.caption(f"Turn: {turn + 1}/7")
        col_info3.caption(f"Difficulty: {DIFFICULTY_LABELS.get(difficulty, difficulty)}")

        # Render chat history
        session_history = state.get("socratic_session", [])
        _render_chat_bubbles(session_history)

        # Current question (not yet in history)
        current_q = st.session_state["current_question"]
        st.markdown(f"""
            <div class="bubble-row bubble-row-agent">
                <div class="chat-bubble agent-bubble">{SOCRATES_AVATAR} {current_q}</div>
            </div>
        """, unsafe_allow_html=True)

        # ── Voice banner (appears after turn threshold for discursive subjects) ─
        voice_mode = st.session_state.get("voice_mode", False)
        voice_banner_dismissed = st.session_state.get(f"voice_banner_dismissed_{turn}", False)

        voice_turn_threshold = 0
        if turn >= voice_turn_threshold and not voice_mode and not voice_banner_dismissed:
            st.markdown("""
                <div class="voice-banner">
                    <div class="voice-banner-title">🎤 Want to try answering by voice?</div>
                    <div class="voice-banner-desc">
                        For this subject, explaining out loud is a great way to test your understanding.
                    </div>
                </div>
            """, unsafe_allow_html=True)
            col_voice_yes, col_voice_no = st.columns(2)
            if col_voice_yes.button("🎤 Record audio", key=f"voice_yes_{turn}", use_container_width=True):
                st.session_state["voice_mode"] = True
                st.rerun()
            if col_voice_no.button("✍️ No, I'll type", key=f"voice_no_{turn}", use_container_width=True):
                st.session_state[f"voice_banner_dismissed_{turn}"] = True
                st.rerun()

        # ── Voice input mode ─────────────────────────────────────────────────
        if voice_mode:
            audio_data = st.audio_input("🎤 Record your answer (max 2 minutes)", key=f"audio_{turn}")

            col_send_audio, col_switch_text, col_end_v = st.columns([2, 2, 1])

            if col_send_audio.button("📤 Submit recording", type="primary", use_container_width=True):
                if audio_data:
                    with st.spinner("Transcribing and evaluating your answer..."):
                        audio_bytes = audio_data.read()
                        transcription = transcribe_audio(audio_bytes)
                        answer_text = transcription.get("text", "")

                        if answer_text.strip():
                            if is_non_answer(answer_text.strip()):
                                state = _handle_non_answer(state, action, current_q, answer_text.strip(), turn)
                            else:
                                state = _process_answer(
                                    state, action, current_q, answer_text, turn,
                                    is_voice=True, transcription=transcription
                                )
                            st.session_state["voice_mode"] = False
                        else:
                            st.warning("Could not transcribe audio. Please try again or type your answer.")

                    st.session_state["agent_state"] = state
                    st.rerun()
                else:
                    st.warning("Please record your answer first.")

            if col_switch_text.button("✍️ Switch to text", use_container_width=True):
                st.session_state["voice_mode"] = False
                st.rerun()

            if col_end_v.button("🛑", use_container_width=True, help="End debate"):
                with st.spinner("Generating final feedback..."):
                    state["current_action"] = action
                    final = generate_final_feedback(state)
                    st.session_state["final_feedback"] = final
                    st.session_state["session_finished"] = True
                    st.session_state["socratic_active"] = False
                    st.session_state["voice_mode"] = False
                st.session_state["agent_state"] = state
                st.rerun()

        # ── Text input mode ──────────────────────────────────────────────────
        else:
            # Answer input (key includes turn to auto-clear after submission)
            answer = st.text_area("Your answer...", key=f"socratic_answer_{turn}", label_visibility="collapsed",
                                  placeholder="Type your answer here...")

            col_submit, col_end = st.columns([1, 1])

            if col_submit.button("📤 Submit", type="primary", use_container_width=True):
                if answer and answer.strip():
                    if is_non_answer(answer.strip()):
                        with st.spinner("Let me give you a hint…"):
                            state = _handle_non_answer(state, action, current_q, answer.strip(), turn)
                    else:
                        with st.spinner("Evaluating your answer..."):
                            state = _process_answer(state, action, current_q, answer.strip(), turn)
                    st.session_state["agent_state"] = state
                    st.rerun()

            if col_end.button("🛑 End debate", use_container_width=True):
                with st.spinner("Generating final feedback..."):
                    state["current_action"] = action
                    final = generate_final_feedback(state)
                    st.session_state["final_feedback"] = final
                    st.session_state["session_finished"] = True
                    st.session_state["socratic_active"] = False
                st.session_state["agent_state"] = state
                st.rerun()

        st.divider()

    # ── Pending actions (not in socratic mode) ───────────────────────────────
    if not socratic_active and not session_finished:
        if not pending:
            st.markdown("""
<div style="
    background:linear-gradient(145deg,#1a2e1a,#162e16);
    border:1px solid rgba(85,239,196,0.25); border-radius:14px;
    padding:1.25rem 1.5rem; text-align:center; color:#55efc4;
    font-size:0.95rem; font-weight:600;
">🎉 No pending actions — great work!</div>
""", unsafe_allow_html=True)
        else:
            st.markdown("""
<style>
.ac-card {
    display:flex; align-items:stretch;
    background:linear-gradient(145deg,#1e1e2e,#16213e);
    border:1px solid rgba(255,255,255,0.07);
    border-radius:14px; overflow:hidden; margin-bottom:0.6rem;
}
.ac-accent { width:4px; flex-shrink:0; }
.ac-body { flex:1; padding:0.9rem 1.25rem; }
.ac-header { display:flex; align-items:center; gap:0.5rem; margin-bottom:0.35rem; }
.ac-icon { font-size:1.15rem; line-height:1; }
.ac-type { font-size:0.7rem; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; }
.ac-badge {
    margin-left:auto; font-size:0.65rem; font-weight:700;
    padding:2px 9px; border-radius:10px;
    background:rgba(255,255,255,0.07);
}
.ac-reason { font-size:0.85rem; color:#b0b0c0; line-height:1.5; }
.ac-response-tutor {
    background:linear-gradient(135deg,rgba(116,185,255,0.08),rgba(162,155,254,0.06));
    border:1px solid rgba(116,185,255,0.22); border-radius:12px;
    padding:1rem 1.25rem; margin:0.4rem 0 0.8rem; font-size:0.9rem; color:#d0d8f0; line-height:1.6;
}
.ac-response-peer {
    background:linear-gradient(135deg,rgba(162,155,254,0.1),rgba(85,239,196,0.06));
    border:1px solid rgba(162,155,254,0.28); border-radius:12px;
    padding:1rem 1.25rem; margin:0.4rem 0 0.8rem; font-size:0.9rem; color:#d0d8f0; line-height:1.6;
}
.ac-gs-wrap {
    background:linear-gradient(145deg,#1a1a2e,#16213e);
    border:1px solid rgba(162,155,254,0.2); border-radius:14px;
    padding:1.25rem 1.25rem 0.75rem; margin:0.4rem 0 0.8rem;
}
</style>
""", unsafe_allow_html=True)

            st.markdown("### Suggested Actions")

            _pinned = st.session_state.get("pinned_response", {})
            _gs_action_id = st.session_state.get("goal_selector_action_id")

            for i, action in enumerate(pending[:6]):
                action_id = (action.action_type, action.target_topic_id)
                meta = ACTION_META.get(action.action_type, {
                    "icon": "▪️",
                    "label": action.action_type.replace("_", " ").title(),
                    "color": "#888888",
                })
                priority = getattr(action, "priority", 0.5)
                if priority >= 0.8:
                    badge_text, badge_color = "High priority", "#ff7675"
                elif priority >= 0.6:
                    badge_text, badge_color = "Medium", "#fdcb6e"
                else:
                    badge_text, badge_color = "Low", "#636e72"

                _has_inline = (_pinned.get("action_id") == action_id) or (_gs_action_id == action_id)

                col_card, col_btn = st.columns([6, 1], vertical_alignment="center")
                with col_card:
                    st.markdown(f"""
<div class="ac-card">
  <div class="ac-accent" style="background:{meta['color']};"></div>
  <div class="ac-body">
    <div class="ac-header">
      <span class="ac-icon">{meta['icon']}</span>
      <span class="ac-type" style="color:{meta['color']};">{meta['label']}</span>
      <span class="ac-badge" style="color:{badge_color};">{badge_text}</span>
    </div>
    <div class="ac-reason">{action.reason}</div>
  </div>
</div>""", unsafe_allow_html=True)

                with col_btn:
                    if not _has_inline:
                        if st.button("Accept →", key=f"btn_{i}_{action.target_topic_id}", type="primary", use_container_width=True):
                            action.accepted = True
                            state["current_action"] = action

                            if action.action_type in ("introduce_topic", "fill_gap", "review_prerequisites"):
                                with st.spinner("Tutor thinking…"):
                                    state = tutor_node(state)
                                tutor_msgs = [m for m in state.get("messages", []) if m.get("source") == "tutor"]
                                content = tutor_msgs[-1]["content"] if tutor_msgs else ""
                                st.session_state["pinned_response"] = {"action_id": action_id, "rtype": "tutor", "content": content}
                                st.session_state["agent_state"] = state
                                st.rerun()

                            elif action.action_type == "quiz_topic":
                                st.session_state["pending_quiz_action"] = action
                                st.session_state["goal_selector_action_id"] = action_id
                                st.session_state["agent_state"] = state
                                st.rerun()

                            elif action.action_type == "peer_match":
                                with st.spinner("Finding peer match…"):
                                    state = peer_matcher_node(state)
                                pm = state.get("peer_match")
                                content = pm["reason"] if pm else "No match found at the moment."
                                st.session_state["pinned_response"] = {"action_id": action_id, "rtype": "peer_match", "content": content}
                                st.session_state["agent_state"] = state
                                st.rerun()

                # ── Inline response: tutor or peer_match ─────────────────────
                if _pinned.get("action_id") == action_id:
                    rtype = _pinned.get("rtype")
                    content = _pinned.get("content", "")
                    if rtype == "tutor":
                        st.markdown(f'<div class="ac-response-tutor">📖 {content}</div>', unsafe_allow_html=True)
                    elif rtype == "peer_match":
                        st.markdown(f'<div class="ac-response-peer">🤝 <strong>Peer Match Found!</strong><br>{content}</div>', unsafe_allow_html=True)
                    if st.button("✓ Got it", key=f"dismiss_{i}_{action.target_topic_id}", use_container_width=False):
                        st.session_state.pop("pinned_response", None)
                        st.rerun()

                # ── Inline goal selector: quiz ────────────────────────────────
                if _gs_action_id == action_id:
                    st.markdown('<div class="ac-gs-wrap">', unsafe_allow_html=True)
                    st.markdown("**🎯 What is your goal for this debate?**")
                    st.caption("The final feedback will be tailored to your learning objective.")
                    st.markdown('</div>', unsafe_allow_html=True)

                    col_g1, col_g2, col_g3 = st.columns(3)
                    for col, goal, label, desc in [
                        (col_g1, "exam", "📝 Exam", "Precision and completeness — as in an exam."),
                        (col_g2, "study", "📚 Study", "Conceptual depth and clarity."),
                        (col_g3, "work", "💼 Work", "Practical application and problem-solving."),
                    ]:
                        with col:
                            with st.container(border=True):
                                st.markdown(f"### {label}")
                                st.caption(desc)
                                if st.button(f"Choose {label}", key=f"goal_{goal}", use_container_width=True):
                                    _qa = st.session_state["pending_quiz_action"]
                                    state["student_goal"] = goal
                                    state["current_action"] = _qa
                                    state["session_topic_id"] = _qa.target_topic_id
                                    state["socratic_session"] = []
                                    state["socratic_turn"] = 0
                                    state["voice_used_in_session"] = False

                                    from agent.evaluator import _get_current_mastery, _difficulty_for_mastery
                                    mastery = _get_current_mastery(state, _qa.target_topic_id)
                                    state["current_difficulty"] = _difficulty_for_mastery(mastery)

                                    with st.spinner("Starting the debate…"):
                                        question = generate_question(state)

                                    st.session_state["current_question"] = question
                                    st.session_state["quiz_action"] = _qa
                                    st.session_state["socratic_active"] = True
                                    st.session_state.pop("goal_selector_action_id", None)
                                    st.session_state.pop("pending_quiz_action", None)
                                    st.session_state["agent_state"] = state
                                    st.rerun()
