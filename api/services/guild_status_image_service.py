import io
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

IMG_W    = 960
HDR_H    = 64
COL_H    = 38
ROW_H    = 46

BG         = (15, 15, 22)
HDR_BG     = (28, 28, 42)
COL_BG     = (22, 22, 36)
ROW_EVEN   = (20, 20, 30)
ROW_ODD    = (17, 17, 26)
SEP        = (40, 40, 58)
WHITE      = (230, 230, 240)
GRAY       = (130, 130, 150)
GOLD       = (255, 200, 60)
SILVER     = (180, 190, 210)
BRONZE     = (200, 150, 100)
ACCENT     = (80, 160, 255)

# 열 정의: (제목, x시작, 너비, 정렬)
COLS = [
    ("순위",       12,  58, "center"),
    ("캐릭터명",   70, 190, "left"),
    ("직업",      260, 150, "left"),
    ("전투력",    410, 200, "right"),
    ("아이템레벨", 610, 150, "right"),
    ("갱신",      760, 200, "left"),
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


def _draw_text_aligned(draw, text, x, col_w, y, font, fill, align):
    try:
        bb = draw.textbbox((0, 0), text, font=font)
        tw = bb[2] - bb[0]
    except Exception:
        tw = len(text) * 9
    if align == "center":
        draw.text((x + (col_w - tw) // 2, y), text, fill=fill, font=font)
    elif align == "right":
        draw.text((x + col_w - tw - 4, y), text, fill=fill, font=font)
    else:
        draw.text((x + 4, y), text, fill=fill, font=font)


def _rank_color(rank: int):
    if rank == 1:
        return GOLD
    if rank == 2:
        return SILVER
    if rank == 3:
        return BRONZE
    return WHITE


def _time_ago(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)
        diff = datetime.now(timezone.utc) - dt
        m = int(diff.total_seconds() // 60)
        if m < 60:
            return f"{m}분 전"
        h = m // 60
        if h < 24:
            return f"{h}시간 전"
        return f"{h // 24}일 전"
    except Exception:
        return "-"


def generate_guild_status_image(members: list) -> bytes:
    """
    members: [{"name", "class", "combat_power", "item_level", "level", "updated_at"}, ...]
    이미 combat_power 내림차순으로 정렬된 상태로 받음
    """
    n = len(members)
    total_h = HDR_H + COL_H + max(n, 1) * ROW_H + 8

    img  = Image.new("RGB", (IMG_W, total_h), BG)
    draw = ImageDraw.Draw(img)

    f_hdr  = _load_font(24)
    f_col  = _load_font(16)
    f_name = _load_font(18)
    f_sub  = _load_font(15)

    # ── 헤더 ──────────────────────────────────────────────────
    draw.rectangle([0, 0, IMG_W - 1, HDR_H - 1], fill=HDR_BG)
    now_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    draw.text((20, (HDR_H - 24) // 2), "⚔ 길드 현황", fill=WHITE, font=f_hdr)
    try:
        bb = draw.textbbox((0, 0), now_str, font=f_sub)
        tw = bb[2] - bb[0]
    except Exception:
        tw = len(now_str) * 8
    draw.text((IMG_W - tw - 16, (HDR_H - 15) // 2), now_str, fill=GRAY, font=f_sub)

    # ── 열 헤더 ───────────────────────────────────────────────
    col_y = HDR_H
    draw.rectangle([0, col_y, IMG_W - 1, col_y + COL_H - 1], fill=COL_BG)
    draw.line([0, col_y, IMG_W, col_y], fill=SEP)
    draw.line([0, col_y + COL_H - 1, IMG_W, col_y + COL_H - 1], fill=SEP)
    for title, cx, cw, align in COLS:
        ty = col_y + (COL_H - 16) // 2
        _draw_text_aligned(draw, title, cx, cw, ty, f_col, GRAY, align)

    # ── 데이터 행 ─────────────────────────────────────────────
    if not members:
        row_y = HDR_H + COL_H
        draw.rectangle([0, row_y, IMG_W - 1, row_y + ROW_H - 1], fill=ROW_EVEN)
        draw.text((IMG_W // 2 - 60, row_y + (ROW_H - 18) // 2), "등록된 길드원이 없습니다", fill=GRAY, font=f_name)
    else:
        for i, m in enumerate(members):
            rank   = i + 1
            row_y  = HDR_H + COL_H + i * ROW_H
            row_bg = ROW_EVEN if i % 2 == 0 else ROW_ODD
            draw.rectangle([0, row_y, IMG_W - 1, row_y + ROW_H - 1], fill=row_bg)
            draw.line([0, row_y, IMG_W, row_y], fill=SEP)

            ty = row_y + (ROW_H - 18) // 2

            # 순위
            r_col = _rank_color(rank)
            _draw_text_aligned(draw, str(rank), COLS[0][1], COLS[0][2], ty, f_name, r_col, "center")

            # 캐릭터명
            _draw_text_aligned(draw, m["name"], COLS[1][1], COLS[1][2], ty, f_name, WHITE, "left")

            # 직업
            _draw_text_aligned(draw, m.get("class", "-"), COLS[2][1], COLS[2][2], ty, f_sub, GRAY, "left")

            # 전투력
            cp_str = f"{m['combat_power']:,}"
            _draw_text_aligned(draw, cp_str, COLS[3][1], COLS[3][2], ty, f_name, ACCENT, "right")

            # 아이템레벨
            il = m.get("item_level") or 0
            il_str = f"{il:,}" if il else "-"
            _draw_text_aligned(draw, il_str, COLS[4][1], COLS[4][2], ty, f_sub, WHITE, "right")

            # 갱신
            _draw_text_aligned(draw, _time_ago(m["updated_at"]), COLS[5][1], COLS[5][2], ty, f_sub, GRAY, "left")

    # 하단 구분선
    draw.line([0, total_h - 2, IMG_W, total_h - 2], fill=SEP)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.read()
