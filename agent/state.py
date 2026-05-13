from typing import TypedDict
from pydantic import BaseModel
from enum import StrEnum


class MasteryZone(StrEnum):
    UNEXPLORED = "unexplored"
    SKIMMED = "skimmed"
    STUDIED = "studied"
    STRUGGLING = "struggling"
    CONSOLIDATING = "consolidating"
    MASTERED = "mastered"


class TopicMastery(BaseModel):
    topic_id: str
    topic_name: str
    page_range: tuple[int, int]
    keywords_count: int
    notes_count: int
    chats_count: int
    fsrs_avg_difficulty: float
    fsrs_total_lapses: int
    fsrs_total_reps: int
    mastery_zone: MasteryZone


class BehavioralPattern(BaseModel):
    pattern_type: str
    details: str
    topic_ids: list[str]
    confidence: float


class PendingAction(BaseModel):
    action_type: str
    target_topic_id: str
    reason: str
    priority: float
    accepted: bool | None = None
    prerequisite_topic_ids: list[str] = []


class AgentState(TypedDict):
    raw_metadata: dict
    document_domain: str
    topic_list: list[dict]
    dependency_graph: dict
    session_timeline: list[dict]
    behavioral_patterns: list[BehavioralPattern]
    knowledge_map: list[TopicMastery]
    pending_actions: list[PendingAction]
    current_action: PendingAction | None
    peer_pool: list[dict]
    peer_match: dict | None
    messages: list[dict]
    difficulty_level: str
    # Socratic session fields
    socratic_session: list[dict]     # [{"role": "agent"|"user", "content": "..."}]
    socratic_turn: int               # Current turn (0-6, max 7)
    current_difficulty: str          # Current difficulty level
    session_topic_id: str | None     # Active topic in the socratic session
    student_goal: str                # "work" | "study" | "exam"
    # Speech-to-Text fields
    voice_used_in_session: bool      # Whether the student used voice at least once
