"""
یوٹیوب اسٹوڈیو لاگ ان اسکرپٹ (Bulletproof YouTube Studio Connect)
یہ اسکرپٹ خودکار طور پر یوٹیوب اسٹوڈیو کا لاگ ان سیشن ہمیشہ کے لیے محفوظ کرتا ہے۔
"""

import sys
import os
import asyncio
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).resolve().parent
SESSION_DIR = BASE_DIR / "browser_session"
SESSION_FILE = SESSION_DIR / "storage_state.json"

async def main():
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 68)
    print("یوٹیوب اسٹوڈیو لاگ ان سیشن کا آغاز (Agent AM YouTube Connect)")
    print("=" * 68)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars"
            ],
            ignore_default_args=["--enable-automation"]
        )
        context = await browser.new_context(
            viewport=None,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        print("یوٹیوب اسٹوڈیو کا صفحہ کھولا جا رہا ہے...")
        await page.goto("https://studio.youtube.com")

        print("\nلاگ ان کا انتظار جاری ہے...")
        print("جیسے ہی آپ لاگ ان مکمل کریں گے، یہ خودکار طور پر سیشن محفوظ کر لے گا۔")

        # 10 منٹ تک پولنگ چیک کریں کہ لاگ ان ہو گیا ہے
        logged_in = False
        for _ in range(300):
            await asyncio.sleep(2)
            try:
                curr_url = page.url
                # اگر گوگل سائن ان پیج سے نکل کر یوٹیوب یا اسٹوڈیو پر آ جائے
                if "accounts.google.com" not in curr_url and ("studio.youtube.com" in curr_url or "youtube.com" in curr_url):
                    # اگر صرف یوٹیوب پر ہے تو اسٹوڈیو ری ڈائریکٹ کریں
                    if "studio.youtube.com" not in curr_url:
                        await page.goto("https://studio.youtube.com")
                        await asyncio.sleep(3)
                    
                    await page.wait_for_load_state("networkidle")
                    await context.storage_state(path=str(SESSION_FILE))
                    logged_in = True
                    break
            except Exception:
                pass

        if logged_in and SESSION_FILE.exists() and SESSION_FILE.stat().st_size > 50:
            print("\n" + "=" * 68)
            print("ماشاء اللہ! آپ کا یوٹیوب اسٹوڈیو سیشن 100% محفوظ ہو گیا ہے!")
            print(f"فائل کا راستہ: {SESSION_FILE}")
            print("اب Agent AM خودکار طور پر کمیونٹی ٹیب پر کوئز اور پولز شیڈول کرے گا۔")
            print("=" * 68)
        else:
            print("\nلاگ ان مکمل نہیں ہو سکا یا سیشن محفوظ نہیں ہوا۔ برائے مہربانی دوبارہ کوشش فرمائیں۔")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
