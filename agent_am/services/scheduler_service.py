import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from agent_am.config.settings import settings
from agent_am.core.workflow import workflow
from agent_am.core.queue_manager import queue_manager

logger = logging.getLogger("agent_am.scheduler")

class SchedulerService:
    """
    پس منظر میں بلا تعطل چلنے والا شیڈولر سروس (Persistent Background Scheduler)
    پاکستان ٹائم زون (Asia/Karachi) کے مطابق روزانہ خودکار ورک فلو اور پوسٹنگ انجام دیتا ہے۔
    اینٹی گریویٹی یا براؤزر بند ہونے پر بھی بیک گراؤنڈ ورکر کے ذریعے متحرک رہتا ہے۔
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=settings.tz)
        self.is_running = False

    def setup_jobs(self):
        """تمام شیڈول شدہ جابز کو رجسٹر کرتا ہے"""
        # روزانہ تفصیلی آڈٹ اور ورک فلو کا وقت
        audit_hour, audit_minute = map(int, settings.DAILY_AUDIT_TIME.split(":"))

        # 1. روزانہ صبح کا بنیادی آڈٹ اور قطار کی تیاری
        self.scheduler.add_job(
            workflow.execute_daily_workflow,
            trigger=CronTrigger(hour=audit_hour, minute=audit_minute, timezone=settings.tz),
            id="daily_morning_audit_workflow",
            name="یومیہ آڈٹ اور قطار تیاری",
            replace_existing=True,
            misfire_grace_time=3600,
            coalesce=True
        )
        logger.info(f"یومیہ آڈٹ جاب رجسٹرڈ: ہر روز صبح {settings.DAILY_AUDIT_TIME} بجے (Asia/Karachi)")

        # 2. ہر 2 گھنٹے بعد قطار کی خودکار جانچ (Missed Run Recovery & Horizon Check)
        self.scheduler.add_job(
            self._heartbeat_and_queue_check,
            trigger=IntervalTrigger(hours=2, timezone=settings.tz),
            id="periodic_queue_replenish",
            name="قطار کی توثیق اور مسڈ رن ریکوری",
            replace_existing=True,
            coalesce=True
        )
        logger.info("مسڈ رن ریکوری اور قطار کی توثیقی جاب ہر 2 گھنٹے بعد رجسٹرڈ")

        # 3. خودکار پوسٹ ڈسپیچر (ہر 60 سیکنڈ بعد شیڈول وقت کی جانچ اور اشاعت)
        from agent_am.services.dispatcher_service import queue_dispatcher
        self.scheduler.add_job(
            queue_dispatcher.dispatch_due_posts,
            trigger=IntervalTrigger(seconds=60, timezone=settings.tz),
            id="auto_post_dispatcher",
            name="خودکار پوسٹنگ ڈسپیچر",
            replace_existing=True,
            coalesce=True
        )
        logger.info("خودکار پوسٹنگ ڈسپیچر رجسٹرڈ (ہر 60 سیکنڈ بعد لائیو وقت کی جانچ)")


    async def _heartbeat_and_queue_check(self):
        """چیک کرتا ہے کہ اگلے 48 گھنٹوں کی قطار مکمل ہے یا نہیں"""
        try:
            logger.info("بیک گراؤنڈ ہارٹ بیٹ: 48 گھنٹے پوسٹنگ قطار کی تصدیق کی جا رہی ہے...")
            await queue_manager.replenish_queue(days_ahead=2)
        except Exception as e:
            logger.error(f"ہارٹ بیٹ قطار چیک میں خرابی: {str(e)}")

    def start(self):
        """شیڈولر کو اسٹارٹ کرتا ہے"""
        if not self.is_running:
            self.setup_jobs()
            self.scheduler.start()
            self.is_running = True
            logger.info("Agent AM خودکار شیڈولر کامیابی سے اسٹارٹ ہو گیا ہے۔")

    def shutdown(self):
        """شیڈولر کو باوقار طریقے سے بند کرتا ہے"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("شیڈولر بند کر دیا گیا۔")

scheduler_service = SchedulerService()
