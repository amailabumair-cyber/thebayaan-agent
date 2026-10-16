"""
urdu_production_exporter.py — Phase 5: Production Package Markdown Exporter
===========================================================================
ویڈیو پروڈکشن پیکیج (اسکرپٹ، مستند مآخذ، بصری پرامپٹس، ایڈیٹنگ چیک لسٹ، میٹا ڈیٹا)
کو باضابطہ اردو مارک ڈاؤن رپورٹ کی شکل میں `reports/` فولڈر میں برآمد کرتا ہے۔
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional

import pytz

from agent_am.database.models import VideoProductionProject
from .pipeline_manager import pipeline_manager
from .script_builder import script_builder

logger = logging.getLogger("agent_am.production_pipeline.urdu_production_exporter")

PKT = pytz.timezone("Asia/Karachi")
REPORTS_DIR = "reports"


class UrduProductionExporter:
    """
    پروڈکشن پیکیج کو مارک ڈاؤن میں محفوظ کرنے والا ایکسپورٹر۔
    """

    async def export_production_package(
        self, project_code: str = "VPP-001", save_to_file: bool = True
    ) -> str:
        """
        کسی بھی پروجیکٹ کا مکمل پروڈکشن پیکیج تیار اور محفوظ کرے۔
        """
        now_pkt = datetime.now(PKT)
        today_str = now_pkt.strftime("%Y-%m-%d")
        time_str = now_pkt.strftime("%I:%M %p")

        # پہلے تصدیق کریں کہ فلیگ شپ پروجیکٹ سیڈ ہو چکا ہے
        await script_builder.seed_flagship_project()

        project = await pipeline_manager.get_project(project_code)
        if not project:
            return f"خرابی: پروجیکٹ کوڈ '{project_code}' نہیں ملا۔"

        sources = json.loads(project.verified_sources_json or "[]")
        scene_prompts = json.loads(project.scene_prompts_json or "[]")
        voiceover_checklist = json.loads(project.voiceover_checklist_json or "[]")
        titles = json.loads(project.suggested_titles_json or "[]")
        tags = json.loads(project.tags_json or "[]")

        lines = [
            f"# 🎬 The Bayaan — ویڈیو پروڈکشن پیکیج [{project.project_code}]",
            "",
            f"**عنوان:** {project.title_urdu}",
            f"**موجودہ مرحلہ:** `{project.stage.value}` | **ہدف اشاعت:** {project.target_publish_date or 'طے شدہ نہیں'}",
            f"**اشاعت کی حتمی منظوری:** {'✅ منظور شدہ' if project.is_publication_approved else '⏳ انسانی منظوری کی منتظر (Strict Gate)'}",
            f"**تاریخ رپورٹ:** {today_str} ({time_str} PKT)",
            "",
            "---",
            "",
            "## 📜 1. مستند تاریخی تحقیق اور مصدقہ مآخذ (Primary & Authentic Sources)",
            "",
            f"> **تاریخی خلاصہ:** {project.historical_notes_urdu}",
            "",
            "### مصدقہ مآخذ و حوالہ جات:",
        ]

        for s in sources:
            lines.append(f"- 📖 {s}")

        if project.disputed_points_notes_urdu:
            lines += [
                "",
                "### ⚠️ روایات کی احتیاط و متنازعہ مقامات:",
                f"> {project.disputed_points_notes_urdu}",
            ]

        lines += [
            "",
            "---",
            "",
            "## ⚡ 2. ابتدائی 15 سیکنڈ کا پاور ہک (Hook Script)",
            "",
            f"> **\"{project.opening_hook_urdu}\"**",
            "",
            "---",
            "",
            "## ⏱️ 3. اسکرپٹ کا زمانی خاکہ (Script Outline & Timings)",
            "",
            "```text",
            project.script_outline_urdu or "",
            "```",
            "",
            "---",
            "",
            "## 📝 4. مکمل اردو اسکرپٹ (Full Urdu Script)",
            "",
            project.full_script_draft_urdu or "",
            "",
            "---",
            "",
            "## 🎨 5. منظر بہ منظر بصری پرامپٹس (AI Visual Prompts for Midjourney/Flux)",
            "",
        ]

        for sp in scene_prompts:
            lines += [
                f"### منظر {sp.get('scene')} ({sp.get('timestamp')}):",
                f"**اردو صداکاری:** *\"{sp.get('narration_urdu')}\"*",
                f"**انگریزی پرامپٹ:**",
                f"```text",
                f"{sp.get('prompt')}",
                f"```",
                "",
            ]

        lines += [
            "---",
            "",
            "## 🎙️ 6. صداکاری و ایڈیٹنگ چیک لسٹ (Voiceover & Editing Checklist)",
            "",
        ]

        for chk in voiceover_checklist:
            lines.append(f"- [x] {chk}")

        lines += [
            "",
            "---",
            "",
            "## 🚀 7. یوٹیوب میٹا ڈیٹا اور ایس ای او (SEO Metadata)",
            "",
            "### تجویز کردہ 3 عنوانات:",
        ]

        for idx, t in enumerate(titles, 1):
            lines.append(f"{idx}. {t}")

        lines += [
            "",
            "### تھمب نیل کا بصری خاکہ:",
            f"> {project.thumbnail_concept_urdu}",
            "",
            "### مکمل یوٹیوب ڈسکرپشن مع ٹائم اسٹیمپس:",
            "```text",
            project.description_draft_urdu or "",
            "```",
            "",
            "### یوٹیوب سرچ ٹیگز:",
            f"`{', '.join(tags)}`",
            "",
            "---",
            "",
            "## 🛡️ اشاعت کے لیے کڑا گیٹ (Publication Approval Gate)",
            "",
            "> **سسٹم کا بنیادی قانون:** یہ ویڈیو اس وقت تک یوٹیوب پر اپلوڈ یا پبلش نہیں ہو سکتی جب تک ایڈمن صریح اجازت نہ دے۔",
            "> تمام فائلیں، اسکرپٹس اور پرامپٹس لوکل سسٹم میں تیار ہیں۔ حتمی ویڈیو کی ریکارڈنگ اور منظوری انسانی فیصلے کے تابع ہے۔",
            "",
            "---",
            f"*یہ مکمل پروڈکشن پیکیج Agent AM کے فیز 5 نے {now_pkt.strftime('%Y-%m-%d %H:%M')} (PKT) پر تیار کیا۔*",
        ]

        report_md = "\n".join(lines)

        if save_to_file:
            path = self._save_production_report(report_md, project_code)
            logger.info(f"پروڈکشن پیکیج فائل محفوظ: {path}")

        return report_md

    def _save_production_report(self, md: str, project_code: str) -> str:
        """رپورٹ فائل محفوظ کرے"""
        os.makedirs(REPORTS_DIR, exist_ok=True)
        path = os.path.join(REPORTS_DIR, f"production_package_{project_code}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        return path


# Singleton
urdu_production_exporter = UrduProductionExporter()
