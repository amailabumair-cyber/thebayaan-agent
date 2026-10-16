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
        await page.goto("https://www.youtube.com")
        await page.wait_for_load_state("networkidle")
        
        # Click Create button
        create_btn = page.locator("button:has-text('Create'), ytd-topbar-menu-button-renderer:has-text('Create')").first
        await create_btn.click()
        await asyncio.sleep(1)
        
        # Click "Create post"
        post_link = page.locator("ytd-compact-link-renderer:has-text('Create post')").first
        await post_link.click()
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)
        await page.screenshot(path="reports/post_composer_modal.png")
        print("Page URL after Create post:", page.url)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
