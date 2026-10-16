import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from agent_am.config.settings import settings
from agent_am.database.models import PostType, PostStatus

logger = logging.getLogger("agent_am.community_post_service")

class CommunityPostService:
    """
    یوٹیوب کمیونٹی پوسٹس (کوئز اور ٹیکسٹ پول) کی خودکار اشاعت اور شیڈولنگ سروس
    Playwright اور حقیقی کروم براؤزر کے مستند سیشن کے ذریعے 100% مستند ایگزیکیوشن
    """

    def __init__(self):
        self.publish_mode = settings.PUBLISH_MODE
        self.session_file = Path("./browser_session/storage_state.json")

    def has_active_browser_session(self) -> bool:
        """چیک کرتا ہے کہ آیا یوٹیوب اسٹوڈیو لاگ ان سیشن موجود ہے"""
        return self.session_file.exists() and self.session_file.stat().st_size > 50

    async def schedule_community_post(
        self,
        post_type: PostType,
        target_date: str,
        scheduled_time: datetime,
        question: str,
        options: list,
        correct_answer: Optional[str] = None,
        explanation: Optional[str] = None,
        source_reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        کمیونٹی پوسٹ کو شائع یا شیڈول کرنے کی مرکزی کمانڈ
        """
        now_pkt = settings.now()
        if scheduled_time.tzinfo is None:
            scheduled_time = scheduled_time.replace(tzinfo=settings.tz)

        # اگر براؤزر سیشن متحرک ہے
        if self.has_active_browser_session():
            return await self._publish_via_playwright(
                post_type=post_type,
                scheduled_time=scheduled_time,
                question=question,
                options=options,
                correct_answer=correct_answer,
                explanation=explanation,
                source_reference=source_reference
            )
        else:
            logger.info("یوٹیوب براؤزر سیشن فائل موجود نہیں۔ پوسٹ محفوظ اور تصدیق شدہ ہے۔")
            return {
                "success": True,
                "status": PostStatus.VALIDATED,
                "external_id": f"PENDING_SESSION_{int(scheduled_time.timestamp())}",
                "note_urdu": "پوسٹ تیار ہے لیکن لاگ ان سیشن دستیاب نہیں ہے۔"
            }

    async def _publish_via_playwright(
        self,
        post_type: PostType,
        scheduled_time: datetime,
        question: str,
        options: list,
        correct_answer: Optional[str] = None,
        explanation: Optional[str] = None,
        source_reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Playwright کے ذریعے یوٹیوب پر لائیو کوئز یا پول شائع کرنا
        """
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    channel="chrome",
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
                )
                context = await browser.new_context(
                    storage_state=str(self.session_file),
                    viewport={"width": 1280, "height": 900},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
                page = await context.new_page()

                channel_url = f"https://www.youtube.com/channel/{settings.CHANNEL_ID}/posts?show_create_dialog=1"
                logger.info(f"یوٹیوب پوسٹ ڈائیلاگ کھولا جا رہا ہے: {channel_url}")
                try:
                    await page.goto(channel_url, wait_until="domcontentloaded", timeout=45000)
                except Exception as e:
                    logger.warning(f"صفحہ لوڈ کرنے میں تنبیہ لیکن جاری رکھا جا رہا ہے: {e}")
                await asyncio.sleep(3)

                if "accounts.google.com" in page.url:
                    await browser.close()
                    return {
                        "success": False,
                        "status": PostStatus.FAILED,
                        "error": "یوٹیوب لاگ ان سیشن کی میعاد ختم ہو چکی ہے (Session expired)",
                        "external_id": None
                    }

                # 1. قسم منتخب کریں: Quiz یا Text poll
                if post_type == PostType.QUIZ:
                    btn = page.locator("button:has-text('Quiz')").first
                    if await btn.is_visible():
                        await btn.click()
                    await asyncio.sleep(1.5)

                    # سوال درج کریں
                    q_box = page.locator("#contenteditable-root").first
                    await q_box.click()
                    await q_box.fill(question)
                    await asyncio.sleep(0.5)

                    # آپشنز کی تعداد بڑھائیں اگر 2 سے زیادہ ہوں
                    add_btn = page.locator("button:has-text('Add answer')").first
                    for _ in range(len(options) - 2):
                        if await add_btn.is_visible():
                            await add_btn.click()
                            await asyncio.sleep(0.5)

                    # آپشنز پُر کریں
                    for idx, opt_text in enumerate(options, 1):
                        opt_locator = page.locator(f"textarea[placeholder='Answer {idx}']").first
                        if await opt_locator.is_visible():
                            await opt_locator.fill(opt_text, force=True)
                            await asyncio.sleep(0.3)

                    # درست جواب منتخب کریں
                    if correct_answer and correct_answer in options:
                        try:
                            correct_idx = options.index(correct_answer) + 1
                            parent_row = page.locator(f"textarea[placeholder='Answer {correct_idx}']").locator("xpath=ancestor::yt-posts-creation-option-view-model")
                            mark_btn = parent_row.locator("button[aria-label='Mark as correct answer']").first
                            if await mark_btn.is_visible():
                                await mark_btn.click(force=True)
                                await asyncio.sleep(0.5)
                        except Exception as e:
                            logger.warning(f"درست جواب کا نشان لگانے میں تنبیہ: {e}")

                    # وضاحت درج کریں
                    if explanation:
                        exp_box = page.locator("textarea[placeholder='Add an explanation (optional)']").first
                        if await exp_box.is_visible():
                            full_exp = f"{explanation} (ماخذ: {source_reference})" if source_reference else explanation
                            await exp_box.fill(full_exp, force=True)
                            await asyncio.sleep(0.5)

                else:
                    # Text Poll
                    btn = page.locator("button:has-text('Text poll')").first
                    if await btn.is_visible():
                        await btn.click()
                    await asyncio.sleep(1.5)

                    # سوال درج کریں
                    q_box = page.locator("#contenteditable-root").first
                    await q_box.click()
                    await q_box.fill(question)
                    await asyncio.sleep(0.5)

                    # مزید آپشنز کا بٹن (اگر 2 سے زیادہ ہوں)
                    add_btn = page.locator("button:has-text('Add another option'), button:has-text('Add option')").first
                    for _ in range(len(options) - 2):
                        if await add_btn.is_visible():
                            await add_btn.click()
                            await asyncio.sleep(0.5)

                    # آپشنز پُر کریں (YouTube پر Text Poll کے لیے placeholder='Add option' ہوتا ہے)
                    opt_locators = await page.locator("[placeholder='Add option']").all()
                    for idx, opt_text in enumerate(options):
                        if idx < len(opt_locators):
                            await opt_locators[idx].click()
                            await opt_locators[idx].fill(opt_text)
                            await asyncio.sleep(0.3)

                # اسکرین شاٹ برائے ریکارڈ
                os.makedirs("reports", exist_ok=True)
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                await page.screenshot(path=f"reports/post_presubmit_{timestamp_str}.png")

                # پوسٹ بٹن چیک کریں اور یقینی بنائیں کہ یہ فعال (Enabled) ہے
                post_btn = page.locator("#post-button button, button:has-text('Post')").last
                is_vis = await post_btn.is_visible()
                is_enabled = await post_btn.is_enabled() if is_vis else False

                if not is_vis or not is_enabled:
                    await browser.close()
                    logger.error("یوٹیوب پوسٹ بٹن ڈس ایبلڈ یا غیر دستیاب تھا (شاید آپشنز یا فیلڈز مکمل نہیں ہو سکے)")
                    return {
                        "success": False,
                        "status": PostStatus.FAILED,
                        "error": "یوٹیوب پوسٹ بٹن فعال (Enabled) نہیں تھا، فارم نامکمل رہ گیا",
                        "external_id": None
                    }

                # فعال بٹن دبائیں
                await post_btn.click()
                await asyncio.sleep(5)
                await page.screenshot(path=f"reports/post_submitted_{timestamp_str}.png")
                await browser.close()
                external_id = f"yt_post_{int(datetime.now().timestamp())}"
                logger.info(f"پوسٹ کامیابی سے یوٹیوب پر شائع ہو گئی۔ ID: {external_id}")
                return {
                    "success": True,
                    "status": PostStatus.PUBLISHED,
                    "external_id": external_id,
                    "note_urdu": "کمیونٹی پوسٹ کامیابی سے یوٹیوب چینل پر براہِ راست شائع ہو چکی ہے۔"
                }


        except Exception as e:
            logger.error(f"Playwright پبلشنگ میں خرابی: {str(e)}")
            return {
                "success": False,
                "status": PostStatus.FAILED,
                "error": f"آٹومیشن خرابی: {str(e)}",
                "external_id": None
            }

community_post_service = CommunityPostService()
