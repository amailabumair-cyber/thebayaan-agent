import json
import logging
from typing import Dict, Any, List
from sqlalchemy import select, and_
from agent_am.config.settings import settings
from agent_am.database.connection import AsyncSessionLocal
from agent_am.database.models import (
    AuditReport,
    PostQueue,
    PostType,
    PostStatus,
    ExecutionLog,
    SystemHealth,
    ChannelConfig
)
from agent_am.core.workflow import workflow
from agent_am.core.queue_manager import queue_manager
from agent_am.services.ai_engine import ai_engine
from agent_am.services.youtube_service import youtube_service

logger = logging.getLogger("agent_am.commands")

class UrduCommandHandler:
    """
    صارف کے لیے اردو کمانڈ پروسیسر (Urdu Command Processor)
    مقررہ اردو ہدایات کو سمجھ کر بیک اینڈ پر مستند کارروائی کرتا ہے۔
    """

    async def handle_command(self, cmd_text: str) -> Dict[str, Any]:
        """اردو کمانڈ کو پروسیس کر کے جواب فراہم کرتا ہے"""
        cmd = cmd_text.strip()
        logger.info(f"موصول شدہ اردو کمانڈ: {cmd}")

        if "روزانہ آڈٹ شروع کریں" in cmd or "آڈٹ رن کریں" in cmd:
            return await self.cmd_run_audit()
        elif "آج کی رپورٹ دکھائیں" in cmd or "رپورٹ دکھائیں" in cmd:
            return await self.cmd_show_today_report()
        elif "اگلے دو دن کی پوسٹس دکھائیں" in cmd or "پوسٹس دکھائیں" in cmd or "قطار دکھائیں" in cmd:
            return await self.cmd_show_upcoming_posts()
        elif "شیڈول شدہ پوسٹس کی تصدیق کریں" in cmd or "تصدیق کریں" in cmd:
            return await self.cmd_verify_scheduled_posts()
        elif "ناکام کاموں کی تفصیل دکھائیں" in cmd or "ایرر دکھائیں" in cmd:
            return await self.cmd_show_failed_tasks()
        elif "ایجنٹ کا سسٹم اسٹیٹس دکھائیں" in cmd or "اسٹیٹس دکھائیں" in cmd or "سسٹم ہیلتھ" in cmd:
            return await self.cmd_show_system_status()
        elif "نئی کوئز پوسٹ تیار کریں" in cmd or "کوئز تیار کریں" in cmd:
            return await self.cmd_generate_single_quiz()
        elif "نیا ٹیکسٹ پول تیار کریں" in cmd or "پول تیار کریں" in cmd:
            return await self.cmd_generate_single_poll()
        else:
            return {
                "success": False,
                "command": cmd,
                "message_urdu": (
                    f"معذرت، کمانڈ '{cmd}' کی شناخت نہیں ہو سکی۔\n"
                    "دستیاب کمانڈز:\n"
                    "1. 'روزانہ آڈٹ شروع کریں'\n"
                    "2. 'آج کی رپورٹ دکھائیں'\n"
                    "3. 'اگلے دو دن کی پوسٹس دکھائیں'\n"
                    "4. 'شیڈول شدہ پوسٹس کی تصدیق کریں'\n"
                    "5. 'ناکام کاموں کی تفصیل دکھائیں'\n"
                    "6. 'ایجنٹ کا سسٹم اسٹیٹس دکھائیں'\n"
                    "7. 'نئی کوئز پوسٹ تیار کریں'\n"
                    "8. 'نیا ٹیکسٹ پول تیار کریں'"
                )
            }

    async def cmd_run_audit(self) -> Dict[str, Any]:
        """روزانہ آڈٹ دستی طور پر چلاتا ہے"""
        res = await workflow.execute_daily_workflow(is_manual=True)
        return {
            "success": True,
            "title_urdu": "روزانہ آڈٹ مکمل ہو گیا ہے",
            "message_urdu": (
                f"چینل 'The Bayan' کا آڈٹ کامیابی سے مکمل ہوا۔\n"
                f"تاریخ: {res['report_date']}\n"
                f"زیرِ التواء شیڈول پوسٹس: {res['upcoming_posts_count']}\n"
                f"فائل کا راستہ: {res.get('report_paths', {}).get('markdown_path', '')}"
            ),
            "data": res
        }

    async def cmd_show_today_report(self) -> Dict[str, Any]:
        """آج کی محفوظ شدہ آڈٹ رپورٹ دکھاتا ہے"""
        today_str = settings.now().strftime("%Y-%m-%d")
        async with AsyncSessionLocal() as session:
            stmt = select(AuditReport).where(AuditReport.report_date == today_str)
            res = await session.execute(stmt)
            rep = res.scalar_one_or_none()
            if not rep:
                # اگر آج کی رپورٹ موجود نہیں تو پہلے آڈٹ رن کریں
                await workflow.execute_daily_workflow(is_manual=True)
                res = await session.execute(stmt)
                rep = res.scalar_one_or_none()

            if rep:
                return {
                    "success": True,
                    "title_urdu": f"آج کی آڈٹ رپورٹ ({today_str})",
                    "message_urdu": rep.summary_urdu,
                    "report_date": today_str,
                    "markdown_path": rep.markdown_path,
                    "html_path": rep.html_path,
                    "total_views": rep.total_views,
                    "total_subscribers": rep.total_subscribers
                }
            return {
                "success": False,
                "message_urdu": f"تاریخ {today_str} کے لیے کوئی رپورٹ تیار نہیں ہو سکی۔"
            }

    async def cmd_show_upcoming_posts(self) -> Dict[str, Any]:
        """اگلے دو دن کی پوسٹس دکھاتا ہے"""
        posts = await queue_manager.get_upcoming_queue(days_ahead=2)
        if not posts:
            # اگر خالی ہے تو قطار کو بھریں
            await queue_manager.replenish_queue(days_ahead=2)
            posts = await queue_manager.get_upcoming_queue(days_ahead=2)

        summary_lines = []
        for p in posts:
            label = "کوئز (Quiz)" if p["post_type"] == "QUIZ" else "ٹیکسٹ پول (Text Poll)"
            summary_lines.append(f"• {label} [{p['target_date']} - {p['scheduled_time']}]: {p['question_text']} ({p['status']})")

        return {
            "success": True,
            "title_urdu": "اگلے 48 گھنٹوں کی قطار (Scheduled Posts)",
            "message_urdu": "\n".join(summary_lines) if summary_lines else "کوئی شیڈول شدہ پوسٹ موجود نہیں ہے۔",
            "posts": posts
        }

    async def cmd_verify_scheduled_posts(self) -> Dict[str, Any]:
        """شیڈول شدہ پوسٹس کی تصدیق کرتا ہے"""
        posts = await queue_manager.get_upcoming_queue(days_ahead=2)
        verified_count = sum(1 for p in posts if p["status"] in ["SCHEDULED", "VALIDATED"])
        return {
            "success": True,
            "title_urdu": "شیڈول شدہ پوسٹس کی تصدیق کا نتیجہ",
            "message_urdu": f"کل پوسٹس: {len(posts)} | مصدقہ اور تیار پوسٹس: {verified_count}",
            "verified_count": verified_count,
            "total_count": len(posts)
        }

    async def cmd_show_failed_tasks(self) -> Dict[str, Any]:
        """ناکام کاموں کی تفصیل دکھاتا ہے"""
        async with AsyncSessionLocal() as session:
            stmt = select(ExecutionLog).where(ExecutionLog.status.in_(["FAILED", "WARNING"])).order_by(ExecutionLog.id.desc()).limit(10)
            res = await session.execute(stmt)
            logs = res.scalars().all()

            if not logs:
                return {
                    "success": True,
                    "title_urdu": "ناکام کاموں کا جائزہ",
                    "message_urdu": "ماشاء اللہ! سسٹم میں کوئی ناکام کام یا خرابی موجود نہیں ہے۔ تمام کام معمول کے مطابق سرانجام پا رہے ہیں۔"
                }

            lines = []
            for l in logs:
                lines.append(f"• [{l.created_at.strftime('%Y-%m-%d %H:%M')}] جاب: {l.job_name} | ایرر: {l.error_message}")

            return {
                "success": True,
                "title_urdu": "حالیہ ناکام یا انتباہی لاگز",
                "message_urdu": "\n".join(lines),
                "count": len(logs)
            }

    async def cmd_show_system_status(self) -> Dict[str, Any]:
        """سسٹم کا لائیو اسٹیٹس فراہم کرتا ہے"""
        async with AsyncSessionLocal() as session:
            stmt = select(SystemHealth)
            res = await session.execute(stmt)
            healths = res.scalars().all()

            lines = [f"ایجنٹ نام: {settings.AGENT_NAME}", f"ٹائم زون: {settings.TIMEZONE} (PST)", f"چینل: {settings.CHANNEL_NAME}"]
            for h in healths:
                lines.append(f"• {h.component}: {h.status} ({h.message_urdu})")

            return {
                "success": True,
                "title_urdu": "ایجنٹ اے ایم لائیو سسٹم اسٹیٹس",
                "message_urdu": "\n".join(lines)
            }

    async def cmd_generate_single_quiz(self) -> Dict[str, Any]:
        """ایک نیا اسلامی تاریخ کوئز تیار کر کے دکھاتا ہے"""
        quiz = await ai_engine.generate_quiz()
        return {
            "success": True,
            "title_urdu": "نیا اسلامی تاریخ کوئز تیار ہے",
            "message_urdu": (
                f"سوال: {quiz['question']}\n"
                f"آپشنز: {', '.join(quiz['options'])}\n"
                f"درست جواب: {quiz.get('correct_answer')}\n"
                f"وضاحت: {quiz.get('explanation')}\n"
                f"ماخذ: {quiz.get('source_reference')}"
            ),
            "data": quiz
        }

    async def cmd_generate_single_poll(self) -> Dict[str, Any]:
        """ایک نیا ٹیکسٹ پول تیار کر کے دکھاتا ہے"""
        poll = await ai_engine.generate_poll()
        return {
            "success": True,
            "title_urdu": "نیا ٹیکسٹ پول تیار ہے",
            "message_urdu": (
                f"سوال: {poll['question']}\n"
                f"آپشنز:\n" + "\n".join([f"• {opt}" for opt in poll['options']]) + f"\nماخذ/مقصد: {poll.get('source_reference')}"
            ),
            "data": poll
        }

urdu_commands = UrduCommandHandler()
