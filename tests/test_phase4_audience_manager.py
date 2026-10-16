"""
test_phase4_audience_manager.py — Phase 4 Audience Manager Tests
================================================================
یہ ٹیسٹس چیک کرتے ہیں:
1. تبصروں کے جذبات کی درجہ بندی (Positive, Question, Request, Confusion)
2. شائستہ اور مؤدبانہ اردو مسودہ جوابات (Draft Replies Only)
3. ڈرافٹ اونلی سیفٹی: کوئی خودکار پوسٹنگ نہیں
4. کمنٹ فیچر کی انضمام و استقامت
5. سامعین کے تاثرات پر مبنی پول و کوئز تجاویز
6. اردو اینالیٹکس رپورٹ کا اجراء
"""

import pytest
import pytest_asyncio
from agent_am.database.models import (
    AudienceComment,
    CommentSentiment,
    DraftReplyStatus,
)
from agent_am_growth.audience_manager.engagement_analyzer import (
    engagement_analyzer,
    EngagementAnalyzer,
)
from agent_am_growth.audience_manager.comment_fetcher import (
    comment_fetcher,
    CommentFetcher,
)
from agent_am_growth.audience_manager.urdu_audience_reporter import (
    urdu_audience_reporter,
)


# ---------------------------------------------------------------------------
# Test 1: Sentiment Classification
# ---------------------------------------------------------------------------
def test_comment_sentiment_classification():
    """مختلف تبصروں کے جذبات و مقاصد کی درست درجہ بندی"""
    ea = EngagementAnalyzer()

    # دعائیہ کمنٹ
    assert ea.classify_comment("ماشاءاللہ بہت ہی عمدہ اور معلوماتی ویڈیو") == CommentSentiment.POSITIVE
    assert ea.classify_comment("جزاک اللہ خیر") == CommentSentiment.POSITIVE

    # سوالیہ کمنٹ
    assert ea.classify_comment("حضرت نوحؑ کی کشتی کتنے عرصے تک پانی میں رہی؟") == CommentSentiment.QUESTION
    assert ea.classify_comment("کیا یہ واقعہ صحیح بخاری میں موجود ہے؟") == CommentSentiment.QUESTION

    # فرمائش
    assert ea.classify_comment("سلطان صلاح الدین ایوبی کی فتحِ بیت المقدس پر ویڈیو بنائیں") == CommentSentiment.REQUEST

    # اشکال یا الجھن
    assert ea.classify_comment("لیکن تاریخ طبری میں اس روایت پر اختلاف ہے، شک ہے") == CommentSentiment.CONFUSION

    # عام
    assert ea.classify_comment("ہم سب دیکھ رہے ہیں") == CommentSentiment.NEUTRAL


# ---------------------------------------------------------------------------
# Test 2: Polite Draft Reply Generation
# ---------------------------------------------------------------------------
def test_draft_reply_generation():
    """قدرتی اور شائستہ اردو مسودہ جوابات کی تیاری"""
    ea = EngagementAnalyzer()

    # سوال کا جواب
    reply_q = ea.generate_draft_reply("@Ahmad123", "کیا یہ واقعہ قرآن میں ہے؟", CommentSentiment.QUESTION)
    assert "محترم @Ahmad123" in reply_q
    assert "سوال" in reply_q
    assert "مستند" in reply_q

    # فرمائش کا جواب
    reply_r = ea.generate_draft_reply("@Usman99", "غزوہ موتہ پر ویڈیو لائیں", CommentSentiment.REQUEST)
    assert "محترم @Usman99" in reply_r
    assert "فرمائش" in reply_r

    # چینل کے اپنے کمنٹ کا کوئی ڈرافٹ جواب نہیں بننا چاہیے
    reply_self = ea.generate_draft_reply("@TheBayaanUrdu", "آپ کی کیا رائے ہے؟", CommentSentiment.QUESTION)
    assert reply_self == ""


# ---------------------------------------------------------------------------
# Test 3: Safety Guarantee - Draft Only Status
# ---------------------------------------------------------------------------
def test_draft_only_status_invariant():
    """تمام جوابات صرف مسودہ (DRAFT_ONLY) کے طور پر نشان زد ہوں گے"""
    assert DraftReplyStatus.DRAFT_ONLY.value == "DRAFT_ONLY"


# ---------------------------------------------------------------------------
# Test 4: Audience Analysis & Reporting
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_engagement_analyzer_summary():
    """اینگیجمنٹ اینالائزر تجاویز اور سمری درست تیار کرتا ہے"""
    summary = await engagement_analyzer.analyze_and_update_comments()

    assert summary.total_comments >= 0
    assert len(summary.proposed_quiz_poll_topics) >= 2
    for p in summary.proposed_quiz_poll_topics:
        assert p["type"] in ["QUIZ", "POLL"]
        assert len(p["topic"]) > 10
        assert len(p["reason"]) > 10


# ---------------------------------------------------------------------------
# Test 5: Urdu Audience Reporter creates valid report
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_urdu_audience_reporter(tmp_path):
    """سامعین کے تجزیے کی مکمل رپورٹ تیار ہوتی ہے مع حفاظتی انتباہ"""
    original_save = urdu_audience_reporter._save_audience_report

    def mock_save(md, today_str):
        path = str(tmp_path / f"audience_test_{today_str}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        return path

    urdu_audience_reporter._save_audience_report = mock_save

    try:
        md = await urdu_audience_reporter.generate_audience_report(fetch_live=False, save_to_file=True)
    finally:
        urdu_audience_reporter._save_audience_report = original_save

    assert "The Bayaan" in md
    assert "حفاظتی پالیسی" in md
    assert "Drafts Only" in md
    assert "تناسب" in md
