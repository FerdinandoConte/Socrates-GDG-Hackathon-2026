from .llm import call_llm
from .state import MasteryZone


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


def tutor_node(state: dict) -> dict:
    action = state["current_action"]
    km = state.get("knowledge_map", [])
    topic_list = state.get("topic_list", [])
    raw = state.get("raw_metadata", {})
    studied = [tm.topic_name for tm in km if tm.mastery_zone not in (MasteryZone.UNEXPLORED, MasteryZone.SKIMMED)]

    if action.action_type == "review_prerequisites":
        prereq_id = action.prerequisite_topic_ids[0] if action.prerequisite_topic_ids else ""
        prereq = next((t for t in topic_list if t["id"] == prereq_id), None)
        struggling = next((t for t in topic_list if t["id"] == action.target_topic_id), None)
        prereq_name = prereq["name"] if prereq else "the prerequisite"
        struggling_name = struggling["name"] if struggling else "this topic"

        response = call_llm(
            system_prompt=(
                f'You are a tutor. The student is struggling with "{struggling_name}" '
                f'and the likely root cause is a weak prerequisite: "{prereq_name}".\n\n'
                f"Do three things:\n"
                f'1. Briefly recall the key concepts of "{prereq_name}" (2-3 sentences)\n'
                f'2. Show explicitly how these concepts are needed to understand "{struggling_name}"\n'
                f"3. Ask the student to explain the connection in their own words\n\n"
                f"Student already knows: {', '.join(studied) or 'nothing yet'}.\n"
                f"Prerequisite content: {_section_content(raw, prereq_id, topic_list)}\n"
                f"Struggling topic content: {_section_content(raw, action.target_topic_id, topic_list)}\n"
                f"Always reply in English."
            ),
            user_message="Give me the prerequisite review.",
        )
    else:
        topic = next((t for t in topic_list if t["id"] == action.target_topic_id), None)
        topic_name = topic["name"] if topic else action.target_topic_id
        content = _section_content(raw, action.target_topic_id, topic_list)

        response = call_llm(
            system_prompt=(
                f'You are a tutor. Introduce "{topic_name}" intuitively.\n'
                f"Use everyday analogies. Max 3-4 sentences. End with a thought-provoking question.\n"
                f"Student already knows: {', '.join(studied) or 'nothing yet'}.\n"
                f"Section content: {content}\n"
                f"Always reply in English."
            ),
            user_message=f"Introduce '{topic_name}'.",
        )

    messages = list(state.get("messages", []))
    messages.append({"role": "assistant", "content": response, "source": "tutor"})
    return {**state, "messages": messages}
