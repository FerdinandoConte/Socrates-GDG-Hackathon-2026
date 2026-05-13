# Socrates: Technical Design Document

## 1. Product Overview
**Socrates** is a web application featuring a multi-agent ecosystem designed for guided and active learning. The system processes educational material uploaded by the user (PDF, images, DOCX, XLS) and manages multimodal interaction (text and voice).

**Integrated Split-Screen Interface:** The user experience is structured to eliminate unnecessary cognitive load. The student always views the original document in the main area of the screen, while the agent (with text/voice chat and interaction tools) is anchored in a permanent lateral sidebar. This layout allows simultaneous consultation of the material and interaction with the AI without ever losing context.

The AI is not a mere passive responder: it can actively guide the choice of interaction format. For example, when faced with purely descriptive documents, the agent will take the initiative to request the student to send voice notes to verify genuine assimilation of key concepts.

## 2. The Four Phases of Learning

### Phase 1: The Initial Hook (The Curious Agent)
The first contact with the uploaded material never produces a simple summary. The goal in this phase is to break the "boredom barrier" and provide an overview.

*   **Mapping and Metaphors:** The agent generates a high-level mind map and introduces the topic through intuitive metaphors, anecdotes, and real-world application cases.
*   **Autonomous Exploration:** The user is prompted to explore the nodes of the concept map independently, stimulating curiosity and preparing for systematic study (framing the goal as reaching a learning outcome rather than just an AI-generated output without student effort).
*   **Secondary Feature (Disable Introductory Example):** The student can decide to bypass this gentle approach. By enabling this option, the system will not generate metaphors or anecdotes, allowing the user who already has a good baseline to jump straight into the technical study of the material.

### Phase 2: The Core System (The Socratic Agent and Active Approach)
This phase begins when the student has acquired basic familiarity. This agent is the core innovation: it does not answer; it asks questions.

*   **Zero Passive Prompting:** If the student attempts a shortcut by entering prompts like "Explain this topic", the agent activates a constructive categorical refusal. The objective is to force the user to process and reason about the material.
*   **Targeted Maieutics:** The agent asks questions designed to test the depth of understanding. The goal is to push the user to their cognitive limits, making them fall into contradiction or error on concepts learned too superficially, and then helping them reconstruct those concepts.
*   **Refusal Management (Skip Question):** To avoid frustration and cognitive dead-ends, the student is not obligated to answer at all costs. They can choose to refuse a specific question from the agent. In this case, the agent acknowledges the refusal (recording it as data for the adaptive plan) and either waits or formulates a new subsequent question to smoothly continue the tutoring process.
*   **Secondary Feature (Disable AI Proactivity):** If the user needs to take full control of the session, they can turn off the Socratic Agent's proactivity. This option disables unsolicited questions and constructive refusals, temporarily transforming the AI into a custom assistant guided only by direct requests.

### Phase 3: Voice Evaluation (The "Feynman Agent") [Optional, text default]
A specialized module to test expository mastery via speech-to-text interaction. The agent challenges the user to explain a complex concept out loud, "as if talking to a child". The transcription is then analyzed based on three pillars:

*   **Clarity:** Evaluates the synthesis ability and the use of effective metaphors compared to the overuse of unnecessary technical jargon.
*   **Completeness:** Verifies that no logical steps or fundamental parts of the topic have been omitted.
*   **Correctness:** Identifies factual errors, hallucinations, or flaws in logical reasoning.

### Phase 4: The Adaptation Engine (Rubric, Delta, and Scaffolding)
The study plan is not static but changes in real-time based on the user's responses and actions (including "skips" of questions), ensuring a hyper-personalized experience.

*   **Delta Analysis (Via Scoring Rubric):** At each interaction, the agent uses a rigorous evaluation grid to measure the "Delta" (the distance) between the student's answer and the optimal desirable output.
*   **Dynamic Scaffolding:** If the delta is too large, the agent re-evaluates its approach. It activates scaffolding (supportive structure) by adding clues, simplifying terms, or providing new metaphorical prompts. As the student demonstrates mastery and the gap decreases, the scaffolding is gradually removed, allowing the user to proceed independently.
*   **Pacing (Study Rhythm):** If responses to Socratic prompts or the Feynman Test are excellent, the plan accelerates towards more complex concepts. Conversely, if uncertainties, evasive answers, a high number of skipped questions, or long silences/stuttering in voice notes are detected, the rhythm slows down, and the agent focuses on consolidating the basics.

### Phase 5: Peer Matching
*(Upcoming Feature)* Automatically matches students who are struggling with a topic with peers who have already mastered it, fostering collaborative learning.

## 3. User Stories
*   As a user, I want to view my uploaded document on the main screen while chatting with the AI, so that I don't lose context or increase my cognitive load while studying.
*   As a user, I want to interact with the system using both text and voice, so that I can choose the most comfortable medium for my current learning task. (optional)
*   As a user, I want to explore a high-level mind map of the document instead of reading a standard summary, so that I can independently discover the connections and focus on the learning outcome.
*   As a user, I want the option to toggle off the introductory examples, so that I can dive straight into the technical study if I already possess a strong baseline understanding.
*   As a user, I want to be challenged with questions, so that I can expose my superficial misunderstandings and reconstruct my knowledge solidly.
*   As a user, I want the ability to skip a specific question without penalty, so that I can continue the session when a question is unclear, without being blocked.
*   As a user, I want to be able to disable the AI agent, so that I can take full manual control of the session.

## 4. Functional Requirements
*   The system shall provide a split-screen user interface.
*   The system shall provide a persistent lateral sidebar that houses the conversational interface and interactive elements (mind map).
*   The system shall automatically extract key concepts and generate an interactive, navigable mind map.
*   The system shall generate at least one intuitive metaphor or practical use-case anecdote related to the core topic. (only at the beginning)
*   The system shall not generate traditional text summaries of the documents.
*   The system shall utilize a guardrail filter to detect explicit requests for direct answers (e.g., "explain this," "summarize") and trigger a predefined constructive refusal protocol.
*   The system shall dynamically generate maieutic follow-up questions designed to test logical consistency based on the document data and previous user inputs.
*   The system shall provide a UI interaction (e.g., a "Skip" button) allowing the user to bypass the current Socratic question.
*   The system shall evaluate user responses using a predefined scoring rubric to calculate a numerical "delta" between the user's input and the AI-generated optimal reference output.
*   The system shall trigger "scaffolding" protocols (injecting hints, simplifying terminology) when the calculated delta exceeds a defined maximum threshold.
*   The system shall progressively reduce the frequency of scaffolding interventions as the user's delta score decreases over time.
*   The system will have to dynamically adjust the "pacing" (difficulty and speed of difficulty progression) based on an aggregated analysis of recent delta scores, textual evasiveness, and audio hesitancy markers (e.g., long pauses or filler words).

**Optional Requirements:**
*   The system will have to analyze the format of the uploaded content and proactively prompt the user to utilize speech-to-text interactions if the material is categorized as heavily descriptive or text-dense. (optional)
*   The system shall evaluate the transcription against three specific criteria: Clarity (ratio of simple terms/metaphors to technical jargon), Completeness (presence of core logical steps), and Correctness (absence of logical flaws or factual errors).
