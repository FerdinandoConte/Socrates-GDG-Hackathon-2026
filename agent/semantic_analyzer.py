from cache_paths import domain_classification_cache, topic_dependency_cache
from .llm import call_llm_structured
from .schemas import DomainClassification, TopicDependencyGraph

CLASSIFICATION_SYSTEM_MESSAGE = """Classify the document as 'stem' or 'humanities' based on its headings and content."""

TOPIC_DEPENDENCY_SYSTEM_MESSAGE = """Extract topics and dependencies from these document headings.
Rules:
- Assign sequential ids: t1, t2, t3, ...
- page_range: [start, end] inclusive. Each topic ends where the next begins minus 1.
- The last topic ends at page {total_pages}.
- dependencies: topic A is a prerequisite of B if understanding B requires A."""

def _headings_text(raw_metadata: dict) -> str:
    book = raw_metadata["books"][0]
    lines = []
    for h in book.get("headings", []):
        indent = "  " * h.get("indentLevel", 0)
        lines.append(f"{indent}- {h['title']} (page {h['pageNumber']})")
    return "\n".join(lines)


def _sample_content(raw_metadata: dict) -> str:
    book = raw_metadata["books"][0]
    kws = [k["text"] for k in book.get("keywords", [])[:10]]
    notes = [n["text"][:120] for n in book.get("notes", [])[:3]]
    parts = ["Keywords: " + ", ".join(kws)]
    if notes:
        parts.append("Notes: " + " | ".join(notes))
    return "\n".join(parts)


def semantic_analyzer_node(state: dict) -> dict:
    headings = _headings_text(state["raw_metadata"])
    sample = _sample_content(state["raw_metadata"])
    total_pages = state["raw_metadata"]["books"][0].get("pages", 12)

    class_user_message = f"Headings:\n{headings}\n\nContent sample:\n{sample}"
    class_cache_key = (class_user_message, CLASSIFICATION_SYSTEM_MESSAGE)
    if class_cache_key in domain_classification_cache:
        classification = domain_classification_cache.get(class_cache_key)
    else:
        classification: DomainClassification = call_llm_structured(
            system_prompt=CLASSIFICATION_SYSTEM_MESSAGE,
            user_message=class_user_message,
            schema=DomainClassification,
        )
        domain_classification_cache.set(key=class_cache_key, value=classification)

    fmtd_sys_msg = TOPIC_DEPENDENCY_SYSTEM_MESSAGE.format(total_pages=total_pages)
    topic_dependency_user_message = f"Headings:\n{headings}"
    topic_dep_cache_key = (topic_dependency_user_message, fmtd_sys_msg)
    if topic_dep_cache_key in topic_dependency_cache:
        graph = topic_dependency_cache.get(topic_dep_cache_key)
    else:
        graph: TopicDependencyGraph = call_llm_structured(
            system_prompt=fmtd_sys_msg,
            user_message=topic_dependency_user_message,
            schema=TopicDependencyGraph,
        )
        topic_dependency_cache.set(key=topic_dep_cache_key, value=graph)

    return {
        **state,
        "document_domain": str(classification.domain),
        "topic_list": [t.model_dump() for t in graph.topics],
        "dependency_graph": graph.dependencies,
    }
