import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(storage_state="browser_session/storage_state.json")
        page = await context.new_page()
        await page.goto("https://www.youtube.com/channel/UCcf-vu1rx2g9gPHdPwrPvYQ/posts?show_create_dialog=1")
        await page.wait_for_load_state("networkidle")
        
        # Click "Quiz" button
        quiz_btn = page.locator("button:has-text('Quiz'), [aria-label*='Quiz'], ytd-button-renderer:has-text('Quiz')").first
        await quiz_btn.click()
        await asyncio.sleep(2)
        await page.screenshot(path="reports/quiz_form.png")
        print("Quiz form opened!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
