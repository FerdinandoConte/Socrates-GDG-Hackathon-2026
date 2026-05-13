from .session_analyzer import build_knowledge_map
from .state import MasteryZone, TopicMastery


def find_match(user_map: list[TopicMastery], peer_map: list[TopicMastery]) -> dict | None:
    for ut in user_map:
        if ut.mastery_zone != MasteryZone.STRUGGLING:
            continue
        u_start, u_end = ut.page_range
        for pt in peer_map:
            p_start, p_end = pt.page_range
            pages_overlap = u_start <= p_end and p_start <= u_end
            if pages_overlap and pt.mastery_zone in (MasteryZone.MASTERED, MasteryZone.CONSOLIDATING):
                return {
                    "topic": ut.topic_name,
                    "reason": f"You're struggling with '{ut.topic_name}' — your peer has mastered it and could help.",
                }
    return None


def peer_matcher_node(state: dict) -> dict:
    peer_pool = state.get("peer_pool", [])
    if not peer_pool:
        return {**state, "peer_match": None}

    user_map = state.get("knowledge_map", [])
    peer_map = peer_pool[0]["marco"]["knowledge_map"] # FOR DEMO ONLY
    match = find_match(user_map, peer_map)
    return {**state, "peer_match": match}
