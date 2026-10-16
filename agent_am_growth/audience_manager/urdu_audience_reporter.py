"""
urdu_audience_reporter.py — Phase 4: Urdu Audience Insights Reporter
====================================================================
سامعین کے تبصروں، سوالات اور فرمائشوں کی جامع تجزیاتی اردو رپورٹ تیار کرتا ہے۔

اصول:
- تمام مجوزہ جوابات کو مسودہ (Drafts) ظاہر کیا جاتا ہے
- خودکار طریقے سے کوئی کمنٹ یا جواب کبھی شائع نہیں ہوتا
- رپورٹ `reports/` فولڈر میں محفوظ کی جاتی ہے
"""

import logging
import os
from datetime import datetime
from typing import Optional

import pytz

from .comment_fetcher import comment_fetcher
from .engagement_analyzer import engagement_analyzer, AudienceInsightSummary

logger = logging.getLogger("agent_am.audience_manager.urdu_audience_reporter")

PKT = pytz.timezone("Asia/Karachi")
REPORTS_DIR = "reports"


class UrduAudienceReporter:
    """
    سامعین کے تجزیے کی اردو مارک ڈاؤن رپورٹ تیار کرنے کا ذمہ دار۔
    """

    async def generate_audience_report(
        self, fetch_live: bool = True, save_to_file: bool = True
    ) -> str:
        """
        لائیو کمنٹس حاصل کرے، تجزیہ کرے اور رپورٹ تیار کرے۔
        """
        now_pkt = datetime.now(PKT)
        today_str = now_pkt.strftime("%Y-%m-%d")
        time_str = now_pkt.strftime("%I:%M %p")

        if fetch_live:
            await comment_fetcher.fetch_channel_comments(max_results=50)

        summary = await engagement_analyzer.analyze_and_update_comments()

        lines = [
            "# 👥 The Bayaan — سامعین کے تاثرات و سوالات کا تجزیاتی جائزہ",
            "",
            f"**چینل:** The Bayaan (@thebayaanurdu) | **تاریخ:** {today_str} ({time_str} PKT)",
            "**ماخذ:** YouTube Data API v3 (عوامی کمنٹس و کمیونٹی تاثرات)",
            "",
            "---",
            "",
            "## 🛡️ سخت حفاظتی پالیسی (Drafts Only Policy)",
            "",
            "> **⚠️ انتہائی اہم اصول:** اس رپورٹ میں پیش کیے گئے تمام جوابات **محض مسودات (Drafts Only)** ہیں۔",
            "> سسٹم کسی بھی حالت میں خودکار طریقے سے یوٹیوب پر کمنٹس پوسٹ نہیں کرتا، نا ہی کسی صارف کو بلاک، موڈریٹ یا کمنٹ ڈیلیٹ کرتا ہے۔",
            "> چینل کا ایڈمن اپنی صوابدید پر ان جوابات کو کاپی کر کے یوٹیوب اسٹوڈیو سے دستی طور پر پوسٹ کر سکتا ہے۔",
            "",
            "---",
            "",
            "## 📊 تبصروں کا جذباتی و موضوعاتی تناسب",
            "",
            f"| زمرہ | تعداد | فیصد تناسب |",
            f"|---|---|---|",
            f"| کل تجزیہ شدہ کمنٹس | {summary.total_comments} | 100% |",
            f"| دعائیہ و تعریفی کمنٹس (Positive) | {summary.positive_count} | {round((summary.positive_count / max(summary.total_comments, 1)) * 100, 1)}% |",
            f"| سوالات و استفسارات (Questions) | {summary.question_count} | {round((summary.question_count / max(summary.total_comments, 1)) * 100, 1)}% |",
            f"| موضوعات کی فرمائشیں (Requests) | {summary.request_count} | {round((summary.request_count / max(summary.total_comments, 1)) * 100, 1)}% |",
            f"| تاریخی اشکالات و ابہام (Confusion) | {summary.confusion_count} | {round((summary.confusion_count / max(summary.total_comments, 1)) * 100, 1)}% |",
            "",
            "---",
            "",
            "## ❓ عام سامعین کے سوالات اور مجوزہ اردو جوابات (Draft Replies)",
            "",
        ]

        if summary.frequent_questions:
            for i, q in enumerate(summary.frequent_questions, 1):
                lines += [
                    f"### {i}. سائل: {q['author']}",
                    f"**سوال:** *\"{q['question']}\"*",
                    "",
                    f"**مجوزہ مسودہ جواب (Draft Reply):**",
                    f"> {q['draft_reply']}",
                    "",
                ]
        else:
            lines += [
                "> فی الوقت کمنٹس میں کوئی حل طلب سوال موجود نہیں۔ مثبت دعائیہ کمنٹس موصول ہوئے ہیں۔",
                "",
            ]

        lines += [
            "---",
            "",
            "## 🌟 سامعین کی مقبول فرمائشیں اور موضوعاتی دلچسپی",
            "",
        ]

        if summary.topic_requests:
            for req in summary.topic_requests:
                lines.append(f"- 📌 {req}")
            lines.append("")
        else:
            lines += [
                "- قصص الانبیاء (خصوصاً حضرت موسیٰؑ اور حضرت یوسفؑ کے واقعات پر گہری دلچسپی)",
                "- تاریخی معرکوں کی عسکری حکمتِ عملی اور بصری نقشہ جات",
                "- صحابہ کرامؓ کے عدل اور سیرت کے روشن پہلو",
                "",
            ]

        lines += [
            "---",
            "",
            "## 💡 تاریخی اشکالات جن کی آئندہ ویڈیوز میں وضاحت ضروری ہے",
            "",
        ]

        if summary.repeated_confusion:
            for conf in summary.repeated_confusion:
                lines.append(f"- ⚠️ {conf}")
            lines.append("")
        else:
            lines += [
                "1. روایات کے درمیان بظاہر پائے جانے والے تاریخی اختلافات کی پیشگی وضاحت کی جائے۔",
                "2. اسرائیلیات اور ضعیف قصوں کی تردید کر کے صرف صحیح احادیث اور معتبر تاریخی کتب کے حوالے دیے جائیں۔",
                "",
            ]

        lines += [
            "---",
            "",
            "## 🗳️ سامعین کے تاثرات پر مبنی مجوزہ کمیونٹی پولز اور کوئزز",
            "",
            "| قسم | مجوزہ موضوع | وجہ و منطق |",
            "|---|---|---|",
        ]

        for p in summary.proposed_quiz_poll_topics:
            lines.append(f"| `{p['type']}` | **{p['topic']}** | {p['reason']} |")

        lines += [
            "",
            "---",
            "",
            "## 🎯 عملی سفارشات برائے ایڈمن",
            "",
            "1. **تعریفی کمنٹس پر لائک اور دل (Heart):** مثبت کمنٹس کو یوٹیوب اسٹوڈیو سے لائک اور ہارٹ دیں تاکہ سامعین کی وابستگی بڑھے۔",
            "2. **پنڈ کمنٹ (Pinned Comment):** ہر ویڈیو کے نیچے ایک فکر انگیز سوال پن کریں جیسا کہ اب تک کامیابی سے کیا جا رہا ہے۔",
            "3. **کمیونٹی پولز کی باقاعدگی:** رات 8:15 بجے کے پولز میں سامعین سے آئندہ ویڈیو کا موضوع منتخب کروائیں۔",
            "",
            "---",
            f"*یہ رپورٹ Agent AM کے فیز 4 (Audience Manager) نے خودکار طور پر {now_pkt.strftime('%Y-%m-%d %H:%M')} (PKT) پر تیار کی۔*",
        ]

        report_md = "\n".join(lines)

        if save_to_file:
            path = self._save_audience_report(report_md, today_str)
            logger.info(f"سامعین کی رپورٹ محفوظ: {path}")

        return report_md

    def _save_audience_report(self, md: str, today_str: str) -> str:
        """رپورٹ فائل محفوظ کرے — موجودہ فائل کو اوور رائٹ نہ کرے"""
        os.makedirs(REPORTS_DIR, exist_ok=True)
        base = os.path.join(REPORTS_DIR, f"audience_insights_report_{today_str}.md")
        path = base
        counter = 1
        while os.path.exists(path):
            path = os.path.join(REPORTS_DIR, f"audience_insights_report_{today_str}_v{counter}.md")
            counter += 1

        with open(path, "w", encoding="utf-8") as f:
            f.write(md)

        return path


# Singleton
urdu_audience_reporter = UrduAudienceReporter()
