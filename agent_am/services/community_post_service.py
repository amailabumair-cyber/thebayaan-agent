import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from agent_am.config.settings import settings
from agent_am.database.models import PostType, PostStatus

logger = logging.getLogger("agent_am.community_post_service")

class CommunityPostService:
    """
    یوٹیوب کمیونٹی پوسٹس کی خودکار اشاعت اور شیڈولنگ سروس
    تمام 4 اقسام کی مکمل سپورٹ:
    1. QUIZ (اسلامی تاریخ کوئز مع 4 آپشنز، درست جواب اور حوالہ)
    2. TEXT_POLL / POLL (معلوماتی ٹیکسٹ پول مع 2 تا 4 آپشنز)
    3. IMAGE (تصویر پوسٹ مع معلوماتی اردو کیپشن)
    4. IMAGE_POLL (تصویر پول مع 2 تا 4 آپشنز اور تصاویر)
    """

    def __init__(self):
        self.publish_mode = settings.PUBLISH_MODE
        self.session_file = Path("./browser_session/storage_state.json")
        self._ensure_session_file()

    def _ensure_session_file(self):
        """اگر کلاؤڈ پر YOUTUBE_SESSION_B64 موجود ہو تو سیشن فائل خودکار بنا دیتا ہے"""
        if not self.session_file.exists() or self.session_file.stat().st_size < 50:
            b64_env = os.getenv("YOUTUBE_SESSION_B64")
            if b64_env:
                try:
                    import base64
                    self.session_file.parent.mkdir(parents=True, exist_ok=True)
                    self.session_file.write_bytes(base64.b64decode(b64_env.strip()))
                    logger.info("کلاؤڈ سیشن فائل کامیابی سے YOUTUBE_SESSION_B64 سے لوڈ کر لی گئی۔")
                except Exception as e:
                    logger.error(f"سیشن ڈیکوڈ کرنے میں خرابی: {e}")

    def has_active_browser_session(self) -> bool:
        """چیک کرتا ہے کہ آیا یوٹیوب اسٹوڈیو لاگ ان سیشن موجود ہے"""
        self._ensure_session_file()
        return self.session_file.exists() and self.session_file.stat().st_size > 50

    async def schedule_community_post(
        self,
        post_type: PostType,
        target_date: str,
        scheduled_time: datetime,
        question: str,
        options: Optional[List[str]] = None,
        correct_answer: Optional[str] = None,
        explanation: Optional[str] = None,
        source_reference: Optional[str] = None,
        image_path: Optional[str] = None,
        option_images: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        کمیونٹی پوسٹ کو شائع یا شیڈول کرنے کی مرکزی کمانڈ
        """
        options = options or []
        option_images = option_images or []

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
                source_reference=source_reference,
                image_path=image_path,
                option_images=option_images,
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
        options: List[str],
        correct_answer: Optional[str] = None,
        explanation: Optional[str] = None,
        source_reference: Optional[str] = None,
        image_path: Optional[str] = None,
        option_images: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Playwright کے ذریعے یوٹیوب پر لائیو کوئز، پول، تصویر یا تصویر پول شائع کرنا
        """
        option_images = option_images or []
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
                await asyncio.sleep(4)

                if "accounts.google.com" in page.url:
                    await browser.close()
                    return {
                        "success": False,
                        "status": PostStatus.FAILED,
                        "error": "یوٹیوب لاگ ان سیشن کی میعاد ختم ہو چکی ہے (Session expired)",
                        "external_id": None
                    }

                # =============================================================
                # نوعیت 1: QUIZ (کوئز مع 4 آپشنز، درست جواب اور وضاحت)
                # =============================================================
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

                # =============================================================
                # نوعیت 2: TEXT_POLL / POLL (معلوماتی ٹیکسٹ پول)
                # =============================================================
                elif post_type in [PostType.POLL, PostType.TEXT_POLL]:
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

                    # آپشنز پُر کریں
                    opt_locators = await page.locator("[placeholder='Add option']").all()
                    for idx, opt_text in enumerate(options):
                        if idx < len(opt_locators):
                            await opt_locators[idx].click()
                            await opt_locators[idx].fill(opt_text)
                            await asyncio.sleep(0.3)

                # =============================================================
                # نوعیت 3: IMAGE (تصویر پوسٹ مع کیپشن)
                # =============================================================
                elif post_type == PostType.IMAGE:
                    btn = page.locator("button:has-text('Image')").first
                    if await btn.is_visible():
                        await btn.click()
                    await asyncio.sleep(2)

                    # تصویر اٹیچ کریں
                    if image_path and Path(image_path).exists():
                        select_link = page.locator("text='select from your computer'").first
                        if await select_link.is_visible():
                            async with page.expect_file_chooser() as fc_info:
                                await select_link.click()
                            file_chooser = await fc_info.value
                            await file_chooser.set_files(str(image_path))
                            await asyncio.sleep(4)
                        else:
                            # فال بیک فائل ان پٹ
                            file_input = page.locator("input[type='file'][accept*='image']").first
                            if await file_input.count() > 0:
                                await file_input.set_input_files(str(image_path))
                                await asyncio.sleep(4)

                    # کیپشن / پیغام درج کریں
                    q_box = page.locator("ytd-backstage-post-dialog #contenteditable-root, #contenteditable-root").last
                    if await q_box.is_visible() and question:
                        await q_box.fill(question)
                        await asyncio.sleep(1)

                # =============================================================
                # نوعیت 4: IMAGE_POLL (تصویر پول مع 2 تا 4 آپشنز اور تصاویر)
                # =============================================================
                elif post_type == PostType.IMAGE_POLL:
                    btn = page.locator("button:has-text('Image poll')").first
                    if await btn.is_visible():
                        await btn.click()
                    await asyncio.sleep(2)

                    # سوال درج کریں
                    q_box = page.locator("ytd-backstage-post-dialog #contenteditable-root, #contenteditable-root").last
                    if await q_box.is_visible():
                        await q_box.fill(question)
                        await asyncio.sleep(1)

                    # اگر آپشنز 2 سے زیادہ ہوں تو 'Add option' پر کلک کریں
                    add_opt_btn = page.locator("yt-button-renderer.add-option button").first
                    for _ in range(len(options) - 2):
                        if await add_opt_btn.is_visible():
                            await add_opt_btn.click()
                            await asyncio.sleep(0.5)

                    # ہر آپشن کا ٹیکسٹ اور تصویر اٹیچ کریں
                    textareas = await page.locator("ytd-backstage-image-poll-editor-renderer textarea").all()
                    add_img_btns = await page.locator("ytd-backstage-image-poll-editor-renderer .add-image-icon-button button").all()

                    for idx, opt_text in enumerate(options):
                        # ٹیکسٹ درج کریں
                        if idx < len(textareas):
                            await textareas[idx].fill(opt_text)
                            await asyncio.sleep(0.3)

                        # متعلقہ آپشن کی تصویر اٹیچ کریں
                        if idx < len(add_img_btns) and idx < len(option_images):
                            opt_img = option_images[idx]
                            if opt_img and Path(opt_img).exists():
                                async with page.expect_file_chooser() as fc_info:
                                    await add_img_btns[idx].click()
                                file_chooser = await fc_info.value
                                await file_chooser.set_files(str(opt_img))
                                await asyncio.sleep(2.5)

                # اسکرین شاٹ برائے ریکارڈ
                os.makedirs("reports", exist_ok=True)
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                await page.screenshot(path=f"reports/post_presubmit_{timestamp_str}.png")

                # پوسٹ بٹن چیک کریں
                post_btn = page.locator("#post-button button, button:has-text('Post')").last
                is_vis = await post_btn.is_visible()
                is_enabled = await post_btn.is_enabled() if is_vis else False

                if not is_vis or not is_enabled:
                    await browser.close()
                    logger.error(f"یوٹیوب پوسٹ بٹن غیر فعال تھا (پوسٹ ٹائپ: {post_type.value})")
                    return {
                        "success": False,
                        "status": PostStatus.FAILED,
                        "error": "یوٹیوب پوسٹ بٹن فعال (Enabled) نہیں تھا، فارم فیلڈز نامکمل رہ گئے",
                        "external_id": None
                    }

                # فعال پوسٹ بٹن دبائیں
                await post_btn.click()
                await asyncio.sleep(5)
                await page.screenshot(path=f"reports/post_submitted_{timestamp_str}.png")
                await browser.close()

                external_id = f"yt_post_{int(datetime.now().timestamp())}"
                logger.info(f"پوسٹ [{post_type.value}] کامیابی سے یوٹیوب پر شائع ہو گئی۔ ID: {external_id}")
                return {
                    "success": True,
                    "status": PostStatus.PUBLISHED,
                    "external_id": external_id,
                    "note_urdu": f"پوسٹ ({post_type.value}) کامیابی سے یوٹیوب چینل پر براہِ راست شائع ہو چکی ہے۔"
                }

        except Exception as e:
            logger.error(f"Playwright پبلشنگ میں خرابی [{post_type}]: {str(e)}")
            return {
                "success": False,
                "status": PostStatus.FAILED,
                "error": f"آٹومیشن خرابی: {str(e)}",
                "external_id": None
            }

community_post_service = CommunityPostService()
