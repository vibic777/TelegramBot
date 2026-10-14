from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT = Path("assets/stickers/archive")
OUT.mkdir(parents=True, exist_ok=True)
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
FONT_REGULAR = "C:/Windows/Fonts/arial.ttf"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)


def center_text(draw: ImageDraw.ImageDraw, text: str, y: int, f: ImageFont.FreeTypeFont, fill: str) -> None:
    box = draw.textbbox((0, 0), text, font=f, stroke_width=1)
    draw.text(((512 - (box[2] - box[0])) // 2, y), text, font=f, fill=fill, stroke_width=1, stroke_fill="#ffffff")


def sticker(kind: str, title: str, accent: str, caption: str) -> None:
    im = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # A die-cut badge with a generous white edge for Telegram's sticker viewer.
    d.rounded_rectangle((18, 18, 494, 494), radius=130, fill="white")
    d.rounded_rectangle((31, 31, 481, 481), radius=116, fill="#fff7fb")
    d.ellipse((75, 62, 437, 424), fill="#ffe5f0", outline=accent, width=8)

    # Simple cartoon Nastya portrait: dark hair, face, glasses and a teacher's collar.
    d.ellipse((150, 105, 362, 328), fill="#382637", outline="white", width=10)
    d.ellipse((169, 132, 343, 315), fill="#ffd8bd", outline="#ffffff", width=8)
    d.pieslice((163, 103, 351, 238), 180, 360, fill="#382637")
    d.polygon([(174, 186), (185, 125), (218, 148), (205, 228)], fill="#382637")
    d.polygon([(336, 183), (326, 126), (293, 150), (308, 230)], fill="#382637")
    for x in (213, 286):
        d.ellipse((x - 22, 194, x + 22, 226), outline="#613d54", width=7)
        d.ellipse((x - 5, 203, x + 5, 216), fill="#402c38")
    d.line((235, 209, 264, 209), fill="#613d54", width=6)
    d.arc((236, 236, 276, 270), 10, 165, fill="#a83c68", width=6)
    d.ellipse((188, 232, 213, 247), fill="#f29aa7")
    d.ellipse((297, 232, 322, 247), fill="#f29aa7")

    d.polygon([(157, 350), (208, 300), (256, 333), (304, 300), (355, 350), (386, 431), (126, 431)],
              fill="#6e4a83", outline="white")
    d.line((207, 310, 256, 356, 305, 310), fill="white", width=8)

    if kind == "physics":
        d.rounded_rectangle((87, 83, 425, 154), radius=18, fill="#344766", outline="white", width=7)
        center_text(d, "E = mc²", 96, font(37, True), "white")
        d.ellipse((374, 149, 410, 185), fill="#ffcd5b")
        center_text(d, "ФИЗИКА — ЭТО ИСКРА", 431, font(25, True), "#80365f")
    else:
        d.rounded_rectangle((82, 87, 430, 163), radius=18, fill="#263448", outline="white", width=7)
        d.ellipse((101, 105, 119, 123), fill="#ff718b")
        d.ellipse((130, 105, 148, 123), fill="#ffcd5b")
        d.ellipse((159, 105, 177, 123), fill="#6dd6ad")
        d.text((112, 127), "</> IT", font=font(26, True), fill="#b9f5e4")
        center_text(d, "БАГ? ПОПРАВИМ", 431, font(27, True), "#80365f")

    im.save(OUT / f"nastya_{kind}.webp", "WEBP", lossless=True, method=6)


sticker("physics", "", "#5979ae", "")
sticker("it", "", "#5ab99b", "")
