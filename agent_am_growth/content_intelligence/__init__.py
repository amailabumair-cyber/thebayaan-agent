"""
Phase 3 — Content Intelligence Module
======================================
The Bayaan چینل کے لیے اسلامی تاریخ پر مبنی 30 روزہ کونٹینٹ کیلنڈر،
موضوعات کی ترجیحی درجہ بندی، ہکس، تھمب نیل تصورات اور معنوی تکرار کی روک تھام۔
"""

from .fingerprint import (
    normalize_urdu_text,
    compute_content_fingerprint,
    tokenize_urdu,
    calculate_jaccard_similarity,
    content_deduplicator,
    SimilarityCheckResult,
)
from .topic_generator import (
    topic_generator,
    TopicIdea,
    CURATED_TOPICS,
)
from .calendar_generator import (
    calendar_generator,
    CALENDAR_30_DAYS_BLUEPRINT,
)
from .urdu_calendar_exporter import (
    urdu_calendar_exporter,
)

__all__ = [
    "normalize_urdu_text",
    "compute_content_fingerprint",
    "tokenize_urdu",
    "calculate_jaccard_similarity",
    "content_deduplicator",
    "SimilarityCheckResult",
    "topic_generator",
    "TopicIdea",
    "CURATED_TOPICS",
    "calendar_generator",
    "CALENDAR_30_DAYS_BLUEPRINT",
    "urdu_calendar_exporter",
]
