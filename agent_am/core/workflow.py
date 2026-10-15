import time
import logging
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy import select
from agent_am.config.settings import settings
from agent_am.database.connection import AsyncSessionLocal
from agent_am.database.models import ExecutionLog, SystemHealth
from agent_am.services.audit_service import audit_service
from agent_am.services.report_generator import report_generator
from agent_am.core.queue_manager import queue_manager
from agent_am.services.youtube_service import youtube_service
from agent_am.services.notification_service import notification_service

logger = logging.getLogger("agent_am.workflow")

class AutonomousWorkflow:
    """
    خودکار یومیہ ورک فلو برائے Agent AM (Autonomous Daily Workflow)
    مرحلہ وار بغیر کسی انسانی مداخلت کے مکمل خودکار طریقے سے انجام پاتا ہے۔
    """

    async def execute_daily_workflow(self, is_manual: bool = False) -> Dict[str, Any]:
        """
        پانچوں مراحل پر مشتمل یومیہ ورک فلو چلاتا ہے
        """
        start_time = time.time()
        now_pkt = settings.now()
        report_date = now_pkt.strftime("%Y-%m-%d")
        task_label = "دستی عمل (Manual)" if is_manual else "خودکار یومیہ شیڈول (Scheduled)"
        
        logger.info(f"=== {task_label}: تاریخ {report_date} کے ورک فلو کا آغاز ===")
        failed_tasks: List[str] = []

        # =====================================================================
        # مرحلہ 1: سسٹم ہیلتھ اور کنکشن چیک (Stage 1: Pre-flight & Health Check)
        # =====================================================================
        try:
            yt_status = "HEALTHY" if youtube_service.is_configured() else "DEGRADED"
            ai_status = "HEALTHY" if settings.is_ai_configured() else "DEGRADED"
            await self._update_health("youtube_api", yt_status, "یوٹیوب ڈیٹا اے پی آئی کنکشن لائیو ہے" if yt_status == "HEALTHY" else "یوٹیوب اے پی آئی کی موجود نہیں، ٹیسٹنگ موڈ فعال ہے")
            await self._update_health("ai_engine", ai_status, f"اے آئی ماڈل فعال ہے ({settings.AI_PROVIDER})" if ai_status == "HEALTHY" else "اے آئی چابی درکار ہے، مستند فال بیک کیٹلاگ فعال ہے")
            await self._update_health("scheduler", "HEALTHY", "پس منظر شیڈولر فعال اور مستعد ہے")
        except Exception as e:
            failed_tasks.append(f"مرحلہ 1 (سسٹم ہیلتھ): {str(e)}")

        # =====================================================================
        # مرحلہ 2: دی بیان چینل کا آڈٹ (Stage 2: Audit The Bayan)
        # =====================================================================
        audit_data = {}
        try:
            audit_data = await audit_service.perform_daily_audit()
        except Exception as e:
            err_msg = f"مرحلہ 2 (چینل آڈٹ میں خرابی): {str(e)}"
            logger.error(err_msg)
            failed_tasks.append(err_msg)
            # کم سے کم ڈیٹا فراہم کریں تاکہ اگلا مرحلہ نہ رکے
            audit_data = {
                "report_date": report_date,
                "period_start": now_pkt,
                "period_end": now_pkt,
                "channel_title": settings.CHANNEL_NAME,
                "total_views": 0,
                "total_subscribers": 0,
                "total_videos": 0,
                "recent_videos_count": 0,
                "top_videos": [],
                "low_videos": [],
                "ai_analysis": {}
            }

        # =====================================================================
        # مرحلہ 3: کوئز اور پول قطار کی تیاری (Stage 3: Replenish Queue)
        # =====================================================================
        try:
            await queue_manager.replenish_queue(days_ahead=2)
        except Exception as e:
            err_msg = f"مرحلہ 3 (پوسٹنگ قطار میں خرابی): {str(e)}"
            logger.error(err_msg)
            failed_tasks.append(err_msg)

        # آئندہ شیڈول شدہ پوسٹس حاصل کریں
        upcoming_posts = await queue_manager.get_upcoming_queue(days_ahead=2)

        # =====================================================================
        # مرحلہ 4: اردو آڈٹ رپورٹ کی تیاری و محفوظگی (Stage 4: Generate Report)
        # =====================================================================
        report_result = {}
        try:
            report_result = await report_generator.generate_and_save_report(
                audit_data=audit_data,
                upcoming_posts=upcoming_posts,
                failed_tasks=failed_tasks
            )
        except Exception as e:
            err_msg = f"مرحلہ 4 (رپورٹ جنریشن میں خرابی): {str(e)}"
            logger.error(err_msg)
            failed_tasks.append(err_msg)

        # =====================================================================
        # مرحلہ 5: لاگنگ اور سمری ریکارڈ (Stage 5: Logging & Finalization)
        # =====================================================================
        duration_ms = int((time.time() - start_time) * 1000)
        overall_status = "FAILED" if len(failed_tasks) > 1 else ("WARNING" if failed_tasks else "SUCCESS")

        async with AsyncSessionLocal() as session:
            exec_log = ExecutionLog(
                job_name="daily_autonomous_workflow",
                task_type="FULL_DAILY_PIPELINE",
                status=overall_status,
                duration_ms=duration_ms,
                details_urdu=f"تاریخ: {report_date} | دورانیہ: {duration_ms}ms | زیرِ التواء پوسٹس: {len(upcoming_posts)}",
                error_message="; ".join(failed_tasks) if failed_tasks else None
            )
            session.add(exec_log)
            await session.commit()

        logger.info(f"=== {task_label} کامیابی سے مکمل ہوا۔ اسٹیٹس: {overall_status} ({duration_ms}ms) ===")
        return {
            "status": overall_status,
            "report_date": report_date,
            "duration_ms": duration_ms,
            "upcoming_posts_count": len(upcoming_posts),
            "report_paths": report_result,
            "failed_tasks": failed_tasks
        }

    async def _update_health(self, component: str, status: str, msg_urdu: str):
        """ماڈیول کی ہیلتھ اپڈیٹ کرتا ہے"""
        async with AsyncSessionLocal() as session:
            stmt = select(SystemHealth).where(SystemHealth.component == component)
            res = await session.execute(stmt)
            entry = res.scalar_one_or_none()
            if not entry:
                entry = SystemHealth(
                    component=component,
                    status=status,
                    message_urdu=msg_urdu,
                    last_checked_at=datetime.utcnow()
                )
                session.add(entry)
            else:
                entry.status = status
                entry.message_urdu = msg_urdu
                entry.last_checked_at = datetime.utcnow()
            await session.commit()

workflow = AutonomousWorkflow()
