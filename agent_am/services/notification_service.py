import logging
import httpx
from typing import Optional
from agent_am.config.settings import settings

logger = logging.getLogger("agent_am.notifications")

class NotificationService:
    """
    اطلاعاتی سروس برائے ایجنٹ اے ایم (Agent AM Notification & Alerting)
    صارف کو اہم واقعات، آڈٹ رپورٹس، اور ناکامیوں سے اردو میں مطلع کرتی ہے۔
    """

    def __init__(self):
        self.webhook_url = settings.ALERT_WEBHOOK_URL.strip()
        self._last_alert_key: Optional[str] = None

    async def send_alert(self, title_urdu: str, message_urdu: str, level: str = "INFO") -> bool:
        """
        اردو الرٹ روانہ کرتا ہے۔ ڈپلیکیٹ فلڈ روکنے کے ساتھ۔
        """
        alert_key = f"{title_urdu}:{message_urdu[:50]}"
        if level != "INFO" and alert_key == self._last_alert_key:
            logger.info("ایک جیسا ایرر بار بار بھیجنے سے روکا گیا (Duplicate alert suppressed)")
            return False

        logger.info(f"[{level}] {title_urdu}: {message_urdu}")

        if not self.webhook_url:
            # اگر ویب ہک کنفیگرڈ نہیں ہے تو لوکل لاگنگ ہی کافی ہے
            return False

        payload = {
            "agent": settings.AGENT_NAME,
            "channel": settings.CHANNEL_NAME,
            "title": title_urdu,
            "message": message_urdu,
            "level": level,
            "timestamp": settings.now().strftime("%Y-%m-%d %I:%M %p PST")
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self.webhook_url, json=payload)
                if 200 <= res.status_code < 300:
                    self._last_alert_key = alert_key
                    return True
                else:
                    logger.warning(f"الرٹ بھیجنے میں خرابی: اسٹیٹس کوڈ {res.status_code}")
                    return False
        except Exception as e:
            logger.error(f"ویب ہک الرٹ بھیجنے میں ناکامی: {str(e)}")
            return False

    async def notify_daily_report_completed(self, report_date: str, summary_urdu: str):
        """روزانہ کی رپورٹ تیار ہونے کی اطلاع"""
        title = f"📢 روزانہ آڈٹ رپورٹ مکمل ({report_date})"
        await self.send_alert(title, summary_urdu, level="INFO")

    async def notify_post_scheduled(self, post_type: str, target_date: str, post_time: str, question: str):
        """کمیونٹی پوسٹ کے کامیابی سے شیڈول ہونے کی اطلاع"""
        type_name = "کوئز (Quiz)" if post_type == "QUIZ" else "ٹیکسٹ پول (Text Poll)"
        title = f"✅ نئی {type_name} شیڈول کر دی گئی"
        msg = f"تاریخ: {target_date}\nوقت: {post_time}\nسوال: {question}"
        await self.send_alert(title, msg, level="INFO")

    async def notify_failure(self, task_name_urdu: str, error_details: str):
        """کسی بھی جاب یا سروس کی ناکامی کا الرٹ"""
        title = f"⚠️ خرابی کی اطلاع: {task_name_urdu}"
        await self.send_alert(title, error_details, level="ERROR")

notification_service = NotificationService()
