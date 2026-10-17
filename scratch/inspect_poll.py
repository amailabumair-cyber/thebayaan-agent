import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def inspect_poll():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(
            storage_state="browser_session/storage_state.json",
            viewport={"width": 1280, "height": 900}
        )
        page = await context.new_page()
        await page.goto("https://www.youtube.com/channel/UCcf-vu1rx2g9gPHdPwrPvYQ/posts?show_create_dialog=1")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)
        
        btn = page.locator("button:has-text('Text poll')").first
        if await btn.is_visible():
            print("Clicking 'Text poll' button...")
            await btn.click()
            await asyncio.sleep(2)
        else:
            print("Text poll button NOT visible!")
        
        inputs = await page.locator("textarea, input, [contenteditable='true']").all()
        print(f"Total inputs found: {len(inputs)}")
        for idx, el in enumerate(inputs):
            tag = await el.evaluate("e => e.tagName")
            placeholder = await el.get_attribute("placeholder") or ""
            aria_label = await el.get_attribute("aria-label") or ""
            vis = await el.is_visible()
            elem_id = await el.get_attribute("id") or ""
            print(f"[{idx}] Tag: {tag} | ID: '{elem_id}' | Placeholder: '{placeholder}' | Aria: '{aria_label}' | Vis: {vis}")
        
        buttons = await page.locator("button").all()
        print(f"Total buttons: {len(buttons)}")
        for idx, b in enumerate(buttons):
            bt = (await b.inner_text()).strip()
            aria = await b.get_attribute("aria-label") or ""
            vis = await b.is_visible()
            if any(k in bt.lower() or k in aria.lower() for k in ["poll", "option", "post", "add", "cancel"]):
                print(f"Button [{idx}]: Text: '{bt}' | Aria: '{aria}' | Vis: {vis}")

        await page.screenshot(path="reports/inspect_poll_test.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_poll())
