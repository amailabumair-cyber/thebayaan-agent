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
        await asyncio.sleep(2)
        
        # Click Quiz button
        quiz_btn = page.locator("button:has-text('Quiz')").first
        await quiz_btn.click()
        await asyncio.sleep(2)
        
        # Find all inputs and editables
        inputs = await page.evaluate("""
            () => {
                const els = Array.from(document.querySelectorAll('input, textarea, div[contenteditable="true"], ytd-backstage-post-dialog-renderer *'));
                return els.filter(e => e.offsetHeight > 0).map(e => ({
                    tag: e.tagName,
                    id: e.id,
                    className: e.className,
                    placeholder: e.placeholder || e.getAttribute('placeholder') || '',
                    ariaLabel: e.getAttribute('aria-label') || '',
                    role: e.getAttribute('role') || ''
                })).slice(0, 30);
            }
        """)
        import json
        print(json.dumps(inputs, indent=2))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
