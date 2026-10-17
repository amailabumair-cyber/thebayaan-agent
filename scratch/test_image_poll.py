import asyncio
from pathlib import Path
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright

def create_option_image(filename: str, title: str, bg_color=(28, 37, 65)):
    img = Image.new("RGB", (800, 800), color=bg_color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 780, 780], outline=(255, 183, 3), width=6)
    draw.text((400, 400), title, fill=(255, 255, 255), anchor="mm")
    out_path = Path("reports") / filename
    img.save(out_path)
    return out_path.resolve()

async def test_image_poll():
    img1 = create_option_image("poll_opt1.png", "Makkah", bg_color=(11, 19, 43))
    img2 = create_option_image("poll_opt2.png", "Madinah", bg_color=(28, 37, 65))
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

        # 1. Click Image poll button
        poll_btn = page.locator("button:has-text('Image poll')").first
        await poll_btn.click()
        await asyncio.sleep(2)

        # 2. Enter poll question
        q_box = page.locator("ytd-backstage-post-dialog #contenteditable-root, #contenteditable-root").last
        if await q_box.is_visible():
            await q_box.fill("آپ کا سب سے پسندیدہ روحانی سفر کون سا ہے؟")
            await asyncio.sleep(1)

        # 3. Check all textareas inside ytd-backstage-image-poll-editor-renderer
        textareas = await page.locator("ytd-backstage-image-poll-editor-renderer textarea").all()
        print(f"Found {len(textareas)} textareas in editor renderer.")

        if len(textareas) >= 2:
            await textareas[0].fill("مکہ مکرمہ")
            await asyncio.sleep(0.5)
            await textareas[1].fill("مدینہ منورہ")
            await asyncio.sleep(0.5)

        # 4. Attach images
        add_img_btns = await page.locator("ytd-backstage-image-poll-editor-renderer .add-image-icon-button button").all()
        print(f"Found {len(add_img_btns)} add-image buttons.")

        if len(add_img_btns) >= 2:
            print("Triggering file chooser for option 1...")
            async with page.expect_file_chooser() as fc1:
                await add_img_btns[0].click()
            file_chooser1 = await fc1.value
            await file_chooser1.set_files(str(img1))
            await asyncio.sleep(3)

            print("Triggering file chooser for option 2...")
            async with page.expect_file_chooser() as fc2:
                await add_img_btns[1].click()
            file_chooser2 = await fc2.value
            await file_chooser2.set_files(str(img2))
            await asyncio.sleep(3)

        await page.screenshot(path="reports/test_image_poll_filled.png")
        print("Captured reports/test_image_poll_filled.png")

        post_btn = page.locator("#post-button button, button:has-text('Post')").last
        is_vis = await post_btn.is_visible()
        is_en = await post_btn.is_enabled() if is_vis else False
        print(f"Post button visible: {is_vis}, enabled: {is_en}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_image_poll())
