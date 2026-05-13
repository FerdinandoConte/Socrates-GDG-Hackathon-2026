from pydantic import BaseModel, Field

from .llm import call_llm, call_llm_structured
from .schemas import InternalEvaluation, FinalSessionFeedback, StudentGoal, VoiceAnalysis
from .state import MasteryZone, TopicMastery
from .speech import format_voice_metadata

# ── Difficulty levels (ordered by complexity) ────────────────────────────────
DIFFICULTY_LEVELS = ["recognition", "recall", "recall_angled", "application", "transfer"]

MASTERY_TO_DIFFICULTY = {
    MasteryZone.SKIMMED: "recognition",
    MasteryZone.STUDIED: "recall",
    MasteryZone.STRUGGLING: "recall_angled",
    MasteryZone.CONSOLIDATING: "application",
    MasteryZone.MASTERED: "transfer",
}

DIFFICULTY_DESCRIPTION = {
    "recognition": "multiple choice / recognition question (easy)",
    "recall": "open-ended simple recall question",
    "recall_angled": "open-ended question from a different angle",
    "application": "application scenario question",
    "transfer": "transfer to a different domain question (hard)",
}

# ── Non-answer detection ─────────────────────────────────────────────────────

_NON_ANSWER_PATTERNS = frozenset([
    "i don't know", "i dont know", "idk", "no idea", "can't say", "cannot say",
    "not sure", "i'm not sure", "im not sure", "don't know", "dont know",
    "dunno", "no clue", "i have no idea", "pass", "skip", "no answer",
    "i don't know the answer", "i have no answer", "i do not know",
    "i am not sure", "i'm unsure", "unsure", "i don't have an answer",
    "i have no clue", "beats me", "no clue whatsoever",
])


def is_non_answer(text: str) -> bool:
    normalized = text.strip().lower().rstrip(".,!? ")
    return normalized in _NON_ANSWER_PATTERNS


class HintResponse(BaseModel):
    hint: str = Field(description="Brief encouraging hint (2-3 sentences) that nudges toward understanding without giving the answer away")
    follow_up_question: str = Field(description="A simpler rephrasing or scaffolding question to help the student approach the concept")


def generate_hint(state: dict, question: str) -> HintResponse:
    action = state["current_action"]
    topic_list = state.get("topic_list", [])
    raw = state.get("raw_metadata", {})
    topic = next((t for t in topic_list if t["id"] == action.target_topic_id), None)
    topic_name = topic["name"] if topic else action.target_topic_id
    content = _section_content(raw, action.target_topic_id, topic_list)

    return call_llm_structured(
        system_prompt=(
            f"You are a supportive Socratic tutor. The student admitted they don't know the answer.\n\n"
            f'Topic: "{topic_name}"\n'
            f"Question asked: {question}\n"
            f"Reference content: {content}\n\n"
            f"Instructions:\n"
            f"1. Write a brief, warm hint (2-3 sentences) that nudges the student toward the concept "
            f"without giving the full answer away. Start with an encouraging phrase.\n"
            f"2. Rephrase the question in a simpler or more concrete way to scaffold their thinking.\n"
            f"Always reply in English."
        ),
        user_message="The student said they don't know. Give a hint and a simpler question.",
        schema=HintResponse,
    )


# ── Evaluation categories ─────────────────────────────────────────────────────
STEM_CATEGORIES = [
    "Technical precision",
    "Definition accuracy",
    "Appropriate terminology",
    "Logical reasoning",
    "Completeness of the answer",
]

HUMANITIES_CATEGORIES = [
    "Argument quality",
    "Ability to connect concepts",
    "Critical thinking",
    "Use of textual evidence",
    "Originality of the answer",
]

MAX_TURNS = 7

# ── Goal labels for prompts ──────────────────────────────────────────────────
GOAL_CONTEXT = {
    StudentGoal.EXAM: (
        "The student is preparing for an exam. "
        "Focus on precision, completeness, and the ability to explain concepts clearly under exam conditions."
    ),
    StudentGoal.STUDY: (
        "The student is studying to deepen understanding. "
        "Focus on conceptual clarity, connections between topics, and long-term retention."
    ),
    StudentGoal.WORK: (
        "The student is learning for professional application. "
        "Focus on practical applicability, real-world scenarios, and problem-solving skills."
    ),
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _section_content(raw_metadata: dict, topic_id: str, topic_list: list[dict]) -> str:
    topic = next((t for t in topic_list if t["id"] == topic_id), None)
    if not topic:
        return ""
    ps, pe = topic["page_range"]
    book = raw_metadata["books"][0]
    kws = [kw["text"] for kw in book.get("keywords", []) if ps <= (kw.get("pageNo") or -1) <= pe]
    notes = [n["text"][:200] for n in book.get("notes", []) if ps <= (n.get("pageNo") or -1) <= pe]
    parts = []
    if kws:
        parts.append("Keywords: " + ", ".join(kws[:12]))
    if notes:
        parts.append("Notes: " + " | ".join(notes))
    return "\n".join(parts) or f"Pages {ps}–{pe}"


def _get_current_mastery(state: dict, topic_id: str) -> MasteryZone:
    km = state.get("knowledge_map", [])
    entry = next((tm for tm in km if tm.topic_id == topic_id), None)
    return entry.mastery_zone if entry else MasteryZone.STUDIED


def _difficulty_for_mastery(mastery: MasteryZone) -> str:
    return MASTERY_TO_DIFFICULTY.get(mastery, "recall")


def _format_conversation_history(socratic_session: list[dict]) -> str:
    lines = []
    for msg in socratic_session:
        role = "Socratic Agent" if msg["role"] == "agent" else "Student"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines) if lines else "(no previous conversation)"


# ── Core functions ───────────────────────────────────────────────────────────

def generate_question(state: dict) -> str:
    """Generate the first Socratic question for a topic, based on current mastery."""
    action = state["current_action"]
    topic_list = state.get("topic_list", [])
    raw = state.get("raw_metadata", {})
    domain = state.get("document_domain", "stem")

    topic = next((t for t in topic_list if t["id"] == action.target_topic_id), None)
    topic_name = topic["name"] if topic else action.target_topic_id
    mastery = _get_current_mastery(state, action.target_topic_id)
    difficulty = _difficulty_for_mastery(mastery)
    content = _section_content(raw, action.target_topic_id, topic_list)

    return call_llm(
        system_prompt=(
            f"You are a Socratic learning agent. Your role is to guide the student through "
            f"questions that probe their understanding, not to lecture.\n\n"
            f'Topic: "{topic_name}"\n'
            f"Document domain: {domain}\n"
            f"Difficulty level: {DIFFICULTY_DESCRIPTION.get(difficulty, difficulty)}\n"
            f"Reference content: {content}\n\n"
            f"Generate a single Socratic question at the specified difficulty level.\n"
            f"The question should encourage the student to think and explain, not just recall.\n"
            f"Reply in English with ONLY the question text, nothing else."
        ),
        user_message=f"Generate a {difficulty} Socratic question about '{topic_name}'.",
    )


def evaluate_answer_internal(state: dict, question: str, answer: str) -> InternalEvaluation:
    """Evaluate the student's answer internally (not shown to the student).
    Updates knowledge map and generates the next adaptive follow-up question."""
    action = state["current_action"]
    topic_list = state.get("topic_list", [])
    raw = state.get("raw_metadata", {})
    domain = state.get("document_domain", "stem")
    content = _section_content(raw, action.target_topic_id, topic_list)
    history = _format_conversation_history(state.get("socratic_session", []))

    topic = next((t for t in topic_list if t["id"] == action.target_topic_id), None)
    topic_name = topic["name"] if topic else action.target_topic_id

    categories = STEM_CATEGORIES if domain == "stem" else HUMANITIES_CATEGORIES

    return call_llm_structured(
        system_prompt=(
            f"You are evaluating a student's answer in a Socratic dialogue.\n\n"
            f'Topic: "{topic_name}"\n'
            f"Document domain: {domain}\n"
            f"Reference content: {content}\n\n"
            f"Conversation so far:\n{history}\n\n"
            f"Current question: {question}\n"
            f"Student answer: {answer}\n\n"
            f"Evaluation categories: {', '.join(categories)}\n\n"
            f"Instructions:\n"
            f"1. Assess overall_understanding as 'poor', 'partial', or 'solid'\n"
            f"2. Assign an internal_score (0-100) — this is NOT shown to the student\n"
            f"3. Generate a follow_up_question that:\n"
            f"   - If understanding is 'poor': simplify and approach from a different angle\n"
            f"   - If understanding is 'partial': probe the specific weak area deeper\n"
            f"   - If understanding is 'solid': escalate difficulty or explore connections\n"
            f"   The follow-up should be Socratic — guide, don't lecture.\n"
            f"Always reply in English."
        ),
        user_message="Evaluate the answer and generate a follow-up question.",
        schema=InternalEvaluation,
    )


def evaluate_voice_answer_internal(
    state: dict, question: str, transcription: dict
) -> InternalEvaluation:
    """Evaluate a student's oral answer with voice-specific analysis.
    Receives the transcription with metadata (pauses, confidence) from ElevenLabs."""
    action = state["current_action"]
    topic_list = state.get("topic_list", [])
    raw = state.get("raw_metadata", {})
    domain = state.get("document_domain", "stem")
    content = _section_content(raw, action.target_topic_id, topic_list)
    history = _format_conversation_history(state.get("socratic_session", []))
    voice_meta = format_voice_metadata(transcription)

    topic = next((t for t in topic_list if t["id"] == action.target_topic_id), None)
    topic_name = topic["name"] if topic else action.target_topic_id

    categories = STEM_CATEGORIES if domain == "stem" else HUMANITIES_CATEGORIES

    return call_llm_structured(
        system_prompt=(
            f"You are evaluating a student's ORAL answer in a Socratic dialogue.\n\n"
            f'Topic: "{topic_name}"\n'
            f"Document domain: {domain}\n"
            f"Reference content: {content}\n\n"
            f"Conversation so far:\n{history}\n\n"
            f"Current question: {question}\n\n"
            f"Voice response data:\n{voice_meta}\n\n"
            f"Content evaluation categories: {', '.join(categories)}\n\n"
            f"Instructions:\n"
            f"1. Assess overall_understanding as 'poor', 'partial', or 'solid'\n"
            f"2. Assign an internal_score (0-100) — this is NOT shown to the student\n"
            f"3. Generate a follow_up_question that:\n"
            f"   - If understanding is 'poor': simplify and approach from a different angle\n"
            f"   - If understanding is 'partial': probe the specific weak area deeper\n"
            f"   - If understanding is 'solid': escalate difficulty or explore connections\n"
            f"   If the student hesitated on specific terms, the follow-up should rephrase "
            f"those concepts to help the student articulate them better.\n"
            f"4. Provide voice_analysis with:\n"
            f"   - hesitation_level: assess based on pauses, filler words, reformulations\n"
            f"   - long_pauses_count: number of pauses > 3 seconds\n"
            f"   - imprecise_terms: generic words used instead of correct technical terms\n"
            f"   - expressive_coherence: does the speech follow a logical thread?\n"
            f"Always reply in English."
        ),
        user_message="Evaluate the oral answer, generate a follow-up, and provide voice analysis.",
        schema=InternalEvaluation,
    )


def update_knowledge_map(
    state: dict, evaluation: InternalEvaluation, is_voice: bool = False
) -> list[TopicMastery]:
    """Update the knowledge map for the current topic based on the internal evaluation score.
    For voice answers, a softer penalty is applied (oral hesitation ≠ written failure).
    Returns the updated knowledge map."""
    topic_id = state["current_action"].target_topic_id
    km = list(state.get("knowledge_map", []))
    score = evaluation.internal_score

    # Oral hesitation is not as severe as a written wrong answer
    if is_voice and score < 40:
        score = max(score + 15, 40)

    # Mastery escalation/de-escalation order
    mastery_order = [
        MasteryZone.UNEXPLORED,
        MasteryZone.SKIMMED,
        MasteryZone.STUDIED,
        MasteryZone.STRUGGLING,
        MasteryZone.CONSOLIDATING,
        MasteryZone.MASTERED,
    ]
    # For escalation purposes, define the "positive" progression
    positive_order = [
        MasteryZone.UNEXPLORED,
        MasteryZone.SKIMMED,
        MasteryZone.STUDIED,
        MasteryZone.CONSOLIDATING,
        MasteryZone.MASTERED,
    ]

    updated = []
    for tm in km:
        if tm.topic_id != topic_id:
            updated.append(tm)
            continue

        current = tm.mastery_zone

        if score >= 80 and current in positive_order:
            idx = positive_order.index(current)
            new_zone = positive_order[min(idx + 1, len(positive_order) - 1)]
        elif score < 40:
            new_zone = MasteryZone.STRUGGLING
        else:
            # 40-79: maintain current zone
            new_zone = current

        updated.append(TopicMastery(
            topic_id=tm.topic_id,
            topic_name=tm.topic_name,
            page_range=tm.page_range,
            keywords_count=tm.keywords_count,
            notes_count=tm.notes_count,
            chats_count=tm.chats_count,
            fsrs_avg_difficulty=tm.fsrs_avg_difficulty,
            fsrs_total_lapses=tm.fsrs_total_lapses,
            fsrs_total_reps=tm.fsrs_total_reps + 1,
            mastery_zone=new_zone,
        ))

    return updated


def generate_final_feedback(state: dict) -> FinalSessionFeedback:
    """Generate final session feedback shown to the student at the end of the Socratic dialogue.
    Analyzes the entire conversation history and provides category-based qualitative feedback
    contextualized to the student's goal."""
    action = state["current_action"]
    topic_list = state.get("topic_list", [])
    raw = state.get("raw_metadata", {})
    domain = state.get("document_domain", "stem")
    goal = state.get("student_goal", StudentGoal.STUDY)
    content = _section_content(raw, action.target_topic_id, topic_list)
    history = _format_conversation_history(state.get("socratic_session", []))

    topic = next((t for t in topic_list if t["id"] == action.target_topic_id), None)
    topic_name = topic["name"] if topic else action.target_topic_id

    categories = STEM_CATEGORIES if domain == "stem" else HUMANITIES_CATEGORIES
    # Add voice category if the student used voice during the session
    if state.get("voice_used_in_session", False):
        categories = categories + ["Oral exposition"]
    goal_context = GOAL_CONTEXT.get(goal, GOAL_CONTEXT[StudentGoal.STUDY])

    return call_llm_structured(
        system_prompt=(
            f"You are generating the final feedback for a Socratic learning session.\n\n"
            f'Topic: "{topic_name}"\n'
            f"Document domain: {domain}\n"
            f"Reference content: {content}\n\n"
            f"Complete Socratic dialogue:\n{history}\n\n"
            f"Student's goal: {goal_context}\n\n"
            f"Evaluation categories: {', '.join(categories)}\n\n"
            f"Instructions:\n"
            f"1. For each category, assess the student's level as 'strong', 'adequate', or 'weak' "
            f"with a specific comment based on their answers throughout the dialogue.\n"
            f"2. Identify the weakest_category — the most critical area for improvement.\n"
            f"3. Write an overall_summary — a qualitative paragraph about the student's understanding. "
            f"Do NOT include numeric scores.\n"
            f"4. Write a recommendation contextualized to the student's goal. "
            f"Be specific and actionable.\n\n"
            f"Always reply in English."
        ),
        user_message="Generate the final session feedback.",
        schema=FinalSessionFeedback,
    )


def should_continue_session(state: dict, evaluation: InternalEvaluation) -> bool:
    """Decide whether to continue the Socratic dialogue or stop.
    Returns True if the session should continue."""
    turn = state.get("socratic_turn", 0)
    session = state.get("socratic_session", [])

    # Max 7 turns
    if turn >= MAX_TURNS:
        return False

    # Check for 2 consecutive 'solid' → stop (student has demonstrated understanding)
    recent_evals = [
        msg.get("_evaluation")
        for msg in session
        if msg.get("role") == "user" and msg.get("_evaluation")
    ]
    if len(recent_evals) >= 2:
        last_two = recent_evals[-2:]
        if all(e.get("overall_understanding") == "solid" for e in last_two):
            return False

    # Check for 3 consecutive 'poor' → stop (suggest tutor instead)
    if len(recent_evals) >= 3:
        last_three = recent_evals[-3:]
        if all(e.get("overall_understanding") == "poor" for e in last_three):
            return False

    return True


# ── Node function (for LangGraph, kept for compatibility) ────────────────────

def evaluator_node(state: dict) -> dict:
    question = generate_question(state)
    messages = list(state.get("messages", []))
    messages.append({"role": "assistant", "content": question, "source": "evaluator_question"})
    return {**state, "messages": messages, "current_question": question}
