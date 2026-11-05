"""Logo de Power City Tycoon (style cartoon, facon Roblox). python3 logo.py <police.ttf> <sortie.png>"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

POLICE, SORTIE = sys.argv[1], sys.argv[2]
L, H = 1600, 1100
NAVY = (22, 30, 70)
img = Image.new("RGBA", (L, H), (0, 0, 0, 0))


def degrade(taille, haut, bas):
    g = Image.new("RGBA", taille)
    d = ImageDraw.Draw(g)
    for y in range(taille[1]):
        t = y / max(1, taille[1] - 1)
        d.line([(0, y), (taille[0], y)], fill=tuple(int(haut[i] + (bas[i] - haut[i]) * t) for i in range(3)) + (255,))
    return g


def texte(txt, cx, cy, taille, haut, bas, rot=0):
    f = ImageFont.truetype(POLICE, taille)
    calque = Image.new("RGBA", (L, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    box = d.textbbox((0, 0), txt, font=f)
    x, y = cx - (box[2] - box[0]) / 2 - box[0], cy - (box[3] - box[1]) / 2 - box[1]
    d.text((x + 10, y + 16), txt, font=f, fill=NAVY, stroke_width=26, stroke_fill=NAVY)       # ombre
    d.text((x, y), txt, font=f, fill=NAVY, stroke_width=26, stroke_fill=NAVY)                # contour fonce
    d.text((x, y), txt, font=f, fill=(255, 255, 255), stroke_width=11, stroke_fill=(255, 255, 255))  # liseré blanc
    masque = Image.new("L", (L, H), 0)
    ImageDraw.Draw(masque).text((x, y), txt, font=f, fill=255)
    bb = masque.getbbox()
    g = degrade((bb[2] - bb[0], bb[3] - bb[1]), haut, bas)
    calque.paste(g, (bb[0], bb[1]), masque.crop(bb))
    # reflet brillant sur le haut des lettres
    reflet = Image.new("L", (L, H), 0)
    ImageDraw.Draw(reflet).rectangle((0, bb[1], L, bb[1] + (bb[3] - bb[1]) * 0.32), fill=90)
    blanc = Image.new("RGBA", (L, H), (255, 255, 255, 255))
    m2 = Image.composite(reflet, Image.new("L", (L, H), 0), masque)
    calque = Image.composite(blanc, calque, m2.point(lambda v: v))
    if rot:
        calque = calque.rotate(rot, resample=Image.BICUBIC, center=(cx, cy))
    img.alpha_composite(calque)


def eclair(cx, cy, s, rot=0):
    pts = [(0.15, -1.0), (0.75, -1.0), (0.35, -0.15), (0.8, -0.15), (-0.2, 1.1), (0.05, 0.15), (-0.4, 0.15)]
    calque = Image.new("RGBA", (L, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    p = [(cx + x * s, cy + y * s) for x, y in pts]
    d.polygon([(x + 6, y + 9) for x, y in p], fill=NAVY)
    d.line(p + [p[0]], fill=NAVY, width=int(s * 0.28), joint="curve")
    d.polygon(p, fill=(255, 214, 30))
    d.polygon([(cx + x * s, cy + y * s) for x, y in [(0.2, -0.95), (0.62, -0.95), (0.35, -0.4), (0.12, -0.4)]], fill=(255, 245, 170))
    if rot:
        calque = calque.rotate(rot, resample=Image.BICUBIC, center=(cx, cy))
    img.alpha_composite(calque)


def immeuble(cx, base, w, h, corps, fenetre, rot):
    """Immeuble cartoon avec un visage (yeux + sourire) et une antenne a lumiere rouge."""
    calque = Image.new("RGBA", (L, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    x0, y0, x1, y1 = cx - w / 2, base - h, cx + w / 2, base
    d.line([(cx + w * 0.2, y0), (cx + w * 0.2, y0 - 60)], fill=NAVY, width=14)
    d.ellipse((cx + w * 0.2 - 17, y0 - 82, cx + w * 0.2 + 17, y0 - 48), fill=(240, 40, 40), outline=NAVY, width=7)
    d.rounded_rectangle((x0 + 8, y0 + 12, x1 + 8, y1 + 12), 26, fill=NAVY)
    d.rounded_rectangle((x0, y0, x1, y1), 26, fill=corps, outline=NAVY, width=12)
    d.rounded_rectangle((x0 + 10, y0 + 10, x0 + w * 0.28, y1 - 10), 18, fill=tuple(min(255, c + 35) for c in corps))
    cols, rangs = 3, int(h / 70)
    fw, fh = w * 0.17, 34
    for r in range(rangs):
        for c in range(cols):
            fx = x0 + w * 0.18 + c * w * 0.26
            fy = y0 + 30 + r * 66
            if fy + fh > y1 - 150 and r > 1:
                continue
            d.rounded_rectangle((fx, fy, fx + fw, fy + fh), 7, fill=fenetre, outline=NAVY, width=5)
    # visage
    ey = y1 - 120
    for ex in (cx - w * 0.2, cx + w * 0.2):
        d.ellipse((ex - 26, ey - 30, ex + 26, ey + 30), fill=(255, 255, 255), outline=NAVY, width=7)
        d.ellipse((ex - 11, ey - 8, ex + 13, ey + 20), fill=NAVY)
    d.arc((cx - 46, y1 - 105, cx + 46, y1 - 40), 15, 165, fill=NAVY, width=10)
    calque = calque.rotate(rot, resample=Image.BICUBIC, center=(cx, base))
    img.alpha_composite(calque)


immeuble(185, 1000, 230, 520, (88, 120, 235), (255, 236, 120), 8)
immeuble(1415, 1000, 230, 480, (90, 200, 90), (255, 200, 90), -8)
texte("POWER", 800, 230, 280, (255, 226, 60), (255, 140, 0), rot=2)
texte("CITY", 800, 520, 300, (255, 255, 255), (190, 205, 230), rot=-1)
texte("TYCOON!", 800, 820, 260, (140, 235, 255), (20, 140, 240), rot=-2)
eclair(395, 140, 95, rot=-12)
eclair(1215, 125, 85, rot=14)
img.save(SORTIE)



def miniature(LF, HF, logo_l, chemin):
    """Fond ciel + herbe a studs, logo au centre."""
    fond = Image.new("RGBA", (LF, HF))
    d = ImageDraw.Draw(fond)
    sol = int(HF * 0.82)
    for y in range(HF):
        t = y / (HF - 1)
        d.line([(0, y), (LF, y)], fill=(int(70 + 90 * t), int(170 + 60 * t), 255, 255))
    d.rectangle((0, sol, LF, HF), fill=(80, 210, 40, 255))
    for gx in range(0, LF, 60):
        for gy in range(sol + 10, HF, 60):
            d.rounded_rectangle((gx + 14, gy + 14, gx + 46, gy + 46), 9, outline=(60, 180, 30, 255), width=4)
    logo = img.resize((logo_l, int(logo_l * H / L)))
    x = (LF - logo.width) // 2
    y = max(20, sol - logo.height + 40) if LF > HF else (sol - logo.height) // 2 + 60   # portrait : logo au milieu du ciel
    halo = Image.new("RGBA", (LF, HF), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse((x + logo.width * 0.15, y, x + logo.width * 0.85, y + logo.height), fill=(255, 250, 200, 150))
    fond.alpha_composite(halo.filter(ImageFilter.GaussianBlur(90)))
    fond.alpha_composite(logo, (x, y))
    fond.convert("RGB").save(chemin)


miniature(1920, 1080, 1360, SORTIE.replace(".png", "_miniature_1920x1080.png"))
miniature(1080, 1920, 1040, SORTIE.replace(".png", "_portrait_1080x1920.png"))
