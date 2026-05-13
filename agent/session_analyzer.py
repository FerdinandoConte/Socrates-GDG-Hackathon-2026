from collections import defaultdict
from datetime import datetime
from .state import TopicMastery, BehavioralPattern, MasteryZone


def _ts(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000)


def build_timeline(raw_metadata: dict) -> list[dict]:
    book = raw_metadata["books"][0]
    events: list[dict] = []

    for kw in book.get("keywords", []):
        events.append({"type": "keyword", "timestamp": kw["createdAt"], "text": kw.get("text", ""), "page": kw.get("pageNo"), "icon": "📌"})

    for note in book.get("notes", []):
        events.append({"type": "note", "timestamp": note["createdAt"], "text": note.get("text", "")[:80], "page": note.get("pageNo"), "icon": "📝"})

    for chat in book.get("chats", []):
        events.append({"type": "chat", "timestamp": chat["createdAt"], "text": chat.get("title", "AI Chat"), "page": None, "icon": "💬"})

    for q in book.get("questions", []):
        events.append({"type": "flashcard", "timestamp": q["createdAt"], "text": q.get("text", "")[:60], "page": q.get("pageNo"), "icon": "🃏"})
        for r in q.get("results", []):
            events.append({"type": "review", "timestamp": r["time"], "text": f"Review — rating {r['rating']}", "page": q.get("pageNo"), "icon": "🔄"})

    events.sort(key=lambda e: e["timestamp"])
    for e in events:
        e["datetime"] = _ts(e["timestamp"]).strftime("%Y-%m-%d %H:%M")
    return events


def _page_topic(page: int | None, topic_list: list[dict]) -> str | None:
    if page is None:
        return None
    for t in topic_list:
        s, e = t["page_range"]
        if s <= page <= e:
            return t["id"]
    return None


def _chat_page(chat: dict, reading_sessions: list[dict]) -> int | None:
    ts = chat.get("createdAt", 0)
    for rs in reading_sessions:
        if rs.get("startTime", 0) <= ts <= rs.get("endTime", 0):
            return rs.get("pageNo")
    return None


def build_knowledge_map(raw_metadata: dict, topic_list: list[dict]) -> list[TopicMastery]:
    book = raw_metadata["books"][0]
    rs_list = book.get("readingSessions", [])
    results = []

    for topic in topic_list:
        tid = topic["id"]
        ps, pe = topic["page_range"]

        kw_count = sum(1 for kw in book.get("keywords", []) if ps <= (kw.get("pageNo") or -1) <= pe)
        note_count = sum(1 for n in book.get("notes", []) if ps <= (n.get("pageNo") or -1) <= pe)

        chat_count = 0
        for ch in book.get("chats", []):
            pg = _chat_page(ch, rs_list)
            if pg is not None and ps <= pg <= pe:
                chat_count += 1

        flashcards = [q for q in book.get("questions", []) if ps <= (q.get("pageNo") or -1) <= pe]
        cards = [q["Card"] for q in flashcards if q.get("Card")]

        fsrs_avg_diff = sum(c["difficulty"] for c in cards) / len(cards) if cards else 0.0
        fsrs_total_reps = sum(c["reps"] for c in cards) if cards else 0
        fsrs_total_lapses = sum(c["lapses"] for c in cards) if cards else 0

        mastery = _compute_mastery(kw_count, note_count, chat_count, fsrs_total_lapses, fsrs_avg_diff, fsrs_total_reps)

        results.append(TopicMastery(
            topic_id=tid,
            topic_name=topic["name"],
            page_range=(ps, pe),
            keywords_count=kw_count,
            notes_count=note_count,
            chats_count=chat_count,
            fsrs_avg_difficulty=round(fsrs_avg_diff, 2),
            fsrs_total_lapses=fsrs_total_lapses,
            fsrs_total_reps=fsrs_total_reps,
            mastery_zone=mastery,
        ))

    return results


def _compute_mastery(kw: int, notes: int, chats: int, lapses: int, avg_diff: float, reps: int) -> MasteryZone:
    if kw == 0 and notes == 0:
        return MasteryZone.UNEXPLORED
    if kw > 0 and notes == 0 and chats == 0 and reps == 0:
        return MasteryZone.SKIMMED
    if reps >= 5 and lapses == 0 and avg_diff <= 4.0:
        return MasteryZone.MASTERED
    if lapses > 0 or avg_diff > 6.0:
        return MasteryZone.STRUGGLING
    if reps > 0:
        return MasteryZone.CONSOLIDATING
    return MasteryZone.STUDIED


def detect_patterns(timeline: list[dict], knowledge_map: list[TopicMastery]) -> list[BehavioralPattern]:
    patterns: list[BehavioralPattern] = []

    for tm in knowledge_map:
        if tm.keywords_count >= 5 and (tm.notes_count >= 1 or tm.chats_count >= 1):
            patterns.append(BehavioralPattern(
                pattern_type="deep_dive",
                details=f"Dense engagement on '{tm.topic_name}': {tm.keywords_count} keywords + notes/chats",
                topic_ids=[tm.topic_id],
                confidence=0.9,
            ))

    for i, tm in enumerate(knowledge_map):
        if tm.mastery_zone == MasteryZone.UNEXPLORED and 0 < i < len(knowledge_map) - 1:
            prev_ok = any(knowledge_map[j].mastery_zone != MasteryZone.UNEXPLORED for j in range(i))
            next_ok = any(knowledge_map[j].mastery_zone != MasteryZone.UNEXPLORED for j in range(i + 1, len(knowledge_map)))
            if prev_ok and next_ok:
                patterns.append(BehavioralPattern(
                    pattern_type="topic_skip",
                    details=f"'{tm.topic_name}' (pp. {tm.page_range[0]}-{tm.page_range[1]}) skipped between studied sections",
                    topic_ids=[tm.topic_id],
                    confidence=0.85,
                ))

    for i in range(1, len(timeline)):
        gap_min = (timeline[i]["timestamp"] - timeline[i - 1]["timestamp"]) / 60000
        if gap_min > 30:
            patterns.append(BehavioralPattern(
                pattern_type="long_pause",
                details=f"{int(gap_min)} min gap between {timeline[i-1]['datetime']} and {timeline[i]['datetime']}",
                topic_ids=[],
                confidence=0.95,
            ))

    struggle_ids = defaultdict(int)
    for tm in knowledge_map:
        if tm.fsrs_avg_difficulty > 5.0 and tm.fsrs_total_reps > 0:
            struggle_ids[tm.topic_id] += 1
    if struggle_ids:
        names = [tm.topic_name for tm in knowledge_map if tm.topic_id in struggle_ids]
        patterns.append(BehavioralPattern(
            pattern_type="spaced_repetition_struggle",
            details=f"High-difficulty flashcards on: {', '.join(names)}",
            topic_ids=list(struggle_ids.keys()),
            confidence=0.8,
        ))

    return patterns


def detect_over_struggling(knowledge_map: list[TopicMastery], dependency_graph: dict) -> list[dict]:
    results = []
    for topic in knowledge_map:
        if topic.mastery_zone != MasteryZone.STRUGGLING:
            continue
        if topic.fsrs_total_reps < 3 or topic.fsrs_avg_difficulty <= 6.5:
            continue
        prereq_ids = dependency_graph.get(topic.topic_id, [])
        weak = [t for t in knowledge_map if t.topic_id in prereq_ids and t.mastery_zone in (MasteryZone.UNEXPLORED, MasteryZone.SKIMMED, MasteryZone.STRUGGLING)]
        if weak:
            results.append({"topic": topic, "weak_prerequisites": weak})
    return results


def session_analyzer_node(state: dict) -> dict:
    timeline = build_timeline(state["raw_metadata"])
    knowledge_map = build_knowledge_map(state["raw_metadata"], state["topic_list"])
    patterns = detect_patterns(timeline, knowledge_map)
    return {**state, "session_timeline": timeline, "behavioral_patterns": patterns, "knowledge_map": knowledge_map}
