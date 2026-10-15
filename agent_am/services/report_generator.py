import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy import select
from agent_am.config.settings import settings
from agent_am.database.connection import AsyncSessionLocal
from agent_am.database.models import AuditReport, PostQueue, PostStatus
from agent_am.services.notification_service import notification_service

logger = logging.getLogger("agent_am.report_generator")

class ReportGenerator:
    """
    روزانہ اردو آڈٹ رپورٹ جنریٹر (Daily Urdu Report Generator)
    چینل کی تمام تفصیلات، سفارشات، اور شیڈول شدہ پوسٹس کو مارک ڈاؤن اور ایچ ٹی ایم ایل میں مستقل محفوظ کرتا ہے۔
    """

    def __init__(self):
        self.reports_dir = Path(settings.REPORTS_DIR)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    async def generate_and_save_report(
        self,
        audit_data: Dict[str, Any],
        upcoming_posts: List[Dict[str, Any]],
        failed_tasks: List[str] = None
    ) -> Dict[str, Any]:
        """
        مکمل روزانہ کی رپورٹ تیار کر کے مستقل فائلز اور ڈیٹا بیس میں محفوظ کرتا ہے۔
        """
        report_date = audit_data["report_date"]
        period_start_str = audit_data["period_start"].strftime("%Y-%m-%d %I:%M %p PST")
        period_end_str = audit_data["period_end"].strftime("%Y-%m-%d %I:%M %p PST")
        channel_name = audit_data.get("channel_title", settings.CHANNEL_NAME)
        ai_analysis = audit_data.get("ai_analysis", {})

        # مارک ڈاؤن مواد کی تیاری (Markdown Report)
        md_lines = [
            f"# 📊 روزانہ آڈٹ رپورٹ برائے یوٹیوب چینل: {channel_name}",
            f"**تاریخ رپورٹ:** {report_date} | **رپورٹنگ دورانیہ:** {period_start_str} تا {period_end_str}",
            f"**ایجنٹ:** {settings.AGENT_NAME} | **ٹائم زون:** Asia/Karachi (پاکستان کا معیاری وقت)\n",
            "---",
            "## 1. چینل کے مجموعی شماریات (Channel Overview)",
            f"- **کل سبسکرائبرز:** {audit_data.get('total_subscribers', 0):,}",
            f"- **کل مشاہدات (Views):** {audit_data.get('total_views', 0):,}",
            f"- **کل اپلوڈ شدہ ویڈیوز:** {audit_data.get('total_videos', 0)}",
            f"- **حالیہ زیرِ جائزہ ویڈیوز:** {audit_data.get('recent_videos_count', 0)}\n",
            "## 2. اعلیٰ کارکردگی کا مظاہرہ کرنے والی ویڈیوز (Top Performing)",
        ]

        top_vids = audit_data.get("top_videos", [])
        if top_vids:
            for i, v in enumerate(top_vids, 1):
                md_lines.append(f"{i}. **{v['title']}** — ویوز: {v.get('views', 0):,} | لائیکس: {v.get('likes', 0):,} | کمنٹس: {v.get('comments', 0):,}")
        else:
            md_lines.append("_کوئی ویڈیو دستیاب نہیں ہوئی۔_")

        md_lines.append("\n## 3. وہ ویڈیوز جن میں بہتری کی گنجائش ہے (Areas for Improvement)")
        low_vids = audit_data.get("low_videos", [])
        if low_vids:
            for i, v in enumerate(low_vids, 1):
                md_lines.append(f"{i}. **{v['title']}** — ویوز: {v.get('views', 0):,} | لائیکس: {v.get('likes', 0):,}")
        else:
            md_lines.append("_ڈیٹا محدود ہونے کے باعث فہرست دستیاب نہیں ہے۔_")

        md_lines.append("\n## 4. سامعین کی دلچسپی اور ڈیٹا پر مبنی مشاہدات (Audience Insights)")
        for obs in ai_analysis.get("top_performing_observations", []):
            md_lines.append(f"- 💡 {obs}")
        for obs in ai_analysis.get("underperforming_observations", []):
            md_lines.append(f"- ⚠️ {obs}")

        md_lines.append("\n## 5. مواد کے لیے اسٹریٹجک سفارشات (Strategic Recommendations)")
        for rec in ai_analysis.get("recommendations", []):
            md_lines.append(f"- ✅ {rec}")

        md_lines.append("\n## 6. آئندہ موضوعات کی تجاویز (Future Content Ideas)")
        for topic in ai_analysis.get("future_topics", []):
            md_lines.append(f"- 📌 {topic}")

        md_lines.append("\n## 7. رولنگ 24-48 گھنٹے کمیونٹی پوسٹس کی صورتحال (Quiz & Poll Queue)")
        if upcoming_posts:
            for p in upcoming_posts:
                post_type_label = "کوئز (Quiz)" if p.get("post_type") == "QUIZ" else "ٹیکسٹ پول (Text Poll)"
                status_icon = "🟢" if p.get("status") in [PostStatus.SCHEDULED, PostStatus.VALIDATED] else "🟡"
                md_lines.append(f"- {status_icon} **{post_type_label}** برائے تاریخ: `{p.get('target_date')}` | وقت: `{p.get('scheduled_time')}`")
                md_lines.append(f"  - **سوال:** {p.get('question_text')}")
                if p.get("correct_answer"):
                    md_lines.append(f"  - **درست جواب:** {p.get('correct_answer')}")
                if p.get("source_reference"):
                    md_lines.append(f"  - **ماخذ/حوالہ:** {p.get('source_reference')}")
                md_lines.append(f"  - **اسٹیٹس:** {p.get('status')}\n")
        else:
            md_lines.append("_قطار میں فی الوقت کوئی پوسٹ زیرِ التواء نہیں ہے۔_\n")

        md_lines.append("## 8. ناکام کام اور درکار اجازتیں (Issues & Permissions)")
        if failed_tasks:
            for ft in failed_tasks:
                md_lines.append(f"- ❌ {ft}")
        else:
            md_lines.append("- ✅ تمام سسٹمز معمول کے مطابق کام کر رہے ہیں اور کوئی خرابی ریکارڈ نہیں ہوئی۔\n")

        md_lines.append("## 9. اگلے مجوزہ اقدامات (Next Action Items)")
        md_lines.append("1. شام 6:00 تا 9:00 بجے (PST) شیڈول شدہ کمیونٹی کوئز اور پول کی اشاعت کی توثیق۔")
        md_lines.append("2. اگلے 48 گھنٹوں کی قطار میں نئے علمی سوالات کا اضافہ۔")
        md_lines.append("3. تجویز کردہ تاریخی موضوعات پر ویڈیو اسکرپٹس کا جائزہ۔")

        markdown_content = "\n".join(md_lines)

        # فائلز میں محفوظ کریں (Permanent Storage)
        md_file_path = self.reports_dir / f"audit_report_{report_date}.md"
        html_file_path = self.reports_dir / f"audit_report_{report_date}.html"

        with open(md_file_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        html_content = self._render_html_report(report_date, channel_name, markdown_content)
        with open(html_file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # ڈیٹا بیس میں محفوظ کریں
        summary_urdu = ai_analysis.get("summary_urdu", f"چینل {channel_name} کا یومیہ آڈٹ مکمل ہو گیا ہے۔")
        async with AsyncSessionLocal() as session:
            stmt = select(AuditReport).where(AuditReport.report_date == report_date)
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()

            if not existing:
                report_rec = AuditReport(
                    report_date=report_date,
                    period_start=audit_data["period_start"],
                    period_end=audit_data["period_end"],
                    total_views=audit_data.get("total_views", 0),
                    total_subscribers=audit_data.get("total_subscribers", 0),
                    total_videos=audit_data.get("total_videos", 0),
                    top_performing_videos=json.dumps(top_vids, ensure_ascii=False),
                    low_performing_videos=json.dumps(low_vids, ensure_ascii=False),
                    recommendations_urdu=json.dumps(ai_analysis.get("recommendations", []), ensure_ascii=False),
                    summary_urdu=summary_urdu,
                    markdown_path=str(md_file_path),
                    html_path=str(html_file_path)
                )
                session.add(report_rec)
            else:
                existing.total_views = audit_data.get("total_views", 0)
                existing.total_subscribers = audit_data.get("total_subscribers", 0)
                existing.top_performing_videos = json.dumps(top_vids, ensure_ascii=False)
                existing.summary_urdu = summary_urdu
                existing.markdown_path = str(md_file_path)
                existing.html_path = str(html_file_path)

            await session.commit()

        # صارف کو الرٹ روانہ کریں
        await notification_service.notify_daily_report_completed(report_date, summary_urdu)

        return {
            "report_date": report_date,
            "markdown_path": str(md_file_path),
            "html_path": str(html_file_path),
            "summary_urdu": summary_urdu
        }

    def _render_html_report(self, report_date: str, channel_name: str, md_text: str) -> str:
        """خوبصورت اور ریسپانسو اردو ایچ ٹی ایم ایل رپورٹ بناتا ہے"""
        # سادہ اور خوبصورت HTML رینڈرنگ
        paragraphs = md_text.split("\n\n")
        body_html = ""
        for p in paragraphs:
            if p.startswith("# "):
                body_html += f"<h1>{p[2:]}</h1>\n"
            elif p.startswith("## "):
                body_html += f"<h2>{p[3:]}</h2>\n"
            elif p.startswith("### "):
                body_html += f"<h3>{p[4:]}</h3>\n"
            elif p.startswith("- "):
                items = p.split("\n- ")
                body_html += "<ul>\n" + "".join([f"<li>{item.replace('- ', '')}</li>\n" for item in items]) + "</ul>\n"
            elif p.startswith("1. "):
                items = p.split("\n")
                body_html += "<ol>\n" + "".join([f"<li>{item[3:]}</li>\n" for item in items if item.strip()]) + "</ol>\n"
            else:
                body_html += f"<p>{p.replace(chr(10), '<br>')}</p>\n"

        return f"""<!DOCTYPE html>
<html lang="ur" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>آڈٹ رپورٹ - {channel_name} ({report_date})</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif, 'Noto Nastaliq Urdu';
            background-color: #0f172a;
            color: #f1f5f9;
            line-height: 1.8;
            padding: 2rem;
            margin: 0;
            direction: rtl;
        }}
        .container {{
            max-width: 900px;
            margin: auto;
            background: #1e293b;
            padding: 2.5rem;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            border: 1px solid #334155;
        }}
        h1 {{ color: #38bdf8; border-bottom: 2px solid #38bdf8; padding-bottom: 0.5rem; font-size: 1.8rem; }}
        h2 {{ color: #818cf8; margin-top: 1.8rem; font-size: 1.4rem; }}
        h3 {{ color: #cbd5e1; }}
        p, li {{ font-size: 1.05rem; }}
        ul, ol {{ padding-right: 1.5rem; }}
        code {{ background: #0f172a; padding: 2px 6px; border-radius: 4px; color: #38bdf8; font-family: monospace; }}
        hr {{ border: 0; border-top: 1px solid #334155; margin: 1.5rem 0; }}
        .badge {{ background: #0369a1; padding: 4px 10px; border-radius: 6px; font-size: 0.85rem; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <span class="badge">Agent AM آڈٹ آرکائیو</span>
        {body_html}
    </div>
</body>
</html>"""

report_generator = ReportGenerator()
