"""
Agent AM - Standalone Background Worker
مستقل پس منظر ورکر برائے خودکار شیڈولنگ اور چینل مینجمنٹ

یہ اسکرپٹ بغیر کسی ویب براؤزر، چیٹ جی پی ٹی، یا اینٹی گریویٹی کے مستقل چلتا رہتا ہے
اور پاکستان ٹائم زون (Asia/Karachi) کے مطابق تمام شیڈول شدہ ٹاسکس خود بخود انجام دیتا ہے۔
"""

import asyncio
import signal
import sys
import logging

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from agent_am.config.settings import settings
from agent_am.database.connection import init_db
from agent_am.services.scheduler_service import scheduler_service
from agent_am.core.workflow import workflow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agent_am_worker.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("agent_am.worker")

is_running = True

def handle_exit_signal(sig, frame):
    global is_running
    logger.info("خروج کا سگنل موصول ہوا، ورکر باوقار طریقے سے بند ہو رہا ہے...")
    is_running = False

async def main():
    logger.info(f"=== {settings.AGENT_NAME} ورکر شروع ہو رہا ہے ===")
    logger.info(f"ہدف چینل: {settings.CHANNEL_NAME} | ٹائم زون: {settings.TIMEZONE}")
    
    # ڈیٹا بیس ٹیبلز چیک کریں
    await init_db()
    
    # شیڈولر فعال کریں
    scheduler_service.start()
    logger.info("شیڈولر فعال ہے۔ اگلی یومیہ جاب اپنے مقررہ وقت پر خودکار طور پر چلے گی۔")

    # فوری طور پر قطار کو بھریں تاکہ 24-48 گھنٹے محفوظ رہیں
    try:
        from agent_am.core.queue_manager import queue_manager
        logger.info("48 گھنٹے پوسٹنگ قطار کی ابتدائی توثیق...")
        await queue_manager.replenish_queue(days_ahead=2)
    except Exception as e:
        logger.error(f"ابتدائی قطار بھرنے میں خرابی: {str(e)}")

    # مستقل چلنے والا لوپ
    while is_running:
        await asyncio.sleep(60)

    scheduler_service.shutdown()
    logger.info("ورکر کامیابی سے بند ہو گیا۔")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_exit_signal)
    signal.signal(signal.SIGTERM, handle_exit_signal)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("ورکر کا عمل اختتام پذیر ہوا۔")
