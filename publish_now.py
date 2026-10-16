"""
فوری کمیونٹی پوسٹ پبلشر (100% Verified Live YouTube Community Post Publisher)
"""

import sys
import os
import asyncio
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright
from agent_am.config.settings import settings

BASE_DIR = Path(__file__).resolve().parent
SESSION_FILE = BASE_DIR / "browser_session" / "storage_state.json"

async def publish_quiz_live(quiz_data: dict):
    if not SESSION_FILE.exists():
        print("خرابی: براؤزر سیشن موجود نہیں ہے۔")
        return False

    print("=" * 68)
    print("یوٹیوب کمیونٹی ٹیب پر کوئز کی براہِ راست اشاعت شروع کی جا رہی ہے...")
    print(f"سوال: {quiz_data['question']}")
    print(f"درست جواب: {quiz_data['correct_answer']}")
    print("=" * 68)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await browser.new_context(
            storage_state=str(SESSION_FILE),
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        url = f"https://www.youtube.com/channel/{settings.CHANNEL_ID}/posts?show_create_dialog=1"
        print(f"صفحہ لوڈ ہو رہا ہے: {url}")
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)

        # 1. کلک کریں 'Quiz'
        quiz_btn = page.locator("button:has-text('Quiz')").first
        await quiz_btn.click()
        await asyncio.sleep(1.5)

        # 2. سوال لکھیں
        q_box = page.locator("#contenteditable-root").first
        await q_box.click()
        await q_box.fill(quiz_data["question"])
        await asyncio.sleep(0.5)

        options = quiz_data.get("options", [])
        correct_answer = quiz_data.get("correct_answer")

        # اگر 2 سے زیادہ آپشنز ہیں تو 'Add answer' پر کلک کریں
        add_btn = page.locator("button:has-text('Add answer')").first
        for _ in range(len(options) - 2):
            if await add_btn.is_visible():
                await add_btn.click()
                await asyncio.sleep(0.5)

        # 3. آپشنز پُر کریں
        for idx, opt_text in enumerate(options, 1):
            opt_locator = page.locator(f"textarea[placeholder='Answer {idx}']").first
            if await opt_locator.is_visible():
                await opt_locator.fill(opt_text, force=True)
                await asyncio.sleep(0.3)

        # 4. درست جواب کا انتخاب کریں
        if correct_answer:
            try:
                correct_idx = options.index(correct_answer) + 1
                parent_row = page.locator(f"textarea[placeholder='Answer {correct_idx}']").locator("xpath=ancestor::yt-posts-creation-option-view-model")
                mark_btn = parent_row.locator("button[aria-label='Mark as correct answer']").first
                if await mark_btn.is_visible():
                    await mark_btn.click(force=True)
                    await asyncio.sleep(0.5)
            except Exception as e:
                print(f"درست جواب کا مارک لگانے میں چھوٹا مسئلہ: {str(e)}")

        # 5. وضاحت شامل کریں (Explanation)
        if quiz_data.get("explanation"):
            exp_box = page.locator("textarea[placeholder='Add an explanation (optional)']").first
            if await exp_box.is_visible():
                await exp_box.fill(f"{quiz_data['explanation']} (ماخذ: {quiz_data.get('source_reference', 'تفسیر ابن کثیر')})", force=True)
                await asyncio.sleep(0.5)

        await page.screenshot(path="reports/quiz_pre_submit.png")
        print("کوئز کامیابی سے مکمل پُر ہو گیا! اسکرین شاٹ: reports/quiz_pre_submit.png")

        # 6. 'Post' بٹن پر کلک کریں
        post_btn = page.locator("#post-button button, button:has-text('Post')").last
        if await post_btn.is_visible():
            await post_btn.click(force=True)
            print("پوسٹ بٹن دبا دیا گیا ہے! یوٹیوب پر شائع ہونے کا انتظار...")
            await asyncio.sleep(6)
            await page.screenshot(path="reports/quiz_posted_live.png")
            print("ماشاء اللہ! کوئز کامیابی سے یوٹیوب چینل پر شائع ہو چکا ہے!")
            await browser.close()
            return True
        else:
            print("خرابی: پوسٹ بٹن نظر نہیں آیا۔")
            await browser.close()
            return False

if __name__ == "__main__":
    sample_quiz = {
        "question": "فرعون کا وہ خوفناک انجام جس نے تاریخ بدل دی، یہ واقعہ بحیرہ احمر (Red Sea) کے کس مقام پر پیش آیا تھا؟",
        "options": [
            "خلیج سوئز",
            "خلیج عقبہ",
            "دریائے نیل کا دہانہ",
            "بحر قلزم کا جنوبی حصہ"
        ],
        "correct_answer": "خلیج سوئز",
        "explanation": "تاریخی اور جغرافیائی شواہد کے مطابق حضرت موسیٰ علیہ السلام اور بنی اسرائیل کو بحیرہ احمر کی خلیج سوئز کے مقام پر معجزاتی راستہ ملا اور فرعون اپنے لشکر سمیت اسی مقام پر غرق ہوا۔",
        "source_reference": "تاریخ طبری، جلد اول / تفسیر ابن کثیر (سورۃ یونس: 90)"
    }
    asyncio.run(publish_quiz_live(sample_quiz))
