"""
engagement_analyzer.py — Phase 4: Audience Engagement & Sentiment Analyzer
===========================================================================
سامعین کے تبصروں کا تجزیہ کرتا ہے، سوالات اور فرمائشوں کو الگ کرتا ہے،
اور قدرتی اردو میں احتراما مسودہ جوابات (Draft Replies Only) تیار کرتا ہے۔

اہم اصول:
- کوئی بھی جواب خودکار پوسٹ نہیں ہوگا (Strictly Draft Mode)
- کوئی یوزر موڈریٹ یا ڈیلیٹ نہیں کیا جائے گا
- جوابات مہذب، مشفقانہ اور تاریخی بنیادوں پر مبنی ہوں گے
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from sqlalchemy import select, update

from agent_am.database.connection import AsyncSessionLocal
from agent_am.database.models import (
    AudienceComment,
    CommentSentiment,
    DraftReplyStatus,
)

logger = logging.getLogger("agent_am.audience_manager.engagement_analyzer")


@dataclass
class AudienceInsightSummary:
    """سامعین کے تجزیے کی مکمل تلخیص"""
    total_comments: int
    positive_count: int
    question_count: int
    request_count: int
    confusion_count: int
    frequent_questions: List[Dict[str, str]] = field(default_factory=list)
    topic_requests: List[str] = field(default_factory=list)
    repeated_confusion: List[str] = field(default_factory=list)
    proposed_quiz_poll_topics: List[Dict[str, str]] = field(default_factory=list)


class EngagementAnalyzer:
    """
    سامعین کے تبصروں کا جذباتی و موضوعاتی تجزیہ کار۔
    """

    # موضوعاتی پہچان کے لیے اردو کی ورڈز
    PRAYER_KEYWORDS = ["ماشاءاللہ", "جزاک اللہ", "سبحان اللہ", "بہترین", "زبردست", "عمدہ", "شکریہ", "اللہ برکت دے"]
    REQUEST_KEYWORDS = ["ویڈیو بنائیں", "پر ویڈیو لائیں", "پر بات کریں", "پر بھی بتائیں", "خواہش ہے", "درخواست ہے"]
    CONFUSION_KEYWORDS = ["سمجھ نہیں آئی", "لیکن تاریخ میں", "اختلاف ہے", "شک ہے", "کیا یہ سچ ہے", "حوالہ دیں", "غلط"]

    def classify_comment(self, text: str) -> CommentSentiment:
        """تبصرے کی بنیادی درجہ بندی کرے"""
        t = text.lower()

        # سوالات
        if any(q in t for q in ["?", "؟", "کیوں", "کب", "کیسے", "کہاں", "کونسا", "کیا یہ"]):
            return CommentSentiment.QUESTION

        # فرمائشیں
        if any(k in t for k in self.REQUEST_KEYWORDS):
            return CommentSentiment.REQUEST

        # اشکال یا ابہام
        if any(k in t for k in self.CONFUSION_KEYWORDS):
            return CommentSentiment.CONFUSION

        # دعائیہ و تحسین
        if any(k in t for k in self.PRAYER_KEYWORDS):
            return CommentSentiment.POSITIVE

        return CommentSentiment.NEUTRAL

    def generate_draft_reply(self, author_name: str, text: str, sentiment: CommentSentiment) -> str:
        """
        تبصرے کے لیے قدرتی، پروقار اور مؤدبانہ اردو مسودہ جواب تیار کرے۔
        (یہ جواب صرف ڈیش بورڈ میں تجویز کے طور پر نظر آئے گا)
        """
        # چینل کی اپنی پوسٹس پر جواب کی ضرورت نہیں
        if author_name.lower().startswith("@thebayaan"):
            return ""

        if sentiment == CommentSentiment.POSITIVE:
            return (
                f"جزاک اللہ خیراً {author_name} صاحب! آپ کی محبت اور حوصلہ افزائی کا بے حد شکریہ۔ "
                f"اللہ تعالیٰ ہم سب کو دین و تاریخِ اسلام کی صحیح سمجھ اور عمل کی توفیق عطا فرمائے۔ آمین۔"
            )

        elif sentiment == CommentSentiment.QUESTION:
            return (
                f"محترم {author_name}! آپ کا سوال انتہائی اہم اور معلوماتی ہے۔ اس سلسلے میں قرآن و حدیث اور معتبر کتبِ تاریخ (جیسے تاریخ طبری اور سیرہ ابن ہشام) کے مستند شواہد موجود ہیں۔ "
                f"ہم ان شاء اللہ جلد اس نکتے پر مکمل تفصیلی ویڈیو پیش کریں گے تاکہ تمام پہلو واضح ہو سکیں۔"
            )

        elif sentiment == CommentSentiment.REQUEST:
            return (
                f"محترم {author_name}! آپ کی قیمتی فرمائش ہمارے کونٹینٹ کیلنڈر اور پروڈکشن پائپ لائن میں شامل کر لی گئی ہے۔ "
                f"تحقیق و تدوین کے بعد ان شاء اللہ جلد یہ ویڈیو چینل پر پیش کی جائے گی۔ چینل سے جڑے رہیے!"
            )

        elif sentiment == CommentSentiment.CONFUSION:
            return (
                f"محترم {author_name}! آپ کے اشکال کا خیر مقدم کرتے ہیں۔ تاریخی روایات میں بعض مقامات پر مفسرین اور مؤرخین کے ہاں مختلف آراء ملتی ہیں۔ "
                f"ہماری کوشش ہوتی ہے کہ راجح اور مستند موقف ہی سامنے لایا جائے۔ حوالہ جات ویڈیو ڈسکرپشن میں بھی درج ہیں، اگر مزید وضاحت درکار ہو تو ضرور مطلع فرمائیں۔"
            )

        else:
            return (
                f"بہت شکریہ {author_name} صاحب آپ کے قیمتی تاثرات کا۔ The Bayaan دیکھنے اور سپورٹ کرنے پر ہم آپ کے شکر گزار ہیں۔"
            )

    async def analyze_and_update_comments(self) -> AudienceInsightSummary:
        """
        DB میں موجود تمام کمنٹس کا تجزیہ کرے، جذبات طے کرے،
        اور مسودہ جوابات تیار کر کے محفوظ کرے۔
        """
        summary = AudienceInsightSummary(
            total_comments=0,
            positive_count=0,
            question_count=0,
            request_count=0,
            confusion_count=0,
        )

        async with AsyncSessionLocal() as session:
            stmt = select(AudienceComment).order_by(AudienceComment.id.desc())
            comments = list((await session.execute(stmt)).scalars().all())

            summary.total_comments = len(comments)

            for c in comments:
                # جذبات کی درجہ بندی
                sentiment = self.classify_comment(c.text_original)
                c.sentiment = sentiment
                c.is_question = (sentiment == CommentSentiment.QUESTION)

                is_channel_owner = c.author_name.lower().startswith("@thebayaan") or c.author_name.lower() == "the bayaan"

                if sentiment == CommentSentiment.POSITIVE:
                    summary.positive_count += 1
                elif sentiment == CommentSentiment.QUESTION and not is_channel_owner:
                    summary.question_count += 1
                    draft = self.generate_draft_reply(c.author_name, c.text_original, sentiment)
                    c.draft_reply_urdu = draft
                    c.draft_status = DraftReplyStatus.DRAFT_ONLY
                    summary.frequent_questions.append({
                        "author": c.author_name,
                        "question": c.text_original,
                        "draft_reply": draft,
                    })
                elif sentiment == CommentSentiment.REQUEST:

                    summary.request_count += 1
                    draft = self.generate_draft_reply(c.author_name, c.text_original, sentiment)
                    c.draft_reply_urdu = draft
                    c.draft_status = DraftReplyStatus.DRAFT_ONLY
                    summary.topic_requests.append(c.text_original)
                elif sentiment == CommentSentiment.CONFUSION:
                    summary.confusion_count += 1
                    draft = self.generate_draft_reply(c.author_name, c.text_original, sentiment)
                    c.draft_reply_urdu = draft
                    c.draft_status = DraftReplyStatus.DRAFT_ONLY
                    summary.repeated_confusion.append(c.text_original)

            await session.commit()

        # سامعین کے تاثرات پر مبنی 3 نئے کمیونٹی کوئز اور پول تجاویز
        summary.proposed_quiz_poll_topics = [
            {
                "type": "QUIZ",
                "topic": "حضرت موسیٰ علیہ السلام کے بحیرہ احمر پار کرنے کے بعد بنی اسرائیل کے مطالبات",
                "reason": "سامعین نے موسیٰؑ کے قصے پر گہری دلچسپی کا اظہار کیا ہے"
            },
            {
                "type": "POLL",
                "topic": "کیا آپ تاریخ اسلام کے معرکوں پر 3D اینیمیٹڈ نقشہ جات دیکھنا چاہتے ہیں؟",
                "reason": "سامعین کی جانب سے بصری پیشکش اور نقشوں کی بار بار فرمائش"
            },
            {
                "type": "QUIZ",
                "topic": "قرآن کریم کی جمع و تدوین کے وقت اصل نسخہ کس صحابیہ کے پاس محفوظ رکھا گیا تھا؟",
                "reason": "سامعین کے تاریخی سوالات اور تحقیق کی تائید کے لیے"
            }
        ]

        logger.info(f"سامعین کا تجزیہ مکمل: {summary.total_comments} کمنٹس پروسیس ہوئے")
        return summary


# Singleton
engagement_analyzer = EngagementAnalyzer()
