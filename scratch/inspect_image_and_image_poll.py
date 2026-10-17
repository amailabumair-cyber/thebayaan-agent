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
        
        # 1. Test Image Dialog
        page = await context.new_page()
        url = "https://www.youtube.com/channel/UCcf-vu1rx2g9gPHdPwrPvYQ/posts?show_create_dialog=1"
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(4)
        
        img_btn = page.locator("button:has-text('Image')").first
        if await img_btn.is_visible():
            print("Clicking 'Image' button...")
            await img_btn.click()
            await asyncio.sleep(2)
            await page.screenshot(path="reports/inspect_image_clicked.png")
            file_inputs = await page.locator("input[type='file']").count()
            print(f"Image mode file inputs count: {file_inputs}")
            textareas = await page.locator("textarea, #contenteditable-root").all()
            print(f"Image mode text inputs count: {len(textareas)}")

        await page.close()

        # 2. Test Image Poll Dialog
        page2 = await context.new_page()
        await page2.goto(url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(4)

        img_poll_btn = page2.locator("button:has-text('Image poll')").first
        if await img_poll_btn.is_visible():
            print("Clicking 'Image poll' button...")
            await img_poll_btn.click()
            await asyncio.sleep(2)
            await page2.screenshot(path="reports/inspect_image_poll_clicked.png")
            file_inputs = await page2.locator("input[type='file']").count()
            print(f"Image poll mode file inputs count: {file_inputs}")
            opt_inputs = await page2.locator("[placeholder*='option'], [placeholder*='Option'], textarea").all()
            print(f"Image poll option inputs count: {len(opt_inputs)}")
            for i, opt in enumerate(opt_inputs):
                ph = await opt.get_attribute("placeholder")
                print(f"  Input {i} placeholder: '{ph}'")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
