# Requirements Design Document (RDD)
**Project:** SOCRATES — Active Learning Agent  
**Event:** GDG Hackathon 2026  
**Version:** 1.0  

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [User Stories](#2-user-stories)
3. [Functional Requirements](#3-functional-requirements)
4. [Agent Subsystems](#4-agent-subsystems)
5. [Optional / Future Features](#5-optional--future-features)

---

## 1. Product Overview

**Socrates** is a web application powered by a multi-agent AI ecosystem designed for guided and active learning. The system processes educational material uploaded by the user (PDF, images, DOCX, XLS) and manages a multimodal interaction layer combining text and voice.

### 1.1 Split-Screen Interface

The user experience is structured to eliminate unnecessary cognitive load. The student always sees the original document in the main area of the screen, while the agent (with its text/voice chat and interactive tools) is anchored in a permanent lateral sidebar. This layout enables simultaneous consultation of the source material and AI interaction without ever losing context.

The AI is not a passive responder: it can actively guide the choice of interaction format. For example, when faced with a set of heavily descriptive documents, the agent may take the initiative and ask the student to send voice notes to verify genuine assimilation of key concepts.

### 1.2 Core Learning Phases

The system is organized into four main learning phases:

#### Phase 1 — The Curious Hook
The first contact with uploaded material never produces a plain summary. The objective is to break the "boredom barrier" and provide a high-level overview.

- **Mind Map Generation**: the agent generates a high-level conceptual map and introduces the topic through intuitive metaphors, anecdotes, and real-world application cases.
- **Autonomous Exploration**: the student is encouraged to explore the conceptual map nodes independently, stimulating curiosity and preparing for systematic study (the learning goal is framed as achieving an outcome rather than consuming AI-generated output).
- **Bypass Option** *(toggleable)*: the student may skip the introductory phase. When active, the system skips metaphors and anecdotes, allowing students with prior knowledge to proceed directly to technical study.

#### Phase 2 — The Socratic Agent
This agent takes over once the student has acquired a basic familiarity with the topic. It is the core innovation: it does not answer, it questions.

- **Zero Passive Prompting**: if the student tries to shortcut by entering prompts such as "Explain this topic", the agent triggers a *constructive refusal*. The goal is to force the user to elaborate and reason through the material independently.
- **Targeted Maieutics**: the agent poses carefully designed questions to test the depth of the student's understanding, pushing them toward their cognitive limits — deliberately surfacing contradictions or errors in superficially-learned concepts, then helping reconstruct them.
- **Question Skip Mechanism**: to prevent frustration and cognitive dead-ends, the student is not forced to answer every question. They may skip a specific agent question. The agent records the skip as a data point for adaptive planning and either waits or formulates a follow-up question to continue the tutoring flow seamlessly.
- **Proactivity Toggle** *(optional)*: if the student needs to take full control of the session, they may disable the Socratic Agent's proactivity. This turns off unsolicited questions and constructive refusals, temporarily transforming the AI into a demand-driven assistant.

#### Phase 3 — Feynman Agent *(Optional — default: text)*
A specialized module for testing expository mastery via speech-to-text interaction. The agent challenges the student to explain a complex concept aloud *"as if speaking to a child"*. The transcription is then analysed across three pillars:

- **Clarity**: evaluates the ability to synthesise and use effective metaphors versus unnecessary technical jargon.
- **Completeness**: verifies that no logical steps or fundamental portions of the topic have been omitted.
- **Correctness**: identifies factual errors, hallucinations, or flaws in logical reasoning.

#### Phase 4 — Adaptive Engine: Rubric, Delta, and Scaffolding
The study plan is not static — it evolves in real time based on the student's responses and actions (including question skips), guaranteeing a hyper-personalised experience.

- **Delta Analysis via Scoring Rubric**: at each interaction, the agent uses a rigorous scoring rubric to measure the *delta* (the distance) between the student's response and the optimal reference output.
- **Dynamic Scaffolding**: if the delta is too large, the agent reassesses its approach and activates scaffolding — injecting hints, simplifying terminology, or providing new metaphorical cues. As the student demonstrates mastery and the gap narrows, scaffolding is progressively removed.
- **Pacing**: if responses to Socratic prompts or the Feynman test are excellent, the plan accelerates toward more complex concepts. Conversely, if uncertainty, evasive answers, a high number of skipped questions, or long pauses/hesitations in voice notes are detected, the pace slows and the agent consolidates foundational understanding.

#### Phase 5 — Peer Matching *(Upcoming)*
Students with complementary knowledge maps are matched automatically to facilitate peer-to-peer learning.

---

## 2. User Stories

| ID | As a user, I want to… | So that… |
|----|----------------------|----------|
| US-01 | View my uploaded document in the main screen while chatting with the AI | I don't lose context or increase cognitive load while studying |
| US-02 | Interact with the system using both text and voice | I can choose the most comfortable medium for each learning task |
| US-03 | Explore a high-level mind map of the document instead of reading a standard summary | I can independently discover connections and focus on the learning outcome |
| US-04 | Toggle off introductory examples | I can dive straight into technical study if I already have a strong baseline |
| US-05 | Be challenged with questions | I can expose superficial misunderstandings and reconstruct solid knowledge |
| US-06 | Skip a specific question without penalty | I can continue the session when a question is unclear, without being blocked |
| US-07 | Disable the AI agent's proactivity | I can take full manual control of the session when needed |

---

## 3. Functional Requirements

### 3.1 Core UI

| ID | Requirement |
|----|-------------|
| FR-01 | The system shall provide a split-screen user interface |
| FR-02 | The system shall provide a persistent lateral sidebar housing the conversational interface and interactive elements (mind map) |

### 3.2 Content Processing

| ID | Requirement |
|----|-------------|
| FR-03 | The system shall automatically extract key concepts and generate an interactive, navigable mind map |
| FR-04 | The system shall generate at least one intuitive metaphor or practical use-case anecdote related to the core topic (introductory phase only) |
| FR-05 | The system shall **not** generate traditional text summaries of documents |

### 3.3 Socratic Interaction

| ID | Requirement |
|----|-------------|
| FR-06 | The system shall use a guardrail filter to detect explicit requests for direct answers (e.g., "explain this," "summarise") and trigger a predefined constructive refusal protocol |
| FR-07 | The system shall dynamically generate maieutic follow-up questions designed to test logical consistency, based on document data and previous user inputs |
| FR-08 | The system shall provide a UI interaction (e.g., a "Skip" button) allowing the user to bypass the current Socratic question |

### 3.4 Adaptive Evaluation

| ID | Requirement |
|----|-------------|
| FR-09 | The system shall evaluate user responses using a predefined scoring rubric to calculate a numerical delta between the user's input and the AI-generated optimal reference output |
| FR-10 | The system shall trigger scaffolding protocols (hint injection, terminology simplification) when the calculated delta exceeds a defined maximum threshold |
| FR-11 | The system shall progressively reduce the frequency of scaffolding interventions as the user's delta score decreases over time |
| FR-12 | The system shall dynamically adjust pacing (difficulty and speed of progression) based on aggregated analysis of recent delta scores, textual evasiveness, and audio hesitancy markers (long pauses, filler words) |

---

## 4. Agent Subsystems

### 4.1 Semantic Analyzer

Runs **once** at document load. Performs two tasks:
1. Classifies the document as STEM or Humanities (used by the Evaluator to calibrate scoring criteria)
2. Builds a **topic dependency graph** — a map of which topics are prerequisites for others — used by all downstream agents for intelligent routing and scaffolding

### 4.2 Session Analyzer

Parses the user's study metadata JSON, producing:
- A chronological **study timeline**
- A per-topic **knowledge map** with mastery zones: `unexplored`, `skimmed`, `studied`, `struggling`, `consolidating`, `mastered`
- **Behavioural pattern detection**: deep dives, topic skips, long pauses, spaced repetition struggles, and over-struggling detection

**Over-struggling detection**: triggered when a student shows persistent difficulty on a topic despite multiple repetitions (`mastery_zone == "struggling"` AND `fsrs_total_reps ≥ 3` AND `fsrs_avg_difficulty > 6.5`). The system cross-references weak prerequisites in the dependency graph and proposes a targeted `review_prerequisites` action.

### 4.3 Tutor

Handles three action types:
- `introduce_topic` — intuitive introduction via analogy and metaphor
- `fill_gap` — targeted coverage of unexplored or skimmed material
- `review_prerequisites` — explicit linkage between a fragile prerequisite and the struggling topic, with a prompt for the student to articulate the connection in their own words

### 4.4 Evaluator

Two-step process:
1. **Question generation**: difficulty calibrated to mastery zone

| Mastery Zone | Question Type |
|-------------|---------------|
| `skimmed` | Multiple choice (recognition) |
| `studied` | Open-ended simple (recall) |
| `struggling` | Open-ended simple, alternate angle |
| `consolidating` | Applied scenario |
| `mastered` | Cross-domain transfer |

2. **Response scoring**: rubric-based, domain-aware (STEM emphasises technical precision; Humanities emphasises argumentation and critical thinking)

### 4.5 Peer Matcher

Compares two knowledge maps and surfaces complementary pairings — matching students who struggle in areas where a peer has demonstrated mastery.

---

## 5. Optional / Future Features

| Feature | Description |
|---------|-------------|
| **Voice prompt detection** | Proactively suggest voice interaction when uploaded content is heavily descriptive or text-dense |
| **Speech-to-Text evaluation** | Full Feynman Agent with ElevenLabs integration, hesitation detection, and `VoiceAnalysis` scoring |
| **Peer Matching (live)** | Real-time peer matching against a live student pool (current implementation uses static JSON fixtures) |
| **Multi-document sessions** | Support for multiple documents within a single learning session |
| **Progress persistence** | Store knowledge maps and session history across multiple study sessions (database backend) |
