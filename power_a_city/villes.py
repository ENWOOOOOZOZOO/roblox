"""Power a City : 10 villes de plus en plus futuristes (une par niveau de ville), generees dans Blender.

Utilisation : mets villes.py dans le meme dossier que batiments.py, ouvre villes.py dans Blender >
onglet "Scripting" > Run Script.
Sortie : dossier "poweracity_villes" de ton dossier utilisateur : Ville_01.fbx ... Ville_10.fbx (+ .glb).

Chaque ville fait 40 x 32 m (X = 40 m, Y = 32 m), pivot au centre, au niveau du sol. Elles ont toutes
la meme emprise : le script Verse remplace la ville par la suivante quand la jauge de la ville est pleine.
  1 Village            maisons a toits colores, chemins de terre, mare, sapins, poteaux en bois
  2 Bourg              routes pavees, eglise a clocher, mairie, fontaine, lampadaires
  3 Petite ville       immeubles en brique, boutiques a auvent, parc, chateau d'eau
  4 Ville              bureaux blancs a fenetres bleues, routes avec marquage
  5 Grande ville       tours de verre, tour-antenne au centre, stade
  6 Metropole          gratte-ciel sombres a gradins, antennes, autoroute surelevee
  7 Eco-ville          tours a terrasses vertes, eoliennes et panneaux sur les toits, monorail, canal
  8 Ville futuriste    tours rondes a anneaux cyan, domes de verre, passerelles, plateformes
  9 Cite neon          tours sombres a neons roses et cyan, panneaux holographiques, voitures volantes
 10 Cite celeste       colonnes de lumiere jaune, plateformes rondes a etages, anneaux blancs, vaisseaux
Toutes les villes ont notre texture studs (sol, routes, murs et facades), sauf les cristaux, le verre et les neons.
Chaque .fbx contient aussi des boites de collision simples (UCX_), sauf pour ce qui flotte dans les airs.
"""
import os
import sys
import math
import random
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import batiments as B                     # outils (boite, cylindre, fusion, matieres, textures...)

SORTIE = os.environ.get("POWERACITY_SORTIE_VILLES", os.path.join(os.path.expanduser("~"), "poweracity_villes"))
APERCU = os.environ.get("POWERACITY_APERCU_VILLES", "")      # dossier pour les images d'apercu (optionnel)
B.TEXTURES = os.path.join(SORTIE, "textures")
LX, LY = 40.0, 32.0                       # taille d'une ville
mat = B.matiere


# ---------------------------------------------------------------------------
#  MATERIAUX DES VILLES
# ---------------------------------------------------------------------------
CHEMIN = mat("Chemin_Terre", (0.75, 0.35, 0.19), rugo=0.9)
PAVE = mat("Pave_Gris", (0.2, 0.2, 0.23), rugo=0.9)
ASPHALTE = mat("Asphalte", (0.03, 0.032, 0.04), rugo=0.9)
TROTTOIR = mat("Trottoir", (0.42, 0.43, 0.47), rugo=0.9)
MARQUAGE = mat("Marquage_Blanc", (0.85, 0.85, 0.85), rugo=0.6, studs=False)
TRONC = mat("Tronc_Bois", (0.12, 0.05, 0.02), rugo=0.9, studs=False)
SAPIN = mat("Sapin_Vert", (0.04, 0.62, 0.02), rugo=0.8)
FEUILLAGE = mat("Feuillage_Rond", (0.08, 0.45, 0.03), rugo=0.8)
BOIS = mat("Poteau_Bois", (0.16, 0.08, 0.04), rugo=0.9, studs=False)
MUR_BLANC = mat("Mur_Blanc", (0.78, 0.78, 0.8), rugo=0.7)
MUR_BEIGE = mat("Mur_Beige", (0.7, 0.55, 0.38), rugo=0.7)
MUR_GRIS = mat("Mur_Gris", (0.35, 0.37, 0.42), rugo=0.7)
TOITS = [mat("Toit_Brun", (0.2, 0.07, 0.03), rugo=0.7), mat("Toit_Gris", (0.12, 0.13, 0.16), rugo=0.7),
         mat("Toit_Bleu", (0.06, 0.15, 0.45), rugo=0.7), mat("Toit_Jaune", (0.75, 0.48, 0.1), rugo=0.7),
         mat("Toit_Neige", (0.8, 0.83, 0.88), rugo=0.7)]
PORTE = mat("Porte_Bois", (0.15, 0.06, 0.02), rugo=0.8, studs=False)
CARREAU = mat("Carreau_Clair", (0.45, 0.65, 0.85), rugo=0.3, studs=False)
BRIQUE_CHEM = mat("Brique_Cheminee", (0.25, 0.04, 0.03), rugo=0.8, studs=False)
LAMPE_CHAUDE = mat("Lampe_Chaude", (1.0, 0.75, 0.35), emission=3.0, studs=False)
METAL_NOIR = mat("Metal_Noir", (0.015, 0.015, 0.02), rugo=0.5, studs=False)
PIERRE_EGLISE = mat("Pierre_Eglise", (0.5, 0.48, 0.44), rugo=0.8)
TOIT_ARDOISE_V = mat("Ardoise_Ville", (0.05, 0.06, 0.09), rugo=0.7)
F_BRIQUE = mat("Facade_Brique", (0.3, 0.07, 0.035), rugo=0.8, motif_tex="fenetres", n=1, tuile=3.0,
               couleur2=(0.5, 0.65, 0.8))
F_BRIQUE_CLAIRE = mat("Facade_Brique_Claire", (0.55, 0.3, 0.15), rugo=0.8, motif_tex="fenetres", n=1, tuile=3.0,
                      couleur2=(0.5, 0.65, 0.8))
TOIT_PLAT = mat("Toit_Plat", (0.2, 0.2, 0.22), rugo=0.8)
AUVENTS = [mat("Auvent_Rouge", (0.6, 0.03, 0.03), studs=False), mat("Auvent_Vert", (0.03, 0.4, 0.08), studs=False),
           mat("Auvent_Bleu", (0.03, 0.15, 0.6), studs=False), mat("Auvent_Jaune", (0.8, 0.55, 0.02), studs=False)]
F_BUREAU = mat("Facade_Bureau", (0.8, 0.82, 0.86), rugo=0.6, motif_tex="fenetres", n=1, tuile=3.0,
               couleur2=(0.03, 0.25, 0.85))
F_VERRE = mat("Facade_Verre", (0.3, 0.38, 0.5), rugo=0.3, motif_tex="fenetres", n=1, tuile=3.0,
              couleur2=(0.05, 0.35, 0.8))
F_SOMBRE = mat("Facade_Sombre", (0.02, 0.04, 0.1), rugo=0.3, motif_tex="fenetres", n=1, tuile=3.0,
               couleur2=(0.1, 0.35, 0.65))
F_ECO = mat("Facade_Eco", (0.82, 0.84, 0.82), rugo=0.6, motif_tex="fenetres", n=1, tuile=3.0,
            couleur2=(0.15, 0.45, 0.4))
F_FUTUR = mat("Facade_Futur", (0.85, 0.88, 0.92), rugo=0.4, motif_tex="fenetres", n=1, tuile=3.0,
              couleur2=(0.0, 0.7, 1.0), emission=0.6)
F_NEON_ROSE = mat("Facade_Neon_Rose", (0.012, 0.012, 0.025), rugo=0.4, motif_tex="fenetres", n=1, tuile=3.0,
                  couleur2=(1.0, 0.1, 0.6), emission=2.0)
F_NEON_CYAN = mat("Facade_Neon_Cyan", (0.012, 0.012, 0.025), rugo=0.4, motif_tex="fenetres", n=1, tuile=3.0,
                  couleur2=(0.0, 0.8, 1.0), emission=2.0)
TOIT_CLAIR = mat("Toit_Clair", (0.6, 0.62, 0.66), rugo=0.7)
VERRE_DOME = mat("Verre_Dome", (0.35, 0.65, 0.9), rugo=0.1, studs=False)
VERT_TERRASSE = mat("Terrasse_Verte", (0.05, 0.5, 0.05), rugo=0.8)
SOL_CLAIR = mat("Sol_Clair", (0.5, 0.52, 0.56), rugo=0.7, studs=True, n=6, aleatoire=True)
SOL_SOMBRE = mat("Sol_Sombre", (0.02, 0.022, 0.03), rugo=0.6, studs=True, n=6, aleatoire=True)
STADE = mat("Stade_Blanc", (0.75, 0.77, 0.8), rugo=0.6)
PELOUSE = mat("Pelouse_Stade", (0.05, 0.45, 0.03), rugo=0.9, studs=False)


# ---------------------------------------------------------------------------
#  OUTILS
# ---------------------------------------------------------------------------
def placer(parts, x, y, angle=0.0, z=0.0, nom="Groupe"):
    """Fusionne des pieces construites autour de (0, 0, 0), puis les tourne et les deplace."""
    o = B.fusion(parts, nom)
    o.rotation_euler = (0, 0, angle)
    o.location = (x, y, z)
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o


def ruban(points, larg, m, z=0.03, nom="Ruban"):
    """Bande plate (chemin, route courbe) qui suit une ligne de points."""
    pts = [Vector((p[0], p[1], 0)) for p in points]
    som = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        n = Vector((-t.y, t.x, 0)) * larg / 2
        som += [tuple(p - n + Vector((0, 0, z))), tuple(p + n + Vector((0, 0, z)))]
    faces = [(2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1) for i in range(len(pts) - 1)]
    return B.maillage(nom, som, faces, m)


def lisse(points, pas=8):
    """Courbe douce (Catmull-Rom) passant par les points."""
    p = [Vector(q) for q in points]
    p = [p[0]] + p + [p[-1]]
    out = []
    for i in range(1, len(p) - 2):
        for k in range(pas):
            t = k / pas
            a, b, c, d = p[i - 1], p[i], p[i + 1], p[i + 2]
            out.append(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t ** 3))
    out.append(p[-2])
    return [(q.x, q.y) for q in out]


def dist_segment(px, py, ax, ay, bx, by):
    abx, aby = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / max(abx * abx + aby * aby, 1e-9)))
    return math.hypot(px - ax - t * abx, py - ay - t * aby)


class Plan:
    """Garde la trace de ce qui est deja pose, pour ne pas mettre deux choses au meme endroit."""

    def __init__(self, graine):
        self.rng = random.Random(graine)
        self.cercles = []
        self.lignes = []           # (points, demi-largeur)

    def libre(self, x, y, r, marge=0.4):
        if abs(x) > LX / 2 - r - 0.3 or abs(y) > LY / 2 - r - 0.3:
            return False
        for cx, cy, cr in self.cercles:
            if math.hypot(x - cx, y - cy) < r + cr + marge:
                return False
        for pts, demi in self.lignes:
            for a, b in zip(pts, pts[1:]):
                if dist_segment(x, y, a[0], a[1], b[0], b[1]) < r + demi + marge:
                    return False
        return True

    def prendre(self, x, y, r):
        self.cercles.append((x, y, r))

    def chercher(self, r, essais=200, zone=None):
        for _ in range(essais):
            if zone:
                x, y = self.rng.uniform(zone[0], zone[1]), self.rng.uniform(zone[2], zone[3])
            else:
                x, y = self.rng.uniform(-LX / 2, LX / 2), self.rng.uniform(-LY / 2, LY / 2)
            if self.libre(x, y, r):
                self.prendre(x, y, r)
                return x, y
        return None


def sol(m):
    return B.boite((LX, LY, 0.3), (0, 0, -0.15), m)


# --- elements de decor -----------------------------------------------------
def sapin(x, y, s=1.0):
    p = [B.cylindre(0.14 * s, 0.14 * s, 0.6 * s, (0, 0, 0.3 * s), TRONC, cotes=6)]
    for k, (r, h, z) in enumerate(((1.0, 1.3, 0.55), (0.78, 1.15, 1.25), (0.52, 1.0, 1.9))):
        p.append(B.cylindre(r * s, 0.05 * s, h * s, (0, 0, (z + h / 2) * s), SAPIN, cotes=6))
    return placer(p, x, y, nom="Sapin")


def arbre_rond(x, y, s=1.0, m=None):
    p = [B.cylindre(0.13 * s, 0.13 * s, 1.2 * s, (0, 0, 0.6 * s), TRONC, cotes=6)]
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.95 * s, location=(0, 0, 1.75 * s))
    p.append(B.finir(bpy.context.active_object, m or FEUILLAGE))
    return placer(p, x, y, nom="Arbre")


def poteau(x, y, angle=0.0):
    p = [B.cylindre(0.07, 0.07, 3.0, (0, 0, 1.5), BOIS, cotes=6),
         B.boite((0.9, 0.08, 0.08), (0, 0, 2.7), BOIS)]
    return placer(p, x, y, angle, nom="Poteau")


def lampadaire(x, y, angle=0.0, lum=LAMPE_CHAUDE, h=3.2, pied=METAL_NOIR):
    p = [B.cylindre(0.07, 0.09, h, (0, 0, h / 2), pied, cotes=8),
         B.boite((0.7, 0.08, 0.08), (0.3, 0, h - 0.05), pied),
         B.boite((0.3, 0.22, 0.1), (0.6, 0, h - 0.15), lum)]
    return placer(p, x, y, angle, nom="Lampadaire")


def mare(x, y, rx, ry, m, graine=1):
    rng = random.Random(graine)
    som = [(x, y, 0.04)]
    k = 11
    for i in range(k):
        a = 2 * math.pi * i / k
        f = rng.uniform(0.8, 1.1)
        som.append((x + rx * f * math.cos(a), y + ry * f * math.sin(a), 0.04))
    faces = [(0, 1 + i, 1 + (i + 1) % k) for i in range(k)]
    return B.maillage("Mare", som, faces, m)


# --- batiments -------------------------------------------------------------
def toit_2pans(w, d, h, rh, m, debord=0.18):
    x0, x1, y0, y1 = -w / 2 - debord, w / 2 + debord, -d / 2 - debord, d / 2 + debord
    som = [(x0, y0, h), (x1, y0, h), (x1, y1, h), (x0, y1, h), (x0, 0, h + rh), (x1, 0, h + rh)]
    faces = [(0, 1, 5, 4), (2, 3, 4, 5), (0, 4, 3), (1, 2, 5), (3, 2, 1, 0)]
    return B.maillage("Toit", som, faces, m)


def maison(x, y, angle, w, d, h, mur, toit, cheminee=True, etage=False):
    p = [B.boite((w, d, h), (0, 0, h / 2), mur), toit_2pans(w, d, h, 0.45 * d, toit)]
    p.append(B.boite((0.5, 0.06, 0.95), (w * 0.22, -d / 2 - 0.03, 0.47), PORTE))
    for fx in (-0.25, 0.42) if w > 2.2 else (-0.25,):
        p.append(B.boite((0.45, 0.06, 0.42), (w * fx, -d / 2 - 0.03, h * 0.55), CARREAU))
    if etage:
        for fx in (-0.25, 0.25):
            p.append(B.boite((0.45, 0.06, 0.42), (w * fx, -d / 2 - 0.03, h * 0.82), CARREAU))
    if cheminee:
        p.append(B.boite((0.32, 0.32, 0.45 * d + 0.4), (w * 0.28, d * 0.18, h + 0.2 * d + 0.2), BRIQUE_CHEM))
    return placer(p, x, y, angle, nom="Maison")


def maison_l(x, y, angle, mur, toit):
    """Maison en L (deux toits)."""
    p = [B.boite((3.0, 1.8, 1.8), (0, 0, 0.9), mur), toit_2pans(3.0, 1.8, 1.8, 0.8, toit)]
    aile = [B.boite((1.6, 2.0, 1.8), (0, 0, 0.9), mur), toit_2pans(1.6, 2.0, 1.8, 0.75, toit)]
    a = placer(aile, 0.7, 1.4, math.pi / 2, nom="Aile")
    p.append(a)
    p.append(B.boite((0.5, 0.06, 0.95), (-0.6, -0.93, 0.47), PORTE))
    p.append(B.boite((0.45, 0.06, 0.42), (0.6, -0.93, 1.0), CARREAU))
    return placer(p, x, y, angle, nom="Maison_L")


def immeuble(x, y, w, d, etages, facade, toit=TOIT_PLAT, angle=0.0, detail=True, rng=None, parapet=True):
    h = etages * 3.0
    p = [B.boite((w, d, h), (0, 0, h / 2), facade)]
    if parapet:
        p.append(B.boite((w + 0.2, d + 0.2, 0.3), (0, 0, h + 0.15), toit))
    else:
        p.append(B.boite((w + 0.1, d + 0.1, 0.15), (0, 0, h + 0.07), toit))
    if detail and rng:
        for _ in range(rng.randint(0, 2)):
            p.append(B.boite((0.8, 0.8, 0.6), (rng.uniform(-w / 3, w / 3), rng.uniform(-d / 3, d / 3), h + 0.6), TOIT_PLAT))
    return placer(p, x, y, angle, nom="Immeuble")


def route(x0, y0, x1, y1, larg=3.0, m=None, marquage=True, trottoir=True):
    """Route droite (horizontale ou verticale) avec trottoirs et marquage au milieu."""
    p = []
    long = math.hypot(x1 - x0, y1 - y0)
    ang = math.atan2(y1 - y0, x1 - x0)
    dz = 0.012 if abs(y1 - y0) < 1e-6 else 0.0          # les routes est-ouest passent par-dessus aux carrefours
    p.append(B.boite((long, larg, 0.04 + dz), (0, 0, 0.02 + dz / 2), m or ASPHALTE))
    if trottoir:
        for s in (-1, 1):
            p.append(B.boite((long, 0.5, 0.12), (0, s * (larg / 2 + 0.25), 0.06), TROTTOIR))
    if marquage:
        n = int(long / 2.0)
        for k in range(n):
            p.append(B.boite((0.9, 0.12, 0.01), (-long / 2 + 1.0 + k * 2.0, 0, 0.045 + dz), MARQUAGE))
    return placer(p, (x0 + x1) / 2, (y0 + y1) / 2, ang, nom="Route")


def grille_routes(plan, xs, ys, larg, m=None, marquage=True, trottoir=True):
    """Routes en quadrillage : xs = positions des routes nord-sud, ys = positions des routes est-ouest."""
    p = []
    for x in xs:
        p.append(route(x, -LY / 2, x, LY / 2, larg, m, marquage, trottoir))
        plan.lignes.append((((x, -LY / 2), (x, LY / 2)), larg / 2 + 0.5))
    for y in ys:
        p.append(route(-LX / 2, y, LX / 2, y, larg, m, marquage, trottoir))
        plan.lignes.append((((-LX / 2, y), (LX / 2, y)), larg / 2 + 0.5))
    return p


def ilots(xs, ys, larg):
    """Rectangles libres entre les routes (x0, x1, y0, y1)."""
    bx = [-LX / 2] + sorted(xs) + [LX / 2]
    by = [-LY / 2] + sorted(ys) + [LY / 2]
    out = []
    for i in range(len(bx) - 1):
        for j in range(len(by) - 1):
            x0 = bx[i] + (larg / 2 + 0.8 if i > 0 else 0.6)
            x1 = bx[i + 1] - (larg / 2 + 0.8 if i < len(bx) - 2 else 0.6)
            y0 = by[j] + (larg / 2 + 0.8 if j > 0 else 0.6)
            y1 = by[j + 1] - (larg / 2 + 0.8 if j < len(by) - 2 else 0.6)
            if x1 - x0 > 1.5 and y1 - y0 > 1.5:
                out.append((x0, x1, y0, y1))
    return out


def couper(a, b, tmin, tmax, rng):
    """Coupe le segment [a, b] en morceaux de tmin a tmax (le dernier morceau prend le reste)."""
    out, x = [], a
    while b - x >= tmin * 0.8:
        w = rng.uniform(tmin, tmax)
        if b - (x + w) < tmin * 0.8:
            w = b - x
        out.append((x, x + w))
        x += w
    return out


def remplir_ilot(ilot, rng, faire, taille_min=3.0, taille_max=6.0, espace=0.8):
    """Decoupe un ilot en parcelles et appelle faire(x, y, w, d) pour chacune."""
    x0, x1, y0, y1 = ilot
    p = []
    for a, b in couper(x0, x1, taille_min, taille_max, rng):
        for c, d in couper(y0, y1, taille_min, taille_max, rng):
            r = faire((a + b) / 2, (c + d) / 2, b - a - espace, d - c - espace)
            if r:
                p += r if isinstance(r, list) else [r]
    return p


# ---------------------------------------------------------------------------
#  LES 10 VILLES
# ---------------------------------------------------------------------------
def ville_1():
    """Village : maisons a toits colores, chemins de terre, mare, sapins, poteaux."""
    plan = Plan(1)
    p = [sol(B.SOL)]
    chemins = [lisse([(0.5, -16), (0.3, -8), (-0.5, -1), (0, 5), (1.0, 16)]),
               lisse([(-20, 2.0), (-12, 3.5), (-5, 1.5), (-0.5, -1)]),
               lisse([(0, 5), (6, 6.5), (12, 4), (20, 3.5)]),
               lisse([(0.3, -8), (5, -6.5), (10, -9), (14, -12)]),
               lisse([(-0.5, -1), (-4, -6), (-8, -9)]),
               lisse([(6, 6.5), (7, 11), (5, 16)])]
    for c in chemins:
        p.append(ruban(c, 1.6, CHEMIN))
        plan.lignes.append((c, 0.8))
    p.append(mare(-11, -8, 5.5, 4.0, B.EAU))
    plan.prendre(-11, -8, 5.0)
    rng = plan.rng
    for k in range(20):
        pos = plan.chercher(1.8)
        if not pos:
            continue
        ang = rng.choice([0, math.pi / 2, math.pi, -math.pi / 2]) + rng.uniform(-0.15, 0.15)
        mur = rng.choice([MUR_BLANC, MUR_BLANC, MUR_BEIGE, MUR_GRIS])
        toit = rng.choice(TOITS)
        if k % 6 == 0:
            p.append(maison_l(pos[0], pos[1], ang, mur, toit))
        else:
            p.append(maison(pos[0], pos[1], ang, rng.uniform(2.0, 2.8), rng.uniform(1.7, 2.2), 1.8, mur, toit,
                            cheminee=rng.random() < 0.7))
    for _ in range(40):
        pos = plan.chercher(0.9, essais=60)
        if pos:
            p.append(sapin(pos[0], pos[1], rng.uniform(0.8, 1.3)))
    for c in chemins[:3]:
        for q in c[2::6]:
            if abs(q[0]) < LX / 2 - 1 and abs(q[1]) < LY / 2 - 1:
                p.append(poteau(q[0] + 1.1, q[1], rng.uniform(0, 3)))
    return p, []


def eglise(x, y, angle):
    p = [B.boite((3.2, 6.0, 3.2), (0, 0, 1.6), PIERRE_EGLISE), toit_2pans_y(3.2, 6.0, 3.2, 1.6, TOIT_ARDOISE_V)]
    p.append(B.boite((1.8, 1.8, 6.5), (0, -3.6, 3.25), PIERRE_EGLISE))
    p.append(B.tronc_pyramide(0, -3.6, 6.5, 9.5, 2.0, 2.0, 0.1, 0.1, TOIT_ARDOISE_V))
    p.append(B.boite((0.9, 0.06, 1.6), (0, -4.53, 0.8), PORTE))
    p.append(B.cylindre(0.35, 0.35, 0.06, (0, -4.53, 5.2), MUR_BLANC, cotes=12, rot=(math.radians(90), 0, 0)))
    for yy in (-1.5, 0.5, 2.3):
        for s in (-1, 1):
            p.append(B.boite((0.06, 0.6, 1.3), (s * 1.63, yy, 1.9), CARREAU))
    return placer(p, x, y, angle, nom="Eglise")


def toit_2pans_y(w, d, h, rh, m, debord=0.18):
    """Toit a deux pentes dont le faitage suit l'axe Y."""
    x0, x1, y0, y1 = -w / 2 - debord, w / 2 + debord, -d / 2 - debord, d / 2 + debord
    som = [(x0, y0, h), (x1, y0, h), (x1, y1, h), (x0, y1, h), (0, y0, h + rh), (0, y1, h + rh)]
    faces = [(0, 4, 5, 3), (1, 2, 5, 4), (0, 1, 4), (2, 3, 5), (3, 2, 1, 0)]
    return B.maillage("Toit", som, faces, m)


def ville_2():
    """Bourg : routes pavees, eglise, mairie, fontaine, lampadaires, maisons a etage."""
    plan = Plan(2)
    p = [sol(B.SOL)]
    xs, ys = [-6.0, 9.0], [-3.0]
    p += grille_routes(plan, xs, ys, 2.6, PAVE, marquage=False, trottoir=False)
    # place du village avec fontaine
    p.append(B.boite((7.0, 6.0, 0.05), (1.5, 2.5, 0.025), PAVE))
    plan.prendre(1.5, 2.5, 3.2)
    p.append(B.cylindre(1.3, 1.3, 0.5, (1.5, 2.5, 0.25), PIERRE_EGLISE, cotes=12))
    p.append(B.cylindre(1.1, 1.1, 0.05, (1.5, 2.5, 0.48), B.EAU, cotes=12))
    p.append(B.cylindre(0.2, 0.2, 1.4, (1.5, 2.5, 0.9), PIERRE_EGLISE, cotes=8))
    p.append(B.cylindre(0.5, 0.3, 0.2, (1.5, 2.5, 1.65), PIERRE_EGLISE, cotes=8))
    p.append(eglise(-13.0, 8.5, 0))
    plan.prendre(-13.0, 8.5, 4.2)
    # mairie
    m = [B.boite((6.0, 3.6, 3.6), (0, 0, 1.8), MUR_BEIGE), toit_2pans(6.0, 3.6, 3.6, 1.4, TOIT_ARDOISE_V),
         B.boite((1.0, 1.0, 1.4), (0, 0, 4.9), MUR_BLANC), B.tronc_pyramide(0, 0, 5.6, 6.4, 1.2, 1.2, 0.1, 0.1, TOIT_ARDOISE_V),
         B.boite((1.0, 0.06, 1.6), (0, -1.83, 0.8), PORTE)]
    for fx in (-2.2, -1.2, 1.2, 2.2):
        m.append(B.boite((0.5, 0.06, 0.8), (fx, -1.83, 1.4), CARREAU))
        m.append(B.boite((0.5, 0.06, 0.8), (fx, -1.83, 2.8), CARREAU))
    p.append(placer(m, 2.0, 9.5, 0, nom="Mairie"))
    plan.prendre(2.0, 9.5, 3.8)
    rng = plan.rng
    for k in range(26):
        pos = plan.chercher(1.9)
        if not pos:
            continue
        ang = rng.choice([0, math.pi / 2, math.pi, -math.pi / 2])
        etage = rng.random() < 0.5
        p.append(maison(pos[0], pos[1], ang, rng.uniform(2.2, 3.0), rng.uniform(1.8, 2.3), 3.0 if etage else 1.9,
                        rng.choice([MUR_BLANC, MUR_BEIGE, MUR_GRIS]), rng.choice(TOITS[:4]), etage=etage))
    for x in xs:
        for yy in range(-14, 16, 7):
            p.append(lampadaire(x + 1.8, yy, math.pi))
    for _ in range(26):
        pos = plan.chercher(0.9, essais=60)
        if pos:
            p.append(sapin(*pos, rng.uniform(0.8, 1.2)) if rng.random() < 0.5 else arbre_rond(*pos, rng.uniform(0.8, 1.1)))
    return p, []


def ville_3():
    """Petite ville : immeubles en brique, boutiques a auvent, parc, chateau d'eau."""
    plan = Plan(3)
    p = [sol(B.SOL)]
    xs, ys = [-8.0, 6.0], [-4.0, 7.0]
    larg = 3.0
    p += grille_routes(plan, xs, ys, larg)
    rng = plan.rng
    ilots_ = ilots(xs, ys, larg)
    parc = max(ilots_, key=lambda r: (r[1] - r[0]) * (r[3] - r[2]) if r[0] > -8 and r[1] < 6 else 0)

    def batir(x, y, w, d):
        if rng.random() < 0.25:
            return maison(x, y, rng.choice([0, math.pi]), min(w, 2.8), min(d, 2.2), 1.9, MUR_BLANC, rng.choice(TOITS[:3]))
        et = rng.randint(2, 4)
        o = [immeuble(x, y, w, d, et, rng.choice([F_BRIQUE, F_BRIQUE_CLAIRE]), rng=rng)]
        a = [B.boite((w * 0.9, 0.8, 0.12), (0, -d / 2 - 0.4, 2.4), rng.choice(AUVENTS))]
        o.append(placer(a, x, y, nom="Auvent"))
        return o

    for il in ilots_:
        if il == parc:
            cx, cy = (il[0] + il[1]) / 2, (il[2] + il[3]) / 2
            p.append(mare(cx, cy, (il[1] - il[0]) / 4, (il[3] - il[2]) / 4, B.EAU, graine=3))
            for _ in range(10):
                x, y = rng.uniform(il[0] + 0.8, il[1] - 0.8), rng.uniform(il[2] + 0.8, il[3] - 0.8)
                if math.hypot((x - cx) / ((il[1] - il[0]) / 3), (y - cy) / ((il[3] - il[2]) / 3)) > 1:
                    p.append(arbre_rond(x, y, rng.uniform(0.8, 1.1)))
            continue
        p += remplir_ilot(il, rng, batir, 3.0, 5.0)
    # chateau d'eau
    cx, cy = 15.5, -11.0
    t = [B.cylindre(1.6, 1.6, 2.0, (0, 0, 7.5), MUR_GRIS, cotes=12), B.tronc_pyramide(0, 0, 8.5, 9.3, 2.2, 2.2, 0.2, 0.2, TOIT_PLAT)]
    for a in range(4):
        ang = math.pi / 4 + a * math.pi / 2
        t.append(B.cylindre(0.12, 0.12, 6.6, (1.1 * math.cos(ang), 1.1 * math.sin(ang), 3.3), METAL_NOIR, cotes=6))
    p.append(placer(t, cx, cy, nom="Chateau_Eau"))
    for x in xs:
        for yy in range(-14, 16, 6):
            p.append(lampadaire(x + larg / 2 + 0.3, yy, math.pi))
    return p, []


def ville_4():
    """Ville : bureaux blancs a fenetres bleues, maisons en bordure, routes avec marquage."""
    plan = Plan(4)
    p = [sol(B.SOL)]
    xs, ys = [-10.0, 0.0, 10.0], [-5.0, 6.0]
    larg = 3.2
    p += grille_routes(plan, xs, ys, larg)
    rng = plan.rng

    def batir(x, y, w, d):
        bord = abs(x) > 15 or abs(y) > 12
        if bord and rng.random() < 0.6:
            return maison(x, y, rng.choice([0, math.pi]), min(w, 2.8), min(d, 2.2), 1.9, MUR_BLANC, TOITS[0])
        return immeuble(x, y, w, d, rng.randint(3, 6), F_BUREAU, TOIT_CLAIR, rng=rng)

    for il in ilots(xs, ys, larg):
        p += remplir_ilot(il, rng, batir, 3.5, 6.0)
    for x in xs:
        for yy in range(-14, 16, 6):
            p.append(lampadaire(x + larg / 2 + 0.3, yy, math.pi, h=3.6))
    return p, []


def tour_antenne(x, y):
    p = [B.cylindre(1.4, 0.9, 2.0, (0, 0, 1.0), MUR_GRIS, cotes=8), B.cylindre(0.55, 0.45, 18.0, (0, 0, 11.0), MUR_BLANC, cotes=8),
         B.cylindre(1.6, 1.6, 1.4, (0, 0, 16.0), F_VERRE, cotes=12), B.cylindre(1.7, 1.2, 0.4, (0, 0, 16.9), TOIT_CLAIR, cotes=12),
         B.cylindre(0.12, 0.03, 6.0, (0, 0, 23.0), METAL_NOIR, cotes=6),
         B.cylindre(0.18, 0.18, 0.3, (0, 0, 20.5), B.ROUGE_LUM, cotes=8)]
    return placer(p, x, y, nom="Tour_Antenne")


def stade(x, y):
    p = []
    som, faces = [], []
    k = 24
    for i in range(k):
        a = 2 * math.pi * i / k
        c, s_ = math.cos(a), math.sin(a)
        som += [(4.2 * c, 3.0 * s_, 0), (4.2 * c, 3.0 * s_, 2.2), (2.9 * c, 1.8 * s_, 0.6), (2.9 * c, 1.8 * s_, 0)]
    for i in range(k):
        j = (i + 1) % k
        for c in range(4):
            a0, a1 = 4 * i + c, 4 * i + (c + 1) % 4
            b0, b1 = 4 * j + c, 4 * j + (c + 1) % 4
            faces.append((a0, b0, b1, a1))
    p.append(B.maillage("Tribunes", som, faces, STADE))
    pel = B.cylindre(2.95, 2.95, 0.06, (0, 0, 0.03), PELOUSE, cotes=24)
    pel.scale = (1.0, 0.62, 1)
    p.append(B.finir(pel, PELOUSE))
    return placer(p, x, y, nom="Stade")


def ville_5():
    """Grande ville : tours de verre, tour-antenne au centre, stade."""
    plan = Plan(5)
    p = [sol(TROTTOIR)]
    xs, ys = [-9.0, 3.0, 12.0], [-4.0, 7.0]
    larg = 3.4
    p += grille_routes(plan, xs, ys, larg)
    rng = plan.rng
    p.append(tour_antenne(-1.5, 1.5))
    plan.prendre(-1.5, 1.5, 2.6)
    p.append(stade(-15.0, -10.0))
    plan.prendre(-15.0, -10.0, 4.6)

    def batir(x, y, w, d):
        if not plan.libre(x, y, min(w, d) / 2, marge=0.2):
            return None
        plan.prendre(x, y, min(w, d) / 2)
        if rng.random() < 0.15:
            return arbre_rond(x, y, 1.0)
        return immeuble(x, y, w, d, rng.randint(4, 9), rng.choice([F_VERRE, F_BUREAU]), TOIT_CLAIR, rng=rng)

    for il in ilots(xs, ys, larg):
        p += remplir_ilot(il, rng, batir, 4.0, 6.5)
    for x in xs:
        for yy in range(-14, 16, 6):
            p.append(lampadaire(x + larg / 2 + 0.3, yy, math.pi, h=4.0))
    return p, []


def gratte_ciel(x, y, w, d, etages, facade, rng):
    """Gratte-ciel a gradins (le haut se retrecit), antenne au sommet."""
    p = []
    z = 0.0
    paliers = rng.randint(2, 3)
    for k in range(paliers):
        e = max(2, etages // paliers + (etages % paliers if k == 0 else 0))
        h = e * 3.0
        p.append(B.boite((w, d, h), (0, 0, z + h / 2), facade))
        p.append(B.boite((w + 0.15, d + 0.15, 0.2), (0, 0, z + h + 0.1), TOIT_PLAT))
        z += h + 0.2
        w, d = w * 0.75, d * 0.75
    p.append(B.cylindre(0.1, 0.03, 4.0, (0, 0, z + 2.0), METAL_NOIR, cotes=6))
    p.append(B.cylindre(0.15, 0.15, 0.25, (0, 0, z + 3.6), B.ROUGE_LUM, cotes=8))
    return placer(p, x, y, nom="Gratte_Ciel")


def autoroute(y, z=4.5):
    p = [B.boite((LX, 4.0, 0.5), (0, y, z), MUR_GRIS)]
    for s in (-1, 1):
        p.append(B.boite((LX, 0.2, 0.6), (0, y + s * 1.9, z + 0.55), TROTTOIR))
    for x in range(-18, 20, 6):
        p.append(B.boite((1.0, 1.4, z - 0.25), (x, y, (z - 0.25) / 2), MUR_GRIS))
    for k in range(20):
        p.append(B.boite((0.9, 0.12, 0.02), (-19 + k * 2.0, y, z + 0.26), MARQUAGE))
    return p


def ville_6():
    """Metropole : gratte-ciel sombres a gradins, antennes, autoroute surelevee."""
    plan = Plan(6)
    p = [sol(TROTTOIR)]
    xs, ys = [-7.0, 7.0], [-1.0]
    larg = 3.6
    p += grille_routes(plan, xs, ys, larg)
    p += autoroute(-13.2)
    plan.lignes.append((((-LX / 2, -13.2), (LX / 2, -13.2)), 2.4))
    rng = plan.rng

    def batir(x, y, w, d):
        return gratte_ciel(x, y, w, d, rng.randint(5, 11), rng.choice([F_SOMBRE, F_SOMBRE, F_VERRE]), rng)

    for il in ilots(xs, ys, larg):
        il = (il[0], il[1], max(il[2], -10.8), il[3])
        if il[3] - il[2] > 3:
            p += remplir_ilot(il, rng, batir, 4.5, 7.0, espace=1.2)
    for x in xs:
        for yy in range(-9, 16, 6):
            p.append(lampadaire(x + larg / 2 + 0.3, yy, math.pi, h=4.2, lum=B.BLANC_LUM))
    return p, []


def eolienne_toit(x, y, z):
    p = [B.cylindre(0.08, 0.08, 1.6, (0, 0, 0.8), MUR_BLANC, cotes=6), B.boite((0.4, 0.2, 0.2), (0.1, 0, 1.6), MUR_BLANC)]
    for k in range(3):
        a = 2 * math.pi * k / 3
        p.append(B.boite((0.04, 0.12, 0.9), (0.32, 0.45 * math.sin(a), 1.6 + 0.45 * math.cos(a)), MUR_BLANC,
                         rot=(-a, 0, 0)))
    return placer(p, x, y, z=z, nom="Eolienne_Toit")


def monorail(points, z, rng=None, rames=2):
    """Voie de monorail surelevee (poutre sur piliers) + une rame."""
    pts = lisse(points, 6)
    p = []
    for a, b in zip(pts, pts[1:]):
        a3, b3 = Vector((a[0], a[1], z)), Vector((b[0], b[1], z))
        p.append(B.tube([a3, b3], [0.3, 0.3], TROTTOIR, "Voie", cotes=4))
    for q in pts[::5]:
        p.append(B.cylindre(0.25, 0.3, z, (q[0], q[1], z / 2), TROTTOIR, cotes=8))
    for k in range(rames):
        i = (k * len(pts) // rames + 3) % (len(pts) - 1)
        a, b = Vector((*pts[i], z + 0.75)), Vector((*pts[i + 1], z + 0.75))
        d = (b - a).normalized()
        p.append(B.tube([a - d * 1.8, a + d * 1.8], [0.55, 0.55], MUR_BLANC, "Rame", cotes=8))
        p.append(B.tube([a - d * 1.0, a + d * 1.0], [0.57, 0.57], VERT_TERRASSE, "Bande", cotes=8))
    return p


def ville_7():
    """Eco-ville : tours a terrasses vertes, eoliennes et panneaux sur les toits, monorail, canal."""
    plan = Plan(7)
    p = [sol(B.SOL)]
    # canal
    canal = lisse([(-20, -9), (-8, -10.5), (4, -8.5), (20, -10)])
    p.append(ruban(canal, 3.2, B.EAU, z=0.04))
    for s in (-1, 1):
        bord = [(q[0], q[1] + s * 1.75) for q in canal]
        p.append(ruban(bord, 0.3, TROTTOIR, z=0.1))
    plan.lignes.append((canal, 2.2))
    xs, ys = [-6.0, 8.0], [1.5]
    larg = 3.2
    p += grille_routes(plan, xs, ys, larg)
    rng = plan.rng

    def batir(x, y, w, d):
        if not plan.libre(x, y, min(w, d) / 2, marge=0.1):
            return None
        plan.prendre(x, y, min(w, d) / 2)
        if rng.random() < 0.2:
            return arbre_rond(x, y, 1.1)
        o = []
        et = rng.randint(4, 10)
        h = et * 3.0
        t = [B.boite((w * 0.8, d * 0.8, h), (0, 0, h / 2), F_ECO)]
        for z in range(3, et, 3):
            t.append(B.boite((w, d, 0.25), (0, 0, z * 3.0), VERT_TERRASSE))
            for sx in (-1, 1):
                t.append(B.boite((0.5, 0.5, 0.4), (sx * w * 0.42, -d * 0.42, z * 3.0 + 0.32), FEUILLAGE))
        t.append(B.boite((w * 0.85, d * 0.85, 0.25), (0, 0, h + 0.12), VERT_TERRASSE))
        o.append(placer(t, x, y, nom="Tour_Eco"))
        if rng.random() < 0.5:
            o.append(eolienne_toit(x, y, h + 0.25))
        else:
            sp = [B.boite((0.9, 0.6, 0.05), (dx, 0, 0.35), B.CELLULE, rot=(math.radians(25), 0, 0)) for dx in (-0.5, 0.5)]
            o.append(placer(sp, x, y, z=h + 0.25, nom="Solaire_Toit"))
        return o

    for il in ilots(xs, ys, larg):
        p += remplir_ilot(il, rng, batir, 4.0, 6.0)
    p += monorail([(-18, 13), (-6, 14.5), (8, 13.5), (18, 14.5)], 7.0, rng)
    return p, []


def tour_ronde(x, y, r, h, facade, anneau_mat):
    p = [B.cylindre(r, r, h, (0, 0, h / 2), facade, cotes=16)]
    for z in np.arange(6.0, h, 6.0):
        p.append(B.anneau(r + 0.05, 0.12, (0, 0, float(z)), anneau_mat, seg=24, segm=4))
    p.append(B.dome(r, (0, 0, h), VERRE_DOME, ech=(1, 1, 0.5), segments=16))
    return placer(p, x, y, nom="Tour_Ronde")


def ville_8():
    """Ville futuriste : tours rondes a anneaux cyan, domes de verre, passerelles, plateformes."""
    plan = Plan(8)
    p = [sol(SOL_CLAIR)]
    rng = plan.rng
    # avenues lumineuses
    for x in (-8.0, 8.0):
        p.append(B.boite((0.25, LY, 0.03), (x, 0, 0.015), B.CYAN))
        plan.lignes.append((((x, -LY / 2), (x, LY / 2)), 1.5))
    p.append(B.boite((LX, 0.25, 0.03), (0, 0, 0.015), B.CYAN))
    plan.lignes.append((((-LX / 2, 0), (LX / 2, 0)), 1.5))
    tours = []
    for _ in range(14):
        r = rng.uniform(1.6, 2.6)
        pos = plan.chercher(r + 0.5)
        if pos:
            h = rng.uniform(10, 24)
            p.append(tour_ronde(pos[0], pos[1], r, h, F_FUTUR, B.CYAN))
            tours.append((pos[0], pos[1], r, h))
    for _ in range(5):
        r = rng.uniform(2.0, 3.0)
        pos = plan.chercher(r)
        if pos:
            p.append(B.dome(r, (pos[0], pos[1], 0), VERRE_DOME, segments=16))
            p.append(B.anneau(r, 0.1, (pos[0], pos[1], 0.1), B.CYAN, seg=24, segm=4))
    # passerelles entre les tours proches
    tours.sort(key=lambda t: t[0])
    for a, b in zip(tours, tours[1:]):
        dist = math.hypot(a[0] - b[0], a[1] - b[1])
        if dist < 12:
            z = min(a[3], b[3]) * 0.6
            p.append(B.tube([(a[0], a[1], z), (b[0], b[1], z)], [0.35, 0.35], VERRE_DOME, "Passerelle", cotes=8))
    # plateformes d'atterrissage
    for _ in range(3):
        pos = plan.chercher(1.6)
        if pos:
            p.append(B.cylindre(1.5, 1.5, 0.3, (pos[0], pos[1], 2.2), MUR_BLANC, cotes=16))
            p.append(B.cylindre(0.25, 0.25, 2.1, (pos[0], pos[1], 1.05), MUR_BLANC, cotes=8))
            p.append(B.anneau(1.45, 0.06, (pos[0], pos[1], 2.37), B.CYAN, seg=24, segm=4))
    for _ in range(14):
        pos = plan.chercher(0.8, essais=60)
        if pos:
            p.append(arbre_rond(*pos, 0.8, m=VERT_TERRASSE))
    return p, []


def voiture_volante(x, y, z, angle, lum):
    p = [B.sphere(0.5, (0, 0, 0), METAL_NOIR, ech=(1.8, 0.9, 0.55)), B.boite((0.15, 0.7, 0.12), (-0.85, 0, 0), lum)]
    return placer(p, x, y, angle, z=z, nom="Voiture")


def ville_9():
    """Cite neon : tours sombres a neons roses et cyan, panneaux holographiques, voitures volantes."""
    plan = Plan(9)
    p = [sol(SOL_SOMBRE)]
    rng = plan.rng
    xs, ys = [-7.0, 7.0], [0.0]
    larg = 3.6
    for x in xs:
        p.append(route(x, -LY / 2, x, LY / 2, larg, ASPHALTE, marquage=False, trottoir=False))
        p.append(B.boite((0.15, LY, 0.02), (x - 1.4, 0, 0.05), B.CYAN))
        p.append(B.boite((0.15, LY, 0.02), (x + 1.4, 0, 0.05), B.ROSE_LUM))
        plan.lignes.append((((x, -LY / 2), (x, LY / 2)), larg / 2 + 0.4))
    for y in ys:
        p.append(route(-LX / 2, y, LX / 2, y, larg, ASPHALTE, marquage=False, trottoir=False))
        p.append(B.boite((LX, 0.15, 0.02), (0, y, 0.05), B.CYAN))
        plan.lignes.append((((-LX / 2, y), (LX / 2, y)), larg / 2 + 0.4))
    neons = [B.ROSE_LUM, B.CYAN, B.VIOLET_LUM]

    def batir(x, y, w, d):
        et = rng.randint(4, 11)
        h = et * 3.0
        fac = rng.choice([F_NEON_ROSE, F_NEON_CYAN])
        t = [B.boite((w, d, h), (0, 0, h / 2), fac), B.boite((w + 0.2, d + 0.2, 0.3), (0, 0, h + 0.15), METAL_NOIR)]
        n = rng.choice(neons)
        for sx in (-1, 1):                                                   # neons verticaux aux coins
            t.append(B.boite((0.12, 0.12, h), (sx * (w / 2 + 0.03), -d / 2 - 0.03, h / 2), n))
        if rng.random() < 0.7:                                              # panneau holographique
            zb = rng.uniform(4, max(5, h - 4))
            t.append(B.boite((w * 0.7, 0.08, 1.6), (0, -d / 2 - 0.25, zb), rng.choice(neons)))
        t.append(B.cylindre(0.08, 0.02, 3.0, (w * 0.25, d * 0.2, h + 1.6), METAL_NOIR, cotes=6))
        return placer(t, x, y, nom="Tour_Neon")

    for il in ilots(xs, ys, larg):
        p += remplir_ilot(il, rng, batir, 4.0, 6.5, espace=1.0)
    air = []
    for _ in range(12):
        x, y = rng.uniform(-18, 18), rng.uniform(-14, 14)
        air.append(voiture_volante(x, y, rng.uniform(8, 22), rng.uniform(0, 2 * math.pi), rng.choice(neons)))
    return p, air


JAUNE_NEON = mat("Jaune_Neon", (1.0, 0.75, 0.0), emission=3.0, studs=False)
NAVY_PLAT = mat("Plateforme_Nuit", (0.008, 0.02, 0.07), rugo=0.5)
BLANC_ANNEAU = mat("Anneau_Blanc", (0.8, 0.84, 0.9), rugo=0.4)


def plateforme(r, rng):
    """Plateforme ronde bleu nuit, bord a points lumineux jaunes, petites constructions dessus.
    Construite autour de (0, 0, 0) = centre du dessus."""
    p = [B.cylindre(r, r, 0.35, (0, 0, -0.175), NAVY_PLAT, cotes=16),
         B.cylindre(r * 0.45, 0.25, 1.0, (0, 0, -0.85), NAVY_PLAT, cotes=8),
         B.anneau(r * 0.62, 0.05, (0, 0, 0.03), JAUNE_NEON, seg=24, segm=4)]
    n = int(r * 6)
    for k in range(n):
        a = 2 * math.pi * k / n
        p.append(B.boite((0.16, 0.16, 0.16), (r * math.cos(a), r * math.sin(a), 0.03), JAUNE_NEON))
    for _ in range(rng.randint(1, 3)):
        a, d = rng.uniform(0, 2 * math.pi), rng.uniform(0.5, r * 0.55)
        x, y = d * math.cos(a), d * math.sin(a)
        if rng.random() < 0.5:
            w = rng.uniform(0.5, 0.9)
            p.append(B.boite((w, w, rng.uniform(0.4, 1.0)), (x, y, 0.35), NAVY_PLAT))
        else:
            p.append(B.dome(rng.uniform(0.35, 0.6), (x, y, 0), NAVY_PLAT, segments=10))
    return p


def cerceau(x, y, z, R, rng):
    """Anneau octogonal blanc qui flotte."""
    o = B.anneau(R, 0.38, (0, 0, 0), BLANC_ANNEAU, seg=8, segm=4)
    o.scale = (1, 1, 0.55)
    B.finir(o, BLANC_ANNEAU)
    o.rotation_euler = (rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), math.pi / 8)
    return placer([o], x, y, z=z, nom="Cerceau")


def vaisseau(x, y, z, angle):
    p = [B.sphere(0.6, (0, 0, 0), NAVY_PLAT, ech=(1.7, 1.7, 0.4)), B.dome(0.4, (0, 0, 0.12), NAVY_PLAT, segments=10),
         B.anneau(0.95, 0.05, (0, 0, 0), JAUNE_NEON, seg=16, segm=4)]
    return placer(p, x, y, angle, z=z, nom="Vaisseau")


def ville_10():
    """Cite celeste : colonnes de lumiere jaune, plateformes rondes a etages, anneaux blancs, vaisseaux."""
    plan = Plan(10)
    p = [sol(SOL_SOMBRE)]
    rng = plan.rng
    for x in range(-16, 17, 8):                                                # lignes jaunes au sol
        p.append(B.boite((0.12, LY, 0.02), (x, 0, 0.01), JAUNE_NEON))
    for y in range(-12, 13, 8):
        p.append(B.boite((LX, 0.12, 0.02), (0, y, 0.01), JAUNE_NEON))
    air = []
    colonnes = []
    for _ in range(16):
        pos = plan.chercher(2.6, essais=300)
        if not pos:
            continue
        x, y = pos
        h = rng.uniform(22, 42)
        colonnes.append((x, y, h))
        p.append(B.cylindre(0.7, 0.9, 0.5, (x, y, 0.25), NAVY_PLAT, cotes=8))      # socle
        p.append(B.cylindre(0.18, 0.18, h, (x, y, h / 2), JAUNE_NEON, cotes=8))   # colonne de lumiere
        z = rng.uniform(4, 8)
        while z < h - 1.5:
            air.append(placer(plateforme(rng.uniform(1.8, 3.2), rng), x, y, rng.uniform(0, math.pi), z=z, nom="Plateforme"))
            z += rng.uniform(5, 9)
    for _ in range(30):
        air.append(cerceau(rng.uniform(-18, 18), rng.uniform(-14, 14), rng.uniform(6, 42), rng.uniform(1.6, 3.0), rng))
    for _ in range(14):
        air.append(vaisseau(rng.uniform(-18, 18), rng.uniform(-14, 14), rng.uniform(5, 38), rng.uniform(0, 6.3)))
    for _ in range(4):                                                         # domes au sol
        pos = plan.chercher(2.2)
        if pos:
            p.append(B.dome(2.0, (pos[0], pos[1], 0), NAVY_PLAT, segments=16))
            p.append(B.anneau(2.0, 0.08, (pos[0], pos[1], 0.08), JAUNE_NEON, seg=24, segm=4))
    return p, air


VILLES = [ville_1, ville_2, ville_3, ville_4, ville_5, ville_6, ville_7, ville_8, ville_9, ville_10]


# ---------------------------------------------------------------------------
def rendre(o, chemin):
    sc = bpy.context.scene
    if not sc.camera:
        w = bpy.data.worlds.new("Ciel")
        w.use_nodes = True
        w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.6, 0.78, 0.95, 1)
        w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.7
        sc.world = w
        bpy.ops.object.light_add(type='SUN', rotation=(math.radians(45), math.radians(10), math.radians(-35)))
        bpy.context.active_object.data.energy = 3.0
        bpy.ops.object.camera_add(location=(0, -58, 46))
        cam = bpy.context.active_object
        cam.rotation_euler = (Vector((0, -2, 5)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens = 27
        sc.camera = cam
        sc.view_settings.view_transform = 'Standard'
        sc.render.engine = 'CYCLES'
        sc.cycles.samples = 32
        sc.cycles.device = 'CPU'
        sc.render.resolution_x, sc.render.resolution_y = 960, 640
    for x in sc.objects:
        if x.type == 'MESH':
            x.hide_render = x is not o
    sc.render.filepath = chemin
    bpy.ops.render.render(write_still=True)


def main():
    os.makedirs(SORTIE, exist_ok=True)
    choix = [int(v) for v in os.environ.get("POWERACITY_VILLES", "").split(",") if v.strip()]
    for k, faire in enumerate(VILLES, start=1):
        if choix and k not in choix:
            continue
        nom = "Ville_%02d" % k
        parts, air = faire()
        o = B.fusion(parts, nom)
        ucx = B.collisions(o, pas=1.0, max_boites=120)
        if air:
            v = B.fusion(air, nom + "_Air")
            bpy.ops.object.select_all(action='DESELECT')
            o.select_set(True)
            v.select_set(True)
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.join()
            o.name = o.data.name = nom
        tri = sum(len(f.vertices) - 2 for f in o.data.polygons)
        print("VILLE", nom, tri, "triangles,", len(ucx), "boites de collision")
        bpy.ops.object.select_all(action='DESELECT')
        for c in ucx:
            c.select_set(True)
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.export_scene.fbx(filepath=os.path.join(SORTIE, nom + ".fbx"), use_selection=True,
                                 object_types={'MESH'}, mesh_smooth_type='FACE', path_mode='COPY', embed_textures=True)
        for c in ucx:
            c.select_set(False)
        bpy.ops.export_scene.gltf(filepath=os.path.join(SORTIE, nom + ".glb"), use_selection=True, export_format='GLB')
        if APERCU:
            os.makedirs(APERCU, exist_ok=True)
            rendre(o, os.path.join(APERCU, "apercu_" + nom + ".png"))
            cam = bpy.context.scene.camera
            loc, rot, lens = cam.location.copy(), cam.rotation_euler.copy(), cam.data.lens
            cam.location = (-12, -30, 13)                       # vue rapprochee
            cam.rotation_euler = (Vector((-2, -8, 3)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
            cam.data.lens = 32
            rendre(o, os.path.join(APERCU, "zoom_" + nom + ".png"))
            cam.location, cam.rotation_euler, cam.data.lens = loc, rot, lens
        o.hide_set(True)
        o.location.x += 200 * k            # on range la ville de cote pour construire la suivante
        for c in ucx:
            c.location.x += 200 * k
    print("Export OK :", SORTIE)


if __name__ == "__main__":
    main()
