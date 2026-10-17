import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

def format_urdu(text):
    if not text:
        return ""
    return get_display(arabic_reshaper.reshape(text))

def create_stunning_card(title, card_text, source, topic="فرعون"):
    width, height = 1080, 1080
    
    # 1. Base Gradient Background (Deep Midnight to Dark Royal Teal/Navy)
    base = Image.new("RGBA", (width, height), (6, 12, 28, 255))
    draw = ImageDraw.Draw(base)
    
    # Draw radial-like concentric gradient for glowing aura in center
    cx, cy = width // 2, height // 2 - 30
    max_radius = int(math.hypot(width, height) / 1.5)
    
    # Create radial gradient overlay
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(gradient)
    
    # Glow layers
    for r in range(max_radius, 0, -15):
        alpha = int(70 * (1 - r / max_radius))
        # Warm gold-teal subtle hue at center
        g_draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(14, 43, 75, alpha)
        )
    
    base = Image.alpha_composite(base, gradient)
    draw = ImageDraw.Draw(base)
    
    # 2. Draw Subtle Islamic Geometric Lattice / Stars in background
    pattern_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    p_draw = ImageDraw.Draw(pattern_overlay)
    step = 90
    for x in range(60, width - 60, step):
        for y in range(120, height - 120, step):
            # 8-point geometric star pattern (subtle gold with low alpha)
            r1, r2 = 18, 9
            points = []
            for i in range(16):
                radius = r1 if i % 2 == 0 else r2
                angle = i * math.pi / 8
                px = x + radius * math.cos(angle)
                py = y + radius * math.sin(angle)
                points.append((px, py))
            p_draw.polygon(points, outline=(255, 215, 0, 22), width=1)
            p_draw.circle((x, y), 3, fill=(0, 180, 216, 25))

    base = Image.alpha_composite(base, pattern_overlay)
    draw = ImageDraw.Draw(base)
    
    # 3. Ornate Double Golden Borders with Corner Embellishments
    gold_main = (245, 186, 30)
    gold_soft = (212, 175, 55)
    cyan_glow = (0, 180, 216)
    
    # Outer Border
    draw.rectangle([35, 35, width - 35, height - 35], outline=gold_main, width=5)
    # Inner Thin Accent Border
    draw.rectangle([48, 48, width - 48, height - 48], outline=cyan_glow, width=2)
    # Third Subtle Border
    draw.rectangle([58, 58, width - 58, height - 58], outline=(255, 255, 255, 40), width=1)
    
    # Ornate Islamic Corner Knots
    corner_size = 45
    for cx_c, cy_c, sx, sy in [
        (35, 35, 1, 1),
        (width - 35, 35, -1, 1),
        (35, height - 35, 1, -1),
        (width - 35, height - 35, -1, -1)
    ]:
        x1, y1 = cx_c, cy_c
        x2, y2 = cx_c + sx * corner_size, cy_c + sy * 10
        draw.rectangle([min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)], fill=gold_main)
        x3, y3 = cx_c + sx * 10, cy_c + sy * corner_size
        draw.rectangle([min(x1, x3), min(y1, y3), max(x1, x3), max(y1, y3)], fill=gold_main)
        # Diamond motif in corner
        dm_x, dm_y = cx_c + sx * 24, cy_c + sy * 24
        draw.polygon([
            (dm_x, dm_y - 8),
            (dm_x + 8, dm_y),
            (dm_x, dm_y + 8),
            (dm_x - 8, dm_y)
        ], fill=gold_main)

    # 4. Top Arched Header (Mihrab / Dome Contour)
    arch_w = 400
    arch_top = 70
    arch_bot = 145
    # Islamic arch apex
    draw.arc([width // 2 - arch_w // 2, arch_top, width // 2 + arch_w // 2, arch_top + 100], 180, 360, fill=gold_soft, width=3)
    
    # Top Brand Ribbon
    font_path = "agent_am/ui/static/fonts/JameelNooriNastaleeq.ttf"
    try:
        font_brand = ImageFont.truetype(font_path, 32)
        font_title = ImageFont.truetype(font_path, 48)
        font_body = ImageFont.truetype(font_path, 40)
        font_meta = ImageFont.truetype(font_path, 28)
    except Exception:
        font_brand = ImageFont.load_default()
        font_title = font_brand
        font_body = font_brand
        font_meta = font_brand
    
    # Draw Brand Text with subtle shadow
    brand_str = format_urdu("THE BAYAAN  •  دی بیان")
    draw.text((width // 2 + 1, arch_bot + 1), brand_str, font=font_brand, fill=(0, 0, 0, 180), anchor="mm")
    draw.text((width // 2, arch_bot), brand_str, font=font_brand, fill=gold_main, anchor="mm")
    
    # Header Decorative Divider
    div_y = arch_bot + 35
    draw.line([(width // 2 - 180, div_y), (width // 2 + 180, div_y)], fill=cyan_glow, width=2)
    draw.polygon([
        (width // 2, div_y - 6),
        (width // 2 + 7, div_y),
        (width // 2, div_y + 6),
        (width // 2 - 7, div_y)
    ], fill=gold_main)

    # 5. Title Cartouche (Elegant Banner)
    title_y = div_y + 90
    title_fmt = format_urdu(title)
    
    # Title shadow + text
    draw.text((width // 2 + 2, title_y + 2), title_fmt, font=font_title, fill=(0, 0, 0, 200), anchor="mm")
    draw.text((width // 2, title_y), title_fmt, font=font_title, fill=(255, 235, 120), anchor="mm")
    
    # Title underline with flourish
    tu_y = title_y + 50
    draw.line([(width // 2 - 140, tu_y), (width // 2 + 140, tu_y)], fill=gold_soft, width=2)
    draw.circle((width // 2 - 140, tu_y), 4, fill=gold_main)
    draw.circle((width // 2 + 140, tu_y), 4, fill=gold_main)
    draw.circle((width // 2, tu_y), 5, fill=cyan_glow)

    # 6. Central Card Text (Urdu Nastaliq with Gold Quotes)
    import textwrap
    lines = textwrap.wrap(card_text, width=32)
    total_text_h = len(lines) * 78
    start_y = 540 - (total_text_h // 2)
    
    # Large Elegant Golden Calligraphic Quotation marks « and »
    quote_font = ImageFont.truetype(font_path, 54) if Path(font_path).exists() else font_title
    draw.text((width - 120, start_y - 20), "«", font=quote_font, fill=gold_main, anchor="mm")
    draw.text((120, start_y + total_text_h + 10), "»", font=quote_font, fill=gold_main, anchor="mm")
    
    for idx, l in enumerate(lines):
        line_y = start_y + (idx * 76)
        formatted_line = format_urdu(l)
        # Drop shadow for readability
        draw.text((width // 2 + 2, line_y + 2), formatted_line, font=font_body, fill=(0, 0, 0, 220), anchor="mm")
        # Pristine ivory / bright white text
        draw.text((width // 2, line_y), formatted_line, font=font_body, fill=(250, 252, 255), anchor="mm")

    # 7. Lower Section: Authentic Reference Cartouche
    ref_y = height - 140
    # Divider above reference
    draw.line([(width // 2 - 250, ref_y - 45), (width // 2 + 250, ref_y - 45)], fill=(0, 180, 216, 120), width=1)
    draw.polygon([
        (width // 2, ref_y - 50),
        (width // 2 + 6, ref_y - 45),
        (width // 2, ref_y - 40),
        (width // 2 - 6, ref_y - 45)
    ], fill=gold_main)
    
    # Reference Text with Book Icon / Arabic bracket
    ref_fmt = format_urdu(f"📖 ماخذ و حوالہ: {source}")
    draw.text((width // 2 + 1, ref_y + 1), ref_fmt, font=font_meta, fill=(0, 0, 0, 180), anchor="mm")
    draw.text((width // 2, ref_y), ref_fmt, font=font_meta, fill=(180, 225, 245), anchor="mm")
    
    # Save image
    out_path = Path("reports/test_stunning_pharaoh_card.png")
    base.convert("RGB").save(out_path, quality=95)
    print("Saved to", out_path)
    return out_path

if __name__ == "__main__":
    create_stunning_card(
        title="عبرت کا درس: فرعون کا تکبر اور انجام",
        card_text="جس نے اپنی جھوٹی خدائی کا دعویٰ کیا، اللہ تعالیٰ نے اسے سمندر کی اتھاہ گہرائیوں میں غرق کر کے رہتی دنیا کے لیے نشانِ عبرت بنا دیا۔ تکبر اور ظلم کا انجام ہمیشہ ذلت اور ہلاکت ہے۔",
        source="قرآن مجید، سورۃ یونس، آیت: 92",
        topic="فرعون"
    )
