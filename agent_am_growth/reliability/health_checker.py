import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy import select, and_
from agent_am.config.settings import settings
from agent_am.database.connection import AsyncSessionLocal
from agent_am.database.models import PostQueue, PostStatus, SystemHealth
from agent_am.services.youtube_service import youtube_service
from agent_am.services.scheduler_service import scheduler_service

logger = logging.getLogger("agent_am.health_checker")

class HealthChecker:
    """
    سسٹم ہیلتھ مانیٹر اور مسڈ ٹاسک ڈیٹیکٹر (Health Monitor & Missed Task Detector)
    ڈیٹا بیس، شیڈولر، یوٹیوب کنکشن، لاگ ان سیشن اور چھوٹی ہوئی پوسٹس کی ہمہ وقت نگرانی کرتا ہے۔
    """

    async def check_full_health(self) -> Dict[str, Any]:
        """تمام اہم ماڈیولز کی لائیو جانچ کرتا ہے"""
        health_report = {
            "timestamp": settings.now().strftime("%Y-%m-%d %I:%M %p PST"),
            "overall_status": "HEALTHY",
            "components": {},
            "missed_tasks": []
        }

        # 1. ڈیٹا بیس ہیلتھ
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(select(1))
            health_report["components"]["database"] = {
                "status": "HEALTHY",
                "message_urdu": "SQLite ڈیٹا بیس کنکشن فعال اور مستعد ہے"
            }
        except Exception as e:
            health_report["components"]["database"] = {
                "status": "DOWN",
                "message_urdu": f"ڈیٹا بیس کنکشن میں خرابی: {str(e)}"
            }
            health_report["overall_status"] = "DOWN"

        # 2. شیڈولر ہیلتھ
        sched_running = scheduler_service.is_running
        health_report["components"]["scheduler"] = {
            "status": "HEALTHY" if sched_running else "WARNING",
            "message_urdu": "بیک گراؤنڈ شیڈولر فعال ہے (Asia/Karachi)" if sched_running else "شیڈولر اس وقت غیر فعال ہے"
        }
        if not sched_running and health_report["overall_status"] == "HEALTHY":
            health_report["overall_status"] = "DEGRADED"

        # 3. یوٹیوب ڈیٹا اے پی آئی
        yt_ok = youtube_service.is_configured()
        health_report["components"]["youtube_api"] = {
            "status": "HEALTHY" if yt_ok else "WARNING",
            "message_urdu": "یوٹیوب ڈیٹا اے پی آئی چابی مصدقہ ہے" if yt_ok else "یوٹیوب چابی موجود نہیں"
        }

        # 4. براؤزر لاگ ان سیشن
        session_file = Path("./browser_session/storage_state.json")
        session_ok = session_file.exists() and session_file.stat().st_size > 500
        health_report["components"]["browser_session"] = {
            "status": "HEALTHY" if session_ok else "WARNING",
            "message_urdu": "یوٹیوب اسٹوڈیو لاگ ان سیشن متحرک ہے" if session_ok else "لاگ ان سیشن موجود نہیں یا نامکمل ہے"
        }

        # 5. چھوٹی ہوئی پوسٹس کی جانچ (Missed Tasks Detection)
        missed = await self.detect_missed_tasks()
        health_report["missed_tasks"] = missed
        if missed and health_report["overall_status"] == "HEALTHY":
            health_report["overall_status"] = "WARNING"

        return health_report

    async def detect_missed_tasks(self) -> List[Dict[str, Any]]:
        """
        ایسی تمام پوسٹس تلاش کرتا ہے جن کا وقت گزر چکا ہے مگر وہ ابھی تک شائع نہیں ہو سکیں
        """
        now_pkt = settings.now()
        missed_list = []

        try:
            async with AsyncSessionLocal() as session:
                stmt = select(PostQueue).where(
                    and_(
                        PostQueue.status == PostStatus.VALIDATED,
                        PostQueue.scheduled_time < now_pkt
                    )
                ).order_by(PostQueue.scheduled_time.asc())
                res = await session.execute(stmt)
                records = res.scalars().all()

                for r in records:
                    missed_list.append({
                        "id": r.id,
                        "post_type": r.post_type.value,
                        "target_date": r.target_date,
                        "scheduled_time": r.scheduled_time.strftime("%Y-%m-%d %I:%M %p PST"),
                        "question_text": r.question_text,
                        "delay_hours": round((now_pkt - r.scheduled_time.replace(tzinfo=settings.tz)).total_seconds() / 3600, 1)
                    })
        except Exception as e:
            logger.error(f"چھوٹی ہوئی پوسٹس تلاش کرنے میں خرابی: {str(e)}")

        return missed_list

health_checker = HealthChecker()
