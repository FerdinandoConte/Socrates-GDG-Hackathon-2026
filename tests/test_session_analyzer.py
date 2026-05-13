import pytest
from agent.state import TopicMastery, MasteryZone
from agent.session_analyzer import detect_patterns

def test_detect_deep_dive():
    km = [
        TopicMastery(
            topic_id="t1",
            topic_name="Deep Topic",
            page_range=(1, 5),
            keywords_count=5,
            notes_count=1,
            chats_count=0,
            fsrs_avg_difficulty=0.0,
            fsrs_total_lapses=0,
            fsrs_total_reps=0,
            mastery_zone=MasteryZone.STUDIED
        )
    ]
    patterns = detect_patterns([], km)
    assert len(patterns) == 1
    assert patterns[0].pattern_type == "deep_dive"

def test_detect_topic_skip():
    km = [
        TopicMastery(
            topic_id="t1", topic_name="T1", page_range=(1, 2), keywords_count=1, notes_count=0, chats_count=0, mastery_zone=MasteryZone.SKIMMED,
            fsrs_total_reps=0, fsrs_total_lapses=0, fsrs_avg_difficulty=0.0
        ),
        TopicMastery(
            topic_id="t2", topic_name="T2", page_range=(3, 4), keywords_count=0, notes_count=0, chats_count=0, mastery_zone=MasteryZone.UNEXPLORED,
            fsrs_total_reps=0, fsrs_total_lapses=0, fsrs_avg_difficulty=0.0
        ),
        TopicMastery(
            topic_id="t3", topic_name="T3", page_range=(5, 6), keywords_count=1, notes_count=0, chats_count=0, mastery_zone=MasteryZone.SKIMMED,
            fsrs_total_reps=0, fsrs_total_lapses=0, fsrs_avg_difficulty=0.0
        )
    ]
    patterns = detect_patterns([], km)
    assert len(patterns) == 1
    assert patterns[0].pattern_type == "topic_skip"

def test_detect_long_pause():
    timeline = [
        {"timestamp": 1000000, "datetime": "2026-05-10 10:00"},
        {"timestamp": 1000000 + (35 * 60 * 1000), "datetime": "2026-05-10 10:35"} # 35 min gap
    ]
    patterns = detect_patterns(timeline, [])
    assert len(patterns) == 1
    assert patterns[0].pattern_type == "long_pause"
