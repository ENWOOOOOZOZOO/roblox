"""Enleve le logo en haut du portrait et le remplace par du ciel (meme cadrage).
python3 enlever_logo.py <entree> <sortie>"""
import sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

im = Image.open(sys.argv[1]).convert("RGB").resize((1440, 1920), Image.LANCZOS)
a = np.asarray(im).astype(float)
W, H = 1440, 1920

def moyenne(x0, x1, y0, y1):
    return a[y0:y1, x0:x1].reshape(-1, 3).mean(0)

haut = (moyenne(0, 30, 0, 20) + moyenne(1410, 1440, 0, 20)) / 2         # bleu du haut
bas = moyenne(760, 980, 450, 480)                                         # bleu juste sous le logo
y = np.arange(H)[:, None, None]
t = np.clip(y / 460.0, 0, 1)
ciel = haut * (1 - t) + bas * t
ciel = np.repeat(ciel, W, axis=1)
# raccord : en bas, chaque colonne prend la couleur du ciel juste sous le logo
ligne = a[466:474].mean(0)                                                 # (W, 3)
bleu = (ligne[:, 2] > ligne[:, 0] + 40) & (ligne[:, 2] > 150)              # vrai ciel (pas le perso, pas les billets)
xs = np.arange(W)
ligne = np.stack([np.interp(xs, xs[bleu], ligne[bleu, c]) for c in range(3)], 1)
ligne = np.asarray(Image.fromarray(ligne[None].astype(np.uint8)).resize((W, 1)).filter(ImageFilter.GaussianBlur(25))).astype(float)[0]
mix = np.clip((y - 260) / 200.0, 0, 1)                                    # de 250 a 450 : on rejoint la ligne
ciel = ciel * (1 - mix) + ligne[None, :, :] * mix
# halo clair au centre, comme le soleil derriere le personnage
xx, yy = np.meshgrid(np.arange(W), np.arange(H))
halo = np.exp(-(((xx - 760) / 520) ** 2 + ((yy - 520) / 380) ** 2))[..., None]
ciel = ciel + (np.array([235, 250, 255]) - ciel) * 0.35 * halo * (1 - mix)
fond = Image.fromarray(np.clip(ciel, 0, 255).astype(np.uint8))

# rayons de soleil qui partent du centre (comme dans l'image)
rayons = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(rayons)
cx, cy = 760, 640
for k in range(-7, 8):
    ang = -math.pi / 2 + k * 0.17
    a1, a2 = ang - 0.035, ang + 0.035
    d.polygon([(cx, cy), (cx + 1600 * math.cos(a1), cy + 1600 * math.sin(a1)),
               (cx + 1600 * math.cos(a2), cy + 1600 * math.sin(a2))], fill=40)
rayons = rayons.filter(ImageFilter.GaussianBlur(14))
rayons = Image.fromarray((np.asarray(rayons) * np.clip((440 - np.arange(H)) / 120.0, 0, 1)[:, None]).astype(np.uint8))
fond = Image.composite(Image.new("RGB", (W, H), (240, 252, 255)), fond, rayons)

# petits nuages blancs sur les cotes et etincelles
nuages = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(nuages)
for cxn, cyn, s in ((60, 300, 1.0), (1390, 260, 1.1), (210, 90, 0.7), (1230, 70, 0.6)):
    for dx, dy, r in ((0, 0, 70), (70, 15, 55), (-65, 20, 50), (30, -35, 50), (-20, 30, 60)):
        d.ellipse((cxn + dx * s - r * s, cyn + dy * s - r * s, cxn + dx * s + r * s, cyn + dy * s + r * s), fill=230)
nuages = nuages.filter(ImageFilter.GaussianBlur(6))
fond = Image.composite(Image.new("RGB", (W, H), (245, 250, 255)), fond, nuages)
d = ImageDraw.Draw(fond)
random.seed(4)
for _ in range(14):
    x, yv, r = random.randint(60, 1380), random.randint(30, 400), random.randint(8, 16)
    d.polygon([(x, yv - r), (x + r * 0.25, yv - r * 0.25), (x + r, yv), (x + r * 0.25, yv + r * 0.25),
               (x, yv + r), (x - r * 0.25, yv + r * 0.25), (x - r, yv), (x - r * 0.25, yv - r * 0.25)], fill=(255, 255, 255))

# zone du logo a remplacer, avec un fondu doux sur le bord du bas
masque = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(masque)
d.rectangle((0, 0, W, 450), fill=255)        # logo + son ombre
d.rectangle((0, 0, 360, 462), fill=255)       # bas des immeubles a gauche
d.rectangle((1150, 0, W, 462), fill=255)      # bas des immeubles a droite
d.rectangle((385, 442, 650, H), fill=0)       # on ne touche pas au noeud sur la tete
masque = masque.filter(ImageFilter.GaussianBlur(5))
Image.composite(fond, im, masque).save(sys.argv[2])
