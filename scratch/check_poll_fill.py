import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def test_poll_fill():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(
            storage_state="browser_session/storage_state.json",
            viewport={"width": 1280, "height": 900}
        )
        page = await context.new_page()
        print("Navigating to YouTube posts dialog...")
        await page.goto(
            "https://www.youtube.com/channel/UCcf-vu1rx2g9gPHdPwrPvYQ/posts?show_create_dialog=1",
            wait_until="domcontentloaded",
            timeout=30000
        )
        await asyncio.sleep(4)
        
        # Click Text poll
        poll_btn = page.locator("button:has-text('Text poll')").first
        await poll_btn.wait_for(state="visible", timeout=15000)
        print("Clicking 'Text poll' button...")
        await poll_btn.click()
        await asyncio.sleep(2)
        
        # Fill question
        q_box = page.locator("#contenteditable-root").first
        await q_box.click()
        await q_box.fill("'The Bayan' پر آپ اسلامی تاریخ کے کس اہم دور پر اگلی تفصیلی ویڈیو دیکھنا پسند کریں گے؟")
        await asyncio.sleep(1)
        
        # Find Option fields
        # YouTube option fields have placeholder="Add option"
        opt_locators = await page.locator("[placeholder='Add option']").all()
        print(f"Found {len(opt_locators)} elements with placeholder='Add option'")
        
        # If less than options count (e.g. 4 options), click 'Add another option'
        test_options = ["خلافت راشدہ اور فتوحات", "سیرت النبی ﷺ اور مکی دور", "قصص الانبیاء اور عبرت انگیز سبق", "اندلس اور عثمانی سلطنت"]
        
        add_another_btn = page.locator("button:has-text('Add another option'), button:has-text('Add option')").first
        for i in range(len(test_options) - 2):
            if await add_another_btn.is_visible():
                print(f"Clicking add another option ({i+1})...")
                await add_another_btn.click()
                await asyncio.sleep(0.5)
        
        # Re-fetch option fields
        opt_locators = await page.locator("[placeholder='Add option']").all()
        print(f"Now found {len(opt_locators)} elements with placeholder='Add option'")
        for idx, el in enumerate(opt_locators):
            tag = await el.evaluate("e => e.tagName")
            print(f"Option field {idx}: tag={tag}")
            if idx < len(test_options):
                await el.click()
                await el.fill(test_options[idx])
                await asyncio.sleep(0.3)
        
        await asyncio.sleep(1)
        # Check Post button state
        post_btn = page.locator("#post-button button, button:has-text('Post')").last
        is_vis = await post_btn.is_visible()
        is_en = await post_btn.is_enabled()
        print(f"Post button: visible={is_vis}, enabled={is_en}")
        
        await page.screenshot(path="reports/test_poll_fill_success.png")
        print("Screenshot saved to reports/test_poll_fill_success.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_poll_fill())
