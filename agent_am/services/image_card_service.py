import os
import textwrap
import logging
from pathlib import Path
from typing import Optional, List, Tuple
from PIL import Image, ImageDraw, ImageFont

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_RESHAPER = True
except ImportError:
    HAS_RESHAPER = False

logger = logging.getLogger("agent_am.image_card_service")

class ImageCardService:
    """
    یوٹیوب کمیونٹی ٹیب کے لیے 100% برانڈڈ اسلامی تصویری کارڈز اور پول آپشنز بنانے والی سروس
    """

    def __init__(self):
        self.output_dir = Path("reports/generated_cards")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.font_path = self._get_best_font()

    def _get_best_font(self) -> str:
        """سسٹم کے سب سے بہترین اردو/عربی فونٹ کا انتخاب"""
        candidates = [
            "C:/Windows/Fonts/tahoma.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/times.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        for p in candidates:
            if Path(p).exists():
                return p
        return "arial.ttf"

    def _format_urdu_text(self, text: str) -> str:
        """اردو متن کو جوڑ کر دائیں سے بائیں (RTL) درست شکل دیتا ہے"""
        if not text:
            return ""
        if HAS_RESHAPER:
            try:
                reshaped = arabic_reshaper.reshape(text)
                return get_display(reshaped)
            except Exception as e:
                logger.warning(f"Reshaper error: {e}")
        return text

    async def generate_image_post_card_async(
        self,
        title: str,
        content_text: str,
        source: Optional[str] = "دی بیان (The Bayaan)",
        filename_prefix: str = "img_post",
        bg_image_path: Optional[str] = None
    ) -> Path:
        """
        Playwright اور جدید ایچ ٹی ایم ایل انجن کے ذریعے 1080x1080 سچے نستعلیق
        اور اسلامی جیومیٹرک ڈیزائن کا شاہکار کارڈ تیار کرتا ہے
        """
        out_file = self.output_dir / f"{filename_prefix}_{int(os.times().system * 1000)}.png"
        
        bg_style = "background: radial-gradient(circle at 50% 45%, #0f2744 0%, #081326 60%, #030814 100%);"
        if bg_image_path and Path(bg_image_path).exists():
            abs_bg = Path(bg_image_path).resolve().as_uri()
            bg_style = f"background: linear-gradient(rgba(3,8,20,0.85), rgba(3,8,20,0.85)), url('{abs_bg}') center/cover no-repeat;"

        html_content = f"""<!DOCTYPE html>
<html lang="ur" dir="rtl">
<head>
<meta charset="UTF-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&display=swap">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    width: 1080px; height: 1080px;
    {bg_style}
    font-family: 'Noto Nastaliq Urdu', serif;
    display: flex; flex-direction: column; align-items: center; justify-content: space-between;
    padding: 60px; color: #fff; text-align: center; overflow: hidden;
    position: relative;
  }}
  /* اسلامی پس منظر کی باریک جیومیٹری */
  .bg-pattern {{
    position: absolute; inset: 0;
    background-image: radial-gradient(rgba(245, 186, 30, 0.08) 1px, transparent 1px);
    background-size: 32px 32px;
    pointer-events: none;
  }}
  .border-outer {{
    position: absolute; inset: 24px;
    border: 4px solid #f5ba1e;
    border-radius: 12px;
    pointer-events: none;
  }}
  .border-inner {{
    position: absolute; inset: 34px;
    border: 1.5px solid #00b4d8;
    border-radius: 8px;
    pointer-events: none;
  }}
  .corner-knot {{
    position: absolute; width: 30px; height: 30px;
    border-color: #ffd700; border-style: solid; pointer-events: none;
  }}
  .ck-tl {{ top: 20px; left: 20px; border-width: 5px 0 0 5px; }}
  .ck-tr {{ top: 20px; right: 20px; border-width: 5px 5px 0 0; }}
  .ck-bl {{ bottom: 20px; left: 20px; border-width: 0 0 5px 5px; }}
  .ck-br {{ bottom: 20px; right: 20px; border-width: 0 5px 5px 0; }}

  .header-brand {{
    font-size: 30px; color: #f5ba1e; font-weight: 700;
    letter-spacing: 1px; margin-top: 15px;
    text-shadow: 0 2px 10px rgba(245, 186, 30, 0.4);
  }}
  .divider {{
    width: 260px; height: 2px;
    background: linear-gradient(90deg, transparent, #00b4d8, transparent);
    margin: 10px auto;
  }}
  .title-badge {{
    background: rgba(245, 186, 30, 0.12);
    border: 1.5px solid #f5ba1e;
    color: #ffd700;
    padding: 8px 36px;
    border-radius: 50px;
    font-size: 32px;
    font-weight: 700;
    display: inline-block;
    margin-top: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  }}
  .quote-container {{
    max-width: 900px;
    padding: 10px 40px;
    margin: auto;
  }}
  .quote-text {{
    font-size: 40px;
    line-height: 2.15;
    color: #f8f9fa;
    text-shadow: 0 4px 15px rgba(0,0,0,0.8);
  }}
  .quote-symbol {{
    color: #f5ba1e;
    font-size: 50px;
    vertical-align: middle;
  }}
  .footer-source {{
    font-size: 26px;
    color: #90e0ef;
    background: rgba(0, 180, 216, 0.08);
    border: 1px solid rgba(0, 180, 216, 0.3);
    padding: 8px 32px;
    border-radius: 30px;
    margin-bottom: 20px;
  }}
</style>
</head>
<body>
  <div class="bg-pattern"></div>
  <div class="border-outer"></div>
  <div class="border-inner"></div>
  <div class="corner-knot ck-tl"></div>
  <div class="corner-knot ck-tr"></div>
  <div class="corner-knot ck-bl"></div>
  <div class="corner-knot ck-br"></div>
  <div>
    <div class="header-brand">🕌 THE BAYAAN • دی بیان</div>
    <div class="divider"></div>
    <div class="title-badge">{title}</div>
  </div>
  <div class="quote-container">
    <p class="quote-text">
      <span class="quote-symbol">«</span>
      {content_text}
      <span class="quote-symbol">»</span>
    </p>
  </div>
  <div class="footer-source">
    📖 ماخذ و حوالہ: {source}
  </div>
</body>
</html>"""
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    channel="chrome",
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
                )
                page = await browser.new_page(viewport={"width": 1080, "height": 1080})
                await page.set_content(html_content, wait_until="networkidle")
                await page.screenshot(path=str(out_file))
                await browser.close()
                logger.info(f"نستعلیق کارڈ بذریعہ براؤزر کامیابی سے تیار ہوا: {out_file}")
                return out_file.resolve()
        except Exception as e:
            logger.warning(f"Playwright سے کارڈ بنانے میں تنبیہ: {e}، PIL فال بیک استعمال ہو رہا ہے۔")
            return self.generate_image_post_card(title, content_text, source, filename_prefix)

    def generate_image_post_card(
        self,
        title: str,
        content_text: str,
        source: Optional[str] = "دی بیان (The Bayaan)",
        filename_prefix: str = "img_post"
    ) -> Path:
        """
        1080x1080 اسکوائر ہائی ریزولیوشن اسلامی کارڈ تیار کرتا ہے (PIL فال بیک)
        """
        width, height = 1080, 1080
        # پس منظر: رائل نیوی بلیو
        img = Image.new("RGB", (width, height), color=(11, 19, 43))
        draw = ImageDraw.Draw(img)

        # 1. شاہی سنہری بارڈر
        draw.rectangle([35, 35, width - 35, height - 35], outline=(255, 183, 3), width=6)
        draw.rectangle([50, 50, width - 50, height - 50], outline=(0, 180, 216), width=2)

        # کونوں کے سنہری زاویے
        corner_len = 50
        for x, y, dx, dy in [
            (35, 35, 1, 1),
            (width - 35, 35, -1, 1),
            (35, height - 35, 1, -1),
            (width - 35, height - 35, -1, -1)
        ]:
            x1, y1 = x + dx * corner_len, y + dy * 12
            draw.rectangle([min(x, x1), min(y, y1), max(x, x1), max(y, y1)], fill=(255, 183, 3))
            x2, y2 = x + dx * 12, y + dy * corner_len
            draw.rectangle([min(x, x2), min(y, y2), max(x, x2), max(y, y2)], fill=(255, 183, 3))

        # 2. برانڈنگ ہیڈر (The Bayaan)
        try:
            brand_font = ImageFont.truetype(self.font_path, 36)
            title_font = ImageFont.truetype(self.font_path, 46)
            body_font = ImageFont.truetype(self.font_path, 40)
            meta_font = ImageFont.truetype(self.font_path, 28)
        except Exception:
            brand_font = ImageFont.load_default()
            title_font = brand_font
            body_font = brand_font
            meta_font = brand_font

        # برانڈ ایمبلم
        brand_text = self._format_urdu_text("The Bayaan — دی بیان")
        draw.text((width // 2, 110), brand_text, font=brand_font, fill=(255, 183, 3), anchor="mm")
        draw.line([(width // 2 - 200, 150), (width // 2 + 200, 150)], fill=(0, 180, 216), width=2)

        # 3. عنوان (اگر ہو)
        cur_y = 240
        if title:
            formatted_title = self._format_urdu_text(title)
            draw.text((width // 2, cur_y), formatted_title, font=title_font, fill=(255, 215, 0), anchor="mm")
            cur_y += 80

        # 4. مرکزی متن (اردو ریپنگ مع RTL)
        lines = textwrap.wrap(content_text, width=38)
        for line in lines:
            formatted_line = self._format_urdu_text(line)
            draw.text((width // 2, cur_y), formatted_line, font=body_font, fill=(248, 249, 250), anchor="mm")
            cur_y += 65

        # 5. فوٹر / ماخذ
        if source:
            footer_text = self._format_urdu_text(f"ماخذ و حوالہ: {source}")
            draw.text((width // 2, height - 110), footer_text, font=meta_font, fill=(148, 163, 184), anchor="mm")

        out_file = self.output_dir / f"{filename_prefix}_{int(os.times().system * 1000)}.png"
        img.save(out_file, quality=95)
        logger.info(f"اسلامی کارڈ کامیابی سے تیار ہوا: {out_file}")
        return out_file.resolve()

    def generate_poll_option_card(
        self,
        option_index: int,
        option_text: str,
        bg_color: Optional[Tuple[int, int, int]] = None
    ) -> Path:
        """
        تصویر پول (Image Poll) کے ہر آپشن کے لیے 800x800 اسکوائر کارڈ بناتا ہے
        """
        width, height = 800, 800
        # ہر آپشن کا منفرد خوبصورت ڈارک بیک گراؤنڈ
        default_colors = [
            (11, 19, 43),   # رائل نیوی
            (28, 37, 65),   # مڈ نائٹ
            (20, 40, 50),   # ڈارک سیان
            (30, 20, 45),   # ڈارک پرپل
        ]
        color = bg_color or default_colors[(option_index - 1) % len(default_colors)]

        img = Image.new("RGB", (width, height), color=color)
        draw = ImageDraw.Draw(img)

        # سنہری ڈبل فریم
        draw.rectangle([25, 25, width - 25, height - 25], outline=(255, 183, 3), width=6)
        draw.rectangle([38, 38, width - 38, height - 38], outline=(0, 180, 216), width=2)

        try:
            num_font = ImageFont.truetype(self.font_path, 40)
            text_font = ImageFont.truetype(self.font_path, 44)
        except Exception:
            num_font = ImageFont.load_default()
            text_font = num_font

        # آپشن نمبر ببل
        draw.ellipse([width // 2 - 40, 100, width // 2 + 40, 180], fill=(255, 183, 3))
        draw.text((width // 2, 140), str(option_index), font=num_font, fill=(11, 19, 43), anchor="mm")

        # آپشن متن
        lines = textwrap.wrap(option_text, width=24)
        y_start = height // 2 - (len(lines) * 35) + 30
        for idx, line in enumerate(lines):
            formatted_line = self._format_urdu_text(line)
            draw.text((width // 2, y_start + (idx * 70)), formatted_line, font=text_font, fill=(255, 255, 255), anchor="mm")

        out_file = self.output_dir / f"poll_opt_{option_index}_{int(os.times().system * 1000)}.png"
        img.save(out_file, quality=95)
        return out_file.resolve()

    def process_user_uploaded_image(self, input_path: Path) -> Path:
        """
        صارف کی اپلوڈ کردہ تصویر کو یوٹیوب کمیونٹی ٹیب کی شرائط (Square, High-Res, <5MB) میں کنورٹ کرتا ہے
        """
        try:
            with Image.open(input_path) as img:
                img = img.convert("RGB")
                # اسکوائر کراپ یا اسکیل کریں
                w, h = img.size
                min_dim = min(w, h)
                left = (w - min_dim) // 2
                top = (h - min_dim) // 2
                img_cropped = img.crop((left, top, left + min_dim, top + min_dim))
                img_resized = img_cropped.resize((1080, 1080), Image.Resampling.LANCZOS)
                
                out_path = self.output_dir / f"user_img_{int(os.times().system * 1000)}.png"
                img_resized.save(out_path, format="PNG", quality=95)
                return out_path.resolve()
        except Exception as e:
            logger.error(f"اپلوڈ کردہ تصویر کی پروسیسنگ میں خرابی: {e}")
            return input_path

image_card_service = ImageCardService()
