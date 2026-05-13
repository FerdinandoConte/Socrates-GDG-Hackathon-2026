from .state import PendingAction, MasteryZone
from .session_analyzer import detect_over_struggling


def build_pending_actions(state: dict) -> list[PendingAction]:
    knowledge_map = state.get("knowledge_map", [])
    dependency_graph = state.get("dependency_graph", {})
    actions: list[PendingAction] = []

    for entry in detect_over_struggling(knowledge_map, dependency_graph):
        topic = entry["topic"]
        weak = entry["weak_prerequisites"]
        actions.append(PendingAction(
            action_type="review_prerequisites",
            target_topic_id=topic.topic_id,
            reason=f"You're struggling with '{topic.topic_name}' — the prerequisite '{weak[0].topic_name}' may not be solid yet.",
            priority=1.0,
            prerequisite_topic_ids=[p.topic_id for p in weak],
        ))

    explored = {tm.topic_id for tm in knowledge_map if tm.mastery_zone != MasteryZone.UNEXPLORED}

    for tm in knowledge_map:
        if tm.mastery_zone == MasteryZone.STRUGGLING:
            actions.append(PendingAction(
                action_type="quiz_topic",
                target_topic_id=tm.topic_id,
                reason=f"You've been struggling with '{tm.topic_name}'. A Socratic debate from a different angle might help.",
                priority=0.85,
            ))

    for tm in knowledge_map:
        if tm.mastery_zone == MasteryZone.CONSOLIDATING:
            actions.append(PendingAction(
                action_type="quiz_topic",
                target_topic_id=tm.topic_id,
                reason=f"You're consolidating '{tm.topic_name}'. A Socratic debate can strengthen your understanding.",
                priority=0.75,
            ))

    for tm in knowledge_map:
        if tm.mastery_zone != MasteryZone.UNEXPLORED:
            continue
        prereqs = dependency_graph.get(tm.topic_id, [])
        prereqs_met = all(pid in explored for pid in prereqs)
        actions.append(PendingAction(
            action_type="introduce_topic",
            target_topic_id=tm.topic_id,
            reason=f"You haven't explored '{tm.topic_name}' yet.",
            priority=0.7 if prereqs_met else 0.3,
        ))

    struggling = [tm for tm in knowledge_map if tm.mastery_zone == MasteryZone.STRUGGLING]
    if struggling and state.get("peer_pool"):
        actions.append(PendingAction(
            action_type="peer_match",
            target_topic_id=struggling[0].topic_id,
            reason=f"Connect with a peer who has mastered '{struggling[0].topic_name}'.",
            priority=0.6,
        ))

    actions.sort(key=lambda a: a.priority, reverse=True)
    return actions


def orchestrator_node(state: dict) -> dict:
    accepted_pairs = {(a.action_type, a.target_topic_id) for a in state.get("pending_actions", []) if a.accepted is True}
    pending = [a for a in build_pending_actions(state) if (a.action_type, a.target_topic_id) not in accepted_pairs]
    return {**state, "pending_actions": pending, "current_action": None}


def route_decision(state: dict) -> str:
    action = state.get("current_action")
    if not action or not action.accepted:
        return "end"
    if action.action_type in ("introduce_topic", "fill_gap", "review_prerequisites"):
        return "tutor"
    if action.action_type == "quiz_topic":
        return "evaluator"
    if action.action_type == "peer_match":
        return "peer_matcher"
    return "end"
