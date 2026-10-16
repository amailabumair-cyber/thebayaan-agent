"""
urdu_calendar_exporter.py — Phase 3: Urdu Content Calendar Exporter
===================================================================
30 روزہ کونٹینٹ کیلنڈر کو باضابطہ اور دیدہ زیب اردو مارک ڈاؤن رپورٹ
کی شکل میں `reports/` فولڈر میں برآمد کرتا ہے۔
"""

import json
import logging
import os
from datetime import datetime
from typing import List, Optional

import pytz

from agent_am.database.models import ContentCategory, ContentCalendarEntry
from .calendar_generator import calendar_generator
from .topic_generator import topic_generator

logger = logging.getLogger("agent_am.content_intelligence.urdu_calendar_exporter")

PKT = pytz.timezone("Asia/Karachi")
REPORTS_DIR = "reports"

CATEGORY_NAMES_URDU = {
    ContentCategory.PROPHETS: "قصص الانبیاء",
    ContentCategory.SEERAH: "سیرت النبی ﷺ اور تاریخِ اسلام",
    ContentCategory.COMPANIONS: "خلفائے راشدین اور صحابہ کرام",
    ContentCategory.BATTLES_EVENTS: "تاریخی معرکے اور اہم واقعات",
    ContentCategory.AUDIENCE_QA: "سامعین کے تعلیمی سوالات و جوابات",
}


class UrduCalendarExporter:
    """
    30 روزہ کیلنڈر کو اردو مارک ڈاؤن رپورٹ میں برآمد کرتا ہے۔
    """

    async def export_calendar_report(self, save_to_file: bool = True) -> str:
        """
        30 روزہ مکمل کیلنڈر کی اردو رپورٹ تیار اور محفوظ کرے۔
        """
        now_pkt = datetime.now(PKT)
        today_str = now_pkt.strftime("%Y-%m-%d")
        time_str = now_pkt.strftime("%I:%M %p")

        entries = await calendar_generator.get_calendar_entries()
        if not entries:
            # اگر ڈیٹا بیس میں پہلے سے نہ ہو تو ابھی جنریٹ کریں
            await calendar_generator.generate_and_save_calendar()
            entries = await calendar_generator.get_calendar_entries()

        # تجاویز بھی محفوظ کروائیں اگر نہ ہوں
        await topic_generator.seed_curated_proposals()
        proposals = await topic_generator.get_all_proposals()

        lines = [
            "# 📅 The Bayaan — 30 روزہ جامع اسلامی تاریخ کونٹینٹ کیلنڈر",
            "",
            f"**چینل:** The Bayaan (@thebayaanurdu) | **تاریخِ اجراء:** {today_str} ({time_str} PKT)",
            "**ہدف:** منظم، متوازن اور تاریخی شواہد سے مزین 30 روزہ ویڈیو اور کمیونٹی شیڈول",
            "",
            "---",
            "",
            "## 📌 حکمتِ عملی اور پانچ بنیادی ستون",
            "",
            "The Bayaan چینل کے لیے کونٹینٹ کو پانچ کلیدی ستونوں پر متوازن تقسیم کیا گیا ہے تاکہ ہر ناظر کی دلچسپی برقرار رہے:",
            "",
            "| نمبر | ستون | موضوعات کی نوعیت | ویڈیوز کی تعداد |",
            "|---|---|---|---|",
            "| 1 | قصص الانبیاء | قرآنی سورتوں اور تفاسیر کی روشنی میں انبیاء کرامؑ کی داستانیں | 6 ویڈیوز |",
            "| 2 | سیرت النبی ﷺ | ولادت، ہجرت، اخلاق، اہم سنگ میل اور وصال نبوی | 7 ویڈیوز |",
            "| 3 | خلفائے راشدین و صحابہ | سیدنا ابوبکرؓ، عمرؓ، عثمانؓ، علیؓ، خالد بن ولیدؓ، سلمان فارسیؓ | 6 ویڈیوز |",
            "| 4 | تاریخی معرکے اور واقعات | غزوہ بدر، احد، خندق، خیبر، یرموک، قادسیہ | 6 ویڈیوز |",
            "| 5 | سامعین کے سوالات و تحقیق | جمع قرآن، اصولِ حدیث، خلافت کا سفر، صلاح الدین ایوبی | 5 ویڈیوز |",
            "",
            "---",
            "",
            "## ⏰ روزانہ پوسٹنگ کا معیاری شیڈول",
            "",
            "- **یوٹیوب ویڈیو:** شیڈول کے مطابق شام 4:00 تا 5:00 بجے (پریمیئر)",
            "- **شام 6:15 بجے (کوئز):** اسی دن کی ویڈیو کے موضوع پر مبنی 4 آپشنز والا معلوماتی کوئز مع تصدیق شدہ تاریخی حوالہ",
            "- **رات 8:15 بجے (پول):** ناظرین کی رائے، تجاویز اور تعامل بڑھانے والا پول سوال",
            "- *(تمام اوقات میں قدرتی اثر کے لیے ±15 منٹ کا رینڈم تغیر (Jitter) شامل ہے)*",
            "",
            "---",
            "",
            "## 📋 تفصیلی 30 روزہ روزمرہ شیڈول (Day 1 تا Day 30)",
            "",
        ]

        current_week = 0
        for entry in entries:
            week_num = ((entry.day_number - 1) // 7) + 1
            if week_num != current_week:
                current_week = week_num
                lines += [
                    f"### 🗓️ ہفتہ {current_week}",
                    "",
                    "| دن | تاریخ | زمرہ | ویڈیو عنوان | کوئز (6:15 PM) | پول (8:15 PM) | ترجیح |",
                    "|---|---|---|---|---|---|---|",
                ]

            cat_urdu = CATEGORY_NAMES_URDU.get(entry.category, str(entry.category.value))
            quiz_short = entry.quiz_proposal_urdu[:65] + "..." if len(entry.quiz_proposal_urdu) > 65 else entry.quiz_proposal_urdu
            poll_short = entry.poll_proposal_urdu[:65] + "..." if len(entry.poll_proposal_urdu) > 65 else entry.poll_proposal_urdu

            lines.append(
                f"| دن {entry.day_number} | {entry.target_date} | {cat_urdu} | **{entry.video_title_urdu}** | {quiz_short} | {poll_short} | `{entry.production_priority}` |"
            )

            # اگر ہفتے کا آخری دن ہو تو ٹیبل بند کریں
            if entry.day_number % 7 == 0 or entry.day_number == len(entries):
                lines.append("")

        lines += [
            "---",
            "",
            "## 💡 ویڈیوز کے لیے تجویز کردہ وائرل عنوانات اور ہک اسکرپٹس",
            "",
        ]

        for p in proposals[:6]:
            suggested = json.loads(p.suggested_titles_json)
            lines += [
                f"### 🎯 موضوع: {p.topic_title_urdu}",
                f"- **زمرہ:** {CATEGORY_NAMES_URDU.get(p.category, p.category.value)}",
                f"- **ترجیحی اسکور:** `{p.priority_score}/100`",
                f"- **تجویز کردہ 3 عنوانات:**",
            ]
            for t in suggested:
                lines.append(f"  1. {t}")
            lines += [
                f"- **ابتدائی 15 سیکنڈ کا ہک:** *\"{p.opening_hook_urdu}\"*",
                f"- **تھمب نیل تصور:** {p.thumbnail_concept_urdu}",
                f"- **منطق و اہمیت:** {p.rationale_urdu}",
                f"- **حدود و احتیاط:** {p.uncertainty_notes_urdu}",
                "",
            ]

        lines += [
            "---",
            "",
            "## 🛡️ تکرار اور تاریخی سچائی کا تحفّظ (Deduplication & Integrity)",
            "",
            "1. **نارملائزڈ SHA-256 فنگر پرنٹنگ:** ہر موضوع اور سوال کا عربی/اردو اعراب سے پاک فنگر پرنٹ تیار ہوتا ہے تاکہ تکرار روکی جا سکے۔",
            "2. **معنوی مماثلت (Semantic Token Overlap):** اگر دو سوالات کے الفاظ مختلف مگر مفہوم ایک ہو تو 65% سے زائد مماثلت پر الرٹ جاری ہوتا ہے۔",
            "3. **کوئی من گھڑت حوالہ نہیں:** صرف قرآن کریم، صحیح بخاری، صحیح مسلم، سیرت ابن ہشام، تاریخ طبری اور البدایہ والنہایہ کے مصدقہ حوالے استعمال کیے جاتے ہیں۔",
            "4. **غیر یقینی صورتحال کی شفافیت:** کسی بھی موضوع کے وائرل ہونے یا ویوز کا فرضی دعویٰ نہیں کیا جاتا۔",
            "",
            "---",
            f"*یہ کونٹینٹ کیلنڈر Agent AM کے فیز 3 ماڈیول نے خودکار طور پر {now_pkt.strftime('%Y-%m-%d %H:%M')} (PKT) پر تیار کیا۔*",
        ]

        report_md = "\n".join(lines)

        if save_to_file:
            path = self._save_calendar_report(report_md, today_str)
            logger.info(f"30 روزہ کیلنڈر رپورٹ محفوظ: {path}")

        return report_md

    def _save_calendar_report(self, md: str, today_str: str) -> str:
        """رپورٹ فائل محفوظ کرے — موجودہ فائل کو اوور رائٹ نہ کرے"""
        os.makedirs(REPORTS_DIR, exist_ok=True)
        base = os.path.join(REPORTS_DIR, f"content_calendar_30day_{today_str}.md")
        path = base
        counter = 1
        while os.path.exists(path):
            path = os.path.join(REPORTS_DIR, f"content_calendar_30day_{today_str}_v{counter}.md")
            counter += 1

        with open(path, "w", encoding="utf-8") as f:
            f.write(md)

        return path


# Singleton
urdu_calendar_exporter = UrduCalendarExporter()
