"""
Generate Himalayas Tech and PowerScan logo images for PDF reports.
High-resolution (4x) for crisp, sharp rendering.
"""
import os
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

SCALE = 4


def generate_himalayas_logo():
    """Generate Himalayas Tech logo - mountain chevrons + text"""
    width, height = 260 * SCALE, 140 * SCALE
    img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img, 'RGBA')
    
    orange = (242, 163, 60)
    dark = (35, 35, 35)
    s = SCALE

    # Center X for the mountain icon
    cx = 120 * s
    
    # ---- Mountain chevrons (matching the angular M shape) ----
    thickness = 16 * s
    
    # Left chevron (back mountain, slightly smaller)
    lx = cx - 30*s  # center of left chevron
    peak_y = 15*s
    base_y = 72*s
    hw = 48*s  # half width at base
    
    # Outer left chevron
    draw.polygon([
        (lx, peak_y),           # peak
        (lx - hw, base_y),      # bottom left
        (lx - hw + thickness, base_y),  # inner bottom left
        (lx, peak_y + thickness),       # inner peak
        (lx + hw - thickness, base_y),  # inner bottom right
        (lx + hw, base_y),      # bottom right
    ], fill=orange)
    
    # Right chevron (front mountain, slightly taller, overlapping)
    rx = cx + 25*s
    peak_y2 = 5*s
    base_y2 = 72*s
    hw2 = 48*s
    
    draw.polygon([
        (rx, peak_y2),
        (rx - hw2, base_y2),
        (rx - hw2 + thickness, base_y2),
        (rx, peak_y2 + thickness),
        (rx + hw2 - thickness, base_y2),
        (rx + hw2, base_y2),
    ], fill=orange)
    
    # ---- Text ----
    try:
        font_bold = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 24*s)
        font_sub = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 11*s)
    except:
        font_bold = ImageFont.load_default()
        font_sub = ImageFont.load_default()
    
    # "HIMALAYAS TECH"
    text = "HIMALAYAS TECH"
    bbox_text = draw.textbbox((0, 0), text, font=font_bold)
    tw = bbox_text[2] - bbox_text[0]
    tx = (width - tw) // 2
    draw.text((tx, 80*s), text, fill=dark, font=font_bold)
    
    # "DIGITAL TECHNOLOGY" subtitle
    sub = "DIGITAL TECHNOLOGY"
    bbox_sub = draw.textbbox((0, 0), sub, font=font_sub)
    sw = bbox_sub[2] - bbox_sub[0]
    sx = (width - sw) // 2
    draw.text((sx, 110*s), sub, fill=(120, 120, 120), font=font_sub)
    
    # Crop and save
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    
    path = os.path.join(ASSETS_DIR, "himalayas_tech_logo.png")
    img.save(path, "PNG")
    print(f"Saved: {path} ({img.size[0]}x{img.size[1]})")
    return path


def generate_powerscan_logo():
    """Generate PowerScan logo - lightning bolt + text"""
    width, height = 240 * SCALE, 130 * SCALE
    img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img, 'RGBA')
    
    yellow = (250, 200, 15)
    orange_accent = (240, 140, 40)
    dark_gray = (110, 110, 110)
    dark = (55, 55, 55)
    s = SCALE
    
    cx = 120 * s
    
    # ---- Lightning bolt ----
    # Main bolt shape (cleaner, more geometric)
    draw.polygon([
        (cx + 2*s, 5*s),       # top
        (cx - 18*s, 48*s),     # left notch top
        (cx - 5*s, 45*s),      # inner left
        (cx - 25*s, 88*s),     # bottom tip
        (cx + 12*s, 42*s),     # right notch
        (cx - 2*s, 47*s),      # inner right
    ], fill=yellow)
    
    # Orange accent on left side of bolt
    draw.polygon([
        (cx - 8*s, 38*s),
        (cx - 18*s, 50*s),
        (cx - 5*s, 47*s),
        (cx - 15*s, 68*s),
    ], fill=orange_accent)
    
    # ---- Text ----
    try:
        font_light = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 24*s)
        font_bold = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 24*s)
        font_sub = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 10*s)
    except:
        font_light = ImageFont.load_default()
        font_bold = ImageFont.load_default()
        font_sub = ImageFont.load_default()
    
    # Measure "Power" and "Scan" widths
    pw_bbox = draw.textbbox((0, 0), "Power", font=font_light)
    pw_w = pw_bbox[2] - pw_bbox[0]
    sc_bbox = draw.textbbox((0, 0), "Scan", font=font_bold)
    sc_w = sc_bbox[2] - sc_bbox[0]
    total_w = pw_w + sc_w + 2*s
    
    text_x = (width - total_w) // 2
    text_y = 92 * s
    
    draw.text((text_x, text_y), "Power", fill=dark_gray, font=font_light)
    draw.text((text_x + pw_w + 2*s, text_y), "Scan", fill=dark, font=font_bold)
    
    # "Power Line Diagnosis" subtitle
    sub = "Power Line Diagnosis"
    sub_bbox = draw.textbbox((0, 0), sub, font=font_sub)
    sub_w = sub_bbox[2] - sub_bbox[0]
    sub_x = (width - sub_w) // 2
    draw.text((sub_x, 120*s), sub, fill=(155, 155, 155), font=font_sub)
    
    # Crop and save
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    
    path = os.path.join(ASSETS_DIR, "powerscan_logo.png")
    img.save(path, "PNG")
    print(f"Saved: {path} ({img.size[0]}x{img.size[1]})")
    return path


if __name__ == "__main__":
    generate_himalayas_logo()
    generate_powerscan_logo()
    print("Logo generation complete!")
