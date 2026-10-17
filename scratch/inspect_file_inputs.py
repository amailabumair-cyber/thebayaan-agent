import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def inspect_file_inputs():
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
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(4)

        # 1. Click Image
        img_btn = page.locator("button:has-text('Image')").first
        await img_btn.click()
        await asyncio.sleep(2)
        
        # Check file input for Image
        inputs = await page.locator("input[type='file']").all()
        for idx, inp in enumerate(inputs):
            accept = await inp.get_attribute("accept")
            is_vis = await inp.is_visible()
            name = await inp.get_attribute("name")
            id_val = await inp.get_attribute("id")
            print(f"Image Input {idx}: id='{id_val}', name='{name}', accept='{accept}', visible={is_vis}")

        await page.close()

        # 2. Check Image Poll
        page2 = await context.new_page()
        await page2.goto(url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(4)
        
        img_poll_btn = page2.locator("button:has-text('Image poll')").first
        await img_poll_btn.click()
        await asyncio.sleep(2)

        inputs2 = await page2.locator("input[type='file']").all()
        for idx, inp in enumerate(inputs2):
            accept = await inp.get_attribute("accept")
            is_vis = await inp.is_visible()
            id_val = await inp.get_attribute("id")
            parent_tag = await inp.evaluate("el => el.parentElement.tagName")
            print(f"Image Poll Input {idx}: id='{id_val}', accept='{accept}', visible={is_vis}, parent={parent_tag}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_file_inputs())
