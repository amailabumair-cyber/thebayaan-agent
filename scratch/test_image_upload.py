import asyncio
from pathlib import Path
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright

def create_sample_card(filename="sample_card.png"):
    img = Image.new("RGB", (1080, 1080), color=(11, 19, 43))
    draw = ImageDraw.Draw(img)
    draw.rectangle([30, 30, 1050, 1050], outline=(255, 183, 3), width=6)
    draw.rectangle([50, 50, 1030, 1030], outline=(0, 180, 216), width=2)
    draw.text((540, 540), "The Bayaan", fill=(255, 255, 255), anchor="mm")
    out_path = Path("reports") / filename
    img.save(out_path)
    return out_path.resolve()

async def test_image_fill():
    img_path = create_sample_card("test_image_post.png")
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

        # 1. Click Image button
        img_btn = page.locator("button:has-text('Image')").first
        await img_btn.click()
        await asyncio.sleep(2)

        # 2. Upload file via expect_file_chooser
        select_link = page.locator("text='select from your computer'").first
        if await select_link.is_visible():
            print("Triggering file chooser on 'select from your computer'...")
            async with page.expect_file_chooser() as fc_info:
                await select_link.click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(str(img_path))
            print("File set in file chooser!")
            await asyncio.sleep(5)

        # 3. Enter caption
        q_box = page.locator("ytd-backstage-post-dialog #contenteditable-root, #contenteditable-root").last
        if await q_box.is_visible():
            await q_box.fill("سبحان اللہ وبحمدہ سبحان اللہ العظیم — دی بیان (The Bayaan)")
            await asyncio.sleep(2)

        # Take screenshot of the filled image post dialog
        await page.screenshot(path="reports/test_image_post_filled.png")
        print("Captured reports/test_image_post_filled.png")

        # Check post button status
        post_btn = page.locator("#post-button button, button:has-text('Post')").last
        is_vis = await post_btn.is_visible()
        is_en = await post_btn.is_enabled() if is_vis else False
        print(f"Post button visible: {is_vis}, enabled: {is_en}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_image_fill())
