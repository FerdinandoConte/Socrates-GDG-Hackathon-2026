from enum import StrEnum
from pydantic import BaseModel, Field


class DocumentDomain(StrEnum):
    STEM = "stem"
    HUMANITIES = "humanities"


class DomainClassification(BaseModel):
    domain: DocumentDomain


class TopicInfo(BaseModel):
    id: str = Field(description="Sequential id like t1, t2, t3")
    name: str
    page_range: list[int] = Field(description="[start_page, end_page] inclusive")


class TopicDependencyGraph(BaseModel):
    topics: list[TopicInfo]
    dependencies: dict[str, list[str]] = Field(
        description="Map of topic_id to list of prerequisite topic_ids"
    )


class VoiceAnalysis(BaseModel):
    """Analysis of vocal aspects of an oral answer."""
    hesitation_level: str = Field(description="'low', 'moderate', or 'high'")
    long_pauses_count: int = Field(description="Number of pauses > 3 seconds")
    imprecise_terms: list[str] = Field(
        default_factory=list,
        description="Generic terms used instead of correct technical terminology"
    )
    expressive_coherence: str = Field(description="'coherent', 'fragmented', or 'disorganized'")


class InternalEvaluation(BaseModel):
    """Internal evaluation (not shown to the student).
    Used to update the knowledge map and decide the next question."""
    overall_understanding: str = Field(description="'poor', 'partial', or 'solid'")
    internal_score: int = Field(ge=0, le=100)
    follow_up_question: str = Field(description="Next adaptive Socratic question based on detected gaps")
    voice_analysis: VoiceAnalysis | None = Field(
        default=None,
        description="Voice-specific analysis, present only for oral answers"
    )


class CategoryFeedback(BaseModel):
    """Feedback on a single evaluation category."""
    category: str = Field(description="Category name (e.g. 'Technical precision')")
    level: str = Field(description="'strong', 'adequate', or 'weak'")
    comment: str = Field(description="Specific comment about this category")


class StudentGoal(StrEnum):
    WORK = "work"
    STUDY = "study"
    EXAM = "exam"


class FinalSessionFeedback(BaseModel):
    """Final feedback for the Socratic session, shown to the student."""
    category_feedback: list[CategoryFeedback]
    weakest_category: str
    overall_summary: str = Field(description="Qualitative summary of the student's understanding")
    recommendation: str = Field(description="Suggestion contextualized to the student's goal")
