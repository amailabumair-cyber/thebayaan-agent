import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def inspect():
    session_file = Path("./browser_session/storage_state.json")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await browser.new_context(
            storage_state=str(session_file),
            viewport={"width": 1280, "height": 900}
        )
        page = await context.new_page()
        url = "https://www.youtube.com/channel/UCcf-vu1rx2g9gPHdPwrPvYQ/posts?show_create_dialog=1"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(4)

        # Take screenshot of the initial dialog
        await page.screenshot(path="reports/inspect_dialog.png")
        print("Captured reports/inspect_dialog.png")

        # Find buttons
        buttons = await page.locator("button, ytcp-button").all()
        for b in buttons:
            txt = (await b.inner_text()).strip()
            if txt in ["Image", "Image poll", "Text poll", "Quiz"]:
                print(f"Found button: '{txt}'")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
