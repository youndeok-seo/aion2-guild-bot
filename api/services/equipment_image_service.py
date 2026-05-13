import httpx
import asyncio
import io
from PIL import Image, ImageDraw, ImageFont

# ── 레이아웃 ─────────────────────────────────────────────
IMG_W     = 580
TITLE_H   = 38
ROW_H     = 64
ICON_SIZE = 46
ICON_X    = 10
TEXT_X    = ICON_X + ICON_SIZE + 10   # 66
SKIN_SIZE = 46
SKIN_X    = IMG_W - 10 - SKIN_SIZE    # 524

# ── 색상 ─────────────────────────────────────────────────
BG         = (20, 20, 26)
ROW_ALT    = (24, 24, 32)
TITLE_BG   = (30, 30, 42)
TITLE_CLR  = (220, 220, 235)
SEP_CLR    = (45, 45, 58)
BADGE_CLR  = (0, 150, 210)

GRADE_CLR = {
    "Legend": (255, 165, 60),
    "Epic":   (255, 138, 20),
    "Unique": (80,  170, 255),
    "Special":(160, 160, 175),
}

# 슬롯 표시 순서
SLOT_ORDER = [
    "MainHand", "SubHand",
    "Helmet", "Shoulder", "Torso", "Pants", "Gloves", "Boots", "Cape", "Belt",
    "Necklace", "Earring1", "Earring2", "Ring1", "Ring2",
    "Bracelet1", "Bracelet2", "Rune1", "Rune2", "Amulet",
    "Arcana1", "Arcana2", "Arcana3", "Arcana4", "Arcana5", "Arcana6",
]


def _load_font(size: int) -> ImageFont.ImageFont:
    for path in [
        "C:/Windows/Fonts/malgun.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


async def _fetch(client: httpx.AsyncClient, url: str | None) -> Image.Image | None:
    if not url:
        return None
    try:
        r = await client.get(url, timeout=6.0)
        if r.status_code == 200:
            return Image.open(io.BytesIO(r.content)).convert("RGBA")
    except Exception:
        pass
    return None


def _draw_badge(draw: ImageDraw.ImageDraw, cx: int, cy: int, level: int, font):
    """파란 다이아몬드 초월 뱃지"""
    s = 9
    pts = [(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)]
    draw.polygon(pts, fill=BADGE_CLR)
    t = str(level)
    try:
        bb = draw.textbbox((0, 0), t, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
    except Exception:
        tw, th = 6, 9
    draw.text((cx - tw // 2, cy - th // 2), t, fill=(255, 255, 255), font=font)


async def generate_equipment_image(equipment: list) -> bytes:
    items_by_slot = {item["slot"]: item for item in equipment}
    ordered = [items_by_slot[s] for s in SLOT_ORDER if s in items_by_slot]

    if not ordered:
        img = Image.new("RGB", (IMG_W, 80), BG)
        buf = io.BytesIO(); img.save(buf, "PNG"); buf.seek(0)
        return buf.read()

    # 아이콘 + 스킨 URL 목록
    icon_urls = [item.get("icon") for item in ordered]
    skin_urls = [item.get("skin_icon") for item in ordered]

    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        follow_redirects=True,
        timeout=8.0,
    ) as client:
        item_icons, skin_icons = await asyncio.gather(
            asyncio.gather(*[_fetch(client, u) for u in icon_urls]),
            asyncio.gather(*[_fetch(client, u) for u in skin_urls]),
        )

    f_title = _load_font(15)
    f_name  = _load_font(15)
    f_badge = _load_font(10)

    total_h = TITLE_H + len(ordered) * ROW_H
    img  = Image.new("RGB", (IMG_W, total_h), BG)
    draw = ImageDraw.Draw(img)

    # 타이틀 바
    draw.rectangle([0, 0, IMG_W - 1, TITLE_H - 1], fill=TITLE_BG)
    draw.text((12, (TITLE_H - 15) // 2), "장비", fill=TITLE_CLR, font=f_title)

    for idx, item in enumerate(ordered):
        row_y  = TITLE_H + idx * ROW_H
        row_bg = ROW_ALT if idx % 2 == 0 else BG
        draw.rectangle([0, row_y, IMG_W - 1, row_y + ROW_H - 1], fill=row_bg)
        draw.line([0, row_y, IMG_W, row_y], fill=SEP_CLR)

        icon_y = row_y + (ROW_H - ICON_SIZE) // 2
        icon   = item_icons[idx]
        if icon:
            img.paste(icon.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS),
                      (ICON_X, icon_y), icon.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS))
        else:
            draw.rectangle([ICON_X, icon_y, ICON_X + ICON_SIZE - 1, icon_y + ICON_SIZE - 1],
                           fill=(40, 40, 50), outline=(60, 60, 75))

        gc     = GRADE_CLR.get(item["grade"], (180, 180, 180))
        text_y = row_y + (ROW_H - 18) // 2
        tx     = TEXT_X

        # 초월 뱃지
        exceed = item.get("exceed", 0)
        if exceed:
            badge_cx = tx + 9
            badge_cy = text_y + 9
            _draw_badge(draw, badge_cx, badge_cy, exceed, f_badge)
            tx += 22

        # 강화 레벨 (+20)
        enchant = item.get("enchant", 0)
        if enchant:
            enc_str = f"+{enchant} "
            draw.text((tx, text_y), enc_str, fill=gc, font=f_name)
            try:
                bb = draw.textbbox((0, 0), enc_str, font=f_name)
                tx += bb[2] - bb[0]
            except Exception:
                tx += len(enc_str) * 9

        # 아이템 이름
        draw.text((tx, text_y), item["name"], fill=gc, font=f_name)

        # 스킨 아이콘
        skin = skin_icons[idx]
        if skin:
            skin_y = row_y + (ROW_H - SKIN_SIZE) // 2
            draw.rectangle(
                [SKIN_X - 2, skin_y - 2, SKIN_X + SKIN_SIZE + 1, skin_y + SKIN_SIZE + 1],
                fill=(35, 35, 48), outline=(55, 55, 70),
            )
            img.paste(skin.resize((SKIN_SIZE, SKIN_SIZE), Image.LANCZOS),
                      (SKIN_X, skin_y), skin.resize((SKIN_SIZE, SKIN_SIZE), Image.LANCZOS))

    draw.line([0, total_h - 1, IMG_W, total_h - 1], fill=SEP_CLR)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.read()
