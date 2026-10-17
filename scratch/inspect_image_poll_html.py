import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def inspect():
    session_file = Path("./browser_session/storage_state.json")
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(storage_state=str(session_file), viewport={"width": 1280, "height": 900})
        page = await context.new_page()
        url = "https://www.youtube.com/channel/UCcf-vu1rx2g9gPHdPwrPvYQ/posts?show_create_dialog=1"
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(4)

        poll_btn = page.locator("button:has-text('Image poll')").first
        await poll_btn.click()
        await asyncio.sleep(2)

        renderer = page.locator("ytd-backstage-image-poll-editor-renderer").first
        html = await renderer.inner_html()
        Path("reports/image_poll_dom.html").write_text(html, encoding="utf-8")
        print("Wrote reports/image_poll_dom.html")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
