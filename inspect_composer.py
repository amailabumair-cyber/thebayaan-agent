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
        await page.goto("https://www.youtube.com/channel/UCcf-vu1rx2g9gPHdPwrPvYQ/community")
        await page.wait_for_load_state("networkidle")
        
        # Click on composer
        box = page.locator("#placeholder-area, #contenteditable-textarea").first
        await box.click()
        await asyncio.sleep(2)
        await page.screenshot(path="reports/composer_expanded.png")
        
        # Check buttons
        buttons = await page.locator("button, tp-yt-paper-button, ytd-button-renderer").all_inner_texts()
        print("Available buttons:", [b.strip() for b in buttons if b.strip()])
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
