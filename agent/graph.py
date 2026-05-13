from langgraph.graph import StateGraph, END
from .state import AgentState
from .semantic_analyzer import semantic_analyzer_node
from .session_analyzer import session_analyzer_node
from .orchestrator import orchestrator_node, route_decision
from .tutor import tutor_node
from .evaluator import evaluator_node
from .peer_matcher import peer_matcher_node


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("semantic_analyzer", semantic_analyzer_node)
    graph.add_node("session_analyzer", session_analyzer_node)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("tutor", tutor_node)
    graph.add_node("evaluator", evaluator_node)
    graph.add_node("peer_matcher", peer_matcher_node)

    graph.set_entry_point("semantic_analyzer")
    graph.add_edge("semantic_analyzer", "session_analyzer")
    graph.add_edge("session_analyzer", "orchestrator")

    graph.add_conditional_edges(
        "orchestrator",
        route_decision,
        {"tutor": "tutor", "evaluator": "evaluator", "peer_matcher": "peer_matcher", "end": END},
    )

    graph.add_edge("tutor", "orchestrator")
    graph.add_edge("evaluator", "orchestrator")
    graph.add_edge("peer_matcher", "orchestrator")

    return graph.compile()
