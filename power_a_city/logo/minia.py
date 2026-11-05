"""Ajoute le logo sur la miniature du joueur. python3 minia.py <minia> <logo_1440x608.png> <dossier>"""
import sys, os
from PIL import Image, ImageFilter, ImageEnhance
src, logo_f, out = sys.argv[1:4]
m = Image.open(src).convert("RGB")
logo = Image.open(logo_f).convert("RGBA")

def couvrir(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))

def poser_logo(fond, largeur, cx, cy):
    lg = logo.resize((largeur, round(largeur * logo.height / logo.width)), Image.LANCZOS)
    fond.paste(lg, (cx - lg.width // 2, cy - lg.height // 2), lg)

# paysage 1920 x 1080
pay = couvrir(m, 1920, 1080)
pay.save(os.path.join(out, "minia_paysage_1920x1080_sans_texte.png"))
p2 = pay.copy(); poser_logo(p2, 900, 1430, 230)
p2.save(os.path.join(out, "minia_paysage_1920x1080_avec_texte.png"))

# portrait 1440 x 1920 : fond flou + image entiere au milieu
fond = couvrir(m, 1440, 1920).filter(ImageFilter.GaussianBlur(28))
fond = ImageEnhance.Brightness(fond).enhance(0.85)
img = m.resize((1440, round(1440 * m.height / m.width)), Image.LANCZOS)
y = 1920 - img.height - 260
fond.paste(img, (0, y))
fond.save(os.path.join(out, "minia_portrait_1440x1920_sans_texte.png"))
f2 = fond.copy(); poser_logo(f2, 1320, 720, y // 2 + 20)
f2.save(os.path.join(out, "minia_portrait_1440x1920_avec_texte.png"))
