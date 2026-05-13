# Technical Architecture
**Project:** SOCRATES — Active Learning Agent  
**Version:** POC / Demo Build (GDG Hackathon 2026)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Agent Graph (LangGraph)](#2-agent-graph-langgraph)
3. [Shared State](#3-shared-state-agentstate)
4. [Agent Implementations](#4-agent-implementations)
   - [Semantic Analyzer](#41-semantic-analyzer)
   - [Session Analyzer](#42-session-analyzer)
   - [Tutor](#43-tutor)
   - [Evaluator](#44-evaluator)
   - [Peer Matcher](#45-peer-matcher)
5. [LLM Wrapper](#5-llm-wrapper)
6. [Streamlit Frontend](#6-streamlit-frontend-app)
7. [Project Structure](#7-project-structure)
8. [Dependencies](#8-dependencies)
9. [Implementation Order](#9-implementation-order)

---

## 1. System Overview

Socrates is built as a **single-process, Streamlit-based application** with no separate API server or WebSocket layer. All agents run in-process, orchestrated by a LangGraph `StateGraph`. State is held in memory (Python dict) for the duration of each session — no database is required for the POC.

**POC Constraints:**
- One PDF, one user, one session at a time
- Streamlit as the only frontend (no custom React, no separate API)
- LLM via API (Anthropic Claude or OpenAI GPT-4o), switchable via a wrapper function
- LangGraph for agent orchestration
- Simulated peer matching using two static JSON fixtures
- In-memory state — no persistence between sessions

---

## 2. Agent Graph (LangGraph)

```
Uploaded Document
       │
       ▼
┌──────────────────────┐
│   Semantic Analyzer  │  ← runs once at startup
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│   Session Analyzer   │  ← uses SM's dependency graph
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│     Orchestrator     │  ← conditional router
└──┬──────┬──────┬─────┘
   │      │      │
   ▼      ▼      ▼
Tutor  Evaluator  Peer
                 Matcher
```

```python
from langgraph.graph import StateGraph, END

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
    {
        "tutor": "tutor",
        "evaluator": "evaluator",
        "peer_matcher": "peer_matcher",
        "end": END
    }
)

graph.add_edge("tutor", "orchestrator")
graph.add_edge("evaluator", "orchestrator")
graph.add_edge("peer_matcher", "orchestrator")
```

### Router

```python
def route_decision(state: AgentState) -> str:
    action = state.get("current_action")
    if action is None or not action.accepted:
        return "end"
    if action.action_type in ("introduce_topic", "fill_gap", "review_prerequisites"):
        return "tutor"
    if action.action_type == "quiz_topic":
        return "evaluator"
    if action.action_type == "peer_match":
        return "peer_matcher"
    return "end"
```

---

## 3. Shared State (`AgentState`)

```python
from typing import TypedDict
from pydantic import BaseModel
from enum import StrEnum

class MasteryZone(StrEnum):
    UNEXPLORED     = "unexplored"
    SKIMMED        = "skimmed"
    STUDIED        = "studied"
    STRUGGLING     = "struggling"
    CONSOLIDATING  = "consolidating"
    MASTERED       = "mastered"

class TopicMastery(BaseModel):
    topic_id:             str
    topic_name:           str
    page_range:           tuple[int, int]
    keywords_count:       int
    notes_count:          int
    chats_count:          int
    fsrs_avg_difficulty:  float
    fsrs_total_lapses:    int
    fsrs_total_reps:      int
    mastery_zone:         MasteryZone

class BehavioralPattern(BaseModel):
    pattern_type:  str      # "deep_dive" | "topic_skip" | "long_pause" |
                            # "spaced_repetition_struggle" | "over_struggling"
    details:       str
    topic_ids:     list[str]
    confidence:    float

class PendingAction(BaseModel):
    action_type:             str    # "introduce_topic" | "quiz_topic" |
                                    # "peer_match" | "fill_gap" | "review_prerequisites"
    target_topic_id:         str
    reason:                  str
    priority:                float
    accepted:                bool | None = None
    prerequisite_topic_ids:  list[str] = []

class AgentState(TypedDict):
    raw_metadata:        dict
    # --- Semantic Analyzer outputs ---
    document_domain:     str                    # "stem" | "humanities"
    topic_list:          list[dict]
    dependency_graph:    dict                   # {topic_id: [prerequisite_ids]}
    # --- Session Analyzer outputs ---
    session_timeline:    list[dict]
    behavioral_patterns: list[BehavioralPattern]
    knowledge_map:       list[TopicMastery]
    # --- Action management ---
    pending_actions:     list[PendingAction]
    current_action:      PendingAction | None
    peer_pool:           list[dict]
    peer_match:          dict | None
    messages:            list[dict]
    difficulty_level:    str
```

---

## 4. Agent Implementations

### 4.1 Semantic Analyzer

Runs **once**, immediately after document loading. Performs two LLM calls:

**1 — Domain classification** (`"stem"` or `"humanities"`):  
Used by the Evaluator to calibrate scoring criteria — STEM favours technical precision and exact definitions; Humanities favours argumentation, connections, and critical reasoning.

**2 — Topic dependency graph**:  
Extracts the topic list from document headings and asks the LLM to specify which topics are prerequisites for each other. Result: `{topic_id: [prerequisite_ids]}`.

```python
def semantic_analyzer_node(state: AgentState) -> AgentState:
    headings = extract_headings(state["raw_metadata"])
    sample_content = extract_sample_content(state["raw_metadata"])

    # 1. Domain classification
    domain = call_llm(
        system_prompt=(
            "Classify this document as 'stem' or 'humanities'. "
            "Reply with ONLY one of those two words."
        ),
        user_message=f"Document headings:\n{headings}\n\nContent sample:\n{sample_content}"
    ).strip().lower()

    # 2. Dependency graph
    dep_json = call_llm(
        system_prompt="""Given a list of topics from a document, return a JSON with:
- "topics": list of objects {"id": "...", "name": "...", "page_range": [start, end]}
- "dependencies": object {"topic_id": ["prerequisite_topic_id", ...]}
Topic A is a prerequisite of B if understanding B requires understanding A.
Reply ONLY in JSON.""",
        user_message=f"Topics:\n{headings}"
    )
    parsed = json.loads(dep_json)

    return {
        **state,
        "document_domain":  domain,
        "topic_list":        parsed["topics"],
        "dependency_graph":  parsed["dependencies"],
    }
```

The dependency graph is consumed by:
- **Session Analyzer** — maps annotations to the correct topics; detects over-struggling by cross-referencing struggling topics with weak prerequisites
- **Orchestrator** — prioritises prerequisite review actions when over-struggling is detected
- **Tutor** — explicitly links a fragile prerequisite to the struggling topic

---

### 4.2 Session Analyzer

Single function `analyze_session(raw_json: dict) -> dict` that:

1. **Builds a timeline**: collects all timestamped objects (keywords, notes, chats, flashcards, reviews), and sorts them chronologically
2. **Builds a knowledge map**: for each document section, counts keywords, notes, chats, and FSRS flashcard data
3. **Assigns mastery zones**:

```python
def compute_mastery(topic: TopicMastery) -> MasteryZone:
    if topic.keywords_count == 0 and topic.notes_count == 0:
        return MasteryZone.UNEXPLORED
    if topic.keywords_count > 0 and topic.notes_count == 0 and topic.chats_count == 0:
        return MasteryZone.SKIMMED
    if topic.fsrs_total_lapses > 0 or topic.fsrs_avg_difficulty > 6.0:
        return MasteryZone.STRUGGLING
    if topic.fsrs_total_reps > 0:
        return MasteryZone.CONSOLIDATING
    return MasteryZone.STUDIED
```

4. **Detects behavioural patterns** using simple rule-based logic:
   - `deep_dive`: `keywords ≥ 5` AND `(notes ≥ 1 OR chats ≥ 1)`
   - `topic_skip`: section with zero events between two sections that have events
   - `long_pause`: gap > 30 min between consecutive events
   - `spaced_repetition_struggle`: flashcard ratings of 1–2
   - `over_struggling` — see below

**Over-struggling detection**:

```python
def detect_over_struggling(
    knowledge_map: list[TopicMastery],
    dependency_graph: dict
) -> list[dict]:
    results = []
    for topic in knowledge_map:
        if topic.mastery_zone != MasteryZone.STRUGGLING:
            continue
        if topic.fsrs_total_reps < 3 or topic.fsrs_avg_difficulty <= 6.5:
            continue  # normal struggling, not yet "over"

        prereq_ids = dependency_graph.get(topic.topic_id, [])
        weak_prereqs = [
            t for t in knowledge_map
            if t.topic_id in prereq_ids
            and t.mastery_zone in (
                MasteryZone.UNEXPLORED,
                MasteryZone.SKIMMED,
                MasteryZone.STRUGGLING
            )
        ]
        if weak_prereqs:
            results.append({"topic": topic, "weak_prerequisites": weak_prereqs})
    return results
```

When over-struggling with weak prerequisites is detected, the orchestrator generates a high-priority `review_prerequisites` action. The user-facing message reads:  
*"You are struggling with 'Tiered Isolation' — this may be related to not having consolidated 'Three-Layer Architecture', a connected concept. Would you like to review it first?"*

---

### 4.3 Tutor

Handles three action types via different system prompts.

**For `introduce_topic` and `fill_gap`:**
```
You are a tutor. Introduce "{topic_name}" intuitively.
Use everyday analogies. Max 3–4 sentences. End with a thought-provoking question.
The student has already studied: {studied_topics_list}.
Section content: {section_content}
```

**For `review_prerequisites`:**
```
You are a tutor. The student is struggling with "{struggling_topic}" and you suspect
the problem is a fragile prerequisite: "{prerequisite_topic}".

Your goal:
1. Briefly recall the key concepts of "{prerequisite_topic}" (2–3 sentences)
2. Explicitly show HOW these concepts are needed to understand "{struggling_topic}"
3. Ask the student to explain the connection in their own words

The student already knows: {studied_topics_list}.
Prerequisite content: {prereq_section_content}
Struggling topic content: {struggling_section_content}
```

---

### 4.4 Evaluator

**Step 1 — Question generation**, difficulty calibrated to mastery zone:

| Mastery Zone | Question Type |
|-------------|---------------|
| `skimmed` | Multiple choice (recognition) |
| `studied` | Simple open-ended (recall) |
| `struggling` | Simple open-ended, alternate angle |
| `consolidating` | Applied scenario |
| `mastered` | Cross-domain transfer |

**Step 2 — Response scoring**, domain-aware:

```
Evaluate this response.
Document domain: {document_domain}
Question: {question}
Student's answer: {answer}
Reference content: {section_content}

Evaluation criteria:
- If STEM: technical precision, correctness of definitions, appropriate use of terminology
- If Humanities: quality of argumentation, ability to make connections, critical reasoning

Reply ONLY in JSON:
{"score": 0-100, "feedback": "...", "areas_to_review": ["..."]}
```

#### 4.4.1 Voice Evaluation (Speech-to-Text)

After at least 2 Socratic turns, the agent may propose a voice response. The student records an audio clip, which is transcribed via **ElevenLabs Scribe v1** with word-level timestamps and confidence scores.

The LLM receives additional voice-specific criteria:

```
You are evaluating an ORAL response. In addition to content criteria, analyse:

1. Hesitations: "um", "like", repeated reformulations — genuine uncertainty or normal disfluency?
2. Long pauses (> 3s): reflection (positive) or blockage (negative)?
3. Imprecise terminology: generic words ("that thing", "the concept") instead of specific terms
4. Expository coherence: does the narrative follow a logical thread, or is it fragmented?

Transcription with timestamps: {transcription_with_timestamps}
Low-confidence words: {low_confidence_words}
Detected pauses (> 2s): {detected_pauses}
```

**ElevenLabs integration:**

```python
# agent/speech.py
import requests, os

def transcribe_audio(audio_bytes: bytes) -> dict:
    response = requests.post(
        "https://api.elevenlabs.io/v1/speech-to-text",
        headers={"xi-api-key": os.getenv("ELEVENLABS_API_KEY")},
        files={"file": ("recording.webm", audio_bytes, "audio/webm")},
        data={"model_id": "scribe_v1", "timestamps_granularity": "word"}
    )
    result = response.json()
    return {
        "text":                result["text"],
        "words":               result.get("words", []),
        "detected_pauses":     _extract_pauses(result.get("words", []), threshold=2.0),
        "low_confidence_words": [
            w for w in result.get("words", []) if w.get("confidence", 1) < 0.7
        ],
    }

def _extract_pauses(words: list[dict], threshold: float) -> list[dict]:
    pauses = []
    for i in range(1, len(words)):
        gap = words[i]["start"] - words[i-1]["end"]
        if gap >= threshold:
            pauses.append({
                "after_word":       words[i-1]["text"],
                "before_word":      words[i]["text"],
                "duration_seconds": round(gap, 1)
            })
    return pauses
```

---

### 4.5 Peer Matcher

Loads a second JSON (`data/metadata_peer.json`), runs the same Session Analyzer pipeline, then compares knowledge maps:

```python
def find_match(
    user_map: list[TopicMastery],
    peer_map: list[TopicMastery]
) -> dict | None:
    for u in user_map:
        if u.mastery_zone != MasteryZone.STRUGGLING:
            continue
        for p in peer_map:
            if p.topic_id == u.topic_id and p.mastery_zone in (
                MasteryZone.MASTERED, MasteryZone.CONSOLIDATING
            ):
                return {
                    "topic":  u.topic_name,
                    "reason": f"You are struggling with '{u.topic_name}'; "
                              f"your peer has mastered it."
                }
    return None
```

---

## 5. LLM Wrapper

```python
# agent/llm.py
import os
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

def get_llm():
    if os.getenv("ANTHROPIC_API_KEY"):
        return ChatAnthropic(model="claude-sonnet-4-20250514")
    return ChatOpenAI(model="gpt-4o")

def call_llm(system_prompt: str, user_message: str) -> str:
    llm = get_llm()
    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_message},
    ])
    return response.content
```

The wrapper is intentionally minimal — switching LLM providers requires only changing the relevant environment variable.

---

## 6. Streamlit Frontend (`app.py`)

The UI is organised across three logical screens rendered in a single Streamlit app:

**Screen 1 — Study Timeline**  
Upload the metadata JSON. Display a chronological list of study events with emoji-coded event types:
`📌 keyword` · `📝 note` · `💬 chat` · `🃏 flashcard` · `🔄 review`

**Screen 2 — Knowledge Map**  
LLM-generated natural language overview of detected patterns (what was studied, what was skipped, where the student struggles). Followed by a `st.dataframe` table showing mastery zone per topic.

**Screen 3 — Active Session**  
Pending actions displayed with Accept/Decline buttons. If accepted, the relevant sub-agent runs and its output is displayed in `st.markdown`. For quiz turns, a `st.text_area` collects the student's response and triggers the Evaluator.

---

## 7. Project Structure

```
Scorates_GDG_Hackaton_2026/
├── app.py                        # Streamlit entry point
├── pyproject.toml
├── requirements.txt
├── .env.example
│
├── agent/
│   ├── __init__.py
│   ├── state.py                  # Pydantic models + AgentState
│   ├── graph.py                  # LangGraph StateGraph
│   ├── orchestrator.py           # Conditional router
│   ├── llm.py                    # Unified LLM wrapper
│   ├── semantic_analyzer.py
│   ├── session_analyzer.py
│   ├── tutor.py
│   ├── evaluator.py
│   ├── speech.py                 # ElevenLabs STT integration
│   └── peer_matcher.py
│
├── data/
│   ├── metadata.json             # Sample user study metadata
│   └── metadata_peer.json        # Sample peer metadata (demo fixture)
│
├── tests/
│
└── docs/
    ├── ARCHITECTURE.md           # This document
    ├── REQUIREMENTS.md           # Requirements Design Document
    └── pitch/
        ├── index.html            # Interactive pitch deck (GitHub Pages)
        └── short-demo.mp4
```

---

## 8. Dependencies

```toml
[project]
dependencies = [
    "langgraph>=0.2",
    "langchain-core>=0.3",
    "langchain-openai>=0.2",
    "langchain-anthropic>=0.2",
    "streamlit>=1.35",
    "pydantic>=2.0",
    "elevenlabs>=1.0",
]
```

---

## 9. Implementation Order

Follow this sequence to build the system incrementally, with each step testable in isolation:

1. `agent/state.py` — Pydantic models and `AgentState`
2. `agent/llm.py` — LLM wrapper
3. `agent/semantic_analyzer.py` — Domain classification + dependency graph (validate graph output with document headings)
4. `agent/session_analyzer.py` — JSON parsing, timeline, patterns, knowledge map (uses `topic_list` from step 3)
5. `agent/orchestrator.py` — Conditional router (uses `dependency_graph` for action prioritisation)
6. `agent/tutor.py` — Single LLM call per action type
7. `agent/evaluator.py` — Two LLM calls: question generation + scoring (uses `document_domain` for style)
8. `agent/peer_matcher.py` — Knowledge map comparison
9. `agent/graph.py` — Assembles the full LangGraph (SM → SA → Orchestrator → sub-agents)
10. `app.py` — Streamlit application wiring everything together
11. `data/metadata_peer.json` — Create a fixture with deliberately different patterns from the primary JSON
