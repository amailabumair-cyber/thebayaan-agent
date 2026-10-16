"""
Phase 4 — Audience Manager Module
==================================
The Bayaan چینل کے عوامی کمنٹس کا جائزہ، سوالات کی درجہ بندی،
اور مؤدبانہ اردو مسودہ جوابات (Draft Replies Only)۔
"""

from .comment_fetcher import comment_fetcher
from .engagement_analyzer import (
    engagement_analyzer,
    AudienceInsightSummary,
)
from .urdu_audience_reporter import (
    urdu_audience_reporter,
)

__all__ = [
    "comment_fetcher",
    "engagement_analyzer",
    "AudienceInsightSummary",
    "urdu_audience_reporter",
]
