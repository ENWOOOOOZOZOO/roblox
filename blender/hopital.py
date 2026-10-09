"""Hopital psychiatrique abandonne (map d'horreur pour Fortnite / UEFN), genere dans Blender.

Utilisation : Blender > onglet "Scripting" > Open (ce fichier) > Run Script.
Sortie : dossier "horreur" de ton dossier utilisateur -> hopital.fbx (+ hopital.glb)
         + les textures (couleur + normal map) en .png, aussi incluses dans le fichier.

Le batiment fait 64 x 40 m (un etage, 4 m sous plafond). Tout est place par rapport au point (0, 0, 0) :
dans UEFN, importe hopital.fbx, glisse les 4 meshes dans la map et mets-les tous a la position 0, 0, 0.
  Murs_Sols      : murs, sols, portes et fenetres (encadrements)
  Plafonds_Toit  : plafonds + toit (tu peux le cacher pour travailler dedans)
  Mobilier       : lits, brancards, fauteuils roulants, morgue, bloc, neons...
  Ecritures      : panneaux, sang, ecritures sur les murs
Collisions : ouvre chaque mesh > Collision Complexity = "Use Complex Collision As Simple".

Pieces : hall d'accueil, dortoir, infirmerie, reserve, refectoire, morgue, cellule capitonnee, salle de
contention, 9 chambres-cellules, salle commune, bureau du directeur, archives, douches, bloc operatoire.
"""
import bpy
import bmesh
import math
import os
import random
import numpy as np
from mathutils import Vector, Matrix

SORTIE = os.path.join(os.path.expanduser("~"), "horreur")
L_BAT, P_BAT = 64.0, 40.0     # taille du batiment (x, y) en metres
H = 4.0                       # hauteur sous plafond
EP = 0.25                     # epaisseur des murs
CASE = 0.25                   # precision du plan
TEX = 1024                    # taille des textures

# ---------------------------------------------------------------------------
#  LE PLAN
# ---------------------------------------------------------------------------
PIECES = {
    "Couloir": [(0, 16, 64, 20), (10, 20, 14, 40), (50, 20, 54, 40)],
    "Dortoir": [(0, 0, 20, 16)],
    "Reserve": [(20, 0, 26, 7)],
    "Infirmerie": [(20, 7, 26, 16)],
    "Hall": [(26, 0, 38, 16)],
    "Refectoire": [(38, 0, 52, 16)],
    "Morgue": [(52, 0, 64, 8)],
    "Capitonnee": [(52, 8, 58, 16)],
    "Contention": [(58, 8, 64, 16)],
    "Bureau": [(0, 20, 10, 30)],
    "Archives": [(0, 30, 10, 40)],
    "Commune": [(14, 26, 50, 40)],
    "Douches": [(54, 20, 64, 30)],
    "Bloc": [(54, 30, 64, 40)],
}
for k in range(9):
    PIECES[f"Chambre{k + 1}"] = [(14 + 4 * k, 20, 18 + 4 * k, 26)]

MUR_DE = {"Capitonnee": "Capitonne", "Douches": "Faience", "Morgue": "Faience", "Bloc": "Faience"}
SOL_DE = {"Reserve": "SolBeton", "Archives": "SolBeton", "Capitonnee": "Capitonne", "Contention": "SolBeton",
          "Douches": "SolFaience", "Morgue": "SolFaience", "Bloc": "SolFaience"}
for k in range(9):
    SOL_DE[f"Chambre{k + 1}"] = "SolBeton"

# portes : (mur le long de x ou y, coordonnee du mur, centre, largeur, hauteur, type, panneau)
PORTES = [
    ("x", 0, 32, 2.6, 2.7, "double", None),
    ("x", 16, 32, 6.0, 3.2, "arche", "RECEPTION"),
    ("x", 16, 10, 2.2, 2.6, "double", "DORMITORY"),
    ("x", 16, 23, 1.2, 2.5, "bois", "INFIRMARY"),
    ("x", 7, 23, 1.2, 2.5, "bois", "STORAGE"),
    ("x", 16, 45, 2.2, 2.6, "double", "CAFETERIA"),
    ("x", 16, 55, 1.2, 2.5, "metal", "ISOLATION"),
    ("x", 16, 61, 1.2, 2.5, "metal", "RESTRAINT ROOM"),
    ("x", 8, 61, 1.4, 2.5, "metal", "MORGUE"),
    ("x", 20, 5, 1.2, 2.5, "bois", "DIRECTOR"),
    ("x", 30, 5, 1.2, 2.5, "bois", "ARCHIVES"),
    ("y", 14, 33, 2.2, 2.6, "double", "DAY ROOM"),
    ("y", 50, 33, 2.2, 2.6, "double", None),
    ("y", 54, 25, 1.2, 2.5, "bois", "SHOWERS"),
    ("y", 54, 35, 2.2, 2.6, "double", "OPERATING ROOM"),
    ("x", 40, 12, 1.4, 2.5, "condamnee", "EXIT"),
    ("x", 40, 52, 1.4, 2.5, "condamnee", None),
] + [("x", 20, 16 + 4 * k, 1.1, 2.4, "metal", f"ROOM {k + 1}") for k in range(9)]
SANS_FENETRE = {"Capitonnee", "Morgue", "Hall"}
TROU = (38.4, 16.4, 41.0, 18.9)          # plafond effondre dans le couloir (screamer)


def plan():
    nx, ny = int(L_BAT / CASE), int(P_BAT / CASE)
    G = np.zeros((nx, ny), dtype=int)
    noms = ["Dehors"]
    for nom, rects in PIECES.items():
        noms.append(nom)
        for x0, y0, x1, y1 in rects:
            G[int(x0 / CASE):int(x1 / CASE), int(y0 / CASE):int(y1 / CASE)] = len(noms) - 1
    return G, noms


G_PLAN, NOMS = plan()


def piece_en(x, y):
    i, j = int(math.floor(x / CASE)), int(math.floor(y / CASE))
    if 0 <= i < G_PLAN.shape[0] and 0 <= j < G_PLAN.shape[1]:
        return NOMS[G_PLAN[i, j]]
    return "Dehors"


# ---------------------------------------------------------------------------
#  TEXTURES (fabriquees en numpy, elles se repetent sans couture)
# ---------------------------------------------------------------------------
def grille():
    v, u = np.mgrid[0:TEX, 0:TEX] / TEX
    return u, v


def fbm(graine, beta=1.8, fmin=1, fmax=None, ax=1.0, ay=1.0):
    """Bruit fractal qui se repete (fabrique par FFT) : moyenne 0, ecart-type 1."""
    rng = np.random.default_rng(graine)
    F = np.fft.fft2(rng.normal(size=(TEX, TEX)))
    k = np.fft.fftfreq(TEX) * TEX
    KX, KY = np.meshgrid(k, k)
    kk = np.hypot(KX * ax, KY * ay)
    kk[0, 0] = 1
    filtre = kk ** (-beta)
    filtre[(kk < fmin)] = 0
    if fmax:
        filtre[kk > fmax] = 0
    filtre[0, 0] = 0
    n = np.real(np.fft.ifft2(F * filtre))
    return (n - n.mean()) / (n.std() + 1e-9)


def lisse(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def mix(col, c, a):
    a = np.clip(a, 0, 1)[..., None]
    return col * (1 - a) + np.array(c) * a


def normale_depuis(h, force):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * force
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * force
    n = np.stack([-dx, -dy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def tex_mur():
    """Peinture verte d'asile qui s'ecaille, soubassement plus fonce, coulures, moisissure, fissures.
    v = hauteur sur le mur (0 = sol, 1 = plafond)."""
    u, v = grille()
    col = np.where((v < 0.3)[..., None], np.array([0.30, 0.42, 0.36]), np.array([0.62, 0.69, 0.60]))
    col = col * (1 + 0.06 * fbm(3, 1.2, fmin=10))[..., None]
    col = np.where((np.abs(v - 0.3) < 0.004)[..., None], np.array([0.18, 0.24, 0.2]), col)
    col = np.where((v < 0.025)[..., None], np.array([0.17, 0.17, 0.16]), col)
    pe = fbm(1, 1.9) + 0.5 * fbm(2, 1.5, fmin=6)
    pele = lisse(1.05, 1.2, pe)
    bord = lisse(0.88, 1.05, pe) * (1 - pele)
    col = mix(col, (0.57, 0.54, 0.49), pele)
    col *= (1 - 0.3 * bord)[..., None]
    col = mix(col, (0.40, 0.33, 0.22), lisse(0.6, 1.6, fbm(4, 1.6, ay=6)) * lisse(0.15, 0.95, v) * 0.5)
    col = mix(col, (0.10, 0.12, 0.09), lisse(0.3, 0.0, v) * (0.6 + 0.4 * lisse(-1, 1, fbm(5, 1.5))) * 0.6)
    col = mix(col, (0.05, 0.08, 0.05), lisse(1.4, 2.2, fbm(6, 1.3, fmin=5)) * lisse(0.5, 0.1, v) * 0.8)
    fente = lisse(0.06, 0.0, np.abs(fbm(7, 1.6, fmin=3))) * lisse(0.5, 1.5, fbm(8, 1.2))
    col = mix(col, (0.12, 0.12, 0.11), fente * 0.8)
    col *= (0.85 + 0.15 * lisse(-2, 2, fbm(9, 1.0)))[..., None]
    h = 0.4 * (1 - pele) + 0.5 * bord - 0.6 * fente + 0.05 * fbm(10, 1.0, fmin=60)
    return col, h, 6.0


def tex_sol():
    """Carrelage en damier (8 x 8 carreaux de 30 cm), sale, fissure, avec des carreaux manquants."""
    u, v = grille()
    i, j = np.floor(u * 8).astype(int), np.floor(v * 8).astype(int)
    fu, fv = u * 8 - i, v * 8 - j
    rng = np.random.default_rng(21)
    teinte, manque = rng.normal(0, 0.05, (8, 8)), rng.random((8, 8)) < 0.06
    col = np.where((((i + j) % 2) == 0)[..., None], np.array([0.80, 0.77, 0.68]), np.array([0.16, 0.22, 0.19]))
    col = col * (1 + teinte[j, i])[..., None]
    bordc = np.minimum(np.minimum(fu, 1 - fu), np.minimum(fv, 1 - fv))
    joint = bordc < 0.025
    col = np.where(joint[..., None], np.array([0.25, 0.24, 0.22]), col)
    m = manque[j, i]
    col = np.where(m[..., None], (np.array([0.42, 0.41, 0.39]) * (1 + 0.15 * fbm(22, 1.4, fmin=20))[..., None]), col)
    fente = lisse(0.05, 0.0, np.abs(fbm(23, 1.5, fmin=3))) * lisse(0.3, 1.2, fbm(24, 1.2))
    col = mix(col, (0.1, 0.1, 0.09), fente * 0.8)
    col *= (0.7 + 0.32 * lisse(-1.5, 1.5, fbm(25, 2.0)))[..., None]
    col = mix(col, (0.30, 0.22, 0.12), lisse(1.2, 2.0, fbm(26, 1.6, fmin=3)) * 0.5)
    h = np.where(joint, -0.5, 0.3 * np.clip(bordc / 0.06, 0, 1))
    h = np.where(m, -0.6 + 0.1 * fbm(27, 1.0, fmin=40), h) - 0.4 * fente
    return col, h, 5.0


def tex_plafond():
    """Dalles de faux plafond (60 cm) perforees, auréoles d'eau, dalles tombees (trous noirs)."""
    u, v = grille()
    i, j = np.floor(u * 4).astype(int), np.floor(v * 4).astype(int)
    fu, fv = u * 4 - i, v * 4 - j
    rng = np.random.default_rng(31)
    manque = rng.random((4, 4)) < 0.1
    col = np.tile(np.array([0.78, 0.76, 0.70]), (TEX, TEX, 1)) * (1 + 0.05 * fbm(32, 1.5, fmin=8))[..., None]
    trou = (((fu * 40) % 1 - 0.5) ** 2 + ((fv * 40) % 1 - 0.5) ** 2) < 0.04
    col = np.where(trou[..., None], col * 0.8, col)
    for _ in range(5):
        cu, cv, r = rng.random(), rng.random(), rng.uniform(0.05, 0.15)
        d = np.hypot((u - cu + 0.5) % 1 - 0.5, (v - cv + 0.5) % 1 - 0.5) / r
        col = mix(col, (0.55, 0.45, 0.28), lisse(1.0, 0.7, d) * 0.35 + lisse(0.08, 0.0, np.abs(d - 1)) * 0.6)
    bordc = np.minimum(np.minimum(fu, 1 - fu), np.minimum(fv, 1 - fv))
    cadre = bordc < 0.02
    col = np.where(cadre[..., None], np.array([0.5, 0.5, 0.48]), col)
    m = manque[j, i] & ~cadre
    col = np.where(m[..., None], np.array([0.02, 0.02, 0.02]), col)
    h = np.where(cadre, 0.5, 0.0) - 0.2 * trou + np.where(m, -1.0, 0.0)
    return col, h, 4.0


def tex_capitonne():
    """Mur capitonne en losanges (cellule d'isolement), sale et tache."""
    u, v = grille()
    s, t = u * 6 + v * 8, u * 6 - v * 8
    coussin = np.abs(np.sin(np.pi * s) * np.sin(np.pi * t)) ** 0.6
    bouton = lisse(0.8, 0.97, (np.cos(np.pi * s) * np.cos(np.pi * t)) ** 2)
    h = coussin - 0.7 * bouton
    col = np.array([0.74, 0.70, 0.60]) * (0.62 + 0.38 * coussin)[..., None]
    col = mix(col, (0.55, 0.45, 0.25), lisse(0.8, 1.8, fbm(41, 1.6)) * 0.55)
    col = mix(col, (0.30, 0.04, 0.05), lisse(1.6, 2.4, fbm(42, 1.5, fmin=3)) * 0.6)
    col = mix(col, (0.2, 0.18, 0.14), lisse(0.25, 0.0, v) * 0.5)
    col = np.where((bouton > 0.5)[..., None], col * 0.6, col)
    return col, h, 8.0


def tex_faience():
    """Faience blanche (carreaux de 10 cm) des douches / morgue / bloc : joints noirs, rouille, crasse."""
    u, v = grille()
    i, j = np.floor(u * 30).astype(int), np.floor(v * 40).astype(int)
    fu, fv = u * 30 - i, v * 40 - j
    rng = np.random.default_rng(51)
    casse = rng.random((30, 40)) < 0.03
    col = np.tile(np.array([0.84, 0.85, 0.83]), (TEX, TEX, 1)) * (1 + rng.normal(0, 0.03, (30, 40))[i, j])[..., None]
    bordc = np.minimum(np.minimum(fu, 1 - fu), np.minimum(fv, 1 - fv))
    joint = bordc < 0.06
    col = np.where(joint[..., None], np.array([0.30, 0.29, 0.27]), col)
    col = np.where(casse[i, j][..., None], np.array([0.45, 0.44, 0.42]), col)
    col = mix(col, (0.45, 0.25, 0.12), lisse(0.8, 1.8, fbm(52, 1.6, ay=8)) * lisse(0.3, 0.9, v) * 0.6)
    col = mix(col, (0.25, 0.22, 0.16), lisse(0.35, 0.0, v) * (0.5 + 0.5 * lisse(-1, 1, fbm(53, 1.5))) * 0.7)
    col *= (0.82 + 0.18 * lisse(-2, 2, fbm(54, 1.2)))[..., None]
    h = np.where(joint, -0.5, 0.3 * np.clip(bordc / 0.15, 0, 1)) - 0.5 * casse[i, j]
    return col, h, 5.0


def tex_facade():
    u, v = grille()
    col = np.array([0.55, 0.54, 0.50]) * (1 + 0.08 * fbm(61, 1.3, fmin=20) + 0.06 * fbm(62, 2.0))[..., None]
    col = mix(col, (0.30, 0.28, 0.24), lisse(0.5, 1.6, fbm(63, 1.6, ay=7)) * lisse(0.2, 1.0, v) * 0.5)
    col = mix(col, (0.18, 0.24, 0.12), lisse(0.2, 0.0, v) * (0.5 + 0.5 * lisse(-1, 1, fbm(64, 1.5))) * 0.7)
    fente = lisse(0.05, 0.0, np.abs(fbm(65, 1.6, fmin=3))) * lisse(0.6, 1.4, fbm(66, 1.2))
    col = mix(col, (0.15, 0.15, 0.14), fente * 0.8)
    h = 0.08 * fbm(67, 1.2, fmin=30) - 0.6 * fente
    return col, h, 5.0


def tex_beton():
    u, v = grille()
    col = np.array([0.44, 0.43, 0.41]) * (1 + 0.1 * fbm(71, 1.4, fmin=10) + 0.08 * fbm(72, 2.0))[..., None]
    col = mix(col, (0.22, 0.2, 0.17), lisse(0.8, 1.8, fbm(73, 1.7, fmin=2)) * 0.6)
    fente = lisse(0.05, 0.0, np.abs(fbm(74, 1.6, fmin=3))) * lisse(0.5, 1.4, fbm(75, 1.2))
    col = mix(col, (0.12, 0.12, 0.11), fente * 0.8)
    h = 0.1 * fbm(76, 1.2, fmin=30) - 0.6 * fente
    return col, h, 4.0


def tex_sol_faience():
    u, v = grille()
    i, j = np.floor(u * 24).astype(int), np.floor(v * 24).astype(int)
    fu, fv = u * 24 - i, v * 24 - j
    rng = np.random.default_rng(81)
    col = np.tile(np.array([0.70, 0.71, 0.70]), (TEX, TEX, 1)) * (1 + rng.normal(0, 0.04, (24, 24))[i, j])[..., None]
    bordc = np.minimum(np.minimum(fu, 1 - fu), np.minimum(fv, 1 - fv))
    joint = bordc < 0.05
    col = np.where(joint[..., None], np.array([0.22, 0.21, 0.2]), col)
    col *= (0.65 + 0.35 * lisse(-1.5, 1.5, fbm(82, 2.0)))[..., None]
    col = mix(col, (0.32, 0.25, 0.15), lisse(1.0, 2.0, fbm(83, 1.6)) * 0.5)
    h = np.where(joint, -0.5, 0.2)
    return col, h, 5.0


def tex_metal():
    """Peinture blanche ecaillee sur de la rouille (lits, chaises roulantes, armoires...)."""
    u, v = grille()
    col = np.array([0.80, 0.80, 0.77]) * (1 + 0.04 * fbm(91, 1.2, fmin=20))[..., None]
    eclat = lisse(1.1, 1.3, fbm(92, 1.6, fmin=4))
    rouille = np.array([0.40, 0.21, 0.11]) * (0.8 + 0.4 * lisse(-2, 2, fbm(93, 1.4, fmin=10)))[..., None]
    col = col * (1 - eclat[..., None]) + rouille * eclat[..., None]
    col = mix(col, (0.45, 0.28, 0.15), lisse(0.8, 1.8, fbm(94, 1.6, ay=6)) * 0.4)
    col *= (0.8 + 0.2 * lisse(-2, 2, fbm(95, 1.5)))[..., None]
    return col, 0.4 * (1 - eclat) + 0.05 * fbm(96, 1.0, fmin=50), 4.0


def tex_bois():
    """Planches peintes (portes, bureaux) : la peinture part et montre le bois."""
    u, v = grille()
    planche = np.floor(u * 6)
    fu = u * 6 - planche
    grain = np.sin(v * 2 * np.pi * 40 + 4 * fbm(101, 1.5, fmin=2) + planche * 3)
    bois = np.array([0.42, 0.30, 0.18]) * (0.85 + 0.15 * grain)[..., None]
    peinture = np.array([0.30, 0.36, 0.32]) * (1 + 0.05 * fbm(102, 1.2, fmin=10))[..., None]
    eclat = lisse(0.9, 1.15, fbm(103, 1.6, fmin=3))
    col = peinture * (1 - eclat[..., None]) + bois * eclat[..., None]
    joint = (fu < 0.02) | (fu > 0.98)
    col = np.where(joint[..., None], col * 0.4, col)
    col *= (0.8 + 0.2 * lisse(-2, 2, fbm(104, 1.5)))[..., None]
    h = 0.25 * (1 - eclat) + 0.1 * grain * eclat - 0.6 * joint
    return col, h, 5.0


def tex_matelas():
    u, v = grille()
    raye = ((u * 24) % 1) < 0.35
    col = np.where(raye[..., None], np.array([0.45, 0.50, 0.58]), np.array([0.80, 0.78, 0.72]))
    tache = lisse(0.9, 1.6, fbm(111, 1.7, fmin=2))
    col = mix(col, (0.62, 0.52, 0.26), tache * 0.55)
    col = mix(col, (0.35, 0.22, 0.12), lisse(0.03, 0.0, np.abs(fbm(111, 1.7, fmin=2) - 0.9)) * 0.5)
    col = mix(col, (0.30, 0.05, 0.05), lisse(1.8, 2.4, fbm(112, 1.6, fmin=3)) * 0.7)
    capiton = lisse(0.9, 0.99, (np.cos(np.pi * u * 6) * np.cos(np.pi * v * 6)) ** 2)
    h = 0.15 * np.sin(u * 2 * np.pi * 200) * np.sin(v * 2 * np.pi * 200) - 0.6 * capiton
    return col, h, 4.0


def tex_inox():
    u, v = grille()
    col = np.array([0.60, 0.61, 0.62]) * (1 + 0.06 * fbm(121, 1.0, ax=0.05, ay=1.0))[..., None]
    col = mix(col, (0.35, 0.33, 0.30), lisse(0.9, 1.8, fbm(122, 1.6, fmin=2)) * 0.5)
    col = mix(col, (0.42, 0.22, 0.12), lisse(1.9, 2.5, fbm(123, 1.4, fmin=6)) * 0.7)
    return col, 0.05 * fbm(124, 1.0, ax=0.05, ay=1.0), 3.0


TEXTURES = {"Mur": tex_mur, "Sol": tex_sol, "Plafond": tex_plafond, "Capitonne": tex_capitonne,
            "Faience": tex_faience, "Facade": tex_facade, "SolBeton": tex_beton, "Toit": tex_beton,
            "SolFaience": tex_sol_faience, "Metal": tex_metal, "Bois": tex_bois, "Matelas": tex_matelas,
            "Inox": tex_inox}
COULEURS = {   # matieres sans texture : couleur (sRGB), rugosite
    "Cuir": ((0.24, 0.14, 0.08), 0.6), "Caoutchouc": ((0.04, 0.04, 0.04), 0.8),
    "Porcelaine": ((0.80, 0.80, 0.76), 0.25), "Carton": ((0.48, 0.38, 0.26), 0.9),
    "Papier": ((0.80, 0.78, 0.70), 0.9), "Verre": ((0.12, 0.14, 0.15), 0.05),
    "Plastique": ((0.75, 0.80, 0.76), 0.4), "Drap": ((0.78, 0.76, 0.70), 0.9),
    "Velours": ((0.32, 0.22, 0.20), 0.9), "EauSale": ((0.12, 0.10, 0.06), 0.05),
    "Encre": ((0.04, 0.04, 0.04), 0.6), "Plaque": ((0.78, 0.76, 0.68), 0.4),
    "Rouille": ((0.36, 0.18, 0.09), 0.7), "Sang": ((0.30, 0.02, 0.03), 0.2),
    "Rayure": ((0.70, 0.69, 0.64), 0.8), "Neon": ((0.90, 0.97, 0.92), 0.3),
    "Miroir": ((0.80, 0.80, 0.78), 0.03), "Rideau": ((0.55, 0.62, 0.55), 0.9),
}
ECHELLE_UV = {"Metal": 1.0, "Bois": 1.2, "Matelas": 1.0, "Inox": 1.0}
MATS = {}
TEXCACHE = {}


def donnees_texture(nom):
    if nom not in TEXCACHE:
        TEXCACHE[nom] = TEXTURES[nom]()
    return TEXCACHE[nom]


def lineaire(c):
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def enregistrer(nom, arr, donnees=False):
    hh, ww = arr.shape[:2]
    img = bpy.data.images.new(nom, ww, hh, alpha=False)
    if donnees:
        img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(np.concatenate([np.clip(arr, 0, 1), np.ones((hh, ww, 1))], -1).astype(np.float32).ravel())
    os.makedirs(SORTIE, exist_ok=True)
    img.filepath_raw = os.path.join(SORTIE, nom + ".png")
    img.file_format = 'PNG'
    img.save()
    img.pack()
    return img


def matiere(nom):
    if nom in MATS:
        return MATS[nom]
    m = bpy.data.materials.new(nom)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    if nom in TEXTURES:
        col, h, force = donnees_texture(nom)
        tc = nt.nodes.new("ShaderNodeTexImage")
        tc.image = enregistrer("hopital_" + nom.lower(), col)
        nt.links.new(tc.outputs["Color"], b.inputs["Base Color"])
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = enregistrer("hopital_" + nom.lower() + "_normal", normale_depuis(h, force), True)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
        b.inputs["Roughness"].default_value = 0.4 if nom in ("Faience", "SolFaience", "Inox") else 0.75
        m.diffuse_color = (*lineaire(col.reshape(-1, 3).mean(0)), 1)
    else:
        c, r = COULEURS[nom]
        b.inputs["Base Color"].default_value = (*lineaire(c), 1)
        b.inputs["Roughness"].default_value = r
        m.diffuse_color = (*lineaire(c), 1)
        if nom == "Miroir":
            b.inputs["Metallic"].default_value = 1.0
        if nom == "Neon":
            b.inputs["Emission Color"].default_value = (*lineaire(c), 1)
            b.inputs["Emission Strength"].default_value = 4.0
    MATS[nom] = m
    return m


# ---------------------------------------------------------------------------
#  OUTILS DE CONSTRUCTION
# ---------------------------------------------------------------------------
class Kit:
    """Accumule des boites / cylindres / taches dans un seul mesh, avec une matiere par piece."""

    def __init__(self, nom):
        self.nom = nom
        self.bm = bmesh.new()
        self.mats = []
        self.R = Matrix.Identity(4)
        self.uv_fixes = {}

    def m(self, nom):
        if nom not in self.mats:
            self.mats.append(nom)
        return self.mats.index(nom)

    def place(self, x=0.0, y=0.0, z=0.0, rz=0.0, rx=0.0, ry=0.0):
        self.R = (Matrix.Translation((x, y, z)) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Rotation(ry, 4, 'Y')
                  @ Matrix.Rotation(rx, 4, 'X'))

    def _peindre(self, verts, mat, lisse_=False):
        i = self.m(mat)
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index = i
            if lisse_ and len(f.verts) == 4:
                f.smooth = True

    def boite(self, c, t, mat, rz=0.0, rx=0.0, ry=0.0):
        M = (self.R @ Matrix.Translation(c) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Rotation(ry, 4, 'Y')
             @ Matrix.Rotation(rx, 4, 'X') @ Matrix.Diagonal((max(t[0], 1e-4), max(t[1], 1e-4), max(t[2], 1e-4), 1)))
        self._peindre(bmesh.ops.create_cube(self.bm, size=1.0, matrix=M)["verts"], mat)

    def cylindre(self, a, b, r, mat, n=10, r2=None):
        a, b = Vector(a), Vector(b)
        d = b - a
        if d.length < 1e-5:
            return
        M = self.R @ Matrix.Translation((a + b) / 2) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        res = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=n, radius1=r,
                                    radius2=r if r2 is None else r2, depth=d.length, matrix=M)
        self._peindre(res["verts"], mat, True)

    def tache(self, centre, normale, rayon, mat, graine, etire=1.0, sens=None, pics=0.35):
        """Tache plate irreguliere (sang, flaque...) posee sur une surface."""
        rng = random.Random(graine)
        n = Vector(normale).normalized()
        t1 = (Vector(sens) - n * Vector(sens).dot(n)).normalized() if sens else n.orthogonal().normalized()
        t2 = n.cross(t1)
        c = self.R @ (Vector(centre) + n * 0.004)
        pts = []
        k = 22
        phases = [rng.uniform(0, 6.28) for _ in range(3)]
        for i in range(k):
            a = 2 * math.pi * i / k
            r = rayon * (1 + 0.25 * math.sin(3 * a + phases[0]) + 0.15 * math.sin(5 * a + phases[1]))
            if rng.random() < pics:
                r *= rng.uniform(1.2, 1.8)
            pts.append(self.bm.verts.new(c + self.R.to_3x3() @ (t1 * math.cos(a) * r * etire + t2 * math.sin(a) * r)))
        f = self.bm.faces.new(pts)
        f.normal_update()
        if f.normal.dot(self.R.to_3x3() @ n) < 0:
            f.normal_flip()
        f.material_index = self.m(mat)

    def objet(self, collection=None):
        bm = self.bm
        bm.normal_update()
        uv = bm.loops.layers.uv.new("UV")
        for f in bm.faces:
            nom = self.mats[f.material_index] if self.mats else ""
            e = ECHELLE_UV.get(nom, 1.0)
            a = max(range(3), key=lambda k: abs(f.normal[k]))
            for l in f.loops:
                co = l.vert.co
                l[uv].uv = ((co.y, co.z) if a == 0 else (co.x, co.z) if a == 1 else (co.x, co.y))
                l[uv].uv = (l[uv].uv[0] / e, l[uv].uv[1] / e)
        me = bpy.data.meshes.new(self.nom)
        bm.to_mesh(me)
        bm.free()
        for nom in self.mats:
            me.materials.append(matiere(nom))
        o = bpy.data.objects.new(self.nom, me)
        bpy.context.scene.collection.objects.link(o)
        return o


# ---------------------------------------------------------------------------
#  LA STRUCTURE : murs (avec portes et fenetres), sols, plafonds, toit
# ---------------------------------------------------------------------------
class Structure:
    """Les murs/sols/plafonds ont des UV "monde" : la texture garde la meme taille partout."""

    def __init__(self, nom):
        self.nom = nom
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UV")
        self.mats = []

    def m(self, nom):
        if nom not in self.mats:
            self.mats.append(nom)
        return self.mats.index(nom)

    def quad(self, pts, mat, eu=2.4, ev=2.4, mode="sol"):
        f = self.bm.faces.new([self.bm.verts.new(p) for p in pts])
        f.material_index = self.m(mat)
        for l in f.loops:
            co = l.vert.co
            if mode == "sol":
                l[self.uv].uv = (co.x / eu, co.y / ev)
            elif mode == "x":
                l[self.uv].uv = (co.y / eu, co.z / ev)
            else:
                l[self.uv].uv = (co.x / eu, co.z / ev)
        return f

    def boite_mur(self, axe, c, a0, a1, z0, z1):
        """Un morceau de mur : axe 'x' = le mur suit x (a y = c)."""
        if a1 - a0 < 1e-4 or z1 - z0 < 1e-4:
            return
        e = EP / 2

        def P(a, d, z):
            return Vector((a, c + d, z)) if axe == "x" else Vector((c + d, a, z))

        cotes = []
        for d in (-1, 1):      # les deux grandes faces
            pts = [P(a0, d * e, z0), P(a1, d * e, z0), P(a1, d * e, z1), P(a0, d * e, z1)]
            if (d > 0) == (axe == "x"):
                pts = pts[::-1]
            milieu = (a0 + a1) / 2
            echant = P(milieu, d * (e + 0.3), (z0 + z1) / 2)
            piece = piece_en(echant.x, echant.y)
            mat = "Facade" if piece == "Dehors" else MUR_DE.get(piece, "Mur")
            self.quad(pts, mat, 3.0, H, mode=("x" if axe == "y" else "y"))
        # dessus, dessous et bouts (enduit)
        for pts in ([P(a0, -e, z1), P(a1, -e, z1), P(a1, e, z1), P(a0, e, z1)],
                    [P(a0, e, z0), P(a1, e, z0), P(a1, -e, z0), P(a0, -e, z0)]):
            self.quad(pts if axe == "x" else pts[::-1], "Facade", 3.0, 3.0, mode="sol")
        for a, sgn in ((a0, -1), (a1, 1)):
            pts = [P(a, -e, z0), P(a, e, z0), P(a, e, z1), P(a, -e, z1)]
            if (sgn > 0) == (axe == "y"):
                pts = pts[::-1]
            self.quad(pts, "Facade", 3.0, H, mode=("y" if axe == "y" else "x"))

    def objet(self):
        me = bpy.data.meshes.new(self.nom)
        self.bm.to_mesh(me)
        self.bm.free()
        for nom in self.mats:
            me.materials.append(matiere(nom))
        o = bpy.data.objects.new(self.nom, me)
        bpy.context.scene.collection.objects.link(o)
        return o


def segments_de_murs():
    """Repere sur le plan toutes les limites entre deux pieces (ou avec l'exterieur) -> murs."""
    G = G_PLAN
    nx, ny = G.shape
    murs = []
    for i in range(nx + 1):                     # murs le long de y (a x = i * CASE)
        j = 0
        while j < ny:
            g = G[i - 1, j] if i > 0 else 0
            d = G[i, j] if i < nx else 0
            if g != d:
                j0 = j
                while j < ny and ((G[i - 1, j] if i > 0 else 0) != (G[i, j] if i < nx else 0)):
                    j += 1
                murs.append(("y", i * CASE, j0 * CASE, j * CASE))
            else:
                j += 1
    for j in range(ny + 1):                     # murs le long de x (a y = j * CASE)
        i = 0
        while i < nx:
            g = G[i, j - 1] if j > 0 else 0
            d = G[i, j] if j < ny else 0
            if g != d:
                i0 = i
                while i < nx and ((G[i, j - 1] if j > 0 else 0) != (G[i, j] if j < ny else 0)):
                    i += 1
                murs.append(("x", j * CASE, i0 * CASE, i * CASE))
            else:
                i += 1
    return murs


def construire_structure(mob):
    st = Structure("Murs_Sols")
    murs = segments_de_murs()
    fenetres = []
    for axe, c, a0, a1 in murs:
        ouvertures = []
        for (pa, pc, centre, w, h, typ, _) in PORTES:
            if pa == axe and abs(pc - c) < 1e-6 and a0 < centre < a1:
                ouvertures.append((centre - w / 2, centre + w / 2, 0.0, h))
        # fenetres sur les murs exterieurs
        exterieur = abs(c) < 1e-6 or abs(c - (P_BAT if axe == "x" else L_BAT)) < 1e-6
        if exterieur:
            pos = 2.0
            while pos < (a1 - a0) - 1.0:
                x = a0 + pos
                dedans = Vector((x, c + (0.5 if c < 1 else -0.5), 1.5)) if axe == "x" else \
                    Vector((c + (0.5 if c < 1 else -0.5), x, 1.5))
                piece = piece_en(dedans.x, dedans.y)
                libre = all(not (o[0] - 1.0 < x < o[1] + 1.0) for o in ouvertures)
                coin = False
                for d in (-1.0, -0.6, 0.6, 1.0):          # pas trop pres d'un mur interieur
                    q = dedans + (Vector((d, 0, 0)) if axe == "x" else Vector((0, d, 0)))
                    if piece_en(q.x, q.y) != piece:
                        coin = True
                ecrit = axe == "x" and abs(c - P_BAT) < 1e-6 and 25 < x < 39     # mur de l'ecriture en sang
                if libre and not coin and not ecrit and piece not in SANS_FENETRE and piece != "Dehors":
                    ouvertures.append((x - 0.7, x + 0.7, 1.1, 2.9))
                    fenetres.append((axe, c, x, piece))
                pos += 4.0
        ouvertures.sort()
        a = a0 - EP / 2 * 0.999
        for o0, o1, z0, z1 in ouvertures:
            st.boite_mur(axe, c, a, o0, 0, H)
            st.boite_mur(axe, c, o0, o1, 0, z0)
            st.boite_mur(axe, c, o0, o1, z1, H)
            a = o1
        st.boite_mur(axe, c, a, a1 + EP / 2 * 0.999, 0, H)
    # sols
    for nom, rects in PIECES.items():
        for x0, y0, x1, y1 in rects:
            st.quad([Vector((x0, y0, 0)), Vector((x1, y0, 0)), Vector((x1, y1, 0)), Vector((x0, y1, 0))],
                    SOL_DE.get(nom, "Sol"))
    murs_sols = st.objet()
    # plafonds + toit
    pt = Structure("Plafonds_Toit")
    tx0, ty0, tx1, ty1 = TROU
    for nom, rects in PIECES.items():
        for x0, y0, x1, y1 in rects:
            morceaux = [(x0, y0, x1, y1)]
            if x0 < tx0 and x1 > tx1 and y0 <= ty0 and y1 >= ty1:      # plafond perce par l'eboulement
                morceaux = [(x0, y0, tx0, y1), (tx1, y0, x1, y1), (tx0, ty1, tx1, y1), (tx0, y0, tx1, ty0)]
            for a0, b0, a1, b1 in morceaux:
                pt.quad([Vector((a0, b0, H)), Vector((a0, b1, H)), Vector((a1, b1, H)), Vector((a1, b0, H))],
                        "Capitonne" if nom == "Capitonnee" else "Plafond")
    z = H + 0.3                                    # le dessous du toit et les bords du trou
    pt.quad([Vector((tx0, ty0, z)), Vector((tx0, ty1, z)), Vector((tx1, ty1, z)), Vector((tx1, ty0, z))], "Toit")
    for a, b in (((tx0, ty0), (tx1, ty0)), ((tx1, ty0), (tx1, ty1)), ((tx1, ty1), (tx0, ty1)), ((tx0, ty1), (tx0, ty0))):
        pt.quad([Vector((a[0], a[1], H)), Vector((b[0], b[1], H)), Vector((b[0], b[1], z)), Vector((a[0], a[1], z))],
                "Toit", 2.0, 2.0, mode="sol")
    e = 0.15
    for z, sens in ((H + 0.35, 1),):
        pt.quad([Vector((-e, -e, z)), Vector((L_BAT + e, -e, z)), Vector((L_BAT + e, P_BAT + e, z)),
                 Vector((-e, P_BAT + e, z))], "Toit", 4.0, 4.0)
    for axe, c, a0, a1 in (("x", -e, -e, L_BAT + e), ("x", P_BAT + e, -e, L_BAT + e),
                           ("y", -e, -e, P_BAT + e), ("y", L_BAT + e, -e, P_BAT + e)):
        pt.boite_mur(axe, c, a0, a1, H - 0.2, H + 0.9)
    plafonds = pt.objet()
    # encadrements, barreaux et planches des fenetres
    for axe, c, x, piece in fenetres:
        dedans = 1 if c < 1 else -1
        mob.place()
        for k in range(7):
            p = x - 0.6 + 0.2 * k
            a, b = ((p, c, 1.1), (p, c, 2.9)) if axe == "x" else ((c, p, 1.1), (c, p, 2.9))
            mob.cylindre(a, b, 0.015, "Rouille", 6)
        for z in (1.1, 2.9):
            cc = (x, c, z) if axe == "x" else (c, x, z)
            mob.boite(cc, (1.5, EP + 0.06, 0.08) if axe == "x" else (EP + 0.06, 1.5, 0.08), "Bois")
        for d in (-0.72, 0.72):
            cc = (x + d, c, 2.0) if axe == "x" else (c, x + d, 2.0)
            mob.boite(cc, (0.08, EP + 0.06, 1.88) if axe == "x" else (EP + 0.06, 0.08, 1.88), "Bois")
        if random.random() < 0.35:            # fenetre condamnee par des planches
            for k, ang in enumerate((0.35, -0.3, 0.1)):
                if axe == "x":
                    mob.place(x, c + dedans * (EP / 2 + 0.03), 1.4 + 0.55 * k, 0.0)
                    mob.boite((0, 0, 0), (1.7, 0.03, 0.18), "Bois", ry=ang)
                else:
                    mob.place(c + dedans * (EP / 2 + 0.03), x, 1.4 + 0.55 * k, math.pi / 2)
                    mob.boite((0, 0, 0), (1.7, 0.03, 0.18), "Bois", ry=ang)
            mob.place()
    return murs_sols, plafonds


# ---------------------------------------------------------------------------
#  PORTES
# ---------------------------------------------------------------------------
def battant(k, charniere, d0, ns, longueur, hauteur, angle, typ):
    """Un battant de porte qui tourne autour de sa charniere vers la piece (ns)."""
    d = d0 * math.cos(angle) + ns * math.sin(angle)
    o = ns * math.cos(angle) - d0 * math.sin(angle)
    rz = math.atan2(d.y, d.x)
    centre = charniere + d * (longueur / 2) + o * 0.03
    k.place()
    mat = "Metal" if typ == "metal" else "Bois"
    if typ == "vitre":                       # hublot (on la voit derriere)
        j = charniere + d * (longueur / 2) + o * 0.06
        k.boite((j.x, j.y, 1.6), (0.35, 0.02, 0.3), "Verre", rz=rz)
    k.boite((centre.x, centre.y, hauteur / 2), (longueur, 0.05, hauteur - 0.02), mat, rz=rz)
    poignee = charniere + d * (longueur - 0.12) + o * 0.08
    k.cylindre((poignee.x, poignee.y, 1.0), (poignee.x, poignee.y, 1.15), 0.015, "Rouille", 6)
    if typ == "metal":      # judas et trappe de la porte de cellule
        for zz, hh in ((1.55, 0.25), (1.0, 0.12)):
            j = charniere + d * (longueur / 2) + o * 0.06
            k.boite((j.x, j.y, zz), (0.3, 0.02, hh), "Verre" if zz > 1.2 else "Rouille", rz=rz)


def construire_portes(mob):
    rng = random.Random(5)
    for axe, c, centre, w, h, typ, _ in PORTES:
        o0, o1 = centre - w / 2, centre + w / 2
        n = Vector((0, 1, 0)) if axe == "x" else Vector((1, 0, 0))
        a = Vector((1, 0, 0)) if axe == "x" else Vector((0, 1, 0))
        p = (Vector((centre, c, 0)) if axe == "x" else Vector((c, centre, 0)))
        cote = 1 if piece_en(*(p + n * 0.5).xy) not in ("Couloir", "Dehors") else -1
        ns = n * cote
        pied = lambda t: (Vector((t, c, 0)) if axe == "x" else Vector((c, t, 0))) + ns * (EP / 2)
        # encadrement
        mob.place()
        for t in (o0, o1):
            q = Vector((t, c, h / 2)) if axe == "x" else Vector((c, t, h / 2))
            mob.boite(q, (0.1, EP + 0.06, h) if axe == "x" else (EP + 0.06, 0.1, h), "Bois")
        q = Vector((centre, c, h + 0.05)) if axe == "x" else Vector((c, centre, h + 0.05))
        mob.boite(q, (w + 0.2, EP + 0.06, 0.1) if axe == "x" else (EP + 0.06, w + 0.2, 0.1), "Bois")
        if typ == "arche":
            continue
        angle = math.radians(rng.choice([5, 25, 50, 85, 100]))
        if typ in ("bois", "metal"):
            battant(mob, pied(o0), a, ns, w, h, angle, typ)
        elif typ == "double":
            battant(mob, pied(o0), a, ns, w / 2, h, angle, "bois")
            battant(mob, pied(o1), -a, ns, w / 2, h, math.radians(rng.choice([0, 15, 70])), "bois")
        elif typ == "condamnee":
            battant(mob, pied(o0), a, ns, w, h, 0.0, "vitre")
            for k, ang in enumerate((0.4, -0.35, 0.05)):
                q = Vector((centre, c, 0.6 + 0.7 * k)) - ns * (EP / 2 + 0.05)
                mob.place(q.x, q.y, q.z, 0.0 if axe == "x" else math.pi / 2)
                mob.boite((0, 0, 0), (w + 0.4, 0.04, 0.2), "Bois", ry=ang)
            mob.place()


# ---------------------------------------------------------------------------
#  LE MOBILIER (chaque fonction dessine un objet autour de l'origine, Kit.place le pose)
# ---------------------------------------------------------------------------
def lit(k, sangles=False, sale=True):
    for x in (-0.45, 0.45):
        for y in (-0.95, 0.95):
            k.cylindre((x, y, 0.06), (x, y, 0.5), 0.022, "Metal", 8)
            k.cylindre((x, y, 0.0), (x, y, 0.06), 0.04, "Caoutchouc", 8)
        k.cylindre((x, -0.95, 0.42), (x, 0.95, 0.42), 0.018, "Metal", 8)
        k.cylindre((x, -0.98, 0.5), (x, -0.98, 1.05), 0.022, "Metal", 8)
        k.cylindre((x, 0.98, 0.5), (x, 0.98, 0.85), 0.022, "Metal", 8)
    for y, zh in ((-0.98, 1.05), (0.98, 0.85)):
        k.cylindre((-0.45, y, zh), (0.45, y, zh), 0.022, "Metal", 8)
        k.cylindre((-0.45, y, 0.6), (0.45, y, 0.6), 0.016, "Metal", 8)
        for x in np.linspace(-0.3, 0.3, 4):
            k.cylindre((x, y, 0.6), (x, y, zh), 0.012, "Metal", 6)
    k.boite((0, 0, 0.53), (0.86, 1.88, 0.14), "Matelas")
    k.boite((0, -0.72, 0.65), (0.55, 0.32, 0.1), "Drap", rz=0.08)
    if sangles:
        for y in (-0.35, 0.2, 0.75):
            k.boite((0, y, 0.6), (0.98, 0.07, 0.03), "Cuir")
            for x in (-0.5, 0.5):
                k.boite((x, y, 0.5), (0.03, 0.07, 0.22), "Cuir")


def table_chevet(k):
    k.boite((0, 0, 0.32), (0.42, 0.38, 0.6), "Metal")
    k.boite((0, -0.19, 0.48), (0.36, 0.02, 0.14), "Rouille")


def chaise(k, metal=False):
    mat = "Metal" if metal else "Bois"
    for x in (-0.18, 0.18):
        for y in (-0.18, 0.18):
            k.cylindre((x, y, 0), (x, y, 0.45), 0.018, mat, 6)
        k.cylindre((x, 0.18, 0.45), (x, 0.2, 0.92), 0.018, mat, 6)
    k.boite((0, 0, 0.46), (0.42, 0.42, 0.035), mat)
    k.boite((0, 0.2, 0.78), (0.38, 0.03, 0.2), mat)


def chaise_roulante(k):
    for x in (-0.28, 0.28):
        k.cylindre((x - 0.02, 0.05, 0.3), (x + 0.02, 0.05, 0.3), 0.3, "Caoutchouc", 20)
        k.cylindre((x - 0.025, 0.05, 0.3), (x + 0.025, 0.05, 0.3), 0.05, "Metal", 8)
        k.cylindre((x * 0.8, -0.28, 0.07), (x * 0.8 + 0.01, -0.28, 0.07), 0.07, "Caoutchouc", 10)
        k.cylindre((x * 0.8, -0.28, 0.12), (x * 0.8, -0.22, 0.5), 0.015, "Metal", 6)
        k.cylindre((x * 0.8, 0.22, 0.45), (x * 0.8, 0.26, 0.95), 0.015, "Metal", 6)
        k.cylindre((x * 0.8, 0.26, 0.95), (x * 0.8, 0.38, 0.97), 0.02, "Caoutchouc", 6)
        k.cylindre((x * 0.8, -0.22, 0.65), (x * 0.8, 0.22, 0.65), 0.015, "Metal", 6)
    k.boite((0, 0, 0.5), (0.44, 0.44, 0.04), "Cuir")
    k.boite((0, 0.24, 0.73), (0.42, 0.03, 0.42), "Cuir", rx=-0.1)
    k.boite((0, -0.36, 0.12), (0.4, 0.15, 0.02), "Metal")


def potence(k):
    k.cylindre((0, 0, 0.05), (0, 0, 1.95), 0.012, "Inox", 6)
    for a in range(5):
        an = 2 * math.pi * a / 5
        k.cylindre((0, 0, 0.06), (0.28 * math.cos(an), 0.28 * math.sin(an), 0.04), 0.012, "Inox", 6)
    k.cylindre((-0.12, 0, 1.92), (0.12, 0, 1.92), 0.008, "Inox", 6)
    k.boite((0.1, 0, 1.75), (0.1, 0.03, 0.2), "Plastique")
    k.cylindre((0.1, 0, 1.65), (0.15, -0.1, 0.9), 0.004, "Plastique", 4)


def brancard(k, corps=False):
    for x in (-0.3, 0.3):
        for y in (-0.85, 0.85):
            k.cylindre((x, y, 0.1), (x, y, 0.78), 0.02, "Inox", 6)
            k.cylindre((x - 0.01, y, 0.06), (x + 0.01, y, 0.06), 0.06, "Caoutchouc", 10)
        k.cylindre((x, -0.95, 0.8), (x, 0.95, 0.8), 0.02, "Inox", 6)
    k.boite((0, 0, 0.83), (0.62, 1.9, 0.06), "Matelas")
    if corps:   # une forme humaine sous un drap
        k.cylindre((0, -0.55, 0.95), (0, 0.15, 0.95), 0.2, "Drap", 12)
        k.cylindre((0, -0.62, 0.95), (0, -0.82, 0.95), 0.11, "Drap", 12)
        for x in (-0.09, 0.09):
            k.cylindre((x, 0.15, 0.92), (x, 0.88, 0.92), 0.08, "Drap", 10)
            k.cylindre((x, 0.9, 0.9), (x, 0.92, 1.05), 0.05, "Drap", 8)
        k.boite((0, 0.05, 0.9), (0.66, 1.95, 0.02), "Drap")
        k.boite((0.2, 0.97, 0.98), (0.06, 0.01, 0.04), "Papier")


def bureau(k):
    k.boite((0, 0, 0.75), (1.5, 0.75, 0.05), "Bois")
    for x in (-0.6, 0.6):
        k.boite((x, 0, 0.37), (0.3, 0.7, 0.72), "Bois")
    k.boite((0, 0.36, 0.45), (0.9, 0.02, 0.55), "Bois")
    k.boite((-0.35, -0.05, 0.85), (0.35, 0.3, 0.15), "Metal", rz=0.2)
    k.cylindre((0.5, 0.15, 0.78), (0.5, 0.15, 1.15), 0.012, "Metal", 6)
    k.cylindre((0.5, 0.15, 1.15), (0.4, 0.05, 1.12), 0.07, "Metal", 10, r2=0.02)
    for i in range(4):
        k.boite((0.1 + 0.05 * i, -0.1, 0.78 + 0.003 * i), (0.21, 0.3, 0.003), "Papier", rz=0.3 * i)


def classeur(k, ouvert=False):
    k.boite((0, 0, 0.66), (0.5, 0.6, 1.32), "Metal")
    for z in (0.25, 0.58, 0.91, 1.22):
        k.boite((0, -0.305, z), (0.42, 0.01, 0.26), "Rouille")
    if ouvert:
        k.boite((0, -0.5, 0.91), (0.44, 0.45, 0.26), "Metal")
        for i in range(6):
            k.boite((0, -0.65 + 0.06 * i, 0.98), (0.4, 0.01, 0.24), "Carton")


def etagere(k, contenu="cartons", rng=None):
    rng = rng or random.Random(1)
    for x in (-0.9, 0.9):
        k.boite((x, 0, 1.0), (0.04, 0.45, 2.0), "Metal")
    for z in (0.1, 0.55, 1.0, 1.45, 1.9):
        k.boite((0, 0, z), (1.84, 0.45, 0.03), "Metal")
        x = -0.85
        while x < 0.75:
            if contenu == "cartons":
                l = rng.uniform(0.25, 0.4)
                if rng.random() < 0.8:
                    k.boite((x + l / 2, 0, z + 0.15), (l - 0.03, 0.38, 0.28), "Carton", rz=rng.uniform(-0.1, 0.1))
                x += l
            else:
                if rng.random() < 0.7:
                    hh = rng.uniform(0.12, 0.25)
                    k.cylindre((x + 0.04, rng.uniform(-0.12, 0.12), z + 0.02), (x + 0.04, 0, z + 0.02 + hh),
                               rng.uniform(0.025, 0.045), rng.choice(["Verre", "Plastique", "Carton"]), 8)
                x += 0.1


def table_longue(k, rng):
    k.boite((0, 0, 0.75), (2.4, 0.8, 0.04), "Inox")
    for x in (-1.1, 1.1):
        for y in (-0.33, 0.33):
            k.cylindre((x, y, 0), (x, y, 0.74), 0.025, "Metal", 6)
    for i in range(rng.randint(2, 5)):
        x, y = rng.uniform(-1.0, 1.0), rng.choice([-0.22, 0.22])
        k.boite((x, y, 0.78), (0.4, 0.3, 0.02), "Inox", rz=rng.uniform(-0.3, 0.3))
        k.cylindre((x, y, 0.79), (x, y, 0.85), 0.07, "Porcelaine", 10, r2=0.09)


def banc(k, long=2.4):
    k.boite((0, 0, 0.45), (long, 0.32, 0.04), "Bois")
    for x in (-long / 2 + 0.15, long / 2 - 0.15):
        k.boite((x, 0, 0.22), (0.05, 0.28, 0.44), "Metal")


def lavabo(k, miroir=True):
    k.boite((0, 0, 0.82), (0.55, 0.42, 0.12), "Porcelaine")
    k.boite((0, -0.02, 0.86), (0.42, 0.3, 0.06), "EauSale")
    k.cylindre((0, 0.1, 0), (0, 0.1, 0.76), 0.08, "Porcelaine", 10)
    k.cylindre((0, 0.18, 0.9), (0, 0.05, 1.02), 0.015, "Inox", 6)
    if miroir:
        k.boite((0, 0.2, 1.55), (0.5, 0.02, 0.65), "Verre", ry=0.03)


def toilette(k):
    k.cylindre((0, 0, 0), (0, 0, 0.4), 0.2, "Porcelaine", 12, r2=0.22)
    k.cylindre((0, 0, 0.4), (0, 0, 0.42), 0.21, "Plastique", 12)
    k.boite((0, 0.24, 0.6), (0.4, 0.15, 0.38), "Porcelaine")


def baignoire(k):
    k.boite((0, 0, 0.32), (1.7, 0.75, 0.55), "Porcelaine")
    k.boite((0, 0, 0.5), (1.5, 0.58, 0.2), "EauSale")
    for x in (-0.75, 0.75):
        for y in (-0.3, 0.3):
            k.cylindre((x, y, 0), (x, y, 0.06), 0.05, "Rouille", 8)
    for x in (-0.3, 0.35):
        k.boite((x, 0, 0.62), (0.08, 0.8, 0.03), "Cuir")


def table_operation(k):
    k.cylindre((0, 0, 0), (0, 0, 0.82), 0.14, "Inox", 12)
    k.boite((0, 0, 0.02), (0.6, 0.8, 0.04), "Inox")
    k.boite((0, 0, 0.88), (0.6, 1.9, 0.08), "Inox")
    k.boite((0, -0.9, 0.95), (0.3, 0.2, 0.08), "Cuir")
    for y in (-0.3, 0.3, 0.75):
        k.boite((0, y, 0.94), (0.66, 0.07, 0.03), "Cuir")


def scialytique(k):
    k.cylindre((0, 0, H), (0, 0, H - 0.8), 0.04, "Inox", 8)
    k.cylindre((0, 0, H - 0.8), (0.4, 0.2, H - 1.1), 0.03, "Inox", 8)
    k.cylindre((0.4, 0.2, H - 1.1), (0.4, 0.2, H - 1.25), 0.4, "Inox", 20)
    k.cylindre((0.4, 0.2, H - 1.25), (0.4, 0.2, H - 1.26), 0.33, "Neon", 20)


def electrochoc(k):
    k.boite((0, 0, 0.55), (0.65, 0.45, 1.1), "Bois")
    k.boite((0, -0.23, 0.85), (0.55, 0.02, 0.4), "Metal")
    for i in range(3):
        for j in range(2):
            k.cylindre((-0.18 + 0.18 * i, -0.24, 0.95 - 0.18 * j), (-0.18 + 0.18 * i, -0.28, 0.95 - 0.18 * j),
                       0.045 if j == 0 else 0.025, "Encre" if j == 0 else "Rouille", 12)
    pts = [(0.25, -0.2, 0.6), (0.6, -0.5, 0.2), (1.0, -0.6, 0.1), (1.3, -0.5, 0.6), (1.35, -0.2, 1.25)]
    for a, b in zip(pts[:-1], pts[1:]):
        k.cylindre(a, b, 0.012, "Caoutchouc", 6)


def fauteuil_contention(k):
    k.boite((0, 0, 0.45), (0.6, 0.55, 0.08), "Bois")
    k.boite((0, 0.27, 1.0), (0.6, 0.07, 1.1), "Bois")
    for x in (-0.32, 0.32):
        k.boite((x, 0, 0.7), (0.07, 0.55, 0.06), "Bois")
        k.boite((x, -0.25, 0.4), (0.07, 0.07, 0.8), "Bois")
        k.boite((x, 0.25, 0.4), (0.07, 0.07, 0.8), "Bois")
        k.boite((x, -0.05, 0.74), (0.12, 0.07, 0.03), "Cuir")
        k.boite((x * 0.4, -0.27, 0.2), (0.12, 0.03, 0.07), "Cuir")
    k.boite((0, 0.22, 0.95), (0.64, 0.03, 0.08), "Cuir")
    k.boite((0, 0.22, 1.45), (0.25, 0.1, 0.06), "Cuir")


def tiroirs_morgue(k, ouvert=1):
    k.boite((0, 0, 1.1), (2.2, 0.9, 2.2), "Inox")
    for i in range(3):
        for j in range(3):
            x, z = -0.72 + 0.72 * i, 0.4 + 0.72 * j
            k.boite((x, -0.455, z), (0.62, 0.01, 0.62), "Inox")
            k.cylindre((x - 0.15, -0.47, z + 0.2), (x + 0.15, -0.47, z + 0.2), 0.012, "Rouille", 6)
            k.boite((x, -0.462, z - 0.18), (0.14, 0.005, 0.06), "Papier")
    x, z = 0.0, 1.12
    if ouvert:
        k.boite((x, -0.95, z - 0.25), (0.6, 1.1, 0.04), "Inox")
        k.cylindre((x, -1.35, z - 0.12), (x, -0.6, z - 0.12), 0.18, "Drap", 12)
        k.cylindre((x, -1.38, z - 0.12), (x, -1.5, z - 0.12), 0.1, "Drap", 10)


def comptoir(k):
    k.boite((0, 0, 0.55), (4.0, 0.6, 1.1), "Bois")
    k.boite((0, 0, 1.12), (4.1, 0.7, 0.05), "Bois")
    k.boite((-2.2, 1.2, 0.55), (0.6, 3.0, 1.1), "Bois")
    k.boite((0.8, 0.1, 1.2), (0.25, 0.2, 0.1), "Encre")
    k.cylindre((-0.5, 0.1, 1.15), (-0.5, 0.1, 1.22), 0.06, "Rouille", 10, r2=0.01)


def plante_morte(k):
    k.cylindre((0, 0, 0), (0, 0, 0.45), 0.18, "Rouille", 12, r2=0.22)
    rng = random.Random(3)
    for i in range(7):
        a = rng.uniform(0, 6.28)
        k.cylindre((0, 0, 0.4), (0.3 * math.cos(a), 0.3 * math.sin(a), rng.uniform(0.9, 1.4)), 0.008, "Carton", 4)


def tele(k):
    k.boite((0, 0, 0.35), (0.8, 0.5, 0.7), "Bois")
    k.boite((0, 0, 0.95), (0.7, 0.55, 0.55), "Bois")
    k.boite((-0.06, -0.28, 0.95), (0.5, 0.01, 0.4), "Verre")
    for s in (-1, 1):
        k.cylindre((0, 0, 1.22), (s * 0.3, 0.1, 1.7), 0.006, "Metal", 4)


def piano(k):
    k.boite((0, 0, 0.65), (1.5, 0.6, 1.3), "Bois")
    k.boite((0, -0.45, 0.75), (1.4, 0.3, 0.06), "Bois")
    k.boite((0, -0.45, 0.79), (1.3, 0.25, 0.02), "Porcelaine")
    for i in range(36):
        if i % 7 in (1, 2, 4, 5, 6):
            k.boite((-0.62 + i * 0.036, -0.4, 0.81), (0.018, 0.15, 0.02), "Encre")


def fauteuil(k):
    k.boite((0, 0, 0.25), (0.8, 0.75, 0.5), "Velours")
    k.boite((0, 0.32, 0.65), (0.8, 0.12, 0.8), "Velours")
    for x in (-0.36, 0.36):
        k.boite((x, 0, 0.6), (0.1, 0.75, 0.25), "Velours")


def neon(k, tombe=False):
    if tombe:
        k.cylindre((-0.6, 0, H), (-0.6, 0, H - 0.1), 0.004, "Metal", 4)
        k.boite((0, 0, H - 0.5), (1.25, 0.22, 0.07), "Metal", ry=0.7)
        k.cylindre((0.55, 0, H), (0.55, 0, H - 0.75), 0.004, "Metal", 4)
        return
    k.boite((0, 0, H - 0.05), (1.25, 0.22, 0.07), "Metal")
    for y in (-0.05, 0.05):
        k.cylindre((-0.58, y, H - 0.1), (0.58, y, H - 0.1), 0.014, "Neon", 8)


def radiateur(k):
    for i in range(14):
        k.boite((-0.52 + 0.08 * i, 0, 0.45), (0.05, 0.1, 0.6), "Metal")
    k.cylindre((-0.6, 0, 0.18), (0.6, 0, 0.18), 0.02, "Rouille", 6)


def casier(k, ouvert=0.0):
    """Grand casier en metal ou un joueur peut se cacher (porte devant = -y, charniere a gauche)."""
    w, d, h = 0.7, 0.6, 2.1
    for x in (-w / 2 + 0.01, w / 2 - 0.01):
        k.boite((x, 0, h / 2), (0.02, d, h), "Metal")
    k.boite((0, d / 2 - 0.01, h / 2), (w, 0.02, h), "Metal")
    k.boite((0, 0, h - 0.01), (w, d, 0.02), "Metal")
    k.boite((0, 0, 0.05), (w, d, 0.1), "Metal")
    c = Vector((-w / 2 + (w / 2) * math.cos(ouvert), -d / 2 - (w / 2) * math.sin(ouvert), h / 2 + 0.02))
    nrm = Vector((-math.sin(ouvert), -math.cos(ouvert), 0))
    k.boite(c, (w, 0.02, h - 0.1), "Metal", rz=-ouvert)
    for z in (1.75, 1.82, 1.89):
        k.boite(Vector((c.x, c.y, z)) + nrm * 0.012, (0.4, 0.005, 0.02), "Encre", rz=-ouvert)
    k.boite(c + nrm * 0.015 + Vector((math.cos(ouvert), -math.sin(ouvert), 0)) * 0.28 + Vector((0, 0, 0.05 - h / 2 + 1.0)),
            (0.03, 0.02, 0.15), "Rouille", rz=-ouvert)


def armoire(k):
    """Grande armoire en bois a deux portes (une entrouverte)."""
    k.boite((0, 0.02, 1.1), (1.4, 0.58, 2.2), "Bois")
    k.boite((-0.35, -0.29, 1.1), (0.68, 0.03, 2.1), "Bois")
    k.boite((0.42, -0.48, 1.1), (0.68, 0.03, 2.1), "Bois", rz=0.6)
    k.boite((0.02, -0.15, 1.05), (1.3, 0.25, 2.0), "Encre")


def rideau(k, chemin, z0=0.3, z1=2.55, plis=0.16, prof=0.05):
    """Rideau d'hopital qui pend d'une tringle (chemin = points de la tringle, en coordonnees locales)."""
    pts = [Vector((x, y, 0)) for x, y in chemin]
    for a, b in zip(pts[:-1], pts[1:]):
        k.cylindre((a.x, a.y, z1 + 0.05), (b.x, b.y, z1 + 0.05), 0.012, "Inox", 6)
    for q in pts:
        k.cylindre((q.x, q.y, z1 + 0.05), (q.x, q.y, H), 0.008, "Inox", 4)
    ligne, s_ = [], 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(2, int((b - a).length / 0.03))
        for i in range(n):
            q = a.lerp(b, i / n)
            t = (b - a).normalized()
            ligne.append((q, Vector((-t.y, t.x, 0)), s_ + (b - a).length * i / n))
        s_ += (b - a).length
    ligne.append((pts[-1], ligne[-1][1], s_))
    bm, m = k.bm, k.m("Rideau")
    for cote in (0.0, 0.004):                 # deux faces (visible des deux cotes)
        rang = []
        for q, nn, sv in ligne:
            off = nn * (math.sin(sv / plis * 2 * math.pi) * prof + cote)
            base = k.R @ (q + off)
            rang.append((bm.verts.new(base + Vector((0, 0, z0))), bm.verts.new(base + Vector((0, 0, z1)))))
        for (a0, a1), (b0, b1) in zip(rang[:-1], rang[1:]):
            f = bm.faces.new((a0, b0, b1, a1) if cote else (a1, b1, b0, a0))
            f.material_index = m
            f.smooth = True


def eboulement(k, rng):
    """Plafond effondre dans le couloir : dalles, poutres, tuyaux, gravats. Il reste un passage etroit."""
    tx0, ty0, tx1, ty1 = TROU
    for i in range(5):
        k.place(rng.uniform(tx0, tx1), rng.uniform(ty0 + 0.2, ty1 - 0.6), 0.0, rng.uniform(-0.4, 0.4))
        k.boite((0, 0, 0.3), (2.8, 0.18, 0.2), "Bois", ry=rng.uniform(0.1, 0.5), rx=rng.uniform(-0.2, 0.2))
    for i in range(14):
        k.place(rng.uniform(tx0 - 0.5, tx1 + 0.5), rng.uniform(ty0, ty1 - 0.2), 0.0, rng.uniform(0, 3.14))
        k.boite((0, 0, rng.uniform(0.05, 0.6)), (0.6, 0.6, 0.02), "Plaque", rx=rng.uniform(-1.2, 1.2), ry=rng.uniform(-0.6, 0.6))
    for i in range(30):
        k.place(rng.uniform(tx0 - 0.3, tx1 + 0.3), rng.uniform(ty0, ty1 - 0.3), 0.0, rng.uniform(0, 3.14))
        sz = rng.uniform(0.15, 0.5)
        k.boite((0, 0, sz * 0.3), (sz, sz * 0.8, sz * 0.6), rng.choice(["Plaque", "Carton", "Rouille"]),
                rx=rng.uniform(-0.4, 0.4))
    k.place()
    k.cylindre((tx0 - 0.3, ty0 + 0.6, H - 0.1), (tx1 - 0.2, ty0 + 1.2, 0.2), 0.05, "Rouille", 8)   # tuyau tombe
    k.cylindre((tx1 + 0.2, ty1 - 0.4, H - 0.05), (tx0 + 0.6, ty0 + 0.4, 0.9), 0.08, "Bois", 6)    # poutre
    for i in range(6):                                      # dalles qui pendent au bord du trou
        x = rng.uniform(tx0, tx1)
        k.place(x, rng.choice([ty0, ty1]), H - 0.25, 0.0)
        k.boite((0, 0, 0), (0.6, 0.6, 0.02), "Plaque", rx=rng.choice([-1.0, 1.0]) * rng.uniform(0.6, 1.2))
    k.place()


def papiers(k, x0, y0, x1, y1, n, rng):
    for _ in range(n):
        k.place(rng.uniform(x0, x1), rng.uniform(y0, y1), 0.0, rng.uniform(0, 6.28))
        k.boite((0, 0, 0.002 + rng.uniform(0, 0.004)), (0.21, 0.297, 0.002), "Papier", rx=rng.uniform(-0.05, 0.05))
    k.place()


def gravats(k, x0, y0, x1, y1, n, rng):
    for _ in range(n):
        k.place(rng.uniform(x0, x1), rng.uniform(y0, y1), 0.0, rng.uniform(0, 6.28))
        s = rng.uniform(0.05, 0.25)
        k.boite((0, 0, s * 0.15), (s, s * rng.uniform(0.5, 1), s * 0.3), rng.choice(["Plaque", "Carton", "Rouille"]),
                rx=rng.uniform(-0.3, 0.3))
    k.place()


def meubler(mob, rng):
    P = mob.place
    # dortoir : deux rangees de lits
    for i, x in enumerate((2.0, 5.0, 8.0, 12.5, 15.5, 18.5)):
        P(x, 1.3, 0, 0)
        lit(mob, sangles=(i % 3 == 1))
        P(x + 1.5, 0.5, 0, 0)
        table_chevet(mob)
    for i, x in enumerate((2.0, 5.0, 14.0, 17.0)):
        if i == 1:
            P(x, 13.8, 0.45, math.pi + 0.3, rx=1.45)          # un lit renverse
        else:
            P(x, 14.7, 0, math.pi)
        lit(mob, sangles=(i == 2))
    P(10.3, 7.5, 0, 2.2)
    chaise_roulante(mob)
    P(6.5, 9.0, 0, 0.7, rx=1.57)
    chaise(mob, True)
    papiers(mob, 1, 3, 19, 13, 25, rng)
    # reserve et infirmerie
    for y in (1.0, 3.5):
        P(21.0, y + 0.5, 0, math.pi / 2)
        etagere(mob, "cartons", rng)
    P(25.4, 3.5, 0, -math.pi / 2)
    etagere(mob, "cartons", rng)
    P(20.5, 11.5, 0, math.pi / 2)
    etagere(mob, "flacons", rng)
    P(23.5, 13.0, 0, 0)
    bureau(mob)
    P(23.5, 13.8, 0, math.pi)
    chaise(mob)
    P(24.8, 9.3, 0, 0.1)
    brancard(mob)
    P(22.2, 8.4, 0, 0)
    potence(mob)
    # hall d'accueil
    P(32.0, 10.5, 0, 0)
    comptoir(mob)
    for x in (27.0, 37.0):
        P(x, 5.0, 0, math.pi / 2)
        banc(mob, 3.0)
    for x, y in ((26.6, 0.6), (37.4, 0.6), (26.6, 15.0)):
        P(x, y, 0, 0)
        plante_morte(mob)
    P(30.0, 2.5, 0, 0.9)
    chaise_roulante(mob)
    papiers(mob, 27, 1, 37, 15, 25, rng)
    # refectoire
    P(38.5, 8.0, 0, math.pi / 2)
    mob.boite((0, 0, 0.5), (12.0, 0.7, 1.0), "Inox")
    for y in (3.0, 7.0, 11.0):
        for x in (42.0, 46.5, 50.0):
            P(x, y, 0, 0)
            table_longue(mob, rng)
            for dy in (-0.75, 0.75):
                if rng.random() < 0.2:
                    P(x + rng.uniform(-0.5, 0.5), y + dy * 1.3, 0.16, rng.uniform(0, 3), rx=1.57)
                else:
                    P(x, y + dy, 0, 0)
                banc(mob)
    papiers(mob, 39, 1, 51, 15, 20, rng)
    # morgue
    for x in (54.8, 57.6, 60.4):
        P(x, 0.55, 0, math.pi)
        tiroirs_morgue(mob, ouvert=(x == 57.6))
    P(58.5, 5.2, 0, math.pi / 2)
    table_operation(mob)
    P(58.5, 5.2, 0, 0)
    scialytique(mob)
    P(54.3, 6.0, 0, math.pi / 2)
    brancard(mob, corps=True)
    # cellule capitonnee + contention
    P(55.0, 13.0, 0, 0.2)
    mob.boite((0, 0, 0.08), (0.9, 1.9, 0.16), "Matelas")
    P(61.0, 12.0, 0, 0)
    lit(mob, sangles=True)
    P(59.0, 9.5, 0, math.pi / 4)
    fauteuil_contention(mob)
    P(63.0, 9.2, 0, 0)
    potence(mob)
    # bureau du directeur + archives
    P(5.0, 26.5, 0, math.pi)
    bureau(mob)
    P(5.0, 27.4, 0, 0)
    chaise(mob)
    for y in (21.0, 22.0, 23.0):
        P(0.6, y, 0, math.pi / 2)
        classeur(mob, ouvert=(y == 22.0))
    P(9.5, 25.0, 0, math.pi / 2)
    etagere(mob, "cartons", rng)
    papiers(mob, 1, 21, 9, 29, 30, rng)
    for y in (32.0, 34.5, 37.0):
        for x in (2.0, 5.0, 8.0):
            if (x, y) == (5.0, 34.5):
                P(x, y, 0.25, 0.3, rx=1.4)                  # etagere tombee
            else:
                P(x, y, 0, 0)
            etagere(mob, "cartons", rng)
    papiers(mob, 1, 31, 9, 39, 60, rng)
    # chambres-cellules
    for kc in range(9):
        cx = 16.0 + 4 * kc
        if kc == 2:
            P(cx + 0.4, 24.4, 0.45, 0.1, rx=1.5)
        else:
            P(cx + 0.5, 24.9, 0, math.pi / 2)
        lit(mob, sangles=(kc in (4, 7)))
        P(cx - 1.4, 25.5, 0, math.pi)
        toilette(mob)
        if kc == 0:
            P(cx, 25.6, 0, 0)
            chaise(mob)
        papiers(mob, cx - 1.7, 20.5, cx + 1.7, 25.5, 3, rng)
    # salle commune
    for i in range(8):
        a = 2 * math.pi * i / 8
        P(22.0 + 2.6 * math.cos(a), 33.0 + 2.6 * math.sin(a), 0, a + math.pi / 2)
        chaise(mob)
    P(22.0, 33.0, 0, 0.4)
    chaise(mob, True)
    P(47.5, 38.8, 0, math.pi)
    tele(mob)
    for x in (44.5, 46.5):
        P(x, 35.5, 0, 0)
        fauteuil(mob)
    P(17.2, 39.3, 0, math.pi)
    piano(mob)
    for x, y in ((33.0, 29.0), (39.0, 34.0)):
        P(x, y, 0, 0.3)
        table_longue(mob, rng)
        for dy in (-0.7, 0.7):
            P(x, y + dy, 0, 0.3 if dy < 0 else math.pi + 0.3)
            chaise(mob)
    P(28.0, 37.0, 0, 2.5)
    chaise_roulante(mob)
    papiers(mob, 15, 27, 49, 39, 50, rng)
    # douches
    for y in (21.5, 23.5, 25.5, 27.5):
        P(63.7, y, 0, -math.pi / 2)
        mob.cylindre((0, 0, 0), (0, 0, 2.3), 0.02, "Rouille", 6)
        mob.cylindre((0, 0, 2.3), (0, -0.25, 2.3), 0.02, "Rouille", 6)
        mob.cylindre((0, -0.25, 2.28), (0, -0.25, 2.2), 0.08, "Inox", 10, r2=0.03)
        P(63.3, y + 1.0, 0, 0)
        mob.boite((0, 0, 1.0), (1.4, 0.06, 2.0), "Porcelaine")
    P(57.5, 28.0, 0, 0)
    baignoire(mob)
    for x in (56.0, 58.5, 61.0):
        P(x, 20.4, 0, math.pi)
        lavabo(mob, miroir=False)
    P()
    mob.boite((58.5, 20.15, 1.65), (6.2, 0.02, 1.1), "Miroir")          # grand miroir (screamer)
    for x in (55.5, 61.5):
        mob.boite((x, 20.17, 1.65), (0.04, 0.03, 1.15), "Inox")
    # ---- les cachettes et les endroits a screamers ----
    for i, y in enumerate((31.0, 31.7, 32.4, 33.1, 33.8, 34.5)):         # casiers du couloir ouest
        P(10.45, y, 0, math.pi / 2)
        casier(mob, ouvert={2: 1.3, 4: 0.12}.get(i, 0.0))
    for i, y in enumerate((26.8, 27.5, 28.2, 28.9)):                     # vestiaire des douches
        P(54.45, y, 0, math.pi / 2)
        casier(mob, ouvert=0.4 if i == 1 else 0.0)
    P(9.55, 22.2, 0, -math.pi / 2)
    armoire(mob)
    P(0, 0, 0, 0)
    rideau(mob, [(14.4, 0.2), (14.4, 2.75), (16.6, 2.75), (16.6, 1.2)])   # rideaux autour d'un lit du dortoir
    rideau(mob, [(23.8, 7.6), (23.8, 10.7), (25.3, 10.7)])                # rideau de l'infirmerie
    rideau(mob, [(60.0, 9.0), (60.0, 15.0)], prof=0.07)                  # rideau de la contention
    eboulement(mob, rng)
    # bloc operatoire
    P(59.0, 35.0, 0, 0)
    table_operation(mob)
    scialytique(mob)
    P(62.6, 38.6, 0, 0)
    electrochoc(mob)
    P(61.0, 38.4, 0, 0.3)
    fauteuil_contention(mob)
    P(56.0, 34.0, 0, 0)
    potence(mob)
    P(56.5, 39.4, 0, math.pi)
    etagere(mob, "flacons", rng)
    P(57.3, 36.5, 0, 0.5)
    mob.boite((0, 0, 0.85), (0.6, 0.4, 0.03), "Inox")
    for i in range(6):
        mob.cylindre((-0.2 + 0.08 * i, -0.1, 0.88), (-0.2 + 0.08 * i, 0.1, 0.88), 0.006, "Inox", 4)
    for x in (-0.25, 0.25):
        for y in (-0.15, 0.15):
            mob.cylindre((x, y, 0), (x, y, 0.84), 0.012, "Inox", 6)
    # couloirs
    P(20.0, 18.6, 0, math.pi / 2)
    brancard(mob)
    P(44.0, 17.2, 0, 1.2)
    chaise_roulante(mob)
    P(52.0, 30.0, 0.2, 0.5, rx=1.57)
    chaise(mob, True)
    P(12.0, 31.0, 0, 0.0)
    potence(mob)
    papiers(mob, 1, 16.5, 63, 19.5, 40, rng)
    gravats(mob, 1, 16.5, 63, 19.5, 30, rng)
    # radiateurs sous les fenetres du dortoir et du refectoire
    for x in (4.0, 16.0):
        P(x, 0.25, 0, 0)
        radiateur(mob)
    mob.place()


def neons(mob, rng):
    positions = [(x, 18.0) for x in range(4, 62, 6)] + [(12.0, y) for y in (24, 30, 36)] + \
                [(52.0, y) for y in (24, 30, 36)] + \
                [(5, 4), (15, 4), (5, 12), (15, 12), (32, 5), (32, 12), (42, 4), (48, 4), (42, 12), (48, 12),
                 (23, 11.5), (23, 3.5), (55, 4), (61, 4), (55, 12), (61, 12), (5, 25), (5, 35), (59, 25),
                 (57, 32), (61, 38)] + [(16.0 + 4 * k, 23.0) for k in range(9)] + \
                [(x, y) for x in (20, 32, 44) for y in (30, 36)]
    allumes = []
    for x, y in positions:
        tombe = rng.random() < 0.15 or (x == 52.0 and y == 30)
        if x == 52.0 or abs(x - 40) < 1.5 and abs(y - 18) < 1:   # zone noire + au-dessus de l'eboulement
            if abs(x - 40) < 1.5:
                continue
            mob.place(x, y, 0, math.pi / 2)
            neon(mob, tombe)
            continue
        mob.place(x, y, 0, 0 if piece_en(x, y) != "Couloir" or abs(y - 18) < 1 else math.pi / 2)
        neon(mob, tombe)
        if not tombe and rng.random() < 0.7:
            allumes.append((x, y))
    mob.place()
    return allumes


# ---------------------------------------------------------------------------
#  ECRITURES, PANNEAUX, SANG
# ---------------------------------------------------------------------------
def bruit_lisse(h, w, cellule, graine):
    """Bruit doux (non repete) pour les inscriptions."""
    rng = np.random.default_rng(graine)
    g = rng.normal(size=(h // cellule + 3, w // cellule + 3))
    y, x = np.arange(h) / cellule, np.arange(w) / cellule
    y0, x0 = np.floor(y).astype(int), np.floor(x).astype(int)
    fy, fx = (y - y0)[:, None], (x - x0)[None, :]
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    A, B = g[y0][:, x0], g[y0][:, x0 + 1]
    C, D = g[y0 + 1][:, x0], g[y0 + 1][:, x0 + 1]
    return A * (1 - fx) * (1 - fy) + B * fx * (1 - fy) + C * (1 - fx) * fy + D * fx * fy


def masque_texte(corps, W, Hp, marge=0.1, ss=2):
    """Dessine un texte en pixels (sans aucune librairie) : Blender fabrique les lettres,
    puis on remplit leurs triangles. Renvoie un masque (Hp, W) entre 0 et 1, ligne 0 = en bas."""
    cu = bpy.data.curves.new("txt", 'FONT')
    cu.body = corps
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    o = bpy.data.objects.new("txt", cu)
    bpy.context.scene.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH')
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    tris = np.array([[tuple(v.co.xy) for v in f.verts] for f in bm.faces])
    bm.free()
    me = o.data
    bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.meshes.remove(me)
    w, h = W * ss, Hp * ss
    mn, mx = tris.reshape(-1, 2).min(0), tris.reshape(-1, 2).max(0)
    echelle = min(w * (1 - 2 * marge) / (mx - mn)[0], h * (1 - 2 * marge) / (mx - mn)[1])
    P = (tris - mn) * echelle + (np.array([w, h]) - (mx - mn) * echelle) / 2
    img = np.zeros((h, w), dtype=bool)
    for a, b, c in P:
        x0, y0 = np.floor(np.minimum(np.minimum(a, b), c)).astype(int)
        x1, y1 = np.ceil(np.maximum(np.maximum(a, b), c)).astype(int) + 1
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, w), min(y1, h)
        if x1 <= x0 or y1 <= y0:
            continue
        py, px = np.mgrid[y0:y1, x0:x1] + 0.5
        e0 = (b[0] - a[0]) * (py - a[1]) - (b[1] - a[1]) * (px - a[0])
        e1 = (c[0] - b[0]) * (py - b[1]) - (c[1] - b[1]) * (px - b[0])
        e2 = (a[0] - c[0]) * (py - c[1]) - (a[1] - c[1]) * (px - c[0])
        img[y0:y1, x0:x1] |= ((e0 >= 0) & (e1 >= 0) & (e2 >= 0)) | ((e0 <= 0) & (e1 <= 0) & (e2 <= 0))
    return img.reshape(Hp, ss, W, ss).mean(axis=(1, 3))


def coulures_et_gouttes(m, graine):
    """Ajoute au sang des coulures (qui partent du bas des lettres) et des eclaboussures."""
    h, w = m.shape
    rng = np.random.default_rng(graine)
    a = m.copy()
    for _ in range(int(w / 24)):                               # coulures
        x = int(rng.integers(3, w - 3))
        lignes = np.where(a[:, x] > 0.5)[0]
        if len(lignes) == 0 or rng.random() < 0.3:
            continue
        bas = int(lignes.min())
        L = int(rng.uniform(0.05, 0.45) * h)
        larg = rng.uniform(1.2, 3.2)
        y0 = max(0, bas - L)
        ys = np.arange(y0, bas + 1)
        t = (bas - ys) / max(L, 1)
        xs = np.arange(max(0, x - 6), min(w, x + 7))
        X, Y = np.meshgrid(xs, ys)
        ondule = 1.2 * np.sin(Y * 0.15 + x)
        demi = (larg * (1 - 0.55 * t))[:, None]
        a[y0:bas + 1, xs[0]:xs[-1] + 1] = np.maximum(a[y0:bas + 1, xs[0]:xs[-1] + 1],
                                                     np.clip(demi - np.abs(X - x - ondule) + 0.5, 0, 1))
        gy, gx = np.mgrid[max(0, y0 - 5):min(h, y0 + 5), max(0, x - 5):min(w, x + 6)]
        a[gy, gx] = np.maximum(a[gy, gx], np.clip(larg * 1.1 - np.hypot(gx - x, gy - y0 - 1) + 0.5, 0, 1))
    pleins = np.argwhere(a > 0.5)
    for _ in range(int(w / 10)):                               # eclaboussures
        if len(pleins) == 0:
            break
        cy, cx = pleins[rng.integers(len(pleins))] + rng.normal(0, 0.06 * h, 2).astype(int)
        cy, cx = int(np.clip(cy, 0, h - 1)), int(np.clip(cx, 0, w - 1))
        r = rng.uniform(0.8, 3.5)
        gy, gx = np.mgrid[max(0, cy - 5):min(h, cy + 6), max(0, cx - 5):min(w, cx + 6)]
        if gy.size:
            a[gy, gx] = np.maximum(a[gy, gx], np.clip(r - np.hypot(gx - cx, gy - cy) + 0.5, 0, 1))
    return a


# Lettres tracees au doigt : chaque lettre = des traits (x, y) dans une case de hauteur 1.
def _arc(cx, cy, rx, ry, a0, a1, n=14):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


LETTRES = {
    "A": (0.72, [[(0, 0), (0.36, 1), (0.72, 0)], [(0.16, 0.38), (0.56, 0.4)]]),
    "C": (0.72, [_arc(0.4, 0.5, 0.36, 0.5, 45, 315)]),
    "D": (0.7, [[(0.05, 0), (0.05, 1)], [(0.05, 1), (0.42, 0.95), (0.66, 0.65), (0.64, 0.3), (0.42, 0.04), (0.05, 0)]]),
    "E": (0.6, [[(0.6, 1), (0.05, 1), (0.05, 0), (0.6, 0)], [(0.05, 0.52), (0.47, 0.53)]]),
    "G": (0.76, [_arc(0.4, 0.5, 0.36, 0.5, 45, 330), [(0.74, 0.12), (0.74, 0.45), (0.46, 0.45)]]),
    "H": (0.68, [[(0.05, 1), (0.05, 0)], [(0.63, 1), (0.63, 0)], [(0.05, 0.5), (0.63, 0.52)]]),
    "I": (0.2, [[(0.1, 1), (0.1, 0)]]),
    "K": (0.66, [[(0.05, 1), (0.05, 0)], [(0.62, 1), (0.08, 0.45), (0.64, 0)]]),
    "L": (0.56, [[(0.05, 1), (0.05, 0), (0.56, 0)]]),
    "M": (0.86, [[(0.04, 0), (0.1, 1), (0.43, 0.32), (0.76, 1), (0.82, 0)]]),
    "N": (0.68, [[(0.05, 0), (0.05, 1), (0.63, 0), (0.63, 1)]]),
    "O": (0.8, [_arc(0.4, 0.5, 0.37, 0.5, 90, 470, 20)]),
    "P": (0.62, [[(0.05, 0), (0.05, 1), (0.42, 0.98), (0.6, 0.82), (0.58, 0.6), (0.4, 0.5), (0.05, 0.5)]]),
    "R": (0.66, [[(0.05, 0), (0.05, 1), (0.42, 0.98), (0.6, 0.82), (0.58, 0.6), (0.4, 0.5), (0.05, 0.5)],
                 [(0.3, 0.5), (0.66, 0)]]),
    "S": (0.64, [[(0.62, 0.86), (0.42, 1.0), (0.14, 0.92), (0.07, 0.7), (0.3, 0.54), (0.55, 0.43), (0.65, 0.2),
                  (0.5, 0.02), (0.22, 0.0), (0.02, 0.14)]]),
    "T": (0.72, [[(0, 1), (0.72, 1)], [(0.36, 1), (0.36, 0)]]),
    "U": (0.7, [[(0.05, 1), (0.05, 0.3), (0.16, 0.05), (0.36, 0), (0.55, 0.05), (0.66, 0.3), (0.66, 1)]]),
    "Y": (0.72, [[(0, 1), (0.36, 0.5), (0.72, 1)], [(0.36, 0.5), (0.36, 0)]]),
    "?": (0.62, [[(0.06, 0.78), (0.18, 0.97), (0.42, 1.0), (0.6, 0.85), (0.55, 0.62), (0.33, 0.45), (0.32, 0.24)],
                 [(0.31, 0.04), (0.33, 0.0)]]),
    "'": (0.2, [[(0.1, 1), (0.07, 0.72)]]),
    " ": (0.45, []),
}


def _adoucir2d(pts, fois=2):
    for _ in range(fois):
        q = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            q += [a * 0.75 + b * 0.25, a * 0.25 + b * 0.75]
        q.append(pts[-1])
        pts = q
    return pts


def ecrire_au_doigt(corps, W, Hp, graine, marge=0.08):
    """Ecriture tracee au doigt dans le sang : lettres irregulieres et penchees, traces des doigts
    dans le sang, beaucoup de sang au debut du trait et presque plus a la fin, bavures.
    Renvoie (couverture 0..1, epaisseur du sang) en (Hp, W), ligne 0 = en bas."""
    rng = np.random.default_rng(graine)
    lignes = corps.split("\n")
    larg_unites = [sum(LETTRES[c][0] + 0.2 for c in l) for l in lignes]
    hl = min(Hp * (1 - 2 * marge) / (len(lignes) + 0.35 * (len(lignes) - 1)),
             W * (1 - 2 * marge) / max(larg_unites))
    bloc = hl * (len(lignes) + 0.35 * (len(lignes) - 1))
    haut_bloc = Hp - (Hp - bloc) / 2 + 0.06 * Hp
    alpha = np.zeros((Hp, W))
    dens = np.zeros((Hp, W))
    r0 = 0.085 * hl
    for li, ligne in enumerate(lignes):
        base = haut_bloc - (li + 1) * hl - li * 0.35 * hl
        x = (W - larg_unites[li] * hl) / 2
        penche_ligne = rng.normal(0, 0.03)
        for car in ligne:
            largeur, traits = LETTRES.get(car, LETTRES[" "])
            ech = hl * (1 + rng.normal(0, 0.07))
            rot = rng.normal(0, 0.07) + penche_ligne
            dy = rng.normal(0, 0.05) * hl + (x - W / 2) * penche_ligne
            cr, sr = math.cos(rot), math.sin(rot)
            for trait in traits:
                pts = [np.array([px * ech, py * ech]) for px, py in trait]
                pts = [np.array([q[0] * cr - q[1] * sr + x, q[0] * sr + q[1] * cr + base + dy]) for q in pts]
                tremble = rng.normal(0, 0.012 * hl, (len(pts), 2))
                pts = _adoucir2d([q + t for q, t in zip(pts, tremble)], 2)
                # points regulierement espaces le long du trait
                seg = [np.linalg.norm(b - a) for a, b in zip(pts[:-1], pts[1:])]
                L = sum(seg) + 1e-6
                pas_ = max(1.0, 0.3 * r0)
                n = max(2, int(L / pas_))
                cum = np.concatenate([[0], np.cumsum(seg)])
                phase = rng.uniform(0, 6.28)
                for i in range(n + 1):
                    sl = L * i / n
                    k = min(int(np.searchsorted(cum, sl, side="right")) - 1, len(pts) - 2)
                    f = (sl - cum[k]) / max(seg[k], 1e-6)
                    c = pts[k] * (1 - f) + pts[k + 1] * f
                    tg = (pts[k + 1] - pts[k]) / max(seg[k], 1e-6)
                    nrm = np.array([-tg[1], tg[0]])
                    u = sl / L
                    r = r0 * (1.15 - 0.35 * u) * (1 + 0.08 * math.sin(sl * 0.05 + phase))
                    opac = 1.0 - 0.4 * u ** 1.5
                    sec = 0.1 + 0.6 * u ** 1.4
                    ph = phase + 0.9 * math.sin(sl * 0.021 + phase) + 0.5 * math.sin(sl * 0.067)
                    x0, x1 = int(max(0, c[0] - r - 2)), int(min(W, c[0] + r + 3))
                    y0, y1 = int(max(0, c[1] - r - 2)), int(min(Hp, c[1] + r + 3))
                    if x1 <= x0 or y1 <= y0:
                        continue
                    Y, X = np.mgrid[y0:y1, x0:x1] + 0.5
                    dx, dy_ = X - c[0], Y - c[1]
                    disque = np.clip(r - np.hypot(dx, dy_) + 0.5, 0, 1)
                    travers = (dx * nrm[0] + dy_ * nrm[1]) / r
                    sillon = 0.5 + 0.5 * np.sin(travers * math.pi * (2.0 + 0.6 * math.sin(sl * 0.013)) + ph)
                    tache = 0.5 + 0.5 * np.sin(dx * 0.31 + dy_ * 0.23 + ph * 2) * np.sin(dx * 0.17 - dy_ * 0.29)
                    v = disque * np.clip(opac - sec * (1 - sillon) * 1.1 - 0.35 * sec * tache, 0, 1)
                    alpha[y0:y1, x0:x1] = np.maximum(alpha[y0:y1, x0:x1], v)
                    dens[y0:y1, x0:x1] += v * 0.08 * (1.3 - u)
            x += (largeur + 0.2) * hl + rng.normal(0, 0.04) * hl
    # bavure : un revers de main qui a frotte une partie du texte
    if rng.random() < 0.7:
        yb = int(rng.uniform(0.3, 0.6) * Hp)
        xb0, xb1 = int(rng.uniform(0.1, 0.4) * W), int(rng.uniform(0.5, 0.9) * W)
        Y, X = np.mgrid[0:Hp, xb0:xb1]
        bande = lisse(0.0, 0.6, 1 - np.abs(Y - yb - 0.08 * (X - xb0)) / (0.12 * Hp))
        frotte = np.clip(0.45 + 0.7 * bruit_lisse(Hp, xb1 - xb0, 7, graine), 0, 1)
        alpha[:, xb0:xb1] = np.maximum(alpha[:, xb0:xb1], bande * frotte * 0.3 * np.linspace(1, 0.15, xb1 - xb0)[None, :])
    return alpha, np.clip(dens, 0, 1)


def dessin_sang(corps, marge=0.08):
    def f(fond, hfond, W, Hp, graine):
        a, dens = ecrire_au_doigt(corps, W, Hp, graine, marge)
        a = coulures_et_gouttes(a, graine)
        var = bruit_lisse(Hp, W, 9, graine + 7)
        rouge = np.stack([0.34 + 0.06 * var, 0.025 + 0.01 * var, 0.035 + 0.01 * var], -1)
        rouge = rouge * (1 - 0.5 * dens[..., None])                     # plus sombre la ou il y a beaucoup de sang
        col = fond * (1 - a[..., None]) + rouge * a[..., None]
        return col, hfond * (1 - a) + (np.max(hfond) + 0.2 + 0.4 * dens) * a
    return f


def dessin_griffures(fond, hfond, W, Hp, graine):
    """Batons comptes griffes dans le mur (par paquets de 5)."""
    rng = np.random.default_rng(graine)
    a = np.zeros((Hp, W))
    Y, X = np.mgrid[0:Hp, 0:W]
    x = 0.05 * W
    while x < 0.95 * W:
        for k in range(4):
            xx = x + k * 0.025 * W + rng.normal(0, 2)
            a = np.maximum(a, np.clip(2.0 - np.abs(X - xx - (Y - Hp / 2) * rng.uniform(-0.08, 0.08)), 0, 1)
                           * ((Y > 0.15 * Hp + rng.normal(0, 4)) & (Y < 0.85 * Hp + rng.normal(0, 4))))
        y0, y1 = 0.25 * Hp, 0.75 * Hp
        pente = (y1 - y0) / (0.1 * W)
        a = np.maximum(a, np.clip(2.0 - np.abs((Y - y0) - (X - x + 0.01 * W) * pente) / math.hypot(1, pente), 0, 1)
                       * ((X > x - 0.01 * W) & (X < x + 0.09 * W)))
        x += 0.16 * W
    col = fond * (1 - a[..., None]) + np.array([0.72, 0.70, 0.64]) * a[..., None]
    return col, hfond - 0.6 * a


def decal(nom, mur, centre, normale, larg, haut, dessin, graine, px_m=330):
    """Inscription sur un mur. Le fond de l'image est exactement la texture du mur a cet endroit :
    le raccord est invisible, on ne voit que ce qui est peint / griffe."""
    n = Vector(normale).normalized()
    droite = Vector((-n.y, n.x, 0))
    W = min(2048, int(larg * px_m) // 4 * 4)
    Hp = min(2048, int(W * haut / larg) // 4 * 4)
    col_m, h_m, force = donnees_texture(mur)
    c = Vector(centre)
    off = ((np.arange(W) + 0.5) / W - 0.5) * larg
    le_long = (c.x + droite.x * off) if abs(n.y) > abs(n.x) else (c.y + droite.y * off)
    z = c.z + ((np.arange(Hp) + 0.5) / Hp - 0.5) * haut
    tu = (np.mod(le_long / 3.0, 1.0) * TEX).astype(int) % TEX
    tv = (np.clip(z / H, 0, 0.9999) * TEX).astype(int)
    col, hh = dessin(col_m[tv][:, tu], h_m[tv][:, tu], W, Hp, graine)
    m = bpy.data.materials.new(nom)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.6
    tc = nt.nodes.new("ShaderNodeTexImage")
    tc.image = enregistrer("hopital_" + nom.lower(), col)
    nt.links.new(tc.outputs["Color"], b.inputs["Base Color"])
    tn = nt.nodes.new("ShaderNodeTexImage")
    tn.image = enregistrer("hopital_" + nom.lower() + "_normal", normale_depuis(hh, force * 0.6), True)
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    p0 = c + n * 0.003
    coins = [p0 - droite * larg / 2 - Vector((0, 0, haut / 2)), p0 + droite * larg / 2 - Vector((0, 0, haut / 2)),
             p0 + droite * larg / 2 + Vector((0, 0, haut / 2)), p0 - droite * larg / 2 + Vector((0, 0, haut / 2))]
    return quad_objet(nom, coins, [(0, 0), (1, 0), (1, 1), (0, 1)], m)


def quad_objet(nom, coins, uvs, m):
    bm = bmesh.new()
    f = bm.faces.new([bm.verts.new(q) for q in coins])
    uv = bm.loops.layers.uv.new("UV")
    for l, t in zip(f.loops, uvs):
        l[uv].uv = t
    me = bpy.data.meshes.new(nom)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    o = bpy.data.objects.new(nom, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def atlas_panneaux(noms):
    """Tous les panneaux des portes dans une seule texture (plaques emaillees, bord, rouille, texte noir)."""
    S, ch = 2048, 120
    col = np.zeros((S, S, 3))
    hh = np.zeros((S, S))
    places = {}
    for idx, nom in enumerate(noms):
        cx, cy = (idx // 17) * 1024, (idx % 17) * ch
        larg_m = 0.15 * len(nom) + 0.35
        cw = min(1024, int(ch * larg_m / 0.3))
        Y, X = np.mgrid[0:ch, 0:cw]
        bord = np.minimum(np.minimum(X, cw - 1 - X), np.minimum(Y, ch - 1 - Y))
        fond = np.array([0.80, 0.78, 0.69]) * (1 + 0.05 * bruit_lisse(ch, cw, 7, idx))[..., None]
        rouille = np.clip((bruit_lisse(ch, cw, 12, idx + 50) - 0.6) * 2, 0, 1) + np.clip(1 - bord / 6.0, 0, 1) * 0.6
        fond = fond * (1 - np.clip(rouille, 0, 1)[..., None]) + np.array([0.38, 0.2, 0.1]) * np.clip(rouille, 0, 1)[..., None]
        filet = (np.abs(bord - 10) < 2.0).astype(float)
        texte_m = masque_texte(nom, cw, ch, marge=0.2)
        encre = np.clip(texte_m + filet, 0, 1)
        col[cy:cy + ch, cx:cx + cw] = fond * (1 - encre[..., None]) + np.array([0.06, 0.06, 0.07]) * encre[..., None]
        hh[cy:cy + ch, cx:cx + cw] = 0.3 * encre - 0.4 * np.clip(rouille, 0, 1)
        places[nom] = ((cx / S, cy / S, (cx + cw) / S, (cy + ch) / S), larg_m)
    m = bpy.data.materials.new("Panneaux")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.35
    tc = nt.nodes.new("ShaderNodeTexImage")
    tc.image = enregistrer("hopital_panneaux", col)
    nt.links.new(tc.outputs["Color"], b.inputs["Base Color"])
    tn = nt.nodes.new("ShaderNodeTexImage")
    tn.image = enregistrer("hopital_panneaux_normal", normale_depuis(hh, 3.0), True)
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    return m, places


def enseigne():
    """Grande enseigne de l'hopital au-dessus de l'entree (texte dans la texture)."""
    W, Hp = 2048, 256
    Y, X = np.mgrid[0:Hp, 0:W]
    fond = np.array([0.14, 0.24, 0.19]) * (1 + 0.1 * bruit_lisse(Hp, W, 9, 61))[..., None]
    ecaille = np.clip((bruit_lisse(Hp, W, 14, 62) - 0.5) * 3, 0, 1)
    fond = fond * (1 - ecaille[..., None]) + np.array([0.40, 0.22, 0.12]) * ecaille[..., None]
    lettres = masque_texte("SAKURA PSYCHIATRIC HOSPITAL", W, Hp, marge=0.16)
    use = np.clip(bruit_lisse(Hp, W, 4, 63) * 0.5 + 0.75, 0, 1)
    col = fond * (1 - (lettres * use)[..., None]) + np.array([0.80, 0.76, 0.64]) * (lettres * use)[..., None]
    coul = np.clip((bruit_lisse(Hp, W, 6, 64) - 0.3), 0, 1) * (Y < Hp * 0.5) * 0.5
    col = col * (1 - coul[..., None]) + np.array([0.3, 0.16, 0.08]) * coul[..., None]
    m = bpy.data.materials.new("Enseigne")
    m.use_nodes = True
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexImage")
    tc.image = enregistrer("hopital_enseigne", col)
    nt.links.new(tc.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    return m


def main_sang(k, centre, normale, haut, echelle, graine):
    """Empreinte de main en sang (paume + 5 doigts) sur un mur."""
    nn = Vector(normale).normalized()
    hh = Vector(haut).normalized()
    cote = hh.cross(nn)
    c = Vector(centre)
    k.tache(c, nn, 0.05 * echelle, "Sang", graine, etire=0.85, sens=cote, pics=0.1)
    for i, (dx, dy, lg) in enumerate(((-0.045, 0.07, 0.07), (-0.015, 0.09, 0.09), (0.015, 0.095, 0.095),
                                      (0.042, 0.085, 0.08), (0.07, 0.0, 0.06))):
        bout = c + (cote * dx + hh * dy) * echelle
        k.tache(bout, nn, 0.013 * echelle, "Sang", graine + i + 1, etire=1.0, pics=0.0)
        k.tache((c + bout) / 2, nn, 0.014 * echelle, "Sang", graine + i + 11, etire=lg / 0.04, sens=(bout - c), pics=0.0)


def ecritures(rng):
    sang = Kit("Taches")
    objs = []
    # panneaux au-dessus des portes : plaque + face avant avec le texte (dans la texture)
    noms = [nom for *_, nom in PORTES if nom]
    mat_p, places = atlas_panneaux(noms)
    for axe, c, centre, w, h, typ, nom in PORTES:
        if not nom:
            continue
        n = Vector((0, 1, 0)) if axe == "x" else Vector((1, 0, 0))
        p = (Vector((centre, c, h + 0.45)) if axe == "x" else Vector((c, centre, h + 0.45)))
        rang = lambda piece: {"Couloir": 0, "Hall": 1, "Dehors": 9}.get(piece, 5)
        cote = 1 if rang(piece_en(*(p + n * 0.5).xy)) <= rang(piece_en(*(p - n * 0.5).xy)) else -1
        nn = n * cote
        q = p + nn * (EP / 2 + 0.015)
        (u0, v0, u1, v1), larg = places[nom]
        sang.place()
        sang.boite(q, (larg, 0.03, 0.3) if axe == "x" else (0.03, larg, 0.3), "Plaque")
        droite = Vector((-nn.y, nn.x, 0))
        f = q + nn * 0.017
        coins = [f - droite * larg / 2 - Vector((0, 0, 0.15)), f + droite * larg / 2 - Vector((0, 0, 0.15)),
                 f + droite * larg / 2 + Vector((0, 0, 0.15)), f - droite * larg / 2 + Vector((0, 0, 0.15))]
        objs.append(quad_objet("Panneau", coins, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], mat_p))
    # l'enseigne de l'hopital au-dessus de l'entree
    sang.boite((32, -EP / 2 - 0.05, 3.45), (9.2, 0.08, 1.15), "Rouille")
    for x in (28.5, 35.5):
        sang.boite((x, -EP / 2 - 0.05, 3.0), (0.06, 0.1, 0.4), "Rouille")
    f = Vector((32, -EP / 2 - 0.095, 3.45))
    objs.append(quad_objet("Enseigne", [f + Vector((-4.5, 0, -0.56)), f + Vector((4.5, 0, -0.56)),
                                        f + Vector((4.5, 0, 0.56)), f + Vector((-4.5, 0, 0.56))],
                           [(0, 0), (1, 0), (1, 1), (0, 1)], enseigne()))
    # inscriptions sur les murs (textures) : sang et griffures
    for i, (nom, mur, centre, n, larg, haut, dessin) in enumerate((
            ("Ecriture_jolie", "Mur", (32.0, 40 - EP / 2, 2.2), (0, -1, 0), 7.0, 2.2, dessin_sang("AM I PRETTY?")),
            ("Ecriture_arrive", "Mur", (16.0, 16 + EP / 2, 1.8), (0, 1, 0), 3.8, 1.3, dessin_sang("SHE IS COMING")),
            ("Ecriture_bouche", "Mur", (54 - EP / 2, 38.0, 1.9), (-1, 0, 0), 2.8, 1.6,
             dessin_sang("DON'T LOOK\nAT HER MOUTH")),
            ("Ecriture_aide", "Mur", (36.0, 26 - EP / 2, 1.6), (0, -1, 0), 2.2, 1.1, dessin_sang("HELP ME")),
            ("Ecriture_capitonnee", "Capitonne", (55.0, 8 + EP / 2, 2.0), (0, 1, 0), 4.8, 2.6,
             dessin_sang("AM I PRETTY?\nAM I PRETTY?\nAM I PRETTY?\nAM I PRETTY?", 0.06)),
            ("Griffures", "Mur", (48.0, 26 - EP / 2, 1.3), (0, -1, 0), 2.6, 0.8, dessin_griffures))):
        objs.append(decal(nom, mur, centre, n, larg, haut, dessin, 400 + i))
    # mains en sang, flaques, trainee (au sol et sur les murs)
    for i, (c, n) in enumerate((((56.3, 16 + EP / 2, 1.4), (0, 1, 0)), ((56.9, 16 + EP / 2, 1.1), (0, 1, 0)),
                                ((32.6, 26 - EP / 2, 1.2), (0, -1, 0)), ((14 + EP / 2, 31.0, 1.5), (1, 0, 0)),
                                ((36.6, 40 - EP / 2, 1.0), (0, -1, 0)))):
        main_sang(sang, c, n, (0, 0, 1), 1.6, 100 + 20 * i)
    for i, (x, y, r) in enumerate(((58.5, 5.2, 0.6), (59.0, 35.0, 0.5), (61.0, 12.0, 0.35), (22.0, 33.0, 0.3),
                                   (5.0, 14.0, 0.25))):
        sang.tache((x, y, 0), (0, 0, 1), r, "Sang", 300 + i)
    x = 45.0
    while x < 61.0:               # trainee de sang dans le couloir jusqu'a la contention
        y = 17.6 + 0.4 * math.sin(x * 0.8) - (0.0 if x < 60 else (x - 60) * 1.2)
        sang.tache((x, y, 0), (0, 0, 1), rng.uniform(0.12, 0.22), "Sang", int(x * 10), etire=2.0, sens=(1, 0, 0))
        x += rng.uniform(0.25, 0.5)
    objs.append(sang.objet())
    return objs


# ---------------------------------------------------------------------------
#  CONSTRUCTION + EXPORT
# ---------------------------------------------------------------------------
def nettoyer():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.curves):
        for d in list(c):
            c.remove(d)
    MATS.clear()


def joindre(objs, nom):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = nom
    o.data.name = nom
    return o


def construire(exporter=True):
    nettoyer()
    random.seed(4)
    rng = random.Random(9)
    mob = Kit("Mobilier")
    murs_sols, plafonds = construire_structure(mob)
    construire_portes(mob)
    meubler(mob, rng)
    allumes = neons(mob, rng)
    mobilier = mob.objet()
    ecr = joindre(ecritures(rng), "Ecritures")
    objs = [murs_sols, plafonds, mobilier, ecr]
    for o in objs:
        tri = sum(len(p.vertices) - 2 for p in o.data.polygons)
        print("MESH", o.name, tri, "triangles")
    if exporter:
        os.makedirs(SORTIE, exist_ok=True)
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs:
            o.select_set(True)
        bpy.ops.export_scene.fbx(filepath=os.path.join(SORTIE, "hopital.fbx"), use_selection=True,
                                 object_types={'MESH'}, path_mode='COPY', embed_textures=True,
                                 mesh_smooth_type='FACE', use_tspace=True)
        bpy.ops.export_scene.gltf(filepath=os.path.join(SORTIE, "hopital.glb"), use_selection=True,
                                  export_format='GLB')
        print("Export OK :", os.path.join(SORTIE, "hopital.fbx"))
    return objs, allumes


if __name__ == "__main__":
    construire()
