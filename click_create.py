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
        create_btn = page.locator("button:has-text('Create'), ytd-topbar-menu-button-renderer:has-text('Create'), #buttons ytd-button-renderer").first
        await create_btn.click()
        await asyncio.sleep(2)
        await page.screenshot(path="reports/create_menu.png")
        
        menu_items = await page.locator("ytd-compact-link-renderer, tp-yt-paper-item").all_inner_texts()
        print("Create menu items:", menu_items)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
