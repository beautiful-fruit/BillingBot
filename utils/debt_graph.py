"""
將債務整理結果繪製成網路圖（PNG）。

- 節點：每位使用者的頭像（圓形裁切）
- 邊：付款者 → 收款者的箭頭，並標示金額

規劃結果中每人最多付款給一人，整體是以「最終收款人」為根的樹（或森林），
因此採用階層式樹狀佈局：收款人在上、付款人在下，箭頭一律朝上。
邊只會連接相鄰兩層，同層節點左右錯開，所以箭頭不會穿過其他頭像。
"""

from io import BytesIO
from math import atan2, cos, sin

from PIL import Image, ImageDraw, ImageFont

from utils.debt_planner import Transfer

# 以 SCALE 倍解析度繪製後再縮小，達到反鋸齒效果
SCALE = 2

NODE_RADIUS = 48
PADDING = 40
SLOT_WIDTH = 2 * NODE_RADIUS + 80  # 同層相鄰節點的水平間距
LEVEL_HEIGHT = 2 * NODE_RADIUS + 130  # 相鄰兩層的垂直間距，留給箭頭與金額標籤
MIN_WIDTH = 480
ARROW_LENGTH = 18
ARROW_WIDTH = 9
LINE_WIDTH = 3
LABEL_POSITION = 0.5  # 金額標籤位於箭頭從起點算起的比例位置
LABEL_FONT_SIZE = 20

BACKGROUND = (43, 45, 49, 255)  # Discord 深色背景
EDGE_COLOR = (88, 166, 255, 255)
NODE_BORDER = (255, 255, 255, 255)
LABEL_BG = (30, 31, 34, 235)
LABEL_FG = (255, 255, 255, 255)
FALLBACK_AVATAR = (114, 118, 125, 255)

Point = tuple[float, float]


def _layout(transfers: list[Transfer]) -> tuple[dict[int, Point], int, int]:
    """
    階層式樹狀佈局。回傳 (uid -> 節點中心座標, 畫布寬, 畫布高)。

    每個葉節點佔一個水平欄位，父節點置於其子節點的水平中點；
    深度越深（越下游的付款人）越靠下方。
    """
    parent: dict[int, int] = {t.payer: t.payee for t in transfers}
    received: dict[int, int] = {}
    children: dict[int, list[int]] = {}
    amount_of: dict[int, int] = {t.payer: t.amount for t in transfers}
    for t in transfers:
        children.setdefault(t.payee, []).append(t.payer)
        received[t.payee] = received.get(t.payee, 0) + t.amount
    for items in children.values():
        items.sort(key=lambda u: (-amount_of[u], u))

    users = {uid for t in transfers for uid in (t.payer, t.payee)}
    roots = sorted(
        (uid for uid in users if uid not in parent),
        key=lambda u: (-received.get(u, 0), u),
    )

    slot_x: dict[int, float] = {}
    depth: dict[int, int] = {}
    next_slot = 0

    def place(uid: int, level: int) -> float:
        nonlocal next_slot
        depth[uid] = level
        kids = children.get(uid, [])
        if not kids:
            slot_x[uid] = next_slot
            next_slot += 1
        else:
            xs = [place(kid, level + 1) for kid in kids]
            slot_x[uid] = (xs[0] + xs[-1]) / 2
        return slot_x[uid]

    for root in roots:
        place(root, 0)

    content_width = (next_slot - 1) * SLOT_WIDTH + 2 * (NODE_RADIUS + PADDING)
    width = max(MIN_WIDTH, int(content_width))
    offset_x = (width - content_width) / 2 + NODE_RADIUS + PADDING
    height = int(max(depth.values()) * LEVEL_HEIGHT + 2 * (NODE_RADIUS + PADDING))

    positions = {
        uid: (
            float(offset_x + slot_x[uid] * SLOT_WIDTH),
            float(NODE_RADIUS + PADDING + depth[uid] * LEVEL_HEIGHT),
        )
        for uid in users
    }
    return positions, width, height


def _circle_avatar(data: bytes | None, size: int) -> Image.Image:
    avatar: Image.Image
    if data is not None:
        try:
            avatar = Image.open(BytesIO(data)).convert("RGBA")
            avatar = avatar.resize((size, size), Image.Resampling.LANCZOS)
        except Exception:  # pylint: disable=broad-exception-caught
            avatar = Image.new("RGBA", (size, size), FALLBACK_AVATAR)
    else:
        avatar = Image.new("RGBA", (size, size), FALLBACK_AVATAR)

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(avatar, (0, 0), mask)
    return result


def _edge_endpoints(start: Point, end: Point) -> tuple[Point, Point]:
    """回傳從起點節點邊緣到終點節點邊緣的線段"""
    angle = atan2(end[1] - start[1], end[0] - start[0])
    gap = (NODE_RADIUS + 4) * SCALE
    ux, uy = cos(angle), sin(angle)
    return (
        (start[0] + ux * gap, start[1] + uy * gap),
        (end[0] - ux * gap, end[1] - uy * gap),
    )


def _draw_edge(draw: ImageDraw.ImageDraw, start: Point, end: Point) -> None:
    (x1, y1), (tip_x, tip_y) = _edge_endpoints(start, end)
    angle = atan2(tip_y - y1, tip_x - x1)
    ux, uy = cos(angle), sin(angle)
    arrow_len = ARROW_LENGTH * SCALE
    base_x, base_y = tip_x - ux * arrow_len, tip_y - uy * arrow_len

    draw.line((x1, y1, base_x, base_y), fill=EDGE_COLOR, width=LINE_WIDTH * SCALE)
    half = ARROW_WIDTH * SCALE
    draw.polygon(
        [
            (tip_x, tip_y),
            (base_x - uy * half, base_y + ux * half),
            (base_x + uy * half, base_y - ux * half),
        ],
        fill=EDGE_COLOR,
    )


def _draw_label(
    draw: ImageDraw.ImageDraw,
    start: Point,
    end: Point,
    label: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    (x1, y1), (tip_x, tip_y) = _edge_endpoints(start, end)
    lx = x1 + (tip_x - x1) * LABEL_POSITION
    ly = y1 + (tip_y - y1) * LABEL_POSITION
    left, top, right, bottom = draw.textbbox((lx, ly), label, font=font, anchor="mm")
    pad = 6 * SCALE
    draw.rounded_rectangle(
        (left - pad, top - pad, right + pad, bottom + pad),
        radius=8 * SCALE,
        fill=LABEL_BG,
        outline=EDGE_COLOR,
        width=SCALE,
    )
    draw.text((lx, ly), label, font=font, fill=LABEL_FG, anchor="mm")


def render_debt_graph(
    transfers: list[Transfer],
    avatars: dict[int, bytes | None],
) -> BytesIO:
    """
    transfers: 規劃後的轉帳清單
    avatars: uid -> 頭像圖片 bytes（取得失敗時為 None，會以灰色圓形代替）
    """
    layout, width, height = _layout(transfers)
    positions = {uid: (x * SCALE, y * SCALE) for uid, (x, y) in layout.items()}

    image = Image.new("RGBA", (width * SCALE, height * SCALE), BACKGROUND)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=LABEL_FONT_SIZE * SCALE)

    # 繪製順序：箭頭 → 頭像 → 金額標籤，確保金額不會被頭像遮住
    for t in transfers:
        _draw_edge(draw, positions[t.payer], positions[t.payee])

    size = NODE_RADIUS * 2 * SCALE
    border = 3 * SCALE
    for uid, (x, y) in positions.items():
        draw.ellipse(
            (x - size / 2 - border, y - size / 2 - border,
             x + size / 2 + border, y + size / 2 + border),
            fill=NODE_BORDER,
        )
        avatar = _circle_avatar(avatars.get(uid), size)
        image.alpha_composite(avatar, (int(x - size / 2), int(y - size / 2)))

    for t in transfers:
        _draw_label(draw, positions[t.payer], positions[t.payee], str(t.amount), font)

    image = image.resize((width, height), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
