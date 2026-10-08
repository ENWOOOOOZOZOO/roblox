"""30 dinos et 8 oeufs "en blocs" style Roblox (du plus commun au plus rare).
1 a 20 : les grands dinos. 21 a 30 : les petits dinos. Oeufs : voir OEUFS plus bas.

Utilisation : Blender > onglet "Scripting" > Open (dinos.py) > Run Script (triangle).
Construit chaque dino, calcule sa texture a studs, l'exporte en .glb dans
le dossier "dinos" de ton dossier utilisateur, puis passe au suivant.
(Compter quelques minutes pour les 20.)
Pour n'en faire qu'un : mets son numero dans SEULEMENT, par exemple SEULEMENT = [18].
MODE : "adultes", "bebes" (versions bebe mignonnes, dans le dossier "bebes"),
"oeufs" (dans le dossier "oeufs"), "machine" (machine a fossiles), "outils" (30 outils pour casser)
ou "tous".

Dans Roblox Studio : Avatar > Import 3D.
"""
import bpy
import bmesh
import math
import os
import random
import numpy as np
from mathutils import Vector, Quaternion, Matrix

SEULEMENT = []          # vide = les 20
MODE = "tous"           # "adultes", "bebes", "oeufs", "oeufs50", "machine", "outils", "nouveaux" ou "tous"
DOSSIER = os.path.join(os.path.expanduser("~"), "dinos")
DOSSIER_BEBES = os.path.join(os.path.expanduser("~"), "bebes")
DOSSIER_OEUFS = os.path.join(os.path.expanduser("~"), "oeufs")
BEBE = False            # change pendant la construction
PUPILLE = False         # ajoute une pupille noire quand l'oeil est colore
OEIL_X = 1.0            # taille des yeux (plus grand = plus mignon)
STUDS_PAR_UNITE = 5.0
TEXTURE = 1024
AVEC_STUDS = {"Peau", "Rayure", "Ventre", "Accent", "Coquille", "Bande", "Tache", "Deco1", "Deco2", "Metal", "MetalFonce",
              "Manche", "Grip", "Tete", "Tete2"}

COULEURS_DE_BASE = {
    "Peau": (128, 146, 78), "Rayure": (86, 102, 54), "Ventre": (232, 228, 218),
    "Accent": (200, 120, 60), "Corne": (236, 226, 196), "Dent": (255, 255, 255),
    "Bouche": (206, 24, 36), "Oeil": (12, 12, 14), "Reflet": (255, 255, 255),
    "Griffe": (240, 238, 230), "Pupille": (12, 12, 14),
    # oeufs
    "Coquille": (236, 222, 176), "Bande": (214, 194, 140), "Tache": (196, 170, 116), "Deco1": (150, 110, 64),
    "Deco2": (120, 86, 50), "Lueur": (255, 90, 80), "Os": (244, 240, 226), "Noir": (24, 22, 22),
    # machine
    "Metal": (156, 166, 182), "MetalFonce": (72, 80, 96), "Danger": (250, 200, 40), "Ecran": (18, 52, 70),
    "Bouton": (232, 62, 50), "Vitre": (170, 230, 250),
    # outils
    "Manche": (150, 100, 60), "Grip": (60, 44, 34), "Tete": (170, 170, 176), "Tete2": (120, 120, 128),
    "Lame": (230, 234, 240), "Gemme": (90, 220, 240),
}


def lineaire(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (f(c[0]), f(c[1]), f(c[2]), 1)


# =====================================================================
#  OUTILS DE BASE
# =====================================================================
MATS = {}


def nettoyer():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for d in list(coll):
            coll.remove(d)
    MATS.clear()


def matiere(nom):
    if nom not in MATS:
        m = bpy.data.materials.new(nom)
        m.use_nodes = True
        c = lineaire(COULEURS_DE_BASE[nom])
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = c
        m.diffuse_color = c
        MATS[nom] = m
    return MATS[nom]


def lier(o):
    bpy.context.scene.collection.objects.link(o)
    return o


def activer(o):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def biseauter(o, largeur):
    if largeur <= 0:
        return
    mod = o.modifiers.new("Biseau", 'BEVEL')
    mod.width = largeur
    mod.segments = 1
    mod.limit_method = 'ANGLE'
    mod.angle_limit = math.radians(35)
    activer(o)
    bpy.ops.object.modifier_apply(modifier=mod.name)


def boite(nom, centre, taille, mat, biseau=None, arriere=(1, 1), avant=(1, 1), tangage=0.0, roulis=0.0, lacet=0.0):
    """Boite biseautee. arriere/avant = retrecissement (x, z) du bout +Y / -Y.
    tangage (deg) positif = l'arriere monte. roulis = rotation autour de Y. lacet = autour de Z."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    o = bpy.context.active_object
    o.name = nom
    sx, sy, sz = taille
    for v in o.data.vertices:
        x, y, z = v.co
        fx, fz = arriere if y > 0 else avant
        v.co = (x * sx * fx, y * sy, z * sz * fz)
    o.data.materials.append(matiere(mat))
    if biseau is None:
        biseau = min(sx, sy, sz) * 0.12
    biseauter(o, biseau)
    o.rotation_euler = (math.radians(tangage), math.radians(roulis), math.radians(lacet))
    o.location = centre
    return o


def plaque(nom, points, epaisseur, mat, plan="yz", decalage=(0, 0, 0), biseau=0.04, effile=None):
    """Forme 2D extrudee. plan 'yz' : points (y, z), epaisseur sur X.
    'xz' : points (x, z), epaisseur sur Y. 'xy' : points (x, y), epaisseur sur Z."""
    me = bpy.data.meshes.new(nom)
    bm = bmesh.new()

    def pos(t, a, b):
        if plan == "yz":
            return (t, a, b)
        if plan == "xz":
            return (a, t, b)
        return (a, b, t)

    A = [bm.verts.new(pos(-epaisseur / 2, a, b)) for a, b in points]
    B = [bm.verts.new(pos(epaisseur / 2, a, b)) for a, b in points]
    bm.faces.new(A)
    bm.faces.new(list(reversed(B)))
    n = len(points)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((A[i], A[j], B[j], B[i]))
    if effile:
        for v in bm.verts:
            v.co.x *= effile(v.co.y)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    o = lier(bpy.data.objects.new(nom, me))
    o.location = decalage
    o.data.materials.append(matiere(mat))
    biseauter(o, biseau)
    return o


def ellipse(nom, pos, demi, mat, rot=None, seg=12, anneaux=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=anneaux, radius=1, location=pos)
    o = bpy.context.active_object
    o.name = nom
    o.scale = demi
    if rot is not None:
        o.rotation_mode = 'QUATERNION'
        o.rotation_quaternion = rot
    o.data.materials.append(matiere(mat))
    return o


def cone(nom, pos, rayon, hauteur, mat, direction, sommets=4, echelle=(1, 1, 1)):
    """Cone dont la pointe suit `direction` ; `pos` = centre de la base."""
    d = Vector(direction).normalized()
    bpy.ops.mesh.primitive_cone_add(vertices=sommets, radius1=rayon, radius2=0, depth=hauteur,
                                    location=Vector(pos) + d * (hauteur / 2))
    o = bpy.context.active_object
    o.name = nom
    o.scale = echelle
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    o.data.materials.append(matiere(mat))
    return o


def toucher(objs, origine, direction):
    """Premier point touche par un rayon parmi `objs` (coordonnees du monde)."""
    if not isinstance(objs, (list, tuple)):
        objs = [objs]
    meilleur = (None, None, 1e9)
    for obj in objs:
        mw = obj.matrix_world
        inv = mw.inverted()
        ok, loc, n, _ = obj.ray_cast(inv @ Vector(origine), (inv.to_3x3() @ Vector(direction)).normalized())
        if ok:
            lw = mw @ loc
            d = (lw - Vector(origine)).length
            if d < meilleur[2]:
                nw = (mw.to_3x3().inverted().transposed() @ n).normalized()
                meilleur = (lw, nw, d)
    return meilleur[0], meilleur[1]


def le_long(points, pas):
    res, reste = [], 0.0
    for (a0, b0), (a1, b1) in zip(points, points[1:]):
        L = math.hypot(a1 - a0, b1 - b0)
        t = reste
        while t <= L:
            k = t / L
            res.append((a0 + (a1 - a0) * k, b0 + (b1 - b0) * k))
            t += pas
        reste = t - L
    return res


def objets():
    return [o for o in bpy.data.objects if o.type == 'MESH']


# =====================================================================
#  PIECES DE DINO
# =====================================================================
# Profil de tete carnivore (u = 0 arriere -> 1 avant, v = hauteur / H depuis la ligne de la bouche)
TETE_CARNI_HAUT = [(0, .586), (.135, .957), (.435, 1.0), (.736, .79), (.931, .605), (1.0, .383),
                   (.961, .136), (.766, .025), (.556, 0), (.345, .049), (.18, .198), (.045, .309)]
TETE_CARNI_BAS = [(.195, .074), (.345, -.074), (.556, -.123), (.766, -.099), (.931, .012), (.982, -.123),
                  (.952, -.296), (.811, -.457), (.601, -.543), (.375, -.506), (.18, -.321), (.09, -.031)]
TETE_HERBI = [(0, .5), (.15, .95), (.5, 1.0), (.8, .8), (.97, .5), (1.0, .15), (.96, -.12),
              (.75, -.3), (.45, -.36), (.15, -.3), (0, -.1)]


class Tete:
    """Garde ce qu'il faut pour poser des choses sur la tete."""

    def __init__(self, base, L, H, W):
        self.y0, self.z0 = base
        self.L, self.H, self.W = L, H, W
        self.objs = []

    def p(self, u, v):
        return (self.y0 - u * self.L, self.z0 + v * self.H)

    def effile(self, y):
        u = (self.y0 - y) / self.L
        return 1.0 - 0.28 * max(0.0, min(1.0, (u - 0.5) / 0.48))

    def demi_largeur(self, u):
        return self.W / 2 * self.effile(self.y0 - u * self.L)


def tete_carnivore(base, L, H, W, dents=True, machoire=1.0, arcade=True, rainures=True, oeil=0.16):
    if BEBE:
        arcade, rainures, oeil = False, False, 0.25
    t = Tete(base, L, H, W)
    haut = plaque("Tete", [t.p(u, v) for u, v in TETE_CARNI_HAUT], W, "Peau", biseau=min(H, W) * 0.07, effile=t.effile)
    bas = plaque("Machoire", [t.p(u, v * machoire) for u, v in TETE_CARNI_BAS], W * 0.92, "Peau",
                 biseau=min(H, W) * 0.06, effile=t.effile)
    t.objs = [haut, bas]
    yb, zb = t.p(0.56, -0.02)
    boite("Bouche", (0, yb, zb), (W * 0.7, L * 0.78, H * 0.26), "Bouche", biseau=0.02)
    if dents:
        ligne_h = [t.p(u, v) for u, v in TETE_CARNI_HAUT[6:11]]
        ligne_b = [t.p(u, v * machoire) for u, v in TETE_CARNI_BAS[0:5]][::-1]
        r = H * (0.045 if BEBE else 0.062)
        for ligne, sens, larg, dec in ((ligne_h, -1, W, 0.0), (ligne_b, 1, W * 0.92, 0.5)):
            pas = H * (0.16 if BEBE else 0.12)
            for k, (y, z) in enumerate(le_long(ligne, pas)):
                y -= dec * pas
                demi = larg / 2 * t.effile(y) - r * 1.3
                for s in (-1, 1):
                    cone("Dent", (s * demi, y, z - sens * r * 0.4), r, H * (0.12 if BEBE else 0.19), "Dent", (0, 0, sens))
            y0, z0 = ligne[0]
            demi = larg / 2 * t.effile(y0) - r * 1.3
            for x in np.linspace(-demi * 0.7, demi * 0.7, 4):
                cone("Dent", (x, y0 + r, z0 - sens * r * 0.4), r, H * (0.12 if BEBE else 0.19), "Dent", (0, 0, sens))
    yo, zo = t.p(0.42, 0.62)
    poser_yeux(haut, yo, zo, H * oeil * 1.5)
    for s in (-1, 1):
        if arcade:
            ya, za = t.p(0.5, 0.86)
            boite("Arcade", (s * t.demi_largeur(0.5) * 0.84, ya, za), (W * 0.21, L * 0.32, H * 0.16), "Peau",
                  avant=(0.7, 0.6), tangage=-8)
        yn, zn = t.p(0.9, 0.62)
        boite("Narine", (s * W * 0.18 * t.effile(yn), yn, zn), (W * 0.08, L * 0.1, H * 0.07), "Rayure", biseau=0.01,
              tangage=-20)
        if rainures:
            for u in (0.27, 0.345):
                yr, zr = t.p(u, 0.52)
                boite("Rainure", (s * (W / 2 + 0.005), yr, zr), (0.04, L * 0.036, H * 0.43), "Rayure", biseau=0)
    return t


def tete_herbivore(base, L, H, W, bec=True):
    t = Tete(base, L, H, W)
    tete = plaque("Tete", [t.p(u, v) for u, v in TETE_HERBI], W, "Peau", biseau=min(H, W) * 0.08, effile=t.effile)
    t.objs = [tete]
    if bec:
        yb, zb = t.p(0.93, -0.02)
        boite("Bec", (0, yb, zb), (W * 0.52 * t.effile(yb), L * 0.2, H * 0.5), "Corne", avant=(0.75, 0.7))
    # sourire ferme
    for s in (-1, 1):
        for u in (0.5, 0.62, 0.74):
            y, z = t.p(u, -0.08 - (u - 0.5) * 0.1)
            loc, n = toucher(tete, (s * 20, y, z), (-s, 0, 0))
            if loc:
                boite("Sourire", (loc.x, y, z), (0.03, L * 0.13, H * 0.05), "Rayure", biseau=0)
        yn, zn = t.p(0.88, 0.45)
        loc, n = toucher(tete, (s * W * 0.2, yn - 10, zn), (0, 1, 0))
        if loc:
            ellipse("Narine", loc, (W * 0.05, H * 0.06, H * 0.03), "Rayure", rot=n.to_track_quat('Z', 'Y'), seg=8, anneaux=4)
    yo, zo = t.p(0.35, 0.55)
    poser_yeux(tete, yo, zo, H * (0.34 if BEBE else 0.24))
    return t


def poser_yeux(obj, y, z, taille):
    taille *= OEIL_X
    for s in (-1, 1):
        loc, n = toucher(obj, (s * 30, y, z), (-s, 0, 0))
        if loc is None:
            continue
        q = n.to_track_quat('Z', 'Y')
        ellipse("Oeil", loc, (taille * 0.7, taille, taille * 0.25), "Oeil", rot=q)
        if BEBE or PUPILLE:  # grosse pupille noire (utile quand l'oeil est colore)
            ellipse("Pupille", loc + n * taille * 0.1 + Vector((0, -taille * 0.05, -taille * 0.05)),
                    (taille * 0.45, taille * 0.65, taille * 0.2), "Pupille", rot=q)
        ellipse("Reflet", loc + n * taille * 0.2 + Vector((0, -taille * 0.2, taille * 0.4)),
                (taille * 0.2, taille * 0.24, taille * 0.08), "Reflet", rot=q, seg=8, anneaux=4)


def segments(nom, depart, n, longueur, largeur, hauteur, retrecit, angle0, courbe, vers_avant=False, mat="Peau"):
    """Chaine de blocs (queue ou cou). Renvoie la liste des blocs et le point d'arrivee."""
    p = Vector(depart)
    a = angle0
    blocs = []
    w, h = largeur, hauteur
    for i in range(n):
        r = math.radians(a)
        d = Vector((0, -math.cos(r), math.sin(r))) if vers_avant else Vector((0, math.cos(r), math.sin(r)))
        c = p + d * longueur / 2
        fin = (retrecit, retrecit)
        if vers_avant:
            o = boite(nom, c, (w, longueur, h), mat, avant=fin, tangage=-a)
        else:
            o = boite(nom, c, (w, longueur, h), mat, arriere=fin, tangage=a)
        blocs.append((o, c, w, h))
        p = p + d * longueur * 0.88
        w, h = w * retrecit, h * retrecit
        a += courbe
    return blocs, p


def bandes(blocs, couleur="Rayure", tous_les=1):
    for i, (o, c, w, h) in enumerate(blocs):
        if i % tous_les:
            continue
        loc, _ = toucher(o, (0, c.y, 50), (0, 0, -1))
        if loc:
            boite("Bande", (0, c.y, loc.z - h * 0.3 + 0.03), (w * 1.04 + 0.04, max(0.12, w * 0.09), h * 0.6),
                  couleur, biseau=0.03)


def bandes_corps(corps, c, w, h, l, n=3, couleur="Rayure"):
    for k in range(n):
        y = c[1] - l * 0.3 + k * (l * 0.6 / max(1, n - 1))
        loc, _ = toucher(corps, (0, y, 50), (0, 0, -1))
        if loc:
            boite("Bande", (0, y, loc.z - h * 0.3 + 0.03), (w + 0.06, max(0.14, l * 0.07), h * 0.6), couleur, biseau=0.03)


def piques_dos(y0, y1, pas, h0, h1, mat="Accent", cibles=None, largeur=0.35, inclinaison=0.5, sommets=4):
    cibles = cibles or objets()
    y = y0
    while y <= y1:
        loc, _ = toucher(cibles, (0, y, 60), (0, 0, -1))
        if loc:
            t = (y - y0) / max(1e-6, y1 - y0)
            h = h0 + (h1 - h0) * t
            cone("Pique", loc - Vector((0, 0, h * 0.2)), h * 0.5, h, mat, (0, inclinaison, 1),
                 sommets=sommets, echelle=(largeur, 1, 1))
        y += pas


def patte_arriere(x, hanche_y, hanche_z, cuisse, tibia_l, pied, griffe=0.3, ergot=False):
    cw, cl, ch = cuisse
    boite("Cuisse", (x, hanche_y, hanche_z), cuisse, "Peau", avant=(0.9, 0.85), tangage=-10)
    fw, fl, fh = pied
    bas_cuisse = hanche_z - ch * 0.4
    haut_pied = fh * 0.6
    ht = bas_cuisse - haut_pied
    boite("Tibia", (x, hanche_y + cl * 0.22, haut_pied + ht / 2), (tibia_l, tibia_l, ht + fh * 0.4), "Peau", tangage=18)
    py = hanche_y + cl * 0.15 - fl * 0.25
    boite("Pied", (x, py, fh / 2), pied, "Peau", avant=(1.0, 0.8))
    for k, dx in enumerate((-fw * 0.3, 0, fw * 0.3)):
        boite("Orteil", (x + dx, py - fl / 2 - fl * 0.12, fh * 0.38), (fw * 0.27, fl * 0.35, fh * 0.72), "Peau")
        if ergot and k == 1:
            cone("Ergot", (x + dx, py - fl / 2, fh * 0.75), griffe * 0.45, griffe * 2.2, "Griffe", (0, -0.7, 1))
        else:
            cone("Griffe", (x + dx, py - fl / 2 - fl * 0.26, fh * 0.38), griffe * 0.4, griffe, "Griffe", (0, -1, -0.35))


def patte_colonne(x, y, haut_z, epaisseur, griffe=0.18):
    """Patte droite d'animal a 4 pattes."""
    h = haut_z
    boite("Haut", (x, y, h * 0.7), (epaisseur, epaisseur * 1.1, h * 0.65), "Peau")
    boite("Bas", (x, y + 0.05, h * 0.3), (epaisseur * 0.85, epaisseur * 0.95, h * 0.6), "Peau")
    boite("Pied", (x, y - 0.05, 0.12), (epaisseur * 1.1, epaisseur * 1.2, 0.26), "Peau")
    for dx in (-epaisseur * 0.3, 0, epaisseur * 0.3):
        cone("Ongle", (x + dx, y - epaisseur * 0.62, 0.12), griffe * 0.5, griffe, "Griffe", (0, -1, -0.2))


def bras(x, y, z, taille, griffes=2, griffe=0.18, pouce=0.0):
    w, l, h = taille
    boite("Bras", (x, y, z), (w, w * 1.15, h), "Peau", tangage=20)
    ya = y - l * 0.45
    za = z - h * 0.45
    boite("AvantBras", (x * 1.03, ya, za), (w * 0.95, l, w * 0.95), "Peau")
    for k in range(griffes):
        dx = (k - (griffes - 1) / 2) * w * 0.4
        cone("Griffe", (x * 1.03 + dx, ya - l / 2, za), griffe * 0.35, griffe, "Griffe", (0, -1, -0.5))
    if pouce:
        cone("Pouce", (x * 1.03, ya - l * 0.3, za + w * 0.4), pouce * 0.35, pouce, "Griffe", (0, -0.6, 1))


def proportions_bebe(d, quadrupede=False):
    """Grosse tete, corps court, petites pattes, queue courte."""
    if not BEBE:
        return d
    d = dict(d)
    L, H, W = d["tete"]
    d["tete"] = (L * 1.25, H * 1.5, W * 1.45)
    w, l, h = d["corps"]
    d["corps"] = (w, l * 0.78, h * 0.95)
    cl, cw, ch, ca = d["cou"]
    d["cou"] = (cl * (0.7 if d.get("cou_n", 1) > 1 else 0.5), cw, ch, ca)
    qn, ql, qr, qa, qc = d["queue"]
    d["queue"] = (qn, ql * 0.6, qr, qa, qc)
    if quadrupede:
        d["hauteur"] = d["hauteur"] * 0.75
        if "hauteur_pattes" in d:
            d["hauteur_pattes"] = tuple(x * 0.7 for x in d["hauteur_pattes"])
    else:
        d["hauteur"] = d["hauteur"] * 0.8
        cw_, cl_, ch_ = d["cuisse"]
        d["cuisse"] = (cw_, cl_, ch_ * 0.85)
    return d


def corps_bipede(d):
    """Corps generique de bipede. Renvoie un dict avec les pieces utiles."""
    d = proportions_bebe(d)
    w, l, h = d["corps"]
    hz = d["hauteur"]
    corps = boite("Corps", (0, 0, hz), (w, l, h), "Peau", avant=(0.92, 0.92))
    cl, cw, ch, ca = d["cou"]
    cou, bout = segments("Cou", (0, -l * 0.38, hz + h * 0.18), d.get("cou_n", 1), cl, cw, ch,
                         d.get("cou_retrecit", 0.9), ca, d.get("cou_courbe", 0), vers_avant=True)
    L, H, W = d["tete"]
    base = (bout.y + L * 0.06, bout.z - H * 0.3)
    if d.get("type_tete", "carni") == "carni":
        tete = tete_carnivore(base, L, H, W, machoire=d.get("machoire", 1.0), arcade=d.get("arcade", True),
                              rainures=d.get("rainures", True), oeil=d.get("oeil", 0.16))
    else:
        tete = tete_herbivore(base, L, H, W, bec=d.get("bec", True))
    qn, ql, qr, qa, qc = d["queue"]
    queue, fin = segments("Queue", (0, l * 0.42, hz + h * 0.08), qn, ql, w * 0.82, h * 0.8, qr, qa, qc)
    cuisse = d["cuisse"]
    for s in (-1, 1):
        patte_arriere(s * (w / 2 + cuisse[0] * 0.1), l * 0.1, hz - h * 0.12, cuisse, d["tibia"], d["pied"],
                      griffe=d.get("griffe", 0.3), ergot=d.get("ergot", False))
        bras(s * (w / 2 + d["bras"][0] * 0.05), -l * 0.42, hz - h * 0.02, d["bras"], griffes=d.get("doigts", 2),
             griffe=d.get("griffe_main", 0.2), pouce=d.get("pouce", 0))
    if d.get("bandes", 3):
        bandes_corps(corps, (0, 0, hz), w, h, l, n=d.get("bandes", 3))
        bandes(queue, tous_les=1)
    return {"corps": corps, "cou": cou, "tete": tete, "queue": queue, "fin_queue": fin, "w": w, "l": l, "h": h, "hz": hz,
            "d": d}


def aile_plumes(cote, base, envergure, profondeur, mat="Accent", pointes=6):
    """Aile a plumes vue de dessus (bord arriere en dents de scie)."""
    pts = [(0, 0), (envergure * 0.5, -profondeur * 0.12), (envergure, profondeur * 0.05)]
    for k in range(pointes + 1):
        x = envergure * (1 - k / pointes)
        y = profondeur * (0.35 + 0.65 * k / pointes)
        pts.append((x, y + (0.18 * profondeur if k % 2 else 0)))
    pts.append((0, profondeur * 0.8))
    # retire les doublons du coin
    propre = [pts[0]]
    for q in pts[1:]:
        if (q[0] - propre[-1][0]) ** 2 + (q[1] - propre[-1][1]) ** 2 > 1e-4:
            propre.append(q)
    return plaque("Aile", [(cote * x, y) for x, y in propre], 0.08, mat, plan="xy", decalage=base, biseau=0.02)


def eventail(point, n, longueur, mat="Accent", ouverture=70):
    """Eventail de plumes (bout de queue)."""
    for k in range(n):
        a = math.radians(-ouverture / 2 + ouverture * k / max(1, n - 1))
        cone("Plume", Vector(point), longueur * 0.22, longueur, mat, (math.sin(a), math.cos(a), 0.05),
             echelle=(1, 1, 0.25))


def corps_quadrupede(d):
    d = proportions_bebe(d, quadrupede=True)
    w, l, h = d["corps"]
    hz = d["hauteur"]
    corps = boite("Corps", (0, 0, hz), (w, l, h), "Peau", avant=d.get("avant", (0.92, 0.9)))
    cl, cw, ch, ca = d["cou"]
    cou, bout = segments("Cou", (0, -l * 0.4, hz + h * d.get("cou_z", 0.05)), d.get("cou_n", 1), cl, cw, ch,
                         d.get("cou_retrecit", 0.9), ca, d.get("cou_courbe", 0), vers_avant=True)
    L, H, W = d["tete"]
    base = (bout.y + L * 0.08, bout.z - H * 0.2)
    if d.get("type_tete", "herbi") == "carni":
        tete = tete_carnivore(base, L, H, W)
    else:
        tete = tete_herbivore(base, L, H, W, bec=d.get("bec", True))
    qn, ql, qr, qa, qc = d["queue"]
    queue, fin = segments("Queue", (0, l * 0.42, hz + h * 0.05), qn, ql, w * 0.6, h * 0.65, qr, qa, qc)
    e = d["patte"]
    av, ar = d.get("hauteur_pattes", (hz - h * 0.2, hz - h * 0.2))
    for s in (-1, 1):
        x = s * (w / 2 - e * 0.25)
        patte_colonne(x, -l * 0.32, av, e)
        patte_colonne(x, l * 0.3, ar, e * 1.05)
    if d.get("bandes", 3):
        bandes_corps(corps, (0, 0, hz), w, h, l, n=d.get("bandes", 3))
        bandes(queue)
    return {"corps": corps, "cou": cou, "tete": tete, "queue": queue, "fin_queue": fin, "w": w, "l": l, "h": h, "hz": hz,
            "d": d}


# =====================================================================
#  LES 20 DINOS
# =====================================================================
def t(**kw):
    c = dict(COULEURS_DE_BASE)
    c.update(kw)
    return c


DINOS = []


def dino(numero, nom, rarete, echelle, couleurs):
    def deco(f):
        DINOS.append((numero, nom, rarete, echelle, couleurs, f))
        return f
    return deco


@dino(1, "Compsognathus", "Commun", 0.45, t(Peau=(150, 176, 96), Rayure=(104, 130, 64)))
def compsognathus():
    corps_bipede(dict(corps=(1.6, 2.4, 1.6), hauteur=2.4, cou=(1.3, 0.9, 0.9, 40), tete=(1.8, 0.95, 1.1),
                      queue=(3, 1.6, 0.7, 4, 3), cuisse=(0.75, 1.2, 1.3), tibia=0.5, pied=(0.7, 1.0, 0.35),
                      bras=(0.25, 0.4, 0.55), griffe=0.18, griffe_main=0.12, bandes=2, arcade=False, rainures=False))


@dino(2, "Protoceratops", "Commun", 0.6, t(Peau=(204, 172, 118), Rayure=(150, 116, 74), Accent=(176, 120, 80)))
def protoceratops():
    b = corps_quadrupede(dict(corps=(2.0, 2.6, 1.7), hauteur=1.9, cou=(0.7, 1.3, 1.2, 15), tete=(1.6, 1.0, 1.35),
                              queue=(2, 1.2, 0.65, 0, -4), patte=0.55, bandes=2))
    tt = b["tete"]
    y, z = tt.p(0.05, 0.75)
    plaque("Collerette", [(-0.95, -0.2), (-1.05, 0.45), (-0.6, 0.95), (0, 1.1), (0.6, 0.95), (1.05, 0.45), (0.95, -0.2)],
           0.18, "Accent", plan="xz", decalage=(0, y + 0.1, z - 0.2), biseau=0.04)


@dino(3, "Gallimimus", "Commun", 0.8, t(Peau=(214, 158, 98), Rayure=(160, 104, 60), Corne=(90, 70, 50)))
def gallimimus():
    corps_bipede(dict(corps=(1.8, 2.6, 1.8), hauteur=3.7, cou=(1.0, 0.85, 0.85, 60), cou_n=3, cou_retrecit=0.95,
                      cou_courbe=-10, tete=(1.4, 0.75, 0.85), type_tete="herbi", queue=(4, 1.5, 0.72, 4, 2),
                      cuisse=(0.9, 1.5, 1.7), tibia=0.55, pied=(0.8, 1.1, 0.35), bras=(0.28, 0.6, 0.75), doigts=3,
                      griffe=0.2, griffe_main=0.15, bandes=2))


@dino(4, "Iguanodon", "Commun", 1.0, t(Peau=(120, 146, 112), Rayure=(84, 104, 78), Corne=(220, 210, 170)))
def iguanodon():
    corps_bipede(dict(corps=(2.8, 3.2, 2.6), hauteur=3.5, cou=(1.2, 1.8, 1.6, 25), tete=(2.2, 1.3, 1.6),
                      type_tete="herbi", queue=(3, 1.8, 0.7, 4, 2), cuisse=(1.2, 1.9, 2.0), tibia=0.9,
                      pied=(1.2, 1.5, 0.5), bras=(0.55, 0.8, 1.3), doigts=3, pouce=0.5, bandes=3))


@dino(5, "Pachycephalosaurus", "Peu commun", 0.75,
      t(Peau=(150, 118, 86), Rayure=(104, 78, 56), Accent=(96, 132, 200), Corne=(232, 220, 190)))
def pachycephalosaurus():
    b = corps_bipede(dict(corps=(2.3, 2.6, 2.2), hauteur=3.0, cou=(1.0, 1.5, 1.4, 30), tete=(1.7, 1.25, 1.6),
                          type_tete="herbi", queue=(3, 1.6, 0.7, 4, 2), cuisse=(1.0, 1.6, 1.7), tibia=0.75,
                          pied=(1.0, 1.3, 0.45), bras=(0.35, 0.5, 0.7), bandes=2))
    tt = b["tete"]
    y, z = tt.p(0.4, 0.95)
    ellipse("Dome", (0, y, z), (tt.W * 0.5, tt.L * 0.42, tt.H * 0.55), "Accent", seg=10, anneaux=6)
    for s in (-1, 1):
        for u in (0.15, 0.3, 0.45):
            yy, zz = tt.p(u, 0.75)
            cone("Bosse", (s * tt.demi_largeur(u) * 0.95, yy, zz), 0.12, 0.25, "Corne", (s, 0.3, 0.6))


@dino(6, "Parasaurolophus", "Peu commun", 1.0,
      t(Peau=(72, 150, 140), Rayure=(44, 104, 98), Accent=(240, 130, 50), Ventre=(236, 230, 200)))
def parasaurolophus():
    b = corps_bipede(dict(corps=(2.6, 3.0, 2.4), hauteur=3.3, cou=(1.4, 1.6, 1.4, 40), tete=(2.0, 1.1, 1.4),
                          type_tete="herbi", queue=(3, 1.8, 0.7, 4, 2), cuisse=(1.15, 1.8, 1.9), tibia=0.85,
                          pied=(1.1, 1.4, 0.48), bras=(0.42, 0.6, 1.0), doigts=3, bandes=3))
    tt = b["tete"]
    y, z = tt.p(0.3, 0.9)
    boite("Crete", (0, y + 0.9, z + 0.3), (0.45, 2.4, 0.5), "Accent", arriere=(0.7, 0.7), tangage=22)


@dino(7, "Dilophosaurus", "Peu commun", 0.9,
      t(Peau=(176, 184, 74), Rayure=(110, 120, 44), Accent=(232, 70, 40), Ventre=(240, 236, 210)))
def dilophosaurus():
    b = corps_bipede(dict(corps=(2.2, 2.8, 2.0), hauteur=3.2, cou=(1.4, 1.4, 1.3, 35), tete=(2.4, 1.1, 1.5),
                          queue=(3, 1.8, 0.7, 4, 2), cuisse=(1.0, 1.6, 1.7), tibia=0.75, pied=(1.0, 1.3, 0.45),
                          bras=(0.35, 0.55, 0.8), doigts=3, bandes=3))
    tt = b["tete"]
    for s in (-1, 1):
        pts = [tt.p(u, v) for u, v in ((0.15, 0.9), (0.35, 1.7), (0.6, 1.55), (0.85, 0.9), (0.6, 0.95), (0.35, 0.98))]
        plaque("Crete", pts, 0.12, "Accent", decalage=(s * tt.W * 0.18, 0, 0), biseau=0.03)
    # collerette autour du cou
    o, c, w, h = b["cou"][0]
    plaque("Collerette", [(-1.6, -0.6), (-1.75, 0.3), (-1.2, 1.1), (0, 1.4), (1.2, 1.1), (1.75, 0.3), (1.6, -0.6),
                          (0.9, 0.2), (0, 0.4), (-0.9, 0.2)],
           0.1, "Accent", plan="xz", decalage=(0, c.y + 0.15, c.z), biseau=0.03)


@dino(8, "Velociraptor", "Rare", 0.7,
      t(Peau=(150, 104, 70), Rayure=(92, 60, 40), Accent=(60, 140, 220), Ventre=(236, 220, 196)))
def velociraptor():
    b = corps_bipede(dict(corps=(1.8, 2.6, 1.7), hauteur=2.8, cou=(1.2, 1.0, 1.0, 45), tete=(2.1, 0.85, 1.1),
                          queue=(4, 1.5, 0.75, 0, -1), cuisse=(0.85, 1.4, 1.5), tibia=0.55, pied=(0.8, 1.2, 0.38),
                          bras=(0.3, 0.9, 0.85), doigts=3, griffe=0.22, griffe_main=0.22, ergot=True, bandes=3,
                          rainures=False))
    # plumes : crete sur la tete, le cou et le bout de la queue, plumes sur les bras
    tt = b["tete"]
    for k, u in enumerate((0.0, 0.12, 0.24)):
        y, z = tt.p(u, 0.9)
        cone("Plume", (0, y + 0.1, z), 0.25, 0.7 - k * 0.12, "Accent", (0, 1, 0.8), echelle=(0.35, 1, 1))
    piques_dos(-1.6, -0.6, 0.35, 0.5, 0.4, cibles=[c[0] for c in b["cou"]] + [b["corps"]], largeur=0.3, inclinaison=1.0)
    fin = b["fin_queue"]
    for dz in (-0.15, 0.15):
        cone("PlumeQueue", fin + Vector((0, -0.2, dz)), 0.25, 1.0, "Accent", (0, 1, dz), echelle=(0.3, 1, 1))
    for s in (-1, 1):
        cone("PlumeBras", (s * 1.05, -1.0, 2.55), 0.3, 0.8, "Accent", (s * 0.3, 1, -0.6), echelle=(0.25, 1, 1))


@dino(9, "Ankylosaurus", "Rare", 1.0,
      t(Peau=(104, 112, 78), Rayure=(70, 76, 50), Accent=(186, 166, 120), Corne=(226, 210, 170)))
def ankylosaurus():
    b = corps_quadrupede(dict(corps=(3.4, 3.6, 1.9), hauteur=2.2, avant=(0.85, 0.85), cou=(0.6, 1.6, 1.2, 5),
                              tete=(1.5, 0.9, 1.7), queue=(3, 1.5, 0.62, -2, 0), patte=0.75, bandes=0,
                              hauteur_pattes=(1.6, 1.6)))
    # carapace : rangees de plaques osseuses
    for y in np.linspace(-1.4, 1.4, 6):
        for x in np.linspace(-1.2, 1.2, 4):
            loc, n = toucher(b["corps"], (x, y, 50), (0, 0, -1))
            if loc:
                boite("Ecaille", (x, y, loc.z + 0.05), (0.55, 0.45, 0.22), "Accent")
    for s in (-1, 1):
        for y in np.linspace(-1.3, 1.5, 5):
            cone("PiqueCote", (s * 1.7, y, 2.3), 0.22, 0.6, "Corne", (s, 0.3, 0.1))
        tt = b["tete"]
        yc, zc = tt.p(0.15, 0.8)
        cone("Corne", (s * tt.W * 0.45, yc, zc), 0.15, 0.45, "Corne", (s, 0.5, 0.5))
    fin = b["fin_queue"]
    boite("Massue", fin + Vector((0, 0.3, 0)), (1.2, 0.9, 0.7), "Corne", biseau=0.15)


@dino(10, "Stegosaurus", "Rare", 1.1,
      t(Peau=(112, 140, 84), Rayure=(76, 98, 56), Accent=(224, 96, 50), Corne=(230, 216, 180)))
def stegosaurus():
    b = corps_quadrupede(dict(corps=(2.6, 3.6, 2.4), hauteur=2.9, avant=(0.75, 0.7), cou=(1.0, 1.1, 1.0, -15),
                              cou_z=-0.15, tete=(1.4, 0.8, 0.9), queue=(3, 1.7, 0.66, 8, 4), patte=0.7, bandes=0,
                              hauteur_pattes=(2.0, 2.6)))
    cibles = [b["corps"]] + [q[0] for q in b["queue"]] + [c[0] for c in b["cou"]]
    y = -2.0
    k = 0
    while y < 4.6:
        loc, _ = toucher(cibles, (0, y, 60), (0, 0, -1))
        if loc:
            hmax = 1.4 * math.exp(-((y - 0.2) / 2.2) ** 2) + 0.35
            for s in ((-1,) if k % 2 else (1,)):
                cone("Plaque", (s * 0.22, y, loc.z - 0.15), hmax * 0.55, hmax, "Accent", (s * 0.15, 0, 1),
                     sommets=4, echelle=(0.18, 1, 1))
        y += 0.42
        k += 1
    fin = b["fin_queue"]
    for s in (-1, 1):
        for dy in (-0.4, 0.1):
            cone("PiqueQueue", fin + Vector((s * 0.15, dy, 0.1)), 0.12, 0.9, "Corne", (s, 0.5, 0.5), sommets=6)


@dino(11, "Triceratops", "Epique", 1.15,
      t(Peau=(84, 110, 150), Rayure=(56, 76, 108), Accent=(150, 80, 190), Corne=(244, 236, 214)))
def triceratops():
    b = corps_quadrupede(dict(corps=(3.0, 3.6, 2.4), hauteur=2.6, cou=(0.6, 1.8, 1.6, 10), tete=(2.4, 1.5, 2.0),
                              queue=(2, 1.5, 0.62, 0, -4), patte=0.8, bandes=3))
    tt = b["tete"]
    y, z = tt.p(0.05, 0.6)
    plaque("Collerette", [(-1.5, -0.4), (-1.9, 0.6), (-1.4, 1.7), (0, 2.2), (1.4, 1.7), (1.9, 0.6), (1.5, -0.4)],
           0.22, "Accent", plan="xz", decalage=(0, y + 0.15, z), biseau=0.05)
    for a in np.linspace(-150, -30, 7):
        r = math.radians(a)
        cone("Bosse", (1.75 * math.cos(r), y + 0.15, z + 0.75 - 1.4 * math.sin(r) * 0.95), 0.16, 0.35, "Corne",
             (math.cos(r), 0, -math.sin(r)), sommets=6)
    for s in (-1, 1):
        yc, zc = tt.p(0.42, 0.95)
        cone("Corne", (s * 0.45, yc, zc), 0.2, 1.6, "Corne", (s * 0.15, -1, 0.75), sommets=6)
    yn, zn = tt.p(0.9, 0.55)
    cone("CorneNez", (0, yn, zn), 0.17, 0.6, "Corne", (0, -0.6, 1), sommets=6)


@dino(12, "Brachiosaurus", "Epique", 1.6,
      t(Peau=(104, 112, 184), Rayure=(74, 80, 140), Ventre=(220, 222, 240)))
def brachiosaurus():
    b = corps_quadrupede(dict(corps=(2.8, 3.4, 2.6), hauteur=4.6, avant=(1.0, 1.0), cou=(1.5, 1.4, 1.3, 62), cou_n=4,
                              cou_retrecit=0.88, cou_courbe=4, cou_z=0.35, tete=(1.3, 0.8, 0.9),
                              queue=(3, 1.6, 0.6, -6, -6), patte=0.85, bandes=3, hauteur_pattes=(4.3, 3.6)))
    tt = b["tete"]
    y, z = tt.p(0.35, 1.0)
    boite("BosseNez", (0, y, z), (0.6, 0.6, 0.4), "Peau")
    bandes(b["cou"], tous_les=1)


@dino(13, "Pteranodon", "Epique", 0.9,
      t(Peau=(120, 96, 160), Rayure=(84, 60, 120), Accent=(170, 120, 210), Corne=(250, 210, 90), Ventre=(236, 226, 240)))
def pteranodon():
    hz = 2.4
    corps = boite("Corps", (0, 0, hz), (1.1, 1.8, 1.1), "Peau")
    cou, bout = segments("Cou", (0, -0.8, hz + 0.2), 1, 0.9, 0.6, 0.6, 0.9, 30, 0, vers_avant=True)
    L, H, W = (1.35, 1.1, 1.05) if BEBE else (1.0, 0.75, 0.7)
    tt = tete_herbivore((bout.y + 0.1, bout.z - 0.1), L, H, W, bec=False)
    y, z = tt.p(1.0, 0.1)
    boite("Bec", (0, y - 0.6, z), (0.35, 1.6, 0.35), "Corne", avant=(0.3, 0.3))
    y, z = tt.p(0.1, 0.8)
    boite("Crete", (0, y + 0.8, z + 0.3), (0.15, 1.8, 0.6), "Accent", arriere=(1, 0.3), tangage=18)
    for s in (-1, 1):
        aile = [(0.4, -0.5), (2.2, -0.65), (4.6, -0.3), (5.6, 0.2), (3.4, 0.7), (1.6, 1.0), (0.4, 0.8)]
        plaque("Aile", [(s * x, y) for x, y in aile], 0.1, "Accent", plan="xy", decalage=(0, 0, hz + 0.25), biseau=0.03)
        boite("Os", (s * 2.6, -0.45, hz + 0.3), (4.6, 0.25, 0.22), "Peau", lacet=s * -6)
        boite("Jambe", (s * 0.35, 0.9, hz - 0.75), (0.22, 0.22, 1.1), "Peau", tangage=-35)
        cone("Griffe", (s * 0.35, 1.25, hz - 1.3), 0.06, 0.2, "Griffe", (0, 1, -1))
    piques_dos(-0.6, 0.6, 0.4, 0.3, 0.25, cibles=[corps], largeur=0.3)


@dino(14, "Carnotaurus", "Epique", 1.1,
      t(Peau=(190, 64, 48), Rayure=(60, 28, 26), Accent=(240, 180, 70), Corne=(240, 224, 180), Ventre=(240, 214, 190)))
def carnotaurus():
    b = corps_bipede(dict(corps=(2.4, 3.0, 2.2), hauteur=3.3, cou=(1.1, 1.7, 1.5, 25), tete=(2.3, 1.4, 1.8),
                          queue=(3, 1.8, 0.7, 4, 2), cuisse=(1.1, 1.8, 1.9), tibia=0.85, pied=(1.1, 1.4, 0.48),
                          bras=(0.25, 0.3, 0.45), griffe_main=0.1, bandes=4))
    tt = b["tete"]
    for s in (-1, 1):
        y, z = tt.p(0.4, 1.0)
        cone("Corne", (s * 0.5, y, z - 0.1), 0.22, 0.9, "Corne", (s, 0.2, 0.7), sommets=6)
        for y in np.linspace(-1.2, 1.2, 4):
            loc, n = toucher(b["corps"], (s * 20, y, b["hz"] + 0.4), (-s, 0, 0))
            if loc:
                boite("Bosse", (loc.x, y, loc.z), (0.2, 0.35, 0.35), "Accent")


@dino(15, "Allosaurus", "Legendaire", 1.15,
      t(Peau=(226, 126, 50), Rayure=(52, 34, 26), Accent=(250, 200, 80), Corne=(250, 226, 160), Ventre=(248, 230, 200),
        Oeil=(20, 10, 6)))
def allosaurus():
    b = corps_bipede(dict(corps=(2.6, 3.2, 2.3), hauteur=3.5, cou=(1.3, 1.8, 1.6, 30), tete=(2.9, 1.35, 1.9),
                          queue=(3, 1.9, 0.7, 4, 2), cuisse=(1.15, 1.9, 2.0), tibia=0.88, pied=(1.15, 1.45, 0.5),
                          bras=(0.42, 0.75, 1.0), doigts=3, griffe_main=0.3, bandes=4))
    tt = b["tete"]
    for s in (-1, 1):
        y, z = tt.p(0.55, 0.95)
        cone("Corne", (s * tt.demi_largeur(0.55) * 0.75, y, z), 0.22, 0.5, "Accent", (0, 0.3, 1), sommets=4,
             echelle=(0.5, 1, 1))
    piques_dos(-2.2, 4.0, 0.5, 0.4, 0.2, largeur=0.4)


@dino(16, "Baryonyx", "Legendaire", 1.15,
      t(Peau=(60, 150, 140), Rayure=(30, 90, 86), Accent=(250, 220, 90), Ventre=(230, 240, 226)))
def baryonyx():
    b = corps_bipede(dict(corps=(2.5, 3.2, 2.2), hauteur=3.2, cou=(1.6, 1.5, 1.3, 30), tete=(3.3, 0.95, 1.3),
                          queue=(4, 1.6, 0.74, 4, 1), cuisse=(1.1, 1.8, 1.9), tibia=0.8, pied=(1.1, 1.4, 0.48),
                          bras=(0.55, 0.8, 1.2), doigts=3, griffe_main=0.3, pouce=1.0, bandes=4))
    tt = b["tete"]
    y, z = tt.p(0.3, 1.0)
    boite("Crete", (0, y, z + 0.1), (0.25, 0.9, 0.35), "Accent", avant=(0.4, 0.4))
    piques_dos(-1.6, 5.0, 0.55, 0.45, 0.2, largeur=0.35)


@dino(17, "Spinosaurus", "Legendaire", 1.35,
      t(Peau=(42, 64, 110), Rayure=(24, 38, 70), Accent=(60, 210, 240), Ventre=(200, 214, 236), Oeil=(60, 230, 255),
        Reflet=(220, 255, 255)))
def spinosaurus():
    b = corps_bipede(dict(corps=(2.7, 3.4, 2.4), hauteur=3.5, cou=(1.6, 1.7, 1.5, 30), tete=(3.4, 1.05, 1.45),
                          queue=(4, 1.8, 0.75, 6, 1), cuisse=(1.15, 1.8, 1.8), tibia=0.85, pied=(1.15, 1.4, 0.5),
                          bras=(0.5, 0.8, 1.1), doigts=3, griffe_main=0.3, bandes=0))
    # grande voile sur le dos
    hz = b["hz"]
    top = hz + b["h"] / 2 - 0.2
    pts = [(-2.0, top), (-1.6, top + 1.8), (-0.6, top + 3.0), (0.6, top + 3.2), (1.8, top + 2.6), (3.0, top + 1.3),
           (3.8, top - 0.1)]
    plaque("Voile", pts, 0.18, "Accent", biseau=0.04)
    for y in np.linspace(-1.5, 3.3, 9):
        hy = max(z for (yy, z) in le_long(pts, 0.05) if abs(yy - y) < 0.06) - top
        boite("Epine", (0, y, top + hy / 2), (0.24, 0.16, hy), "Rayure", biseau=0.03)


@dino(18, "T-Rex", "Mythique", 1.3,
      t(Peau=(128, 146, 78), Rayure=(86, 102, 54)))
def trex():
    corps_bipede(dict(corps=(2.85, 3.0, 2.55), hauteur=3.5, cou=(1.3, 2.15, 1.7, 25), tete=(3.33, 1.62, 2.35),
                      queue=(3, 1.75, 0.7, 6, 4), cuisse=(1.2, 1.9, 2.0), tibia=0.9, pied=(1.2, 1.5, 0.52),
                      bras=(0.45, 0.75, 0.85), griffe=0.32, bandes=3))


@dino(19, "Giganotosaurus", "Mythique", 1.45,
      t(Peau=(46, 44, 50), Rayure=(230, 176, 40), Accent=(250, 196, 50), Ventre=(120, 112, 110), Oeil=(255, 200, 40),
        Reflet=(255, 250, 200), Griffe=(250, 200, 60), Corne=(250, 200, 60)))
def giganotosaurus():
    b = corps_bipede(dict(corps=(3.0, 3.4, 2.7), hauteur=3.7, cou=(1.4, 2.2, 1.8, 25), tete=(3.8, 1.7, 2.3),
                          queue=(3, 2.0, 0.7, 6, 3), cuisse=(1.3, 2.0, 2.2), tibia=0.95, pied=(1.25, 1.6, 0.55),
                          bras=(0.45, 0.7, 0.95), doigts=3, griffe=0.36, griffe_main=0.25, bandes=4))
    tt = b["tete"]
    piques_dos(-2.4, 5.2, 0.5, 0.75, 0.3, largeur=0.4)
    for s in (-1, 1):
        for u in (0.45, 0.6, 0.75):
            y, z = tt.p(u, 0.95 - (u - 0.45) * 0.4)
            cone("Bosse", (s * tt.demi_largeur(u) * 0.6, y, z), 0.15, 0.3, "Corne", (s * 0.4, 0, 1))


@dino(20, "Indominus Rex", "Secret", 1.5,
      t(Peau=(226, 226, 222), Rayure=(120, 124, 130), Accent=(140, 146, 156), Ventre=(244, 244, 240),
        Oeil=(255, 40, 30), Reflet=(255, 200, 190), Bouche=(190, 20, 30), Griffe=(60, 60, 66), Corne=(90, 94, 100)))
def indominus():
    b = corps_bipede(dict(corps=(3.0, 3.3, 2.7), hauteur=3.8, cou=(1.4, 2.2, 1.8, 28), tete=(3.6, 1.7, 2.3),
                          queue=(4, 1.8, 0.74, 6, 2), cuisse=(1.3, 2.0, 2.2), tibia=0.95, pied=(1.25, 1.6, 0.55),
                          bras=(0.55, 1.1, 1.4), doigts=3, griffe=0.4, griffe_main=0.45, bandes=5))
    tt = b["tete"]
    piques_dos(-2.6, 6.0, 0.42, 0.9, 0.3, largeur=0.4)
    for s in (-1, 1):
        for u in (0.3, 0.42, 0.54, 0.66):
            y, z = tt.p(u, 0.95)
            cone("CorneOeil", (s * tt.demi_largeur(u) * 0.75, y, z), 0.14, 0.45, "Corne", (s * 0.4, 0.4, 1))
        for y in np.linspace(-1.2, 1.2, 4):
            loc, n = toucher(b["corps"], (s * 20, y, b["hz"] + 0.6), (-s, 0, 0))
            if loc:
                cone("PiqueCote", loc, 0.15, 0.4, "Corne", (s, 0.4, 0.3))


# ---------------------------------------------------------------------
#  LES PETITS DINOS (21 a 30)
# ---------------------------------------------------------------------
@dino(21, "Eoraptor", "Commun", 0.4, t(Peau=(176, 112, 82), Rayure=(122, 72, 50)))
def eoraptor():
    corps_bipede(dict(corps=(1.6, 2.3, 1.5), hauteur=2.3, cou=(1.1, 0.9, 0.9, 40), tete=(1.6, 0.85, 1.0),
                      queue=(3, 1.5, 0.7, 4, 3), cuisse=(0.7, 1.1, 1.2), tibia=0.45, pied=(0.65, 0.9, 0.32),
                      bras=(0.25, 0.45, 0.6), doigts=3, griffe=0.16, griffe_main=0.12, bandes=2, arcade=False,
                      rainures=False))


@dino(22, "Microceratus", "Commun", 0.35,
      t(Peau=(186, 188, 92), Rayure=(132, 134, 58), Accent=(110, 166, 78), Corne=(240, 230, 196)))
def microceratus():
    b = corps_quadrupede(dict(corps=(1.6, 2.0, 1.3), hauteur=1.5, cou=(0.5, 1.0, 0.9, 15), tete=(1.3, 0.85, 1.1),
                              queue=(2, 1.0, 0.65, 0, -4), patte=0.45, bandes=2))
    tt = b["tete"]
    y, z = tt.p(0.05, 0.7)
    plaque("Collerette", [(-0.75, -0.15), (-0.8, 0.35), (-0.45, 0.7), (0, 0.8), (0.45, 0.7), (0.8, 0.35), (0.75, -0.15)],
           0.14, "Accent", plan="xz", decalage=(0, y + 0.08, z - 0.15), biseau=0.03)
    yn, zn = tt.p(0.88, 0.6)
    cone("CorneNez", (0, yn, zn), 0.09, 0.22, "Corne", (0, -0.5, 1), sommets=6)


@dino(23, "Hypsilophodon", "Commun", 0.45,
      t(Peau=(112, 172, 132), Rayure=(70, 120, 88), Corne=(226, 210, 160)))
def hypsilophodon():
    corps_bipede(dict(corps=(1.6, 2.4, 1.5), hauteur=2.7, cou=(1.0, 0.9, 0.9, 40), tete=(1.3, 0.8, 0.9),
                      type_tete="herbi", queue=(4, 1.4, 0.75, 2, 1), cuisse=(0.8, 1.3, 1.4), tibia=0.5,
                      pied=(0.7, 1.0, 0.32), bras=(0.22, 0.45, 0.55), doigts=3, griffe=0.16, griffe_main=0.1, bandes=3))


@dino(24, "Psittacosaurus", "Peu commun", 0.5,
      t(Peau=(222, 164, 92), Rayure=(166, 112, 58), Accent=(92, 70, 52), Corne=(70, 56, 46)))
def psittacosaurus():
    b = corps_bipede(dict(corps=(1.8, 2.4, 1.7), hauteur=2.5, cou=(0.8, 1.1, 1.1, 30), tete=(1.4, 1.1, 1.3),
                          type_tete="herbi", queue=(3, 1.4, 0.7, 4, 2), cuisse=(0.85, 1.4, 1.5), tibia=0.55,
                          pied=(0.8, 1.1, 0.35), bras=(0.3, 0.5, 0.65), doigts=3, griffe=0.18, bandes=2))
    # piquants sur la queue
    piques_dos(1.4, 4.5, 0.22, 0.55, 0.3, cibles=[q[0] for q in b["queue"]], largeur=0.15, inclinaison=0.4,
               mat="Accent", sommets=4)
    tt = b["tete"]
    for s in (-1, 1):
        y, z = tt.p(0.25, 0.1)
        cone("Joue", (s * tt.demi_largeur(0.25) * 0.95, y, z), 0.12, 0.35, "Corne", (s, 0.2, -0.2), sommets=4)


@dino(25, "Oviraptor", "Peu commun", 0.55,
      t(Peau=(112, 132, 176), Rayure=(76, 92, 132), Accent=(244, 142, 60), Corne=(250, 220, 120)))
def oviraptor():
    b = corps_bipede(dict(corps=(1.8, 2.4, 1.7), hauteur=2.8, cou=(1.2, 0.9, 0.9, 45), tete=(1.3, 1.0, 1.0),
                          type_tete="herbi", queue=(3, 1.4, 0.72, 4, 2), cuisse=(0.85, 1.4, 1.5), tibia=0.55,
                          pied=(0.8, 1.1, 0.35), bras=(0.3, 0.75, 0.75), doigts=3, griffe=0.18, griffe_main=0.18,
                          bandes=3))
    tt = b["tete"]
    pts = [tt.p(u, v) for u, v in ((0.25, 0.9), (0.4, 1.9), (0.62, 2.0), (0.85, 1.4), (0.92, 0.75), (0.6, 0.95))]
    plaque("Crete", pts, 0.16, "Accent", biseau=0.03)
    eventail(b["fin_queue"] + Vector((0, -0.2, 0)), 5, 1.1)
    for s in (-1, 1):
        cone("PlumeBras", (s * 1.05, -1.0, 2.6), 0.3, 0.9, "Accent", (s * 0.3, 1, -0.6), echelle=(0.25, 1, 1))


@dino(26, "Minmi", "Rare", 0.45,
      t(Peau=(170, 140, 92), Rayure=(122, 96, 60), Accent=(232, 212, 164), Corne=(240, 232, 206)))
def minmi():
    b = corps_quadrupede(dict(corps=(2.2, 2.4, 1.3), hauteur=1.5, avant=(0.85, 0.85), cou=(0.4, 1.1, 0.9, 5),
                              tete=(1.1, 0.7, 1.2), queue=(3, 1.0, 0.6, -2, 0), patte=0.45, bandes=0,
                              hauteur_pattes=(1.15, 1.15)))
    for y in np.linspace(-0.9, 0.9, 4):
        for x in np.linspace(-0.75, 0.75, 3):
            loc, n = toucher(b["corps"], (x, y, 50), (0, 0, -1))
            if loc:
                boite("Ecaille", (x, y, loc.z + 0.04), (0.42, 0.36, 0.18), "Accent")
    for s in (-1, 1):
        for y in np.linspace(-0.9, 1.0, 4):
            cone("PiqueCote", (s * 1.1, y, 1.6), 0.15, 0.4, "Corne", (s, 0.3, 0.1))
    piques_dos(1.2, 3.6, 0.45, 0.35, 0.2, cibles=[q[0] for q in b["queue"]], mat="Corne", largeur=0.6)


@dino(27, "Troodon", "Rare", 0.5,
      t(Peau=(66, 108, 82), Rayure=(40, 70, 52), Accent=(244, 210, 70), Ventre=(226, 232, 206), Oeil=(250, 200, 40)))
def troodon():
    b = corps_bipede(dict(corps=(1.6, 2.3, 1.5), hauteur=2.6, cou=(1.1, 0.85, 0.85, 45), tete=(1.6, 0.85, 1.0),
                          queue=(4, 1.3, 0.75, 0, -1), cuisse=(0.8, 1.3, 1.4), tibia=0.5, pied=(0.75, 1.1, 0.35),
                          bras=(0.28, 0.75, 0.75), doigts=3, griffe=0.2, griffe_main=0.18, ergot=True, bandes=3,
                          rainures=False, oeil=0.24))
    tt = b["tete"]
    for k, u in enumerate((0.0, 0.12)):
        y, z = tt.p(u, 0.9)
        cone("Plume", (0, y + 0.1, z), 0.2, 0.55 - k * 0.1, "Accent", (0, 1, 0.8), echelle=(0.35, 1, 1))
    eventail(b["fin_queue"] + Vector((0, -0.2, 0)), 3, 0.8)


@dino(28, "Archaeopteryx", "Epique", 0.5,
      t(Peau=(58, 82, 116), Rayure=(30, 42, 64), Accent=(92, 176, 226), Ventre=(214, 226, 240), Corne=(240, 200, 80)))
def archaeopteryx():
    b = corps_bipede(dict(corps=(1.4, 2.0, 1.4), hauteur=2.4, cou=(0.9, 0.8, 0.8, 50), tete=(1.2, 0.75, 0.85),
                          queue=(5, 1.0, 0.8, 0, 0), cuisse=(0.7, 1.1, 1.2), tibia=0.4, pied=(0.6, 0.8, 0.28),
                          bras=(0.22, 0.4, 0.5), doigts=3, griffe=0.14, griffe_main=0.14, bandes=2,
                          rainures=False))
    hz, w, l = b["hz"], b["w"], b["l"]
    for s in (-1, 1):
        aile_plumes(s, (s * w * 0.45, -l * 0.25, hz + 0.25), 3.2, 1.5)
        cone("BoutAile", (s * 3.5, -l * 0.25, hz + 0.25), 0.08, 0.4, "Rayure", (s, -0.3, 0))
    # plumes de chaque cote de la queue
    for o, c, ww, hh in b["queue"]:
        for s in (-1, 1):
            cone("PlumeQueue", c + Vector((s * ww * 0.4, 0, 0)), 0.18, 0.8, "Accent", (s, 0.6, 0), echelle=(1, 1, 0.25))
    eventail(b["fin_queue"] + Vector((0, -0.1, 0)), 5, 1.0)


@dino(29, "Dracorex", "Legendaire", 0.6,
      t(Peau=(132, 92, 176), Rayure=(88, 58, 128), Accent=(90, 60, 136), Corne=(244, 232, 200), Oeil=(80, 240, 120)))
def dracorex():
    b = corps_bipede(dict(corps=(1.9, 2.4, 1.8), hauteur=2.6, cou=(0.9, 1.3, 1.2, 30), tete=(1.5, 1.1, 1.3),
                          type_tete="herbi", queue=(3, 1.5, 0.7, 4, 2), cuisse=(0.9, 1.5, 1.6), tibia=0.65,
                          pied=(0.9, 1.2, 0.4), bras=(0.3, 0.5, 0.65), doigts=3, griffe=0.2, bandes=3))
    tt = b["tete"]
    y, z = tt.p(0.4, 0.95)
    ellipse("Dome", (0, y, z), (tt.W * 0.42, tt.L * 0.35, tt.H * 0.4), "Accent", seg=10, anneaux=6)
    # cornes de dragon autour du crane et sur le museau
    for s in (-1, 1):
        for u, v, l, d in ((0.05, 0.85, 0.9, (s * 0.5, 1, 0.5)), (0.15, 0.7, 0.7, (s * 0.8, 0.8, 0.2)),
                           (0.3, 0.5, 0.5, (s, 0.5, 0)), (0.75, 0.75, 0.4, (s * 0.3, -0.3, 1)),
                           (0.6, 0.85, 0.35, (s * 0.3, 0, 1))):
            yy, zz = tt.p(u, v)
            cone("Corne", (s * tt.demi_largeur(u) * 0.8, yy, zz), l * 0.25, l, "Corne", d, sommets=5)
    piques_dos(-1.0, 3.5, 0.4, 0.4, 0.2, largeur=0.4)


@dino(30, "Microraptor", "Mythique", 0.5,
      t(Peau=(34, 36, 48), Rayure=(66, 44, 130), Accent=(70, 90, 230), Ventre=(80, 84, 110), Oeil=(255, 196, 40),
        Griffe=(220, 220, 240)))
def microraptor():
    b = corps_bipede(dict(corps=(1.4, 2.0, 1.3), hauteur=2.4, cou=(0.9, 0.8, 0.8, 45), tete=(1.4, 0.75, 0.85),
                          queue=(5, 1.1, 0.8, 0, 0), cuisse=(0.7, 1.1, 1.2), tibia=0.4, pied=(0.6, 0.9, 0.28),
                          bras=(0.22, 0.4, 0.5), doigts=3, griffe=0.16, griffe_main=0.14, ergot=True, bandes=3,
                          rainures=False, oeil=0.22))
    hz, w, l = b["hz"], b["w"], b["l"]
    for s in (-1, 1):
        aile_plumes(s, (s * w * 0.45, -l * 0.3, hz + 0.25), 3.0, 1.4)          # ailes avant
        aile_plumes(s, (s * w * 0.4, l * 0.15, hz - 0.45), 2.0, 1.2, mat="Rayure", pointes=4)  # ailes arriere
    for k, u in enumerate((0.0, 0.12, 0.24)):
        y, z = b["tete"].p(u, 0.9)
        cone("Plume", (0, y + 0.1, z), 0.2, 0.6 - k * 0.12, "Accent", (0, 1, 0.8), echelle=(0.35, 1, 1))
    eventail(b["fin_queue"] + Vector((0, -0.1, 0)), 3, 1.3, ouverture=40)


# =====================================================================
#  FINITION : fusion, ventre clair, UV, texture a studs, export
# =====================================================================
def finaliser(nom_fichier, couleurs, echelle, dossier=None, exporter=True, squelette_os=None):
    bas = min((o.matrix_world @ v.co).z for o in objets() for v in o.data.vertices)
    for o in objets():
        o.location.z -= bas
    bpy.ops.object.select_all(action='DESELECT')
    for o in objets():
        o.select_set(True)
    bpy.context.view_layer.objects.active = objets()[0]
    bpy.ops.object.join()
    d = bpy.context.active_object
    d.name = nom_fichier
    # mise a l'echelle depuis l'origine du monde (comme le squelette)
    d.matrix_world = Matrix.Scale(echelle, 4) @ d.matrix_world
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    me = d.data

    noms = [m.name.split(".")[0] for m in me.materials]
    if "Ventre" not in noms:
        me.materials.append(matiere("Ventre"))
        noms.append("Ventre")
    i_peau = noms.index("Peau") if "Peau" in noms else -1
    i_ventre = noms.index("Ventre")
    for p in me.polygons:
        p.use_smooth = False
        if p.material_index == i_peau and p.normal.z < -0.55:
            p.material_index = i_ventre

    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    me.uv_layers.new(name="UV")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(50), island_margin=0.003)
    bpy.ops.object.mode_set(mode='OBJECT')

    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 1
    pts = [v.co for v in me.vertices]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    taille = max(max(p.x for p in pts) - mn.x, max(p.y for p in pts) - mn.y, max(p.z for p in pts) - mn.z)

    def passe(mode):
        img = bpy.data.images.new("bake_" + mode, TEXTURE, TEXTURE, alpha=False, float_buffer=True)
        for slot in me.materials:
            nom = slot.name.split(".")[0]
            nt = slot.node_tree
            nt.nodes.clear()
            out = nt.nodes.new("ShaderNodeOutputMaterial")
            em = nt.nodes.new("ShaderNodeEmission")
            nt.links.new(em.outputs[0], out.inputs["Surface"])
            if mode == "couleur":
                em.inputs["Color"].default_value = lineaire(couleurs[nom])
            elif mode == "masque":
                em.inputs["Color"].default_value = (1, 1, 1, 1) if nom in AVEC_STUDS else (0, 0, 0, 1)
            elif mode == "position":
                tc = nt.nodes.new("ShaderNodeTexCoord")
                mp = nt.nodes.new("ShaderNodeMapping")
                mp.inputs["Scale"].default_value = (1 / taille,) * 3
                mp.inputs["Location"].default_value = -mn / taille
                nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
                nt.links.new(mp.outputs[0], em.inputs["Color"])
            else:
                geo = nt.nodes.new("ShaderNodeNewGeometry")
                vm = nt.nodes.new("ShaderNodeVectorMath")
                vm.operation = 'MULTIPLY_ADD'
                vm.inputs[1].default_value = (0.5, 0.5, 0.5)
                vm.inputs[2].default_value = (0.5, 0.5, 0.5)
                nt.links.new(geo.outputs["Normal"], vm.inputs[0])
                nt.links.new(vm.outputs[0], em.inputs["Color"])
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = img
            nt.nodes.active = tex
        activer(d)
        bpy.ops.object.bake(type='EMIT', margin=4, use_clear=True)
        a = np.empty(TEXTURE * TEXTURE * 4, dtype=np.float32)
        img.pixels.foreach_get(a)
        bpy.data.images.remove(img)
        return a.reshape(TEXTURE, TEXTURE, 4)[..., :3]

    masque = passe("masque")[..., 0]
    P = passe("position") * taille + np.array(mn)
    N = passe("normale") * 2 - 1
    couleur = passe("couleur")

    axe = np.argmax(np.abs(N), axis=-1)
    u = np.where(axe == 0, P[..., 1], P[..., 0]) * STUDS_PAR_UNITE
    v = np.where(axe == 2, P[..., 1], P[..., 2]) * STUDS_PAR_UNITE
    qu = u - np.floor(u) - 0.5
    qv = v - np.floor(v) - 0.5
    m = np.maximum(np.abs(qu), np.abs(qv))
    dedans = np.clip((0.31 - m) / 0.03, 0, 1)
    bord = np.clip(1 - np.abs(m - 0.3) / 0.06, 0, 1)
    lumiere = np.where(np.abs(qv) >= np.abs(qu), np.sign(qv), 0.5 * np.sign(-qu))
    motif = 1 + 0.05 * dedans + bord * 0.2 * lumiere - 0.06 * (1 - dedans)
    c = np.clip(couleur * (1 + masque * (motif - 1))[..., None], 0, 1)
    rgb = np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)
    rgba = np.concatenate([rgb, np.ones((TEXTURE, TEXTURE, 1))], axis=-1).astype(np.float32)
    img = bpy.data.images.new(nom_fichier, TEXTURE, TEXTURE, alpha=False)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()

    final = bpy.data.materials.new(nom_fichier)
    final.use_nodes = True
    tex = final.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    bsdf = final.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.6
    final.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    me.materials.clear()
    me.materials.append(final)
    for p in me.polygons:
        p.material_index = 0

    if not exporter:
        return d
    dossier = dossier or (DOSSIER_BEBES if BEBE else DOSSIER)
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, nom_fichier + ".glb")
    activer(d)
    if squelette_os:
        arm = creer_armature(squelette_os, bas, echelle, d)
        d.select_set(True)
        arm.select_set(True)
    bpy.ops.export_scene.gltf(filepath=chemin, use_selection=True, export_format='GLB')
    nb = sum(len(p.vertices) - 2 for p in me.polygons)
    print(f"Export OK : {chemin} ({nb} triangles)")
    return d


# =====================================================================
#  LES OEUFS (chacun contient 3 a 5 dinos)
# =====================================================================
def coquille(hauteur, rayon, couches, bas=0.5, bande=None):
    """Oeuf en couches de blocs empilees. bande(i) -> nom de couleur de la couche i."""
    dz = hauteur / couches
    for i in range(couches):
        t = (i + 0.5) / couches
        k = (t - 0.42) / (0.58 if t > 0.42 else 0.42)
        r = max(rayon * math.sqrt(max(0.0, 1 - k * k)), rayon * 0.28)
        mat = bande(i) if bande else "Coquille"
        z = bas + i * dz + dz / 2
        boite("Couche", (0, 0, z), (2 * r, 2 * r * 0.72, dz * 1.02), mat, biseau=0.04)
        # un peu moins haut : sinon les dessus des deux blocs se superposent (scintillement)
        boite("Couche", (0, 0, z), (2 * r * 0.72, 2 * r, dz * 0.97), mat, biseau=0.04)
    return [o for o in objets() if o.name.startswith("Couche")]


def blocs_surface(cibles, n, taille, mat, z_min, z_max, saillie=0.35):
    """Petits blocs colles sur la coquille (relief ou taches)."""
    for _ in range(n):
        a = random.uniform(0, 2 * math.pi)
        z = random.uniform(z_min, z_max)
        d = Vector((math.cos(a), math.sin(a), 0))
        loc, nrm = toucher(cibles, Vector((0, 0, z)) + d * 20, -d)
        if loc is None:
            continue
        t = taille * random.uniform(0.7, 1.3)
        boite("Bloc", loc + nrm * t * (saillie - 0.5), (t, t, t * random.uniform(0.8, 1.6)), mat, biseau=0.03)


def eclats(n, rayon, z, hauteur, mat, mat2=None, inclinaison=25, largeur=0.45, decal=0.0):
    """Cristaux / flammes / roseaux en couronne autour de l'oeuf."""
    for k in range(n):
        a = 2 * math.pi * k / n + decal + random.uniform(-0.15, 0.15)
        h = hauteur * random.uniform(0.7, 1.2)
        x, y = rayon * math.cos(a), rayon * math.sin(a)
        tilt = inclinaison * random.uniform(0.6, 1.2)
        o = boite("Eclat", (x, y, z + h / 2), (largeur, largeur, h), mat if (k % 2 == 0 or not mat2) else mat2,
                  avant=(0.6, 0.6), arriere=(0.6, 0.6), biseau=0.04)
        # penche vers l'exterieur
        o.rotation_euler = (math.radians(-tilt * math.sin(a)), math.radians(tilt * math.cos(a)), 0)
        o.location = (x + math.cos(a) * h * 0.2, y + math.sin(a) * h * 0.2, z + h / 2)


def nid_batons(n, rayon, z, longueur, mat, mat2):
    for k in range(n):
        a = 2 * math.pi * k / n + random.uniform(-0.1, 0.1)
        x, y = rayon * math.cos(a), rayon * math.sin(a)
        boite("Baton", (x, y, z + random.uniform(-0.1, 0.15)), (0.32, longueur * random.uniform(0.8, 1.2), 0.3),
              mat if k % 2 else mat2, biseau=0.05, tangage=random.uniform(-25, 25),
              roulis=random.uniform(-20, 20), lacet=math.degrees(a) + random.uniform(-20, 20))


def crane_fossile(cibles, z):
    loc, n = toucher(cibles, (0, -20, z), (0, 1, 0))
    if loc is None:
        return
    y = loc.y - 0.02
    plaque("Crane", [(-0.75, -0.35), (-0.85, 0.15), (-0.55, 0.55), (0.2, 0.6), (0.75, 0.3), (0.85, -0.1),
                     (0.6, -0.4), (-0.3, -0.45)], 0.12, "Os", plan="xz", decalage=(0, y, z), biseau=0.02)
    boite("OrbiteCrane", (-0.35, y - 0.06, z + 0.15), (0.32, 0.06, 0.28), "Noir", biseau=0)
    boite("NezCrane", (0.45, y - 0.06, z + 0.1), (0.14, 0.06, 0.12), "Noir", biseau=0)
    for k in range(6):
        boite("DentCrane", (-0.45 + k * 0.2, y - 0.06, z - 0.3), (0.1, 0.06, 0.14), "Noir", biseau=0)


def eclair(x, y, z, cote, taille, mat):
    pts = [(0, 0), (0.35, 0.55), (0.12, 0.55), (0.4, 1.0), (-0.05, 0.4), (0.15, 0.4), (-0.15, 0)]
    o = plaque("Eclair", [(px * taille, pz * taille) for px, pz in pts], 0.12, mat, plan="xz", decalage=(x, y, z),
               biseau=0.02)
    o.rotation_euler = (0, 0, math.radians(cote))


def feuille(angle, rayon, z, longueur, mat):
    pts = [(0, 0), (longueur * 0.35, -longueur * 0.22), (longueur, 0), (longueur * 0.35, longueur * 0.22)]
    o = plaque("Feuille", pts, 0.08, mat, plan="xy", decalage=(rayon * math.cos(angle), rayon * math.sin(angle), z),
               biseau=0.02)
    o.rotation_euler = (0, math.radians(-28), angle)


def socle(rayon, hauteur, mat, n=1):
    boite("Socle", (0, 0, hauteur / 2), (rayon * 2, rayon * 2, hauteur), mat, biseau=0.08)
    if n > 1:
        boite("Socle", (0, 0, hauteur / 2), (rayon * 2.4, rayon * 1.4, hauteur * 0.8), mat, biseau=0.08)
        boite("Socle", (0, 0, hauteur / 2), (rayon * 1.4, rayon * 2.4, hauteur * 0.8), mat, biseau=0.08)


def theme(*bases, **kw):
    c = dict(COULEURS_DE_BASE)
    for b in bases:
        c.update(b)
    c.update(kw)
    return c


OEUFS = []


def oeuf(numero, nom, rarete, prix, dinos, couleurs):
    """dinos : liste de (numero du dino, chance en %)."""
    def deco(f):
        OEUFS.append(dict(numero=numero, nom=nom, rarete=rarete, prix=prix, dinos=dinos, couleurs=couleurs, f=f))
        return f
    return deco


@oeuf(1, "Oeuf de Sable", "Commun", 100, [(1, 40), (21, 30), (22, 20), (2, 10)],
      theme(Coquille=(238, 222, 176), Bande=(222, 200, 148), Tache=(204, 178, 120), Deco1=(176, 132, 74),
            Deco2=(140, 100, 56)))
def oeuf_sable():
    c = coquille(3.6, 1.45, 11, bas=0.45, bande=lambda i: "Bande" if i % 3 == 1 else "Coquille")
    blocs_surface(c, 26, 0.3, "Coquille", 0.8, 3.6)
    blocs_surface(c, 10, 0.3, "Tache", 0.8, 3.4)
    nid_batons(14, 1.55, 0.35, 2.2, "Deco1", "Deco2")
    nid_batons(10, 1.0, 0.55, 1.6, "Deco2", "Deco1")
    crane_fossile(c, 1.7)


@oeuf(2, "Oeuf de Jungle", "Commun", 500, [(3, 35), (4, 30), (23, 25), (5, 10)],
      theme(Coquille=(132, 186, 96), Bande=(88, 140, 62), Tache=(222, 214, 120), Deco1=(64, 150, 64),
            Deco2=(46, 110, 48)))
def oeuf_jungle():
    c = coquille(3.7, 1.45, 12, bas=0.45, bande=lambda i: "Bande" if i in (3, 4, 8) else "Coquille")
    blocs_surface(c, 16, 0.32, "Tache", 0.8, 3.7)
    blocs_surface(c, 14, 0.28, "Coquille", 0.8, 3.7)
    socle(1.5, 0.45, "Deco2")
    for k in range(9):
        feuille(2 * math.pi * k / 9, 0.9, 0.5, 1.8, "Deco1" if k % 2 else "Deco2")
    for k in range(3):  # lianes
        a = 2 * math.pi * k / 3 + 0.4
        for z in np.linspace(0.9, 3.0, 6):
            loc, nrm = toucher(c, (math.cos(a + z * 0.4) * 20, math.sin(a + z * 0.4) * 20, z),
                               (-math.cos(a + z * 0.4), -math.sin(a + z * 0.4), 0))
            if loc:
                boite("Liane", loc, (0.22, 0.22, 0.42), "Deco2", biseau=0.03)


@oeuf(3, "Oeuf du Marais", "Peu commun", 2000, [(6, 35), (24, 30), (25, 25), (7, 10)],
      theme(Coquille=(92, 156, 150), Bande=(60, 112, 108), Tache=(166, 210, 120), Deco1=(108, 128, 60),
            Deco2=(70, 110, 150), Lueur=(120, 82, 50)))
def oeuf_marais():
    c = coquille(3.8, 1.5, 12, bas=0.4, bande=lambda i: "Bande" if i % 4 == 2 else "Coquille")
    blocs_surface(c, 22, 0.34, "Tache", 0.8, 3.8)
    socle(1.9, 0.35, "Deco2", n=2)
    for k in range(10):  # roseaux avec leur massette
        a = 2 * math.pi * k / 10 + 0.2
        x, y = 1.85 * math.cos(a), 1.85 * math.sin(a)
        h = random.uniform(1.6, 2.6)
        boite("Roseau", (x, y, h / 2), (0.14, 0.14, h), "Deco1", biseau=0.02)
        boite("Massette", (x, y, h - 0.1), (0.24, 0.24, 0.55), "Lueur", biseau=0.04)


@oeuf(4, "Oeuf de Canyon", "Rare", 7500, [(26, 35), (9, 30), (10, 25), (8, 10)],
      theme(Coquille=(196, 120, 84), Bande=(160, 90, 62), Tache=(226, 168, 120), Deco1=(150, 140, 130),
            Deco2=(110, 102, 96)))
def oeuf_canyon():
    c = coquille(3.9, 1.55, 12, bas=0.45, bande=lambda i: "Bande" if i % 2 else "Coquille")
    blocs_surface(c, 18, 0.34, "Tache", 0.8, 3.9)
    # fissures
    for a0 in (0.3, 2.4, 4.2):
        z = 1.0
        a = a0
        while z < 3.6:
            d = Vector((math.cos(a), math.sin(a), 0))
            loc, nrm = toucher(c, Vector((0, 0, z)) + d * 20, -d)
            if loc:
                boite("Fissure", loc, (0.14, 0.14, 0.36), "Noir", biseau=0)
            z += 0.3
            a += random.choice((-0.12, 0.12))
    socle(1.6, 0.45, "Deco2")
    for k in range(14):  # rochers
        a = random.uniform(0, 2 * math.pi)
        r = random.uniform(1.3, 1.9)
        t = random.uniform(0.35, 0.75)
        boite("Rocher", (r * math.cos(a), r * math.sin(a), 0.4 + t / 2), (t, t * 1.2, t),
              random.choice(("Deco1", "Deco2")), lacet=random.uniform(0, 90))


@oeuf(5, "Oeuf de Glace", "Rare", 25000, [(27, 45), (11, 35), (12, 20)],
      theme(Coquille=(196, 228, 248), Bande=(140, 196, 236), Tache=(250, 252, 255), Deco1=(248, 250, 255),
            Deco2=(228, 238, 248), Lueur=(110, 220, 255)))
def oeuf_glace():
    c = coquille(4.0, 1.55, 13, bas=0.5, bande=lambda i: "Bande" if i in (2, 5, 9) else "Coquille")
    blocs_surface(c, 20, 0.32, "Tache", 0.9, 4.0)
    socle(1.7, 0.5, "Deco1", n=2)
    eclats(10, 1.7, 0.4, 1.8, "Lueur", "Coquille", inclinaison=22, largeur=0.42)
    blocs_surface(c, 8, 0.3, "Lueur", 1.0, 3.8, saillie=0.6)
    for k in range(6):  # neige sur le haut
        a = 2 * math.pi * k / 6
        boite("Neige", (0.5 * math.cos(a), 0.5 * math.sin(a), 4.3), (0.6, 0.6, 0.25), "Deco1", biseau=0.06)


@oeuf(6, "Oeuf de Tempete", "Epique", 100000, [(13, 35), (28, 30), (14, 25), (15, 10)],
      theme(Coquille=(128, 104, 196), Bande=(236, 236, 250), Tache=(92, 72, 156), Deco1=(244, 244, 252),
            Deco2=(206, 210, 230), Lueur=(255, 226, 60)))
def oeuf_tempete():
    c = coquille(4.1, 1.6, 13, bas=0.7, bande=lambda i: "Bande" if i % 3 == 0 else "Coquille")
    blocs_surface(c, 20, 0.34, "Tache", 1.0, 4.2)
    for k in range(16):  # nuages
        a = 2 * math.pi * k / 16
        r = random.uniform(1.3, 1.9)
        t = random.uniform(0.6, 1.0)
        boite("Nuage", (r * math.cos(a), r * math.sin(a), 0.4 + random.uniform(0, 0.35)), (t * 1.3, t, t * 0.8),
              random.choice(("Deco1", "Deco2")), biseau=0.15, lacet=math.degrees(a))
    for a in (0.2, 2.3, 4.3):
        eclair(1.65 * math.cos(a), 1.65 * math.sin(a), 1.4, math.degrees(a) + 90, 1.6, "Lueur")


@oeuf(7, "Oeuf des Abysses", "Legendaire", 400000, [(16, 45), (17, 35), (29, 20)],
      theme(Coquille=(30, 54, 110), Bande=(20, 36, 78), Tache=(60, 220, 230), Deco1=(250, 110, 140),
            Deco2=(250, 170, 80), Lueur=(80, 240, 255)))
def oeuf_abysses():
    c = coquille(4.2, 1.6, 13, bas=0.5, bande=lambda i: "Bande" if i % 2 else "Coquille")
    blocs_surface(c, 18, 0.3, "Lueur", 0.9, 4.2, saillie=0.55)
    blocs_surface(c, 14, 0.34, "Coquille", 0.9, 4.2)
    socle(1.7, 0.5, "Bande", n=2)
    for k in range(7):  # coraux
        a = 2 * math.pi * k / 7 + 0.3
        x, y = 1.75 * math.cos(a), 1.75 * math.sin(a)
        mat = "Deco1" if k % 2 else "Deco2"
        h = random.uniform(1.0, 1.8)
        boite("Corail", (x, y, 0.5 + h / 2), (0.3, 0.3, h), mat, biseau=0.04)
        for s in (-1, 1):
            boite("Branche", (x + s * 0.3 * math.sin(a), y - s * 0.3 * math.cos(a), 0.5 + h * 0.75),
                  (0.22, 0.22, h * 0.5), mat, biseau=0.03)
    eclats(6, 1.6, 0.5, 1.2, "Lueur", inclinaison=15, largeur=0.3, decal=0.5)


@oeuf(8, "Oeuf de Volcan", "Mythique", 1500000, [(18, 50), (19, 30), (30, 19), (20, 1)],
      theme(Coquille=(34, 26, 28), Bande=(108, 24, 26), Tache=(150, 30, 30), Deco1=(108, 24, 26),
            Deco2=(54, 34, 34), Lueur=(255, 82, 72)))
def oeuf_volcan():
    c = coquille(4.4, 1.7, 13, bas=0.5, bande=lambda i: "Bande" if i % 2 else "Coquille")
    blocs_surface(c, 22, 0.42, "Bande", 0.9, 4.4)
    blocs_surface(c, 10, 0.3, "Lueur", 0.9, 4.0, saillie=0.6)
    socle(1.8, 0.5, "Deco2", n=2)
    eclats(8, 1.75, 0.3, 2.4, "Lueur", "Deco1", inclinaison=18, largeur=0.5)
    # deux cornes sur le dessus
    for s in (-1, 1):
        for k, (dx, dz, h) in enumerate(((0.45, 4.6, 0.9), (0.65, 5.3, 0.8), (0.75, 5.95, 0.7))):
            boite("Corne", (s * dx, 0, dz), (0.45, 0.45, h), "Deco1" if k < 2 else "Lueur", biseau=0.04,
                  roulis=s * (12 + k * 10))


def construire_oeuf(oe):
    nettoyer()
    random.seed(100 + oe["numero"])
    oe["f"]()
    fichier = f"oeuf_{oe['numero']}_{oe['nom'].split(' ')[-1].lower()}"
    return finaliser(fichier, oe["couleurs"], 1.0, dossier=DOSSIER_OEUFS)


# =====================================================================
#  LA MACHINE A FOSSILES
# =====================================================================
COULEURS_MACHINE = theme(Lueur=(90, 245, 150))


def machine_fossiles():
    # socle en deux marches + bandes de danger devant
    boite("Socle", (0, 0, 0.3), (7.4, 5.2, 0.6), "MetalFonce", biseau=0.08)
    boite("Socle", (0, 0, 0.8), (6.4, 4.4, 0.4), "Metal", biseau=0.06)
    n = 14
    for k in range(n):
        x = -3.5 + 7.0 * (k + 0.5) / n
        boite("Danger", (x, -2.62, 0.3), (7.0 / n, 0.06, 0.45), "Danger" if k % 2 == 0 else "Noir", biseau=0)

    # chambre centrale : bague du bas, piliers, chapeau
    boite("BagueBas", (0, 0, 1.25), (2.7, 2.7, 0.5), "Metal", biseau=0.06)
    boite("Piedestal", (0, 0, 1.6), (1.3, 1.3, 0.25), "MetalFonce", biseau=0.04)
    boite("PiedestalLueur", (0, 0, 1.76), (1.0, 1.0, 0.08), "Lueur", biseau=0.01)
    for sx in (-1, 1):
        for sy in (-1, 1):
            boite("Pilier", (sx * 1.15, sy * 1.15, 2.95), (0.38, 0.38, 3.0), "MetalFonce", biseau=0.05)
    boite("Chapeau", (0, 0, 4.7), (2.8, 2.8, 0.6), "Metal", biseau=0.06)
    boite("Chapeau", (0, 0, 5.15), (2.0, 2.0, 0.35), "MetalFonce", biseau=0.05)
    boite("Antenne", (0, 0, 5.75), (0.18, 0.18, 0.9), "MetalFonce", biseau=0.02)
    boite("Voyant", (0, 0, 6.3), (0.42, 0.42, 0.42), "Lueur", biseau=0.06)
    # anneaux lumineux autour de la chambre
    for z in (1.55, 4.38):
        for sx, sy, w, l in ((0, -1, 2.3, 0.08), (0, 1, 2.3, 0.08), (-1, 0, 0.08, 2.3), (1, 0, 0.08, 2.3)):
            boite("Anneau", (sx * 1.36, sy * 1.36, z), (w, l, 0.12), "Lueur", biseau=0)

    # logo os sur le chapeau
    y = -1.42
    boite("LogoOs", (0, y, 4.7), (1.0, 0.06, 0.18), "Os", biseau=0)
    for sx in (-1, 1):
        for sz in (-1, 1):
            boite("LogoOs", (sx * 0.52, y, 4.7 + sz * 0.1), (0.2, 0.06, 0.2), "Os", biseau=0)

    # reservoirs de liquide de chaque cote
    for sx in (-1, 1):
        x = sx * 2.65
        boite("Reservoir", (x, 0.5, 1.15), (1.3, 1.3, 0.3), "MetalFonce", biseau=0.04)
        boite("Reservoir", (x, 0.5, 3.75), (1.3, 1.3, 0.3), "MetalFonce", biseau=0.04)
        for dx in (-1, 1):
            for dy in (-1, 1):
                boite("MontantReservoir", (x + dx * 0.55, 0.5 + dy * 0.55, 2.45), (0.16, 0.16, 2.4), "Metal", biseau=0.02)
        boite("Liquide", (x, 0.5, 2.3), (0.9, 0.9, 2.1), "Lueur", biseau=0.03)
        for z in (1.8, 2.6, 3.2):
            boite("Bulle", (x + random.uniform(-0.2, 0.2), 0.5 - 0.46, z), (0.16, 0.06, 0.16), "Vitre", biseau=0)
        # tuyaux vers la chambre
        for z in (1.9, 3.4):
            boite("Tuyau", (sx * 1.75, 0.5, z), (1.0, 0.32, 0.32), "MetalFonce", biseau=0.04)
            boite("Raccord", (sx * 1.33, 0.5, z), (0.18, 0.46, 0.46), "Metal", biseau=0.03)

    # trappe d'insertion (devant a gauche) avec fleche lumineuse
    boite("Trappe", (-2.45, -1.6, 1.55), (1.5, 1.2, 1.1), "Metal", biseau=0.08)
    boite("Fente", (-2.45, -2.21, 1.75), (1.0, 0.04, 0.32), "Noir", biseau=0)
    boite("Rebord", (-2.45, -2.24, 1.5), (1.1, 0.08, 0.1), "Danger", biseau=0)
    fleche = [(-0.3, 0.55), (0.3, 0.55), (0.3, 0.25), (0.5, 0.25), (0, -0.2), (-0.5, 0.25), (-0.3, 0.25)]
    plaque("Fleche", fleche, 0.08, "Lueur", plan="xz", decalage=(-2.45, -2.22, 2.35), biseau=0.01)
    boite("SupportFleche", (-2.45, -1.95, 2.35), (0.25, 0.5, 0.25), "MetalFonce", biseau=0.02)

    # panneau de controle (devant a droite) : ecran ADN + boutons
    boite("Pupitre", (2.45, -1.6, 1.55), (1.5, 1.2, 1.1), "Metal", biseau=0.08)
    boite("PupitreHaut", (2.45, -1.75, 2.25), (1.4, 0.8, 0.35), "MetalFonce", biseau=0.05, tangage=-25)
    o = boite("Ecran", (2.45, -2.22, 1.6), (1.15, 0.05, 0.75), "Ecran", biseau=0)
    for k in range(7):  # double helice d'ADN sur l'ecran
        x = 2.45 - 0.42 + k * 0.14
        dz = 0.2 * math.sin(k * 0.9)
        boite("ADN", (x, -2.255, 1.6 + dz), (0.08, 0.02, 0.08), "Lueur", biseau=0)
        boite("ADN", (x, -2.255, 1.6 - dz), (0.08, 0.02, 0.08), "Danger", biseau=0)
    for k, mat in enumerate(("Bouton", "Lueur", "Danger")):
        boite("Bouton", (2.0 + k * 0.45, -1.75, 2.48), (0.26, 0.26, 0.16), mat, biseau=0.03, tangage=-25)

    # aerations a l'arriere
    for k in range(5):
        boite("Aeration", (-1.6 + k * 0.8, 2.22, 0.9), (0.5, 0.06, 0.14), "Noir", biseau=0)


def construire_machine():
    """La machine (texture a studs) + la vitre de la chambre, comme 2e piece du meme fichier :
    dans Roblox, regle la Transparency de la piece "Vitre" (par exemple 0.6)."""
    dossier = os.path.join(os.path.expanduser("~"), "machine")
    nettoyer()
    random.seed(7)
    machine_fossiles()
    d = finaliser("machine_fossiles", COULEURS_MACHINE, 1.0, exporter=False)
    vitre = boite("Vitre", (0, 0, 2.95), (2.1, 2.1, 2.95), "Vitre", biseau=0.03)
    m = bpy.data.materials.new("Vitre")  # materiau a part (celui des bulles a servi au calcul de la texture)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = lineaire(COULEURS_DE_BASE["Vitre"])
    bsdf.inputs["Alpha"].default_value = 0.35
    bsdf.inputs["Roughness"].default_value = 0.05
    vitre.data.materials.clear()
    vitre.data.materials.append(m)
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, "machine_fossiles.glb")
    bpy.ops.object.select_all(action='DESELECT')
    d.select_set(True)
    vitre.select_set(True)
    bpy.context.view_layer.objects.active = d
    bpy.ops.export_scene.gltf(filepath=chemin, use_selection=True, export_format='GLB')
    print("Export OK :", chemin)
    return d


# =====================================================================
#  LES 30 OUTILS POUR CASSER (manche vertical, on tient le bas)
# =====================================================================
def manche(L=4.0, w=0.34, mat="Manche", pommeau="Tete2", bagues=(), grip=True):
    boite("Manche", (0, 0, L / 2), (w, w, L), mat, biseau=w * 0.15)
    if grip:
        for k in range(4):
            boite("Grip", (0, 0, 0.45 + k * 0.32), (w * 1.18, w * 1.18, 0.22), "Grip", biseau=w * 0.08)
    boite("Pommeau", (0, 0, 0.12), (w * 1.55, w * 1.55, 0.26), pommeau, biseau=0.05)
    for z, m in bagues:
        boite("Bague", (0, 0, z), (w * 1.3, w * 1.3, 0.16), m, biseau=0.03)


def gemme(pos, t, mat="Gemme"):
    return ellipse("Gemme", pos, (t, t * 0.7, t * 1.3), mat, seg=4, anneaux=2,
                   rot=Quaternion((0, 0, 1), math.radians(45)))


def bras_courbe(depart, s, envergure, ep, largeur, courbe, mat, segments=4, pointe=None, effile=0.45,
                mats=None):
    """Bras de pioche : blocs le long d'un arc qui retombe, puis une pointe."""
    p = Vector(depart)
    a = 0.0
    L = envergure / segments
    w = largeur
    for i in range(segments):
        a += courbe / segments
        r = math.radians(a)
        d = Vector((s * math.cos(r), 0, -math.sin(r)))
        w = largeur * (1 - effile * i / segments)
        m = mats[i % len(mats)] if mats else mat
        boite("Bras", p + d * L / 2, (L * 1.12, ep, w), m, biseau=min(ep, w) * 0.15, roulis=s * a)
        p = p + d * L * 0.95
    if pointe:
        cone("Pointe", p - d * 0.05, w * 0.6, L * 1.1, pointe, d, sommets=4, echelle=(1, ep / w * 1.2, 1))
    return p, d


def tete_pioche(zc, envergure=1.6, ep=0.36, largeur=0.5, courbe=35, mat="Tete", pointe="Tete2", double=True,
                segments=4, centre=None, mats=None):
    boite("Centre", (0, 0, zc), (0.7, ep * 1.5, 0.75), centre or mat, biseau=0.06)
    bouts = []
    for s in ((-1, 1) if double else (1,)):
        bouts.append(bras_courbe((s * 0.3, 0, zc), s, envergure, ep, largeur, courbe, mat, segments, pointe,
                                 mats=mats))
    return bouts


def tete_marteau(zc, longueur=1.7, cote=0.8, mat="Tete", bouts="Tete2", decal=0.0):
    boite("TeteMarteau", (decal, 0, zc), (longueur, cote, cote), mat, biseau=cote * 0.1)
    for s in (-1, 1):
        boite("Frappe", (decal + s * longueur / 2, 0, zc), (0.18, cote * 1.15, cote * 1.15), bouts, biseau=0.04)


def lame_hache(zc, taille, s, mat="Tete", tranchant="Lame", ep=0.16):
    pts = [(0, -0.45), (taille * 0.55, -taille * 0.75), (taille, -taille * 0.85), (taille * 1.08, 0),
           (taille, taille * 0.85), (taille * 0.55, taille * 0.75), (0, 0.45)]
    plaque("Lame", [(s * x, z) for x, z in pts], ep, mat, plan="xz", decalage=(0, 0, zc), biseau=0.03)
    bord = [(taille * 0.78, -taille * 0.82), (taille, -taille * 0.85), (taille * 1.08, 0), (taille, taille * 0.85),
            (taille * 0.78, taille * 0.82), (taille * 0.86, 0)]
    plaque("Tranchant", [(s * x, z) for x, z in bord], ep * 1.25, tranchant, plan="xz", decalage=(0, 0, zc),
           biseau=0.02)


def lame_pelle(z0, largeur, longueur, mat="Tete", bord="Lame"):
    pts = [(-largeur / 2, 0), (largeur / 2, 0), (largeur / 2, longueur * 0.7), (0, longueur),
           (-largeur / 2, longueur * 0.7)]
    plaque("Pelle", pts, 0.16, mat, plan="xz", decalage=(0, 0, z0), biseau=0.03)
    plaque("BordPelle", [(-largeur / 2, longueur * 0.68), (0, longueur), (largeur / 2, longueur * 0.68),
                         (0, longueur * 0.82)], 0.2, bord, plan="xz", decalage=(0, 0, z0), biseau=0.02)


def meche(depart, direction, longueur, rayon, mat="Tete", mat2="Lame", tours=6):
    """Meche de foreuse : blocs tournes en spirale qui retrecissent + pointe."""
    d = Vector(direction).normalized()
    q = d.to_track_quat('Z', 'Y')
    for k in range(tours):
        t = k / tours
        r = rayon * (1 - 0.75 * t)
        c = Vector(depart) + d * longueur * (t + 0.5 / tours)
        o = boite("Meche", c, (r * 2, r * 2, longueur / tours * 0.95), mat if k % 2 == 0 else mat2, biseau=0.03)
        o.rotation_mode = 'QUATERNION'
        o.rotation_quaternion = q @ Quaternion((0, 0, 1), math.radians(k * 25))
    cone("BoutMeche", Vector(depart) + d * longueur * 0.98, rayon * 0.3, rayon * 1.2, mat2, d, sommets=4)


def tourner(avant, angle, axe, pivot):
    R = Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(angle), 4, axe) @ Matrix.Translation(-Vector(pivot))
    for o in objets():
        if o not in avant:
            o.matrix_world = R @ o.matrix_world


def cristaux(centre, n, taille, mat="Gemme", rayon=0.4):
    for k in range(n):
        a = 2 * math.pi * k / n + random.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), random.uniform(-0.3, 0.3), math.sin(a) * 0.6 + 0.6))
        cone("Cristal", Vector(centre) + d.normalized() * rayon * 0.5, taille * 0.3, taille * random.uniform(0.7, 1.2),
             mat, d, sommets=5)


def eclair_plat(x, y, z, taille, mat="Lueur", miroir=1):
    pts = [(0, 0), (0.35, 0.55), (0.12, 0.55), (0.4, 1.0), (-0.05, 0.4), (0.15, 0.4), (-0.15, 0)]
    plaque("Eclair", [(miroir * px * taille, pz * taille) for px, pz in pts], 0.1, mat, plan="xz",
           decalage=(x, y, z), biseau=0.01)


OUTILS = []


def outil(numero, nom, rarete, couleurs):
    def deco(f):
        OUTILS.append(dict(numero=numero, nom=nom, rarete=rarete, couleurs=couleurs, f=f))
        return f
    return deco


BOIS = dict(Manche=(150, 100, 60), Grip=(96, 64, 40), Tete2=(120, 82, 48))
MANCHE_SOMBRE = dict(Manche=(70, 52, 40), Grip=(30, 26, 26))


@outil(1, "Pioche en bois", "Commun", theme(BOIS, Tete=(178, 128, 76)))
def o_pioche_bois():
    manche(grip=False)
    tete_pioche(3.8, envergure=1.4, courbe=25, segments=3, pointe="Tete2")


@outil(2, "Pelle en bois", "Commun", theme(BOIS, Tete=(186, 136, 82), Lame=(150, 104, 62)))
def o_pelle_bois():
    manche(L=3.6, grip=False)
    lame_pelle(3.4, 1.3, 1.8)


@outil(3, "Pioche en pierre", "Commun", theme(BOIS, Tete=(132, 132, 138), Tete2=(100, 100, 108),
                                              Grip=(206, 176, 116)))
def o_pioche_pierre():
    manche()
    tete_pioche(3.8, envergure=1.5, courbe=30, pointe="Tete2")
    boite("Corde", (0, 0, 3.8), (0.5, 0.62, 0.9), "Grip", biseau=0.04)


@outil(4, "Marteau de pierre", "Commun", theme(BOIS, Tete=(126, 126, 132), Tete2=(96, 96, 104),
                                               Grip=(206, 176, 116)))
def o_marteau_pierre():
    manche(L=3.8)
    tete_marteau(3.7, 1.6, 0.85)
    boite("Corde", (0, 0, 3.7), (0.5, 0.95, 1.0), "Grip", biseau=0.04)


@outil(5, "Pioche en cuivre", "Commun", theme(BOIS, Tete=(204, 118, 66), Tete2=(236, 160, 104),
                                              Grip=(80, 54, 36)))
def o_pioche_cuivre():
    manche(bagues=((3.3, "Tete"),))
    tete_pioche(3.8, envergure=1.6, courbe=32, pointe="Tete2")


@outil(6, "Pelle en fer", "Commun", theme(MANCHE_SOMBRE, Tete=(186, 192, 204), Tete2=(120, 126, 140),
                                          Lame=(236, 240, 246)))
def o_pelle_fer():
    manche(L=3.8, bagues=((3.5, "Tete2"),))
    boite("Poignee", (0, 0, 0.2), (0.9, 0.3, 0.25), "Grip")
    lame_pelle(3.6, 1.4, 2.0)


@outil(7, "Pioche en fer", "Peu commun", theme(MANCHE_SOMBRE, Tete=(186, 192, 204), Tete2=(236, 240, 246)))
def o_pioche_fer():
    manche(bagues=((3.3, "Tete"),))
    tete_pioche(3.85, envergure=1.75, courbe=35, pointe="Tete2")


@outil(8, "Hache de fer", "Peu commun", theme(MANCHE_SOMBRE, Tete=(176, 184, 198), Tete2=(120, 126, 140),
                                              Lame=(240, 244, 250)))
def o_hache_fer():
    manche(bagues=((3.3, "Tete2"),))
    boite("Douille", (0, 0, 3.6), (0.55, 0.42, 0.9), "Tete2")
    lame_hache(3.6, 1.2, 1)


@outil(9, "Marteau de geologue", "Peu commun", theme(Manche=(60, 90, 160), Grip=(30, 30, 36), Tete=(170, 176, 190),
                                                     Tete2=(120, 126, 140)))
def o_geologue():
    manche(L=3.7)
    tete_pioche(3.6, envergure=1.3, courbe=25, double=False, pointe="Tete2")
    boite("FaceMarteau", (-0.6, 0, 3.6), (0.7, 0.55, 0.55), "Tete", biseau=0.05)
    boite("Frappe", (-1.0, 0, 3.6), (0.16, 0.65, 0.65), "Tete2", biseau=0.03)


@outil(10, "Pioche en or", "Peu commun", theme(MANCHE_SOMBRE, Tete=(250, 200, 50), Tete2=(255, 236, 140),
                                               Gemme=(230, 40, 60)))
def o_pioche_or():
    manche(bagues=((3.3, "Tete"), (1.3, "Tete")))
    tete_pioche(3.85, envergure=1.8, courbe=35, pointe="Tete2")
    gemme((0, -0.3, 3.85), 0.2)


@outil(11, "Masse en or", "Peu commun", theme(Manche=(70, 52, 40), Grip=(200, 40, 50), Tete=(250, 196, 46),
                                              Tete2=(196, 140, 30)))
def o_masse_or():
    manche(L=4.2, bagues=((3.6, "Tete"),))
    tete_marteau(4.0, 2.0, 1.15)
    for s in (-1, 1):
        boite("Bande", (s * 0.5, 0, 4.0), (0.16, 1.2, 1.2), "Tete2", biseau=0.03)


@outil(12, "Pioche de glace", "Rare", theme(Manche=(200, 230, 250), Grip=(60, 120, 190), Tete=(150, 210, 250),
                                            Tete2=(230, 248, 255), Gemme=(110, 230, 255), Lueur=(160, 240, 255)))
def o_pioche_glace():
    manche(mat="Manche", bagues=((3.3, "Tete"),))
    bouts = tete_pioche(3.85, envergure=1.8, courbe=30, pointe="Lueur")
    cristaux((0, 0, 4.2), 5, 0.6, "Gemme", rayon=0.5)


@outil(13, "Foreuse a main", "Rare", theme(Manche=(60, 64, 76), Grip=(30, 30, 36), Tete=(200, 206, 216),
                                           Tete2=(250, 196, 40), Lame=(120, 126, 140)))
def o_foreuse():
    manche(L=2.6, mat="Manche")
    boite("Moteur", (0.2, 0, 2.9), (1.4, 0.8, 0.9), "Tete2", biseau=0.1)
    boite("BandeMoteur", (0.2, 0, 2.9), (0.2, 0.84, 0.94), "Grip", biseau=0.02)
    boite("Mandrin", (1.05, 0, 2.9), (0.35, 0.6, 0.6), "Lame", biseau=0.05)
    meche((1.2, 0, 2.9), (1, 0, 0), 1.7, 0.32)


@outil(14, "Pioche en os", "Rare", theme(Manche=(236, 226, 200), Grip=(140, 100, 70), Tete=(240, 234, 214),
                                         Tete2=(250, 248, 236), Os=(240, 234, 214)))
def o_pioche_os():
    manche(mat="Manche", pommeau="Tete")
    for z in (1.6, 2.6):
        boite("Noeud", (0, 0, z), (0.5, 0.5, 0.22), "Tete", biseau=0.06)
    bouts = tete_pioche(3.85, envergure=1.7, courbe=38, pointe="Tete2")
    for p, d in bouts:
        ellipse("BoutOs", p - d * 0.2, (0.3, 0.25, 0.3), "Tete", seg=6, anneaux=4)
    boite("Orbite", (0, -0.29, 3.95), (0.18, 0.04, 0.18), "Noir", biseau=0)


@outil(15, "Pioche de jade", "Rare", theme(MANCHE_SOMBRE, Tete=(60, 176, 120), Tete2=(250, 210, 80),
                                           Gemme=(250, 210, 80)))
def o_pioche_jade():
    manche(bagues=((3.3, "Tete2"), (1.4, "Tete2")))
    tete_pioche(3.85, envergure=1.9, courbe=35, pointe="Tete2", centre="Tete2")
    gemme((0, -0.32, 3.85), 0.22, "Tete")


@outil(16, "Marteau-piqueur", "Rare", theme(Manche=(70, 76, 90), Grip=(30, 30, 36), Tete=(232, 70, 50),
                                             Tete2=(250, 200, 40), Lame=(190, 196, 206)))
def o_marteau_piqueur():
    boite("Poignee", (0, 0, 0.25), (1.6, 0.4, 0.4), "Grip", biseau=0.08)
    boite("Corps", (0, 0, 1.5), (0.9, 0.9, 2.2), "Tete", biseau=0.12)
    for k in range(5):
        boite("Danger", (0, -0.46, 1.0 + k * 0.25), (0.92, 0.04, 0.12), "Tete2" if k % 2 else "Grip", biseau=0)
    boite("Cylindre", (0, 0, 2.9), (0.6, 0.6, 0.7), "Manche", biseau=0.06)
    boite("Burin", (0, 0, 3.7), (0.28, 0.28, 1.0), "Lame", biseau=0.04)
    cone("BoutBurin", (0, 0, 4.18), 0.2, 0.4, "Lame", (0, 0, 1), sommets=4)


@outil(17, "Pioche en diamant", "Epique", theme(MANCHE_SOMBRE, Tete=(90, 226, 236), Tete2=(220, 252, 255),
                                                Gemme=(160, 245, 255)))
def o_pioche_diamant():
    manche(bagues=((3.3, "Tete"), (1.4, "Tete")))
    tete_pioche(3.9, envergure=2.0, courbe=36, pointe="Tete2", segments=5)
    gemme((0, -0.33, 3.9), 0.25)
    gemme((0, 0, 0.42), 0.18)


@outil(18, "Hache double de rubis", "Epique", theme(Manche=(250, 200, 60), Grip=(120, 20, 30), Tete=(210, 36, 56),
                                                     Tete2=(250, 200, 60), Lame=(255, 140, 150), Gemme=(255, 90, 110)))
def o_hache_rubis():
    manche(L=4.2, mat="Manche", pommeau="Tete", bagues=((3.4, "Tete"),))
    boite("Douille", (0, 0, 3.75), (0.6, 0.44, 1.0), "Tete2")
    for s in (-1, 1):
        lame_hache(3.75, 1.35, s)
    cone("Pique", (0, 0, 4.2), 0.18, 0.7, "Tete2", (0, 0, 1), sommets=4)
    gemme((0, -0.27, 3.75), 0.2)


@outil(19, "Pioche en amethyste", "Epique", theme(MANCHE_SOMBRE, Tete=(150, 80, 210), Tete2=(220, 170, 255),
                                                  Gemme=(200, 130, 255), Lueur=(230, 190, 255)))
def o_pioche_amethyste():
    manche(bagues=((3.3, "Tete"), (1.4, "Tete")))
    tete_pioche(3.9, envergure=2.0, courbe=34, pointe="Lueur", segments=5)
    cristaux((0, 0, 4.25), 6, 0.75, "Gemme", rayon=0.5)


@outil(20, "Pioche de lave", "Epique", theme(Manche=(40, 34, 34), Grip=(250, 100, 30), Tete=(38, 32, 34),
                                             Tete2=(255, 120, 30), Lueur=(255, 150, 40)))
def o_pioche_lave():
    manche(mat="Manche", pommeau="Lueur", bagues=((3.3, "Lueur"), (2.3, "Lueur"), (1.4, "Lueur")))
    tete_pioche(3.9, envergure=2.0, courbe=38, pointe="Lueur", segments=5, mats=["Tete", "Tete2"])
    cone("Flamme", (0, 0, 4.25), 0.3, 0.8, "Lueur", (0, 0, 1), sommets=4)
    for s in (-1, 1):
        cone("Flamme", (s * 0.25, 0, 4.2), 0.2, 0.55, "Tete2", (s * 0.4, 0, 1), sommets=4)


@outil(21, "Trident tellurique", "Epique", theme(Manche=(60, 90, 80), Grip=(30, 40, 36), Tete=(70, 170, 150),
                                                  Tete2=(230, 210, 120), Lame=(220, 250, 240), Gemme=(80, 240, 200)))
def o_trident():
    manche(L=4.4, mat="Manche", bagues=((3.4, "Tete2"),))
    boite("Traverse", (0, 0, 4.4), (1.6, 0.36, 0.36), "Tete", biseau=0.05)
    for x in (-0.7, 0, 0.7):
        h = 1.3 if x == 0 else 1.0
        boite("Dent", (x, 0, 4.4 + h / 2), (0.26, 0.26, h), "Tete", biseau=0.04)
        cone("Pointe", (x, 0, 4.4 + h), 0.2, 0.55, "Lame", (0, 0, 1), sommets=4)
    gemme((0, -0.25, 4.4), 0.2)


@outil(22, "Pioche electrique", "Legendaire", theme(Manche=(36, 36, 44), Grip=(250, 210, 40), Tete=(250, 210, 40),
                                                    Tete2=(36, 36, 44), Lueur=(120, 230, 255), Gemme=(120, 230, 255)))
def o_pioche_electrique():
    manche(mat="Manche", bagues=((3.3, "Lueur"), (2.0, "Lueur")))
    tete_pioche(3.95, envergure=2.1, courbe=34, pointe="Lueur", segments=5, mats=["Tete", "Tete2"])
    for s in (-1, 1):
        eclair_plat(s * 0.5, -0.25, 2.4, 0.9, "Lueur", miroir=s)
    gemme((0, -0.33, 3.95), 0.24)


@outil(23, "Pioche T-Rex", "Legendaire", theme(Peau=(128, 146, 78), Rayure=(86, 102, 54), Manche=(80, 60, 44),
                                               Grip=(40, 30, 26), Tete2=(240, 236, 220)))
def o_pioche_trex():
    manche(L=3.6, bagues=((3.2, "Tete2"),))
    avant = set(objets())
    tete_carnivore((0.0, 0.0), 1.9, 0.95, 1.05)
    # la gueule regarde vers +X, posee en haut du manche
    tourner(avant, 90, 'Z', (0, 0, 0))
    for o in objets():
        if o not in avant:
            o.location += Vector((-0.6, 0, 3.6))
    cone("Corne", (-0.7, 0, 4.1), 0.25, 1.4, "Tete2", (-1, 0, -0.3), sommets=4)


@outil(24, "Foreuse turbo", "Legendaire", theme(Manche=(40, 40, 48), Grip=(30, 30, 36), Tete=(220, 40, 50),
                                                Tete2=(250, 200, 50), Lame=(230, 236, 246), Lueur=(120, 230, 255)))
def o_foreuse_turbo():
    manche(L=2.6)
    boite("Moteur", (0.1, 0, 3.0), (1.8, 1.0, 1.2), "Tete", biseau=0.15)
    for k in range(3):
        boite("Aileron", (-0.45 + k * 0.3, 0, 3.65), (0.12, 0.8, 0.3), "Tete2", biseau=0.02)
    boite("Turbo", (-0.85, 0, 3.0), (0.3, 0.8, 0.8), "Lueur", biseau=0.04)
    boite("Mandrin", (1.15, 0, 3.0), (0.4, 0.75, 0.75), "Tete2", biseau=0.06)
    meche((1.3, 0, 3.0), (1, 0, 0), 2.2, 0.42, mat="Lame", mat2="Tete2", tours=8)


@outil(25, "Faux de l'ombre", "Legendaire", theme(Manche=(30, 26, 36), Grip=(90, 40, 140), Tete=(40, 34, 50),
                                                  Lame=(180, 120, 255), Gemme=(190, 100, 255), Lueur=(200, 140, 255)))
def o_faux():
    manche(L=4.6, bagues=((4.0, "Lueur"), (2.5, "Lueur")))
    pts = [(0, 0.3), (1.2, 0.35), (2.2, 0.0), (2.9, -0.6), (3.1, -1.2), (2.6, -0.7), (1.8, -0.35), (0.8, -0.25),
           (0, -0.2)]
    plaque("LameFaux", pts, 0.16, "Tete", plan="xz", decalage=(0, 0, 4.4), biseau=0.03)
    bord = [(1.2, -0.1), (1.8, -0.35), (2.6, -0.7), (3.1, -1.2), (2.9, -0.6), (2.2, -0.12)]
    plaque("Tranchant", bord, 0.2, "Lame", plan="xz", decalage=(0, 0, 4.4), biseau=0.02)
    gemme((0, -0.25, 4.4), 0.24)
    cone("Pique", (0, 0, 4.7), 0.15, 0.6, "Lueur", (0, 0, 1), sommets=4)


@outil(26, "Marteau du tonnerre", "Legendaire", theme(Manche=(90, 60, 40), Grip=(40, 60, 140), Tete=(170, 176, 196),
                                                      Tete2=(250, 200, 60), Lueur=(130, 220, 255)))
def o_marteau_tonnerre():
    manche(L=3.8, bagues=((3.2, "Tete2"),))
    tete_marteau(4.1, 2.1, 1.3)
    for s in (-1, 1):
        boite("Bande", (s * 0.55, 0, 4.1), (0.2, 1.36, 1.36), "Tete2", biseau=0.03)
    boite("Rune", (0, -0.67, 4.1), (0.5, 0.04, 0.5), "Lueur", biseau=0)
    for s in (-1, 1):
        eclair_plat(s * 1.3, 0, 4.6, 0.7, "Lueur", miroir=s)


@outil(27, "Pioche cosmique", "Mythique", theme(Manche=(30, 26, 60), Grip=(120, 60, 200), Tete=(36, 30, 80),
                                                Tete2=(120, 70, 220), Lueur=(255, 240, 160), Gemme=(255, 120, 220)))
def o_pioche_cosmique():
    manche(mat="Manche", bagues=((3.3, "Tete2"), (2.2, "Tete2"), (1.4, "Tete2")))
    bouts = tete_pioche(4.0, envergure=2.2, courbe=36, pointe="Tete2", segments=5)
    for _ in range(14):  # etoiles
        x = random.uniform(-2.0, 2.0)
        z = 4.0 - 0.18 * abs(x) ** 1.6 + random.uniform(-0.15, 0.15)
        boite("Etoile", (x, -0.2, z), (0.1, 0.04, 0.1), "Lueur", biseau=0)
    ellipse("Planete", (0, -0.1, 4.55), (0.38, 0.38, 0.38), "Gemme", seg=10, anneaux=6)
    boite("Anneau", (0, -0.1, 4.55), (1.1, 0.9, 0.06), "Lueur", biseau=0.02, roulis=20)


@outil(28, "Pioche arc-en-ciel", "Mythique", theme(Manche=(250, 250, 250), Grip=(120, 120, 140), Tete=(240, 60, 60),
                                                   Tete2=(250, 150, 40), Lame=(250, 230, 60), Gemme=(70, 210, 110),
                                                   Lueur=(70, 160, 250), Accent=(160, 90, 230)))
def o_pioche_arcenciel():
    manche(mat="Manche", bagues=((3.3, "Tete"), (2.6, "Tete2"), (1.9, "Lame")))
    tete_pioche(4.0, envergure=2.2, courbe=36, pointe="Manche", segments=6,
                mats=["Tete", "Tete2", "Lame", "Gemme", "Lueur", "Accent"], centre="Manche")
    ellipse("Nuage", (0, -0.05, 4.5), (0.6, 0.35, 0.3), "Manche", seg=8, anneaux=5)


@outil(29, "Pioche du dragon", "Mythique", theme(Manche=(40, 20, 24), Grip=(150, 30, 30), Tete=(150, 26, 34),
                                                 Tete2=(40, 20, 24), Lame=(250, 200, 70), Gemme=(255, 170, 40),
                                                 Accent=(200, 50, 50), Corne=(240, 220, 180), Rayure=(90, 16, 24)))
def o_pioche_dragon():
    manche(mat="Manche", bagues=((3.3, "Lame"), (1.4, "Lame")))
    tete_pioche(4.0, envergure=2.2, courbe=38, pointe="Lame", segments=5, mats=["Tete", "Accent"])
    for s in (-1, 1):
        aile_dragon(s, (0, 0.12, 4.25), 1.0, "Accent", "Rayure")
        cone("Corne", (s * 0.2, 0, 4.35), 0.12, 0.6, "Corne", (s * 0.3, 0, 1), sommets=4)
    gemme((0, -0.33, 4.0), 0.26)


@outil(30, "Pioche du Roi Fossile", "Secret", theme(Manche=(30, 26, 26), Grip=(250, 200, 50), Tete=(250, 200, 50),
                                                    Tete2=(30, 26, 26), Lame=(140, 245, 255), Gemme=(255, 60, 80),
                                                    Lueur=(255, 236, 140), Os=(244, 238, 220)))
def o_roi_fossile():
    manche(L=4.4, w=0.4, mat="Manche", pommeau="Tete", bagues=((3.7, "Tete"), (2.7, "Tete"), (1.6, "Tete")))
    gemme((0, 0, 0.5), 0.2)
    for z in (2.2, 3.2):
        gemme((0, -0.24, z), 0.12, "Lame")
    # ailes en os fossilise derriere la tete
    for s in (-1, 1):
        aile_dragon(s, (0, 0.2, 4.5), 1.25, "Tete2", "Os")
    bouts = tete_pioche(4.3, envergure=2.7, ep=0.42, largeur=0.6, courbe=36, pointe="Lame", segments=6,
                        mats=["Tete", "Tete2"])
    for p, d in bouts:
        gemme(p - d * 0.35 + Vector((0, -0.2, 0)), 0.14, "Lame")
    # crane fossile au centre
    boite("Crane", (0, -0.3, 4.3), (0.7, 0.08, 0.6), "Os", biseau=0.02)
    for sx in (-1, 1):
        boite("Orbite", (sx * 0.17, -0.35, 4.4), (0.16, 0.04, 0.16), "Noir", biseau=0)
    for k in range(4):
        boite("DentCrane", (-0.18 + k * 0.12, -0.35, 4.1), (0.06, 0.04, 0.1), "Noir", biseau=0)
    # couronne
    boite("Couronne", (0, 0, 4.9), (0.9, 0.7, 0.3), "Tete", biseau=0.04)
    for x in (-0.35, 0, 0.35):
        cone("PointeCouronne", (x, 0, 5.05), 0.14, 0.45 if x == 0 else 0.32, "Tete", (0, 0, 1), sommets=4)
    gemme((0, -0.36, 4.9), 0.14)
    for z in (4.6, 5.1):
        boite("Aura", (0, 0, z), (0.06, 0.06, 0.06), "Lueur", biseau=0)


def aile_dragon(s, base, t, membrane, os_mat):
    """Aile de chauve-souris : membrane + 3 baleines."""
    pts = [(0.15, -0.1), (0.5, 0.7), (1.0, 1.5), (1.4, 1.95), (1.55, 1.3), (1.9, 1.15), (1.75, 0.6), (2.05, 0.35),
           (1.3, 0.15), (0.6, -0.05)]
    plaque("Aile", [(s * x * t, z * t) for x, z in pts], 0.08, membrane, plan="xz", decalage=base, biseau=0.02)
    for (x0, z0), (x1, z1) in (((0.2, 0), (1.4, 1.95)), ((0.4, 0.1), (1.9, 1.15)), ((0.5, 0.05), (2.05, 0.35))):
        a = Vector((s * x0 * t, 0, z0 * t)) + Vector(base)
        b = Vector((s * x1 * t, 0, z1 * t)) + Vector(base)
        c = (a + b) / 2
        L = (b - a).length
        ang = math.degrees(math.atan2(b.z - a.z, abs(b.x - a.x)))
        boite("Baleine", c + Vector((0, -0.03, 0)), (L, 0.12, 0.1), os_mat, biseau=0.02, roulis=-s * ang)


def construire_outil(ou):
    nettoyer()
    random.seed(200 + ou["numero"])
    ou["f"]()
    nom = ou["nom"].lower()
    for a, b in (("'", ""), ("-", "_"), (" ", "_"), ("é", "e"), ("è", "e")):
        nom = nom.replace(a, b)
    fichier = f"outil_{ou['numero']:02d}_{nom}"
    return finaliser(fichier, ou["couleurs"], 1.0, dossier=os.path.join(os.path.expanduser("~"), "outils"))


# =====================================================================
#  FINITION "LISSE" (raretes hautes) : le corps en blocs devient une peau lisse,
#  les couleurs des blocs sont recopiees dessus (bake "selected to active").
# =====================================================================
DETAILS = ("Dent", "Oeil", "Reflet", "Pupille", "Narine", "Griffe", "Ongle", "Pointe", "Pique", "Corne", "Gemme",
           "Ergot", "Plume", "Pouce", "Eclat", "Cristal", "BoutMeche", "Flamme", "Etoile",
           # pieces fines ou detachees : on les garde nettes (le lissage les ferait disparaitre)
           "Halo", "Aureole", "Chaine", "Fissure", "Couronne", "Lance", "Aile", "Baleine", "Nageoire",
           "Palme", "Aileron", "Visiere", "Boulon")


def _est_detail(o):
    return o.name.split(".")[0].startswith(DETAILS) or o.type != 'MESH'


def _joindre(objs, nom):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    j = bpy.context.active_object
    j.name = nom
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return j


def _copier(objs):
    res = []
    for o in objs:
        c = o.copy()
        c.data = o.data.copy()
        lier(c)
        res.append(c)
    return res


def lisser_poids(obj, iterations=4):
    """Adoucit les poids des os aux articulations (chaque sommet prend la moyenne de ses voisins)."""
    me = obj.data
    nv, ng = len(me.vertices), len(obj.vertex_groups)
    if ng == 0 or nv == 0:
        return
    W = np.zeros((nv, ng), dtype=np.float32)
    for v in me.vertices:
        for g in v.groups:
            W[v.index, g.group] = g.weight
    e = np.empty(len(me.edges) * 2, dtype=np.int32)
    me.edges.foreach_get("vertices", e)
    e = e.reshape(-1, 2)
    deg = np.bincount(e.ravel(), minlength=nv).astype(np.float32)[:, None]
    for _ in range(iterations):
        somme = np.zeros_like(W)
        np.add.at(somme, e[:, 0], W[e[:, 1]])
        np.add.at(somme, e[:, 1], W[e[:, 0]])
        voisins = np.where(deg > 0, somme / np.maximum(deg, 1), W)
        W = 0.5 * W + 0.5 * voisins
    W /= np.maximum(W.sum(axis=1, keepdims=True), 1e-6)
    for gi, vg in enumerate(obj.vertex_groups):
        col = W[:, gi]
        nz = np.nonzero(col > 0.01)[0]
        vg.remove(list(range(nv)))
        for i in nz:
            vg.add([int(i)], float(col[i]), 'REPLACE')


def finaliser_lisse(nom_fichier, couleurs, echelle, dossier=None, max_triangles=14000, squelette_os=None,
                    facettes=False):
    """facettes=True : grandes facettes nettes (style low-poly massif) au lieu d'une peau toute ronde."""
    bas = min((o.matrix_world @ v.co).z for o in objets() for v in o.data.vertices)
    S = Matrix.Scale(echelle, 4)
    for o in objets():
        o.location.z -= bas
        o.matrix_world = S @ o.matrix_world
    originaux = objets()
    corps = [o for o in originaux if not _est_detail(o)]
    details = [o for o in originaux if _est_detail(o)]

    # 1) la peau lisse : copies du corps fusionnees, refaites en voxels puis adoucies
    cible = _joindre(_copier(corps), nom_fichier)
    dims = cible.dimensions
    for nom, reglages in (("REMESH", dict(mode='VOXEL', voxel_size=max(dims) / 100)),
                          ("SMOOTH", dict(factor=1.0, iterations=10 if facettes else 18))):
        mod = cible.modifiers.new(nom, nom)
        for k, v in reglages.items():
            setattr(mod, k, v)
        activer(cible)
        bpy.ops.object.modifier_apply(modifier=mod.name)
    # enleve les petits morceaux isoles (rainures trop fines pour les voxels)
    bm = bmesh.new()
    bm.from_mesh(cible.data)
    bm.verts.ensure_lookup_table()
    vus, morceaux = set(), []
    for v in bm.verts:
        if v.index in vus:
            continue
        pile, groupe = [v], []
        vus.add(v.index)
        while pile:
            x = pile.pop()
            groupe.append(x)
            for e in x.link_edges:
                o = e.other_vert(x)
                if o.index not in vus:
                    vus.add(o.index)
                    pile.append(o)
        morceaux.append(groupe)
    grand = max(len(g) for g in morceaux)
    a_suppr = [v for g in morceaux if len(g) < grand * 0.02 for v in g]
    if a_suppr:
        bmesh.ops.delete(bm, geom=a_suppr, context='VERTS')
    bm.to_mesh(cible.data)
    bm.free()
    nb = sum(len(p.vertices) - 2 for p in cible.data.polygons)
    budget = max_triangles - sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in details)
    if facettes:
        budget = min(budget, 2400)
    if nb > budget:
        mod = cible.modifiers.new("Dec", 'DECIMATE')
        mod.ratio = max(0.05, budget / nb)
        activer(cible)
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if details:
        det = _joindre(_copier(details), "details")
        bpy.ops.object.select_all(action='DESELECT')
        det.select_set(True)
        cible.select_set(True)
        bpy.context.view_layer.objects.active = cible
        bpy.ops.object.join()
    me = cible.data
    me.materials.clear()
    for p in me.polygons:
        p.use_smooth = not facettes
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    me.uv_layers.new(name="UV")
    activer(cible)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 2) la source : les blocs d'origine avec leurs couleurs (ventre clair dessous)
    src = _joindre(originaux, "source")
    sme = src.data
    noms = [m.name.split(".")[0] for m in sme.materials]
    if "Ventre" not in noms:
        sme.materials.append(matiere("Ventre"))
        noms.append("Ventre")
    for slot in sme.materials:
        nom = slot.name.split(".")[0]
        nt = slot.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = lineaire(couleurs[nom])
        nt.links.new(em.outputs[0], out.inputs["Surface"])

    # 3) bake des couleurs de la source vers la peau lisse
    img = bpy.data.images.new("bake_lisse", TEXTURE, TEXTURE, alpha=False, float_buffer=True)
    m = bpy.data.materials.new(nom_fichier)
    m.use_nodes = True
    tex = m.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    m.node_tree.nodes.active = tex
    me.materials.append(m)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 1
    bpy.ops.object.select_all(action='DESELECT')
    src.select_set(True)
    cible.select_set(True)
    bpy.context.view_layer.objects.active = cible
    taille = max(cible.dimensions)
    bpy.ops.object.bake(type='EMIT', use_selected_to_active=True, cage_extrusion=taille * 0.02,
                        max_ray_distance=taille * 0.06, margin=4, use_clear=True)
    a = np.empty(TEXTURE * TEXTURE * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    c = np.clip(a.reshape(TEXTURE, TEXTURE, 4)[..., :3], 0, 1)

    # ventre clair en degrade : la ou la peau regarde vers le bas
    nt = m.node_tree
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(geo.outputs["Normal"], em.inputs["Color"])
    nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    bpy.ops.object.select_all(action='DESELECT')
    cible.select_set(True)
    bpy.context.view_layer.objects.active = cible
    bpy.ops.object.bake(type='EMIT', margin=4, use_clear=True)
    nz = np.empty(TEXTURE * TEXTURE * 4, dtype=np.float32)
    img.pixels.foreach_get(nz)
    nz = nz.reshape(TEXTURE, TEXTURE, 4)[..., 2]
    peau = np.array(lineaire(couleurs["Peau"])[:3])
    ventre = np.array(lineaire(couleurs["Ventre"])[:3])
    proche = np.clip(1 - np.linalg.norm(c - peau, axis=-1) / 0.12, 0, 1)
    f = (np.clip((-nz - 0.2) / 0.45, 0, 1) * proche)[..., None]
    c = c * (1 - f) + ventre * f
    nt.nodes.remove(geo)
    nt.nodes.remove(em)
    nt.links.new(nt.nodes["Principled BSDF"].outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    rgb = np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)
    rgba = np.concatenate([rgb, np.ones((TEXTURE, TEXTURE, 1))], axis=-1).astype(np.float32)
    final_img = bpy.data.images.new(nom_fichier, TEXTURE, TEXTURE, alpha=False)
    final_img.pixels.foreach_set(rgba.ravel())
    final_img.pack()
    tex.image = final_img
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.4
    m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bpy.data.images.remove(img)
    if squelette_os:
        # les poids des os sont recopies des blocs vers la peau lisse, puis adoucis aux articulations
        mod = cible.modifiers.new("Poids", 'DATA_TRANSFER')
        mod.object = src
        mod.use_vert_data = True
        mod.data_types_verts = {'VGROUP_WEIGHTS'}
        mod.vert_mapping = 'POLYINTERP_NEAREST'
        activer(cible)
        bpy.ops.object.datalayout_transfer(modifier=mod.name)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        lisser_poids(cible, 4)
    bpy.data.objects.remove(src, do_unlink=True)

    dossier = dossier or DOSSIER
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, nom_fichier + ".glb")
    activer(cible)
    if squelette_os:
        arm = creer_armature(squelette_os, bas, echelle, cible)
        cible.select_set(True)
        arm.select_set(True)
    bpy.ops.export_scene.gltf(filepath=chemin, use_selection=True, export_format='GLB')
    nb = sum(len(p.vertices) - 2 for p in me.polygons)
    print(f"Export OK : {chemin} ({nb} triangles, lisse)")
    return cible


# =====================================================================
#  GENERATEUR : 150 DINOS EN PLUS (31 a 180)
#  Commun -> Rare : en blocs, gros yeux mignons.  Epique -> Secret : lisses,
#  de plus en plus fantastiques (armure, ailes, flammes, halo, golem...).
# =====================================================================
R = random.Random(0)  # hasard du dino en cours (reinitialise pour chaque dino)


def varier(d, amp):
    """Petites differences de proportions d'un dino a l'autre."""
    d = dict(d)
    for k in ("corps", "tete", "cuisse", "pied", "bras"):
        if k in d:
            d[k] = tuple(x * R.uniform(1 - amp, 1 + amp) for x in d[k])
    return d


# ---------- familles (gabarits) ----------
F = {
    "petit_thero": dict(corps=(1.6, 2.4, 1.5), hauteur=2.4, cou=(1.2, 0.9, 0.9, 40), tete=(1.7, 0.9, 1.05),
                        queue=(3, 1.6, 0.7, 4, 3), cuisse=(0.75, 1.2, 1.3), tibia=0.5, pied=(0.7, 1.0, 0.35),
                        bras=(0.25, 0.5, 0.6), doigts=3, griffe=0.18, griffe_main=0.12, bandes=2),
    "thero": dict(corps=(2.6, 3.2, 2.3), hauteur=3.5, cou=(1.3, 1.8, 1.6, 30), tete=(2.9, 1.35, 1.9),
                  queue=(3, 1.9, 0.7, 4, 2), cuisse=(1.15, 1.9, 2.0), tibia=0.88, pied=(1.15, 1.45, 0.5),
                  bras=(0.42, 0.75, 1.0), doigts=3, griffe_main=0.25, bandes=3),
    "rex": dict(corps=(2.95, 3.1, 2.65), hauteur=3.6, cou=(1.3, 2.2, 1.75, 25), tete=(3.4, 1.7, 2.4),
                queue=(3, 1.8, 0.7, 6, 4), cuisse=(1.25, 1.95, 2.1), tibia=0.95, pied=(1.25, 1.55, 0.55),
                bras=(0.45, 0.7, 0.85), griffe=0.34, bandes=3),
    "raptor": dict(corps=(1.8, 2.6, 1.7), hauteur=2.8, cou=(1.2, 1.0, 1.0, 45), tete=(2.1, 0.85, 1.1),
                   queue=(4, 1.5, 0.75, 0, -1), cuisse=(0.85, 1.4, 1.5), tibia=0.55, pied=(0.8, 1.2, 0.38),
                   bras=(0.3, 0.9, 0.85), doigts=3, griffe=0.22, griffe_main=0.22, ergot=True, bandes=3,
                   rainures=False),
    "petit_ornitho": dict(corps=(1.6, 2.4, 1.5), hauteur=2.7, cou=(1.0, 0.9, 0.9, 40), tete=(1.3, 0.8, 0.9),
                          type_tete="herbi", queue=(4, 1.4, 0.75, 2, 1), cuisse=(0.8, 1.3, 1.4), tibia=0.5,
                          pied=(0.7, 1.0, 0.32), bras=(0.22, 0.45, 0.55), doigts=3, griffe=0.16,
                          griffe_main=0.1, bandes=3),
    "ornitho": dict(corps=(2.5, 3.0, 2.3), hauteur=3.3, cou=(1.2, 1.6, 1.4, 30), tete=(2.0, 1.15, 1.5),
                    type_tete="herbi", queue=(3, 1.8, 0.7, 4, 2), cuisse=(1.1, 1.8, 1.9), tibia=0.85,
                    pied=(1.1, 1.4, 0.48), bras=(0.42, 0.65, 1.0), doigts=3, bandes=3),
    "prosauro": dict(corps=(2.2, 2.8, 2.1), hauteur=3.2, cou=(1.1, 1.1, 1.0, 45), cou_n=3, cou_retrecit=0.92,
                     cou_courbe=-8, tete=(1.3, 0.8, 0.9), type_tete="herbi", queue=(4, 1.6, 0.72, 2, 1),
                     cuisse=(1.0, 1.6, 1.7), tibia=0.7, pied=(0.95, 1.2, 0.42), bras=(0.35, 0.6, 0.9), doigts=3,
                     pouce=0.35, bandes=3),
    "pachy": dict(corps=(2.3, 2.6, 2.2), hauteur=3.0, cou=(1.0, 1.5, 1.4, 30), tete=(1.7, 1.25, 1.6),
                  type_tete="herbi", queue=(3, 1.6, 0.7, 4, 2), cuisse=(1.0, 1.6, 1.7), tibia=0.75,
                  pied=(1.0, 1.3, 0.45), bras=(0.35, 0.5, 0.7), bandes=2),
    "cerato_petit": dict(corps=(1.8, 2.3, 1.5), hauteur=1.7, cou=(0.6, 1.2, 1.1, 15), tete=(1.5, 1.0, 1.3),
                         queue=(2, 1.1, 0.65, 0, -4), patte=0.5, bandes=2),
    "cerato": dict(corps=(2.9, 3.5, 2.3), hauteur=2.6, cou=(0.6, 1.8, 1.6, 10), tete=(2.3, 1.45, 1.95),
                   queue=(2, 1.4, 0.62, 0, -4), patte=0.8, bandes=3),
    "ankylo": dict(corps=(3.2, 3.4, 1.8), hauteur=2.1, avant=(0.85, 0.85), cou=(0.6, 1.5, 1.1, 5),
                   tete=(1.4, 0.85, 1.6), queue=(3, 1.4, 0.62, -2, 0), patte=0.7, bandes=0,
                   hauteur_pattes=(1.55, 1.55)),
    "ankylo_petit": dict(corps=(2.2, 2.5, 1.4), hauteur=1.6, avant=(0.85, 0.85), cou=(0.5, 1.1, 0.9, 5),
                         tete=(1.1, 0.7, 1.2), queue=(3, 1.0, 0.62, -2, 0), patte=0.45, bandes=0,
                         hauteur_pattes=(1.2, 1.2)),
    "stego": dict(corps=(2.6, 3.6, 2.4), hauteur=2.9, avant=(0.75, 0.7), cou=(1.0, 1.1, 1.0, -15), cou_z=-0.15,
                  tete=(1.4, 0.8, 0.9), queue=(3, 1.7, 0.66, 8, 4), patte=0.7, bandes=0, hauteur_pattes=(2.0, 2.6)),
    "sauro": dict(corps=(2.8, 3.5, 2.5), hauteur=4.0, avant=(1.0, 1.0), cou=(1.4, 1.3, 1.2, 50), cou_n=4,
                  cou_retrecit=0.88, cou_courbe=3, cou_z=0.3, tete=(1.3, 0.8, 0.9), queue=(4, 1.7, 0.66, -4, -4),
                  patte=0.85, bandes=3, hauteur_pattes=(3.6, 3.3)),
    "sauro_long": dict(corps=(2.6, 3.6, 2.3), hauteur=3.4, avant=(1.0, 1.0), cou=(1.4, 1.2, 1.1, 22), cou_n=5,
                       cou_retrecit=0.9, cou_courbe=2, cou_z=0.2, tete=(1.2, 0.75, 0.85),
                       queue=(6, 1.5, 0.72, -2, -2), patte=0.8, bandes=3, hauteur_pattes=(2.9, 2.9)),
}
FAMILLES_BIPEDES = {"petit_thero", "thero", "rex", "raptor", "petit_ornitho", "ornitho", "prosauro", "pachy"}
FAMILLES_QUADRUPEDES = {"cerato_petit", "cerato", "ankylo", "ankylo_petit", "stego", "sauro", "sauro_long"}
ECHELLE_FAMILLE = {"petit_thero": 0.45, "thero": 1.0, "rex": 1.15, "raptor": 0.7, "petit_ornitho": 0.5,
                   "ornitho": 0.9, "prosauro": 0.85, "pachy": 0.75, "cerato_petit": 0.5, "cerato": 1.05,
                   "ankylo": 0.95, "ankylo_petit": 0.5, "stego": 1.0, "sauro": 1.45, "sauro_long": 1.35,
                   "ptero": 0.8, "ptero_petit": 0.5, "marin": 1.1, "marin_petit": 0.6}


def corps_ptero(petit=False, crete="pointe", queue_longue=False):
    hz = 2.4
    corps = boite("Corps", (0, 0, hz), (1.1, 1.8, 1.1), "Peau")
    cou, bout = segments("Cou", (0, -0.8, hz + 0.2), 1, 0.9, 0.6, 0.6, 0.9, 30, 0, vers_avant=True)
    L, H, W = (1.4, 1.05, 1.0) if OEIL_X > 1.2 else (1.0, 0.75, 0.7)
    tt = tete_herbivore((bout.y + 0.1, bout.z - 0.1), L, H, W, bec=False)
    y, z = tt.p(1.0, 0.1)
    boite("Bec", (0, y - 0.6, z), (0.35, 1.6, 0.35), "Corne", avant=(0.3, 0.3))
    y, z = tt.p(0.1, 0.8)
    if crete == "pointe":
        boite("Crete", (0, y + 0.8, z + 0.3), (0.15, 1.8, 0.6), "Accent", arriere=(1, 0.3), tangage=18)
    elif crete == "voile":
        plaque("Crete", [tt.p(u, v) for u, v in ((0.2, 0.9), (0.3, 2.6), (0.7, 2.2), (0.9, 0.9))], 0.12, "Accent",
               biseau=0.03)
    env = 4.6 if not petit else 3.6
    for s in (-1, 1):
        aile = [(0.4, -0.5), (env * 0.4, -0.65), (env * 0.85, -0.3), (env, 0.2), (env * 0.62, 0.7), (env * 0.3, 1.0),
                (0.4, 0.8)]
        plaque("Aile", [(s * x, y_) for x, y_ in aile], 0.1, "Accent", plan="xy", decalage=(0, 0, hz + 0.25), biseau=0.03)
        boite("Os", (s * env * 0.47, -0.45, hz + 0.3), (env * 0.84, 0.25, 0.22), "Peau", lacet=s * -6)
        boite("Jambe", (s * 0.35, 0.9, hz - 0.75), (0.22, 0.22, 1.1), "Peau", tangage=-35)
        cone("Griffe", (s * 0.35, 1.25, hz - 1.3), 0.06, 0.2, "Griffe", (0, 1, -1))
    queue = []
    fin = Vector((0, 1.0, hz))
    if queue_longue:
        queue, fin = segments("Queue", (0, 0.8, hz), 4, 0.8, 0.3, 0.3, 0.85, 0, 2)
        cone("BoutQueue", fin, 0.3, 0.5, "Accent", (0, 1, 0), sommets=4, echelle=(0.3, 1, 1))
    return {"corps": corps, "cou": cou, "tete": tt, "queue": queue, "fin_queue": fin, "w": 1.1, "l": 1.8, "h": 1.1,
            "hz": hz, "d": {}}


def corps_marin(sorte="mosa"):
    """Reptile marin sur un socle : plesio (long cou), mosa (gueule de croco), ichthyo (dauphin)."""
    hz = 3.0
    w, l, h = {"plesio": (2.2, 3.2, 1.5), "mosa": (1.9, 3.6, 1.6), "ichthyo": (1.7, 3.0, 1.7)}[sorte]
    corps = boite("Corps", (0, 0, hz), (w, l, h), "Peau", avant=(0.85, 0.8), arriere=(0.8, 0.75))
    cou = []
    if sorte == "plesio":
        cou, bout = segments("Cou", (0, -l * 0.4, hz + h * 0.1), 5, 0.9, 0.8, 0.75, 0.93, 28, -4, vers_avant=True)
        L, H, W = 1.4, 0.75, 0.95
    else:
        bout = Vector((0, -l * 0.42, hz + h * 0.1))
        L, H, W = (2.6, 1.1, 1.4) if sorte == "mosa" else (2.4, 0.9, 1.1)
    tt = tete_carnivore((bout.y + L * 0.06, bout.z - H * 0.3), L, H, W, arcade=(sorte == "mosa"), rainures=False)
    queue, fin = segments("Queue", (0, l * 0.42, hz), 4 if sorte != "ichthyo" else 2, 1.3, w * 0.7, h * 0.7,
                          0.68, 0, 0)
    if sorte == "ichthyo":
        plaque("Nageoire", [(fin.y - 0.2, fin.z), (fin.y + 0.9, fin.z + 1.3), (fin.y + 0.5, fin.z),
                            (fin.y + 0.9, fin.z - 1.3)], 0.14, "Accent", biseau=0.03)
        plaque("Aileron", [(-0.6, hz + h / 2 - 0.1), (0.2, hz + h / 2 + 1.0), (0.6, hz + h / 2 - 0.1)], 0.14,
               "Accent", biseau=0.03)
    else:
        plaque("Nageoire", [(fin.y - 0.3, fin.z), (fin.y + 0.9, fin.z + 0.9), (fin.y + 0.6, fin.z - 0.1),
                            (fin.y + 0.8, fin.z - 0.6)], 0.12, "Accent", biseau=0.03)
    for s in (-1, 1):
        for y0, t_ in ((-l * 0.25, 1.0), (l * 0.25, 0.75)):
            pts = [(0, -0.3), (1.6 * t_, -0.1), (2.2 * t_, 0.35), (1.4 * t_, 0.45), (0, 0.35)]
            o = plaque("Palme", [(s * (w / 2 - 0.1 + x), y0 + y_) for x, y_ in pts], 0.14, "Accent", plan="xy",
                       decalage=(0, 0, hz - h * 0.3), biseau=0.03)
    if OEIL_X <= 1.2:
        bandes_corps(corps, (0, 0, hz), w, h, l, n=3)
    return {"corps": corps, "cou": cou, "tete": tt, "queue": queue, "fin_queue": fin, "w": w, "l": l, "h": h,
            "hz": hz, "d": {}}


# ---------- decors ----------
def _tete_obj(b):
    return b["tete"].objs[0]


def d_corne_nez(b, taille=1.0, mat="Corne"):
    tt = b["tete"]
    y, z = tt.p(0.85, 0.85 if tt.objs else 0.6)
    cone("CorneNez", (0, y, z), 0.18 * taille, 0.7 * taille, mat, (0, -0.4, 1), sommets=6)


def d_cornes_yeux(b, taille=1.0, mat="Corne", vers_avant=False):
    tt = b["tete"]
    for s in (-1, 1):
        y, z = tt.p(0.42, 0.95)
        d = (s * 0.15, -1, 0.75) if vers_avant else (s, 0.2, 0.7)
        cone("Corne", (s * tt.W * 0.25, y, z), 0.2 * taille, 1.0 * taille, mat, d, sommets=6)


def d_crete_ronde(b, mat="Accent"):
    tt = b["tete"]
    plaque("Crete", [tt.p(u, v) for u, v in ((0.3, 0.95), (0.45, 1.6), (0.8, 1.45), (0.95, 0.7), (0.6, 0.95))],
           max(0.12, tt.W * 0.1), mat, biseau=0.03)


def d_cretes2(b, mat="Accent"):
    tt = b["tete"]
    for s in (-1, 1):
        pts = [tt.p(u, v) for u, v in ((0.15, 0.9), (0.35, 1.7), (0.6, 1.55), (0.85, 0.9), (0.6, 0.95), (0.35, 0.98))]
        plaque("Crete", pts, 0.12, mat, decalage=(s * tt.W * 0.18, 0, 0), biseau=0.03)


def d_crete_casque(b, mat="Accent"):
    tt = b["tete"]
    plaque("Crete", [tt.p(u, v) for u, v in ((0.2, 0.9), (0.25, 1.6), (0.45, 1.95), (0.7, 1.6), (0.78, 0.9))],
           tt.W * 0.35, mat, biseau=0.05)


def d_crete_hache(b, mat="Accent"):
    tt = b["tete"]
    plaque("Crete", [tt.p(u, v) for u, v in ((0.15, 0.9), (0.3, 1.8), (0.75, 2.05), (0.65, 1.4), (0.55, 0.95))],
           tt.W * 0.25, mat, biseau=0.04)


def d_crete_tube(b, mat="Accent"):
    tt = b["tete"]
    y, z = tt.p(0.3, 0.9)
    boite("Crete", (0, y + tt.L * 0.45, z + tt.H * 0.27), (0.42, tt.L * 1.2, 0.46), mat, arriere=(0.7, 0.7), tangage=22)


def d_crete_pique(b, mat="Accent"):
    tt = b["tete"]
    y, z = tt.p(0.2, 0.9)
    cone("Crete", (0, y, z), 0.22, 1.2, mat, (0, 1, 0.6), sommets=4, echelle=(0.5, 1, 1))


def d_licorne(b, mat="Accent"):
    tt = b["tete"]
    y, z = tt.p(0.6, 0.95)
    boite("Licorne", (0, y, z + 0.6), (0.2, 0.2, 1.4), mat, tangage=-15)
    boite("Licorne", (0, y - 0.2, z + 1.25), (0.5, 0.15, 0.4), mat)


def d_dome(b, mat="Accent", piques=False):
    tt = b["tete"]
    y, z = tt.p(0.4, 0.95)
    ellipse("Dome", (0, y, z), (tt.W * 0.5, tt.L * 0.42, tt.H * 0.55), mat, seg=10, anneaux=6)
    if piques:
        for s in (-1, 1):
            for u in (0.1, 0.25, 0.4):
                yy, zz = tt.p(u, 0.8)
                cone("Corne", (s * tt.demi_largeur(u) * 0.9, yy, zz), 0.12, 0.5, "Corne", (s * 0.6, 0.6, 0.5))
            yn, zn = tt.p(0.9, 0.5)
            cone("Corne", (s * 0.15, yn, zn), 0.08, 0.3, "Corne", (s * 0.3, -0.5, 1))


def d_collerette(b, taille=1.0, sorte="simple", mat="Accent"):
    tt = b["tete"]
    y, z = tt.p(0.05, 0.6)
    k = taille * tt.W / 2.0
    pts = [(-1.5, -0.4), (-1.9, 0.6), (-1.4, 1.7), (0, 2.2), (1.4, 1.7), (1.9, 0.6), (1.5, -0.4)]
    plaque("Collerette", [(x * k, z_ * k) for x, z_ in pts], 0.2, mat, plan="xz", decalage=(0, y + 0.15, z), biseau=0.05)
    n = {"simple": 7, "pics": 6, "royale": 11}[sorte]
    for a in np.linspace(-160, -20, n):
        r = math.radians(a)
        L = (1.3 if sorte == "pics" else 0.35) * taille
        cone("Pointe", (1.75 * k * math.cos(r), y + 0.15, z + 0.8 * k - 1.35 * k * math.sin(r)), 0.16 * taille, L,
             "Corne", (math.cos(r), 0.3 if sorte == "pics" else 0, -math.sin(r)), sommets=6)


def d_bosse(b, mat="Accent"):
    hz, h, l = b["hz"], b["h"], b["l"]
    loc, _ = toucher(b["corps"], (0, l * 0.25, 60), (0, 0, -1))
    if loc:
        cone("Bosse", loc - Vector((0, 0, 0.3)), 0.5, 1.4, mat, (0, 0.2, 1), sommets=4, echelle=(0.35, 1, 1))


def d_voile(b, hauteur=3.0, mat="Accent", epines=True):
    hz, h, l = b["hz"], b["h"], b["l"]
    top = hz + h / 2 - 0.2
    y0, y1 = -l * 0.6, l * 1.1
    pts = [(y0, top), (y0 + (y1 - y0) * 0.1, top + hauteur * 0.55), (y0 + (y1 - y0) * 0.3, top + hauteur * 0.95),
           (y0 + (y1 - y0) * 0.55, top + hauteur), (y0 + (y1 - y0) * 0.8, top + hauteur * 0.75), (y1, top - 0.1)]
    plaque("Voile", pts, 0.18, mat, biseau=0.04)
    if epines:
        echant = le_long(pts, 0.05)
        for y in np.linspace(y0 + 0.4, y1 - 0.4, 9):
            hy = max(zz for (yy, zz) in echant if abs(yy - y) < 0.08) - top
            boite("Epine", (0, y, top + hy / 2), (0.24, 0.16, hy), "Rayure", biseau=0.03)


def d_plaques(b, mat="Accent", taille=1.0):
    cibles = [b["corps"]] + [q[0] for q in b["queue"]] + [c[0] for c in b["cou"]]
    y, k = -b["l"] * 0.55, 0
    while y < b["l"] * 1.3:
        loc, _ = toucher(cibles, (0, y, 60), (0, 0, -1))
        if loc:
            hmax = (1.4 * math.exp(-((y - 0.2) / 2.2) ** 2) + 0.35) * taille
            s = -1 if k % 2 else 1
            cone("Plaque", (s * 0.22, y, loc.z - 0.15), hmax * 0.55, hmax, mat, (s * 0.15, 0, 1), sommets=4,
                 echelle=(0.18, 1, 1))
        y += 0.42
        k += 1


def d_piques_queue(b, mat="Corne"):
    fin = b["fin_queue"]
    for s in (-1, 1):
        for dy in (-0.4, 0.1):
            cone("Pique", fin + Vector((s * 0.15, dy, 0.1)), 0.12, 0.9, mat, (s, 0.5, 0.5), sommets=6)


def d_piques_epaules(b, mat="Corne"):
    for s in (-1, 1):
        loc, n = toucher(b["corps"], (s * 20, -b["l"] * 0.25, b["hz"] + 0.3), (-s, 0, 0))
        if loc:
            cone("Pique", loc, 0.2, 1.2, mat, (s, 0.4, 0.4), sommets=6)


def d_armure_dos(b, mat="Accent"):
    for y in np.linspace(-b["l"] * 0.4, b["l"] * 0.4, 5):
        for x in np.linspace(-b["w"] * 0.35, b["w"] * 0.35, 4):
            loc, n = toucher(b["corps"], (x, y, 50), (0, 0, -1))
            if loc:
                boite("Ecaille", (x, y, loc.z + 0.05), (b["w"] * 0.16, 0.45, 0.22), mat)
    for s in (-1, 1):
        for y in np.linspace(-b["l"] * 0.4, b["l"] * 0.45, 5):
            loc, n = toucher(b["corps"], (s * 20, y, b["hz"] + 0.1), (-s, 0, 0))
            if loc:
                cone("Pique", loc, 0.2, 0.6, "Corne", (s, 0.3, 0.1))


def d_massue(b, mat="Corne"):
    boite("Massue", b["fin_queue"] + Vector((0, 0.3, 0)), (1.1, 0.85, 0.65), mat, biseau=0.15)


def d_plumes(b, mat="Accent"):
    tt = b["tete"]
    for k, u in enumerate((0.0, 0.12, 0.24)):
        y, z = tt.p(u, 0.9)
        cone("Plume", (0, y + 0.1, z), 0.25, 0.7 - k * 0.12, mat, (0, 1, 0.8), echelle=(0.35, 1, 1))
    eventail(b["fin_queue"] + Vector((0, -0.2, 0)), 5, 1.1, mat)
    for s in (-1, 1):
        cone("Plume", (s * (b["w"] / 2 + 0.2), -b["l"] * 0.4, b["hz"] - b["h"] * 0.1), 0.3, 0.9, mat,
             (s * 0.3, 1, -0.6), echelle=(0.25, 1, 1))


def d_griffes_geantes(b, mat="Griffe"):
    for s in (-1, 1):
        x = s * (b["w"] / 2 + 0.1)
        for dx in (-0.12, 0, 0.12):
            cone("Griffe", (x + dx, -b["l"] * 0.42 - 0.9, b["hz"] - b["h"] * 0.45), 0.08, 1.2, mat, (0, -0.3, -1))


def d_epines_cou(b, mat="Accent"):
    for o, c, w, h in b["cou"]:
        for s in (-1, 1):
            cone("Epine", c + Vector((s * w * 0.2, 0, h * 0.4)), 0.1, 1.1, mat, (s * 0.25, 0.3, 1), sommets=4)


def d_taches(b, mat="Rayure", n=12):
    for _ in range(n):
        s = R.choice((-1, 1))
        y = R.uniform(-b["l"] * 0.4, b["l"] * 0.4)
        z = b["hz"] + R.uniform(-0.1, 0.45) * b["h"]
        loc, nrm = toucher(b["corps"], (s * 30, y, z), (-s, 0, 0))
        if loc:
            t_ = R.uniform(0.18, 0.32)
            ellipse("Tache", loc, (t_, t_ * 1.2, 0.04), mat, rot=nrm.to_track_quat('Z', 'Y'), seg=6, anneaux=4)


def d_piques_dos(b, mat="Accent", taille=1.0):
    piques_dos(-b["l"] * 0.6, b["l"] * 1.6, 0.45, 0.6 * taille, 0.25 * taille, mat=mat, largeur=0.4)


# fantastiques
def d_cristaux(b, mat="Gemme", n=4):
    for y in np.linspace(-b["l"] * 0.35, b["l"] * 0.35, n):
        loc, _ = toucher(b["corps"], (0, y, 60), (0, 0, -1))
        if loc:
            cristaux(loc - Vector((0, 0, 0.2)), 3, 1.0, mat, rayon=0.4)


def d_flammes(b, mat="Lueur", mat2="Accent"):
    points = []
    loc, _ = toucher(b["corps"], (0, 0, 60), (0, 0, -1))
    if loc:
        points.append(loc)
    points.append(b["fin_queue"])
    y, z = b["tete"].p(0.2, 1.0)
    points.append(Vector((0, y, z)))
    for p in points:
        cone("Flamme", p, 0.35, 1.2, mat, (0, 0.3, 1), sommets=4)
        for s in (-1, 1):
            cone("Flamme", p + Vector((s * 0.2, 0.1, 0)), 0.25, 0.8, mat2, (s * 0.5, 0.4, 1), sommets=4)


def d_ailes(b, sorte="dragon", membrane="Accent", os_mat="Rayure", taille=1.0):
    base = (0, -b["l"] * 0.15, b["hz"] + b["h"] * 0.4)
    for s in (-1, 1):
        if sorte == "dragon":
            aile_dragon(s, base, 1.5 * taille, membrane, os_mat)
        else:
            aile_plumes_v(s, base, 1.5 * taille, membrane, os_mat)


def aile_plumes_v(s, base, t, mat1, mat2):
    """Aile a plumes dressee (style pegase / ange) : deux couches de plumes."""
    couches = ((mat2, 1.0, 0.0), (mat1, 0.72, 0.05))
    for mat, k, dy in couches:
        pts = [(0.1, -0.2), (0.6 * k, 0.9 * k), (1.3 * k, 1.8 * k), (2.0 * k, 2.3 * k)]
        for i in range(6):
            a = i / 5
            pts.append(((2.0 - 0.9 * a) * k + (0.25 if i % 2 else 0), (2.3 - 2.3 * a) * k - (0.2 if i % 2 else 0)))
        pts.append((0.4 * k, -0.3))
        plaque("Aile", [(s * x * t, z * t) for x, z in pts], 0.09, mat, plan="xz",
               decalage=(base[0], base[1] + 0.1 + dy, base[2]), biseau=0.02)


def d_halo(b, mat="Lueur"):
    y, z = b["tete"].p(0.4, 1.0)
    c = Vector((0, y, z + 0.9))
    for k in range(12):
        a = 2 * math.pi * k / 12
        boite("Halo", c + Vector((0.7 * math.cos(a), 0.7 * math.sin(a), 0)), (0.3, 0.3, 0.12), mat, biseau=0.02,
              lacet=math.degrees(a))


def d_couronne(b, mat="Accent", gemme_mat="Gemme"):
    y, z = b["tete"].p(0.4, 1.0)
    boite("Couronne", (0, y, z + 0.2), (0.9, 0.9, 0.3), mat, biseau=0.04)
    for x in (-0.35, 0, 0.35):
        cone("Pointe", (x, y - 0.35, z + 0.35), 0.13, 0.45 if x == 0 else 0.32, mat, (0, 0, 1), sommets=4)
        cone("Pointe", (x, y + 0.35, z + 0.35), 0.13, 0.32, mat, (0, 0, 1), sommets=4)
    gemme((0, y - 0.47, z + 0.2), 0.14, gemme_mat)


def d_cornes_demon(b, mat="Corne"):
    tt = b["tete"]
    for s in (-1, 1):
        y, z = tt.p(0.25, 0.95)
        p = Vector((s * tt.W * 0.3, y, z))
        d = Vector((s * 0.6, 0.3, 1)).normalized()
        for k in range(3):
            o = boite("CorneDemon", p + d * 0.3, (0.3 - k * 0.06, 0.3 - k * 0.06, 0.6), mat, biseau=0.04)
            o.rotation_mode = 'QUATERNION'
            o.rotation_quaternion = d.to_track_quat('Z', 'Y')
            p = p + d * 0.55
            d = (d + Vector((0, 0.5, -0.1))).normalized()
        cone("Corne", p, 0.12, 0.5, mat, d, sommets=4)


def d_chaines(b, mat="Rayure"):
    hz, w, l, h = b["hz"], b["w"], b["l"], b["h"]
    for s in (-1, 1):
        a = Vector((s * w * 0.45, -l * 0.35, hz + h * 0.35))
        c = Vector((-s * w * 0.45, l * 0.25, hz - h * 0.3))
        for k in range(9):
            p = a.lerp(c, k / 8) + Vector((s * 0.15, 0, 0))
            boite("Chaine", p, (0.18, 0.32, 0.18) if k % 2 else (0.18, 0.18, 0.32), mat, biseau=0.03)


def d_armure(b, mat="Accent", mat2="Rayure", gemme_mat="Lueur"):
    """Plaques d'armure, epaulieres a pointes, coeur lumineux sur le torse."""
    hz, w, l, h = b["hz"], b["w"], b["l"], b["h"]
    bandes_corps(b["corps"], (0, 0, hz), w + 0.1, h * 1.05, l, n=3, couleur=mat)
    for s in (-1, 1):
        loc, nrm = toucher(b["corps"], (s * 20, -l * 0.3, hz + h * 0.25), (-s, 0, 0))
        if loc:
            boite("Epauliere", loc + Vector((s * 0.15, 0, 0.1)), (0.5, 1.2, 0.7), mat, biseau=0.08)
            for k in range(3):
                cone("Pique", loc + Vector((s * 0.35, -0.4 + k * 0.4, 0.4)), 0.14, 0.6, mat2, (s * 0.6, 0.2, 1))
    loc, nrm = toucher(b["corps"], (0, -40, hz), (0, 1, 0))
    if loc:
        gemme(loc + Vector((0, -0.1, 0)), 0.35, gemme_mat)
        boite("Coeur", loc + Vector((0, 0.05, 0)), (0.9, 0.12, 0.9), mat2, biseau=0.04, lacet=0, roulis=45)


def d_mecha(b, mat="Accent", mat2="Rayure", lueur="Lueur"):
    """Robot : panneaux, boulons, visiere et coeur lumineux."""
    d_armure(b, mat, mat2, lueur)
    tt = b["tete"]
    y, z = tt.p(0.45, 0.62)
    boite("Visiere", (0, y, z), (tt.W * 1.02, tt.L * 0.25, tt.H * 0.16), lueur, biseau=0.02)
    for o, c, w, h in b["queue"][:2] + [(b["corps"], Vector((0, 0, b["hz"])), b["w"], b["h"])]:
        for s in (-1, 1):
            loc, nrm = toucher(o, (s * 20, c.y, c.z), (-s, 0, 0))
            if loc:
                ellipse("Boulon", loc, (0.12, 0.12, 0.06), mat2, rot=nrm.to_track_quat('Z', 'Y'), seg=6, anneaux=4)


def d_yeux_lueur(b, mat="Lueur"):
    pass  # les yeux lumineux viennent de la couleur "Oeil" de la palette


def d_gemmes_corps(b, mat="Lueur"):
    for s in (-1, 1):
        for y in np.linspace(-b["l"] * 0.35, b["l"] * 0.35, 3):
            loc, n = toucher(b["corps"], (s * 30, y, b["hz"] + b["h"] * 0.15), (-s, 0, 0))
            if loc:
                gemme(loc, 0.22, mat)


def d_noyau(b, mat="Lueur"):
    """Coeur lumineux sur le torse, avec des fissures qui rayonnent."""
    loc, n = toucher(b["corps"], (0, -40, b["hz"] + b["h"] * 0.1), (0, 1, 0))
    if loc is None:
        return
    gemme(loc + Vector((0, -0.1, 0)), 0.45, mat)
    for k in range(8):
        a = 2 * math.pi * k / 8
        L = R.uniform(0.6, 1.0)
        p = loc + Vector((math.cos(a) * L * 0.6, -0.04, math.sin(a) * L * 0.6))
        boite("Fissure", p, (L, 0.06, 0.1), mat, biseau=0, roulis=-math.degrees(a))


def d_bras_multiples(b):
    w, l, h, hz = b["w"], b["l"], b["h"], b["hz"]
    for k, dz in enumerate((0.35, -0.25)):
        for s in (-1, 1):
            bras(s * (w / 2 + 0.25), -l * 0.3 + k * 0.4, hz + h * dz, (0.45, 0.9, 1.0), griffes=3, griffe=0.3)


def d_ailes4(b):
    base = (0, -b["l"] * 0.15, b["hz"] + b["h"] * 0.4)
    for s in (-1, 1):
        aile_plumes_v(s, base, 1.7, "Gemme", "Accent")
        aile_plumes_v(s, (base[0], base[1] + 0.35, base[2] - 0.6), 1.15, "Accent", "Gemme")


def d_aureole(b, mat="Lueur"):
    """Grand anneau dresse derriere les epaules."""
    c = Vector((0, b["l"] * 0.05, b["hz"] + b["h"] * 0.9 + 1.0))
    for k in range(18):
        a = 2 * math.pi * k / 18
        boite("Aureole", c + Vector((1.6 * math.cos(a), 0, 1.6 * math.sin(a))), (0.38, 0.14, 0.2), mat, biseau=0.02,
              roulis=-math.degrees(a) + 90)


def d_eventail_paon(b, mat="Accent", oeil_mat="Lueur"):
    """Queue en eventail de paon, avec un oeil de gemme sur chaque plume."""
    c = b["fin_queue"] + Vector((0, -0.6, 0.2))
    for k in range(11):
        a = math.radians(-80 + 160 * k / 10)
        L = 3.2
        pts = [(0, 0), (0.35, L * 0.55), (0, L), (-0.35, L * 0.55)]
        o = plaque("PlumePaon", pts, 0.08, mat if k % 2 else "Gemme", plan="xz", decalage=c, biseau=0.02)
        o.rotation_euler = (0, a, 0)
        tip = c + Vector((math.sin(a) * L * 0.75, 0.05, math.cos(a) * L * 0.75))
        gemme(tip, 0.2, oeil_mat)


def d_lance(b, mat="Accent", lueur="Lueur"):
    w, l, h, hz = b["w"], b["l"], b["h"], b["hz"]
    x = w / 2 + 0.5
    boite("Lance", (x, -l * 0.6, hz), (0.16, 0.16, 5.5), mat, biseau=0.03, tangage=-15)
    cone("PointeLance", (x, -l * 0.6 - 0.7, hz + 2.65), 0.25, 0.9, lueur, (0, -0.26, 1), sommets=4)
    gemme((x, -l * 0.6 - 0.65, hz + 2.45), 0.2, lueur)


DECORS = {
    "corne_nez": d_corne_nez, "cornes_yeux": d_cornes_yeux, "cornes_avant": lambda b: d_cornes_yeux(b, 1.4, vers_avant=True),
    "crete_ronde": d_crete_ronde, "cretes2": d_cretes2, "crete_casque": d_crete_casque, "crete_hache": d_crete_hache,
    "crete_tube": d_crete_tube, "crete_pique": d_crete_pique, "licorne": d_licorne, "dome": d_dome,
    "dome_piques": lambda b: d_dome(b, piques=True), "collerette": d_collerette,
    "collerette_pics": lambda b: d_collerette(b, 1.0, "pics"), "collerette_royale": lambda b: d_collerette(b, 1.1, "royale"),
    "grande_collerette": lambda b: d_collerette(b, 1.35), "bosse": d_bosse, "voile": d_voile,
    "voile_basse": lambda b: d_voile(b, 1.2, epines=False), "plaques": d_plaques, "piques_queue": d_piques_queue,
    "piques_epaules": d_piques_epaules, "armure_dos": d_armure_dos, "massue": d_massue, "plumes": d_plumes,
    "griffes_geantes": d_griffes_geantes, "epines_cou": d_epines_cou, "taches": d_taches, "piques_dos": d_piques_dos,
    "piques_lueur": lambda b: d_piques_dos(b, "Lueur", 1.3), "cristaux": d_cristaux, "flammes": d_flammes,
    "ailes_dragon": d_ailes, "ailes_plumes": lambda b: d_ailes(b, "plumes", "Gemme", "Accent"),
    "ailes_ange_demon": None, "halo": d_halo, "couronne": d_couronne, "cornes_demon": d_cornes_demon,
    "chaines": d_chaines, "armure": d_armure, "mecha": d_mecha, "yeux_lueur": d_yeux_lueur,
}


def d_ailes_ange_demon(b):
    base = (0, -b["l"] * 0.15, b["hz"] + b["h"] * 0.4)
    aile_plumes_v(-1, base, 1.6, "Gemme", "Accent")
    aile_dragon(1, base, 1.6, "Bouche", "Rayure")


DECORS["ailes_ange_demon"] = d_ailes_ange_demon
DECORS.update(gemmes_corps=d_gemmes_corps, noyau=d_noyau, bras_multiples=d_bras_multiples, ailes4=d_ailes4,
              aureole=d_aureole, eventail_paon=d_eventail_paon, lance=d_lance)

# ---------- palettes (Peau, Rayure, Ventre, Accent, Corne, Oeil, Lueur, Gemme) ----------
PALETTES = {
    # communs : couleurs simples
    "olive": dict(Peau=(128, 146, 78), Rayure=(90, 104, 56)),
    "sable": dict(Peau=(214, 184, 126), Rayure=(170, 136, 86), Accent=(190, 120, 70)),
    "terre": dict(Peau=(150, 104, 70), Rayure=(104, 70, 46), Accent=(200, 140, 80)),
    "gris": dict(Peau=(140, 144, 150), Rayure=(98, 102, 110), Accent=(200, 120, 70)),
    "mousse": dict(Peau=(104, 150, 92), Rayure=(66, 104, 60), Accent=(220, 190, 90)),
    "beige": dict(Peau=(222, 204, 170), Rayure=(176, 150, 112), Accent=(160, 110, 80)),
    "rouille": dict(Peau=(184, 110, 72), Rayure=(130, 72, 46), Accent=(240, 200, 120)),
    "kaki": dict(Peau=(160, 156, 104), Rayure=(116, 112, 70), Accent=(110, 140, 80)),
    # peu communs
    "vert_vif": dict(Peau=(100, 186, 84), Rayure=(60, 130, 52), Accent=(250, 200, 60)),
    "ocre": dict(Peau=(222, 164, 64), Rayure=(166, 112, 40), Accent=(180, 70, 50)),
    "bleu_gris": dict(Peau=(108, 132, 168), Rayure=(72, 90, 120), Accent=(240, 160, 70)),
    "terracotta": dict(Peau=(204, 114, 84), Rayure=(146, 74, 54), Accent=(90, 150, 140)),
    "sarcelle": dict(Peau=(72, 150, 140), Rayure=(44, 104, 98), Accent=(240, 130, 50)),
    "fauve": dict(Peau=(196, 150, 92), Rayure=(90, 60, 40), Accent=(220, 70, 60)),
    # rares
    "bleu": dict(Peau=(62, 110, 200), Rayure=(36, 66, 140), Accent=(250, 210, 70), Ventre=(220, 230, 250)),
    "violet": dict(Peau=(130, 90, 190), Rayure=(86, 56, 140), Accent=(250, 180, 80), Ventre=(236, 226, 250)),
    "rouge": dict(Peau=(196, 60, 52), Rayure=(110, 30, 30), Accent=(250, 200, 70), Ventre=(250, 226, 206)),
    "orange_noir": dict(Peau=(236, 130, 40), Rayure=(40, 32, 30), Accent=(250, 220, 90)),
    "emeraude": dict(Peau=(40, 160, 110), Rayure=(20, 100, 70), Accent=(250, 220, 90)),
    "jaune_noir": dict(Peau=(240, 200, 50), Rayure=(36, 32, 30), Accent=(220, 60, 50)),
    "rose": dict(Peau=(236, 130, 170), Rayure=(180, 80, 120), Accent=(120, 200, 230), Ventre=(252, 230, 240)),
    # epiques
    "neon": dict(Peau=(30, 30, 46), Rayure=(60, 255, 200), Accent=(255, 60, 220), Ventre=(60, 60, 90), Oeil=(60, 255, 200),
                 Lueur=(60, 255, 200)),
    "jade": dict(Peau=(60, 170, 120), Rayure=(30, 110, 80), Accent=(250, 210, 90), Corne=(250, 236, 180),
                 Gemme=(140, 255, 190), Oeil=(250, 210, 90)),
    "volcan": dict(Peau=(46, 40, 42), Rayure=(250, 110, 30), Accent=(255, 140, 40), Ventre=(110, 90, 86),
                   Oeil=(255, 170, 40), Lueur=(255, 150, 40)),
    "fer": dict(Peau=(120, 126, 140), Rayure=(70, 76, 90), Accent=(190, 196, 210), Corne=(230, 234, 240),
                Oeil=(255, 80, 60)),
    "ciel": dict(Peau=(130, 180, 250), Rayure=(250, 250, 255), Accent=(255, 220, 120), Ventre=(240, 248, 255),
                 Gemme=(255, 255, 255)),
    "corail": dict(Peau=(250, 130, 110), Rayure=(250, 220, 200), Accent=(70, 200, 210), Ventre=(255, 236, 226)),
    "venin": dict(Peau=(120, 210, 60), Rayure=(60, 30, 90), Accent=(170, 60, 230), Oeil=(250, 240, 60),
                  Lueur=(170, 255, 80)),
    "glacial": dict(Peau=(200, 230, 250), Rayure=(110, 170, 230), Accent=(150, 220, 255), Gemme=(170, 240, 255),
                    Oeil=(90, 200, 255), Lueur=(160, 240, 255)),
    "marais": dict(Peau=(70, 110, 80), Rayure=(40, 70, 50), Accent=(120, 220, 160), Oeil=(250, 230, 80)),
    "abysse": dict(Peau=(24, 42, 90), Rayure=(14, 24, 56), Accent=(60, 220, 240), Ventre=(80, 110, 170),
                   Oeil=(60, 240, 255), Lueur=(60, 240, 255)),
    "ombre": dict(Peau=(46, 36, 70), Rayure=(26, 20, 40), Accent=(170, 90, 255), Ventre=(90, 76, 120),
                  Oeil=(200, 120, 255), Lueur=(190, 120, 255)),
    "soleil": dict(Peau=(250, 200, 70), Rayure=(230, 120, 40), Accent=(255, 240, 160), Oeil=(255, 120, 40)),
    "toxique": dict(Peau=(40, 50, 40), Rayure=(140, 255, 60), Accent=(140, 255, 60), Oeil=(140, 255, 60),
                    Lueur=(140, 255, 60), Ventre=(80, 100, 70)),
    # legendaires et +
    "or": dict(Peau=(240, 190, 50), Rayure=(40, 34, 30), Accent=(255, 230, 120), Corne=(40, 34, 30),
               Ventre=(255, 240, 190), Oeil=(255, 70, 40), Lueur=(255, 236, 140), Gemme=(255, 70, 90)),
    "lave": dict(Peau=(34, 28, 30), Rayure=(255, 100, 20), Accent=(255, 150, 30), Ventre=(80, 60, 56),
                 Oeil=(255, 200, 40), Lueur=(255, 130, 30), Corne=(255, 170, 60), Gemme=(255, 120, 30)),
    "cristal": dict(Peau=(160, 210, 250), Rayure=(100, 150, 230), Accent=(200, 240, 255), Gemme=(140, 230, 255),
                    Lueur=(180, 245, 255), Oeil=(60, 160, 255)),
    "aurore": dict(Peau=(80, 200, 180), Rayure=(160, 90, 220), Accent=(120, 255, 200), Gemme=(220, 140, 255),
                   Lueur=(140, 255, 210)),
    "tonnerre": dict(Peau=(40, 50, 90), Rayure=(250, 230, 70), Accent=(250, 230, 70), Lueur=(120, 220, 255),
                     Oeil=(120, 220, 255), Ventre=(110, 120, 160)),
    "spectre": dict(Peau=(200, 220, 240), Rayure=(130, 150, 190), Accent=(120, 250, 230), Ventre=(240, 248, 255),
                    Oeil=(80, 255, 220), Lueur=(120, 255, 230)),
    "samourai": dict(Peau=(170, 30, 36), Rayure=(30, 26, 28), Accent=(30, 26, 28), Corne=(240, 200, 80),
                     Oeil=(255, 220, 80), Lueur=(255, 210, 80)),
    "galaxie": dict(Peau=(30, 24, 70), Rayure=(255, 240, 160), Accent=(150, 80, 230), Ventre=(70, 50, 130),
                    Gemme=(255, 120, 220), Lueur=(255, 240, 170), Oeil=(255, 240, 170)),
    "demon": dict(Peau=(40, 20, 24), Rayure=(120, 16, 24), Accent=(210, 30, 40), Corne=(30, 20, 20),
                  Bouche=(255, 60, 30), Oeil=(255, 210, 40), Lueur=(255, 200, 40), Gemme=(255, 200, 40)),
    "golem": dict(Peau=(190, 140, 50), Rayure=(40, 36, 34), Accent=(220, 170, 60), Corne=(40, 36, 34),
                  Oeil=(255, 230, 100), Lueur=(255, 220, 90), Ventre=(150, 110, 40)),
    "feu": dict(Peau=(230, 210, 180), Rayure=(30, 26, 26), Accent=(255, 120, 30), Corne=(30, 26, 26),
                Oeil=(255, 120, 30), Lueur=(255, 150, 40), Gemme=(255, 90, 30)),
    "divin": dict(Peau=(250, 248, 240), Rayure=(240, 200, 80), Accent=(255, 220, 100), Corne=(240, 200, 80),
                  Gemme=(255, 255, 255), Lueur=(255, 236, 150), Oeil=(80, 180, 255), Ventre=(255, 250, 230)),
    "ange_demon": dict(Peau=(236, 232, 226), Rayure=(30, 24, 26), Accent=(240, 190, 60), Corne=(30, 24, 26),
                       Gemme=(255, 230, 120), Bouche=(220, 40, 30), Lueur=(255, 210, 80), Oeil=(255, 60, 40)),
    "arcenciel": dict(Peau=(250, 250, 255), Rayure=(240, 70, 80), Accent=(80, 160, 250), Corne=(250, 210, 60),
                      Gemme=(80, 220, 120), Lueur=(190, 100, 240), Oeil=(80, 160, 250)),
    "fossile": dict(Peau=(236, 226, 200), Rayure=(60, 50, 44), Accent=(200, 186, 156), Corne=(236, 226, 200),
                    Ventre=(210, 198, 170), Oeil=(80, 255, 140), Lueur=(80, 255, 140), Bouche=(40, 34, 30)),
    "vide": dict(Peau=(22, 24, 48), Rayure=(12, 12, 28), Accent=(60, 70, 140), Corne=(40, 44, 80),
                 Ventre=(50, 56, 100), Oeil=(120, 240, 255), Lueur=(120, 240, 255), Gemme=(120, 240, 255)),
    "cristal_rose": dict(Peau=(236, 140, 210), Rayure=(170, 70, 170), Accent=(250, 190, 240), Corne=(180, 90, 220),
                         Gemme=(255, 170, 240), Lueur=(255, 200, 250), Oeil=(200, 60, 200), Ventre=(252, 220, 245)),
    "seraphin": dict(Peau=(236, 230, 214), Rayure=(220, 170, 60), Accent=(250, 200, 70), Corne=(220, 170, 60),
                     Gemme=(255, 240, 160), Lueur=(255, 236, 120), Oeil=(250, 190, 40), Ventre=(250, 244, 226)),
    "ciel_divin": dict(Peau=(170, 210, 255), Rayure=(255, 255, 255), Accent=(255, 220, 120), Corne=(255, 220, 120),
                       Gemme=(255, 255, 255), Lueur=(255, 240, 170), Oeil=(80, 150, 255), Ventre=(240, 248, 255)),
    "empereur": dict(Peau=(30, 26, 30), Rayure=(240, 190, 50), Accent=(240, 190, 50), Corne=(240, 190, 50),
                     Gemme=(255, 50, 80), Lueur=(255, 220, 110), Oeil=(255, 60, 60), Ventre=(80, 66, 60)),
}

# ---------- les 150 ----------
# (nom, famille, decors, palette)
LISTE = {
    "Commun": [
        ("Coelophysis", "petit_thero", [], "olive"), ("Herrerasaurus", "petit_thero", ["taches"], "terre"),
        ("Staurikosaurus", "petit_thero", [], "sable"), ("Segisaurus", "petit_thero", [], "gris"),
        ("Tawa", "petit_thero", ["taches"], "rouille"), ("Procompsognathus", "petit_thero", [], "mousse"),
        ("Lesothosaurus", "petit_ornitho", [], "beige"),
        ("Heterodontosaurus", "petit_ornitho", ["taches"], "sable"), ("Dryosaurus", "petit_ornitho", [], "mousse"),
        ("Thescelosaurus", "petit_ornitho", [], "olive"), ("Orodromeus", "petit_ornitho", [], "terre"),
        ("Camptosaurus", "ornitho", [], "gris"),
        ("Tenontosaurus", "ornitho", [], "rouille"), ("Muttaburrasaurus", "ornitho", [], "beige"),
        ("Leptoceratops", "cerato_petit", [], "sable"), ("Bagaceratops", "cerato_petit", ["corne_nez"], "terre"),
        ("Archaeoceratops", "cerato_petit", [], "mousse"), ("Scelidosaurus", "ankylo_petit", ["armure_dos"], "gris"),
        ("Scutellosaurus", "ankylo_petit", ["armure_dos"], "kaki"), ("Gargoyleosaurus", "ankylo", ["armure_dos"], "terre"),
        ("Nodosaurus", "ankylo", ["armure_dos"], "olive"), ("Huayangosaurus", "stego", ["plaques"], "rouille"),
        ("Dacentrurus", "stego", ["plaques", "piques_queue"], "gris"), ("Plateosaurus", "prosauro", [], "sable"),
        ("Massospondylus", "prosauro", ["taches"], "mousse"), ("Anchisaurus", "prosauro", [], "beige"),
        ("Riojasaurus", "prosauro", [], "kaki"), ("Dimorphodon", "ptero_petit", [], "terre"),
        ("Rhamphorhynchus", "ptero_petit", ["queue_longue"], "olive"), ("Pterodactylus", "ptero_petit", [], "gris"),
        ("Anurognathus", "ptero_petit", [], "beige"), ("Nothosaurus", "marin_petit", [], "mousse"),
        ("Mixosaurus", "marin_petit_ichthyo", [], "gris"),
    ],
    "Peu commun": [
        ("Ceratosaurus", "thero", ["corne_nez"], "fauve"), ("Cryolophosaurus", "thero", ["crete_ronde"], "ocre"),
        ("Monolophosaurus", "thero", ["crete_ronde"], "terracotta"), ("Guanlong", "petit_thero", ["crete_ronde"], "vert_vif"),
        ("Eustreptospondylus", "thero", [], "bleu_gris"), ("Megalosaurus", "thero", ["taches"], "fauve"),
        ("Majungasaurus", "thero", ["dome"], "terracotta"),
        ("Concavenator", "thero", ["bosse"], "ocre"), ("Sinraptor", "thero", [], "vert_vif"),
        ("Corythosaurus", "ornitho", ["crete_casque"], "sarcelle"), ("Lambeosaurus", "ornitho", ["crete_hache"], "ocre"),
        ("Maiasaura", "ornitho", ["taches"], "bleu_gris"), ("Edmontosaurus", "ornitho", [], "vert_vif"),
        ("Saurolophus", "ornitho", ["crete_pique"], "terracotta"), ("Tsintaosaurus", "ornitho", ["licorne"], "fauve"),
        ("Hypacrosaurus", "ornitho", ["crete_casque"], "bleu_gris"), ("Stygimoloch", "pachy", ["dome_piques"], "terracotta"),
        ("Stegoceras", "pachy", ["dome"], "sarcelle"),
        ("Centrosaurus", "cerato", ["collerette", "corne_nez"], "fauve"),
        ("Chasmosaurus", "cerato", ["grande_collerette", "cornes_avant"], "bleu_gris"),
        ("Pachyrhinosaurus", "cerato", ["collerette"], "terracotta"),
        ("Einiosaurus", "cerato", ["collerette", "corne_nez"], "vert_vif"),
        ("Euoplocephalus", "ankylo", ["armure_dos", "massue"], "ocre"),
        ("Edmontonia", "ankylo", ["armure_dos", "piques_epaules"], "bleu_gris"),
        ("Diplodocus", "sauro_long", [], "sarcelle"), ("Camarasaurus", "sauro", [], "fauve"),
        ("Plesiosaurus", "marin_plesio", [], "bleu_gris"), ("Tapejara", "ptero_voile", [], "terracotta"),
    ],
    "Rare": [
        ("Carcharodontosaurus", "rex", [], "rouge"), ("Acrocanthosaurus", "thero", ["voile_basse"], "orange_noir"),
        ("Albertosaurus", "thero", [], "bleu"), ("Daspletosaurus", "rex", ["taches"], "violet"),
        ("Tarbosaurus", "rex", [], "emeraude"), ("Yutyrannus", "rex", ["plumes"], "rose"),
        ("Torvosaurus", "thero", ["piques_dos"], "jaune_noir"), ("Utahraptor", "raptor", ["plumes"], "bleu"),
        ("Deinonychus", "raptor", ["plumes"], "rouge"),
        ("Therizinosaurus", "ornitho", ["griffes_geantes", "plumes"], "violet"),
        ("Ouranosaurus", "ornitho", ["voile_basse"], "orange_noir"),
        ("Styracosaurus", "cerato", ["collerette_pics", "corne_nez"], "jaune_noir"),
        ("Kosmoceratops", "cerato", ["collerette_royale", "cornes_yeux"], "rose"),
        ("Torosaurus", "cerato", ["grande_collerette", "cornes_avant"], "bleu"),
        ("Kentrosaurus", "stego", ["plaques", "piques_epaules", "piques_queue"], "emeraude"),
        ("Tuojiangosaurus", "stego", ["plaques", "piques_queue"], "rouge"),
        ("Miragaia", "stego_long", ["plaques"], "violet"), ("Saichania", "ankylo", ["armure_dos", "massue"], "jaune_noir"),
        ("Pinacosaurus", "ankylo", ["armure_dos", "massue"], "bleu"),
        ("Amargasaurus", "sauro", ["epines_cou"], "orange_noir"), ("Mamenchisaurus", "sauro_long", [], "emeraude"),
        ("Dreadnoughtus", "sauro", ["taches"], "rose"), ("Quetzalcoatlus", "ptero", [], "rouge"),
        ("Elasmosaurus", "marin_plesio", [], "bleu"),
        ("Ichthyosaurus", "marin_ichthyo", [], "emeraude"), ("Liopleurodon", "marin", [], "violet"),
    ],
    "Epique": [
        ("Mosasaurus", "marin", ["piques_dos"], "abysse"), ("Argentinosaurus", "sauro", ["taches"], "ciel"),
        ("Shonisaurus", "marin_ichthyo", [], "glacial"), ("Deinocheirus", "ornitho", ["voile_basse", "griffes_geantes"], "soleil"),
        ("Kronosaurus", "marin", [], "ombre"), ("Patagotitan", "sauro_long", ["taches"], "corail"),
        ("Tylosaurus", "marin", ["piques_dos"], "venin"), ("Raptor Neon", "raptor", ["plumes", "piques_lueur"], "neon"),
        ("Triceratops de Jade", "cerato", ["grande_collerette", "cornes_avant", "corne_nez"], "jade"),
        ("Stego Volcanique", "stego", ["plaques", "piques_queue"], "volcan"),
        ("Ankylo de Fer", "ankylo", ["armure_dos", "massue", "piques_epaules"], "fer"),
        ("Brachio Celeste", "sauro", ["cristaux"], "ciel"), ("Ptero Tempete", "ptero", [], "tonnerre"),
        ("Parasaur Corail", "ornitho", ["crete_tube"], "corail"),
        ("Dilopho Venin", "thero", ["cretes2", "piques_dos"], "venin"),
        ("Carno Infernal", "thero", ["cornes_yeux", "piques_dos"], "volcan"),
        ("Allo Glacial", "thero", ["cristaux"], "glacial"), ("Spino des Marais", "thero", ["voile"], "marais"),
        ("Pachy Cristal", "pachy", ["dome", "cristaux"], "cristal"),
        ("Styraco Royal", "cerato", ["collerette_pics", "corne_nez"], "or"),
        ("Baryonyx Abyssal", "thero", ["piques_lueur"], "abysse"), 
        ("Ceratosaure Toxique", "thero", ["corne_nez", "piques_lueur"], "toxique"),
    ],
    "Legendaire": [
        ("Rex de Lave", "rex", ["flammes", "piques_lueur"], "lave"), ("Spino Abyssal", "thero", ["voile", "piques_lueur"], "abysse"),
        ("Giganoto Tonnerre", "rex", ["piques_lueur", "cornes_yeux"], "tonnerre"),
        ("Rex de Cristal", "rex", ["cristaux"], "cristal"),
        ("Triceratops Titan", "cerato", ["collerette_royale", "cornes_avant", "corne_nez", "armure"], "or"),
        ("Brachio Aurore", "sauro", ["cristaux", "epines_cou"], "aurore"),
        ("Quetzal Solaire", "ptero", ["flammes"], "soleil"), ("Mosasaure Royal", "marin", ["couronne", "piques_dos"], "or"),
        ("Stego Cristallin", "stego", ["plaques", "cristaux", "piques_queue"], "cristal"),
        ("Raptor Spectre", "raptor", ["plumes", "piques_lueur"], "spectre"),
        ("Ankylo Forteresse", "ankylo", ["armure_dos", "massue", "armure"], "fer"),
        ("Therizino Faucheur", "ornitho", ["griffes_geantes", "plumes", "piques_lueur"], "ombre"),
        ("Rex Aile", "rex", ["ailes_plumes"], "soleil"), ("Raptor de Feu", "raptor", ["flammes", "armure"], "feu"),
        ("Golem Rex", "rex", ["mecha"], "golem"), ("Dilopho Dragon", "thero", ["cretes2", "ailes_dragon"], "venin"),
        ("Allo Samourai", "thero", ["armure", "cornes_demon"], "samourai"),
    ],
    "Mythique": [
        ("Dragon Rex", "rex", ["ailes_dragon", "cornes_demon", "flammes"], "lave"),
        ("Phenix Ptero", "ptero", ["flammes", "halo"], "feu"),
        ("Leviathan", "marin", ["piques_lueur", "cornes_demon"], "abysse"),
        ("Rex Galaxie", "rex", ["halo", "cristaux", "piques_lueur"], "galaxie"),
        ("Spino Fantome", "thero", ["voile", "chaines"], "spectre"),
        ("Titan de Jade", "sauro", ["cristaux", "armure", "epines_cou"], "jade"),
        ("Roi Demon Rex", "rex", ["ailes_dragon", "cornes_demon", "chaines", "couronne"], "demon"),
        ("Meca-Rex Dore", "rex", ["mecha", "piques_lueur"], "or"),
        ("Pegase Dino Dore", "ornitho", ["ailes_plumes", "flammes", "armure"], "golem"),
        ("Triceratops Infernal", "cerato", ["grande_collerette", "cornes_avant", "flammes", "armure"], "feu"),
    ],
    "Secret": [
        ("Ange-Demon Rex", "rex", ["ailes_ange_demon", "halo", "cornes_demon", "armure"], "ange_demon"),
        ("Dino Arc-en-ciel", "rex", ["ailes_plumes", "cristaux", "halo"], "arcenciel"),
        ("Fossile Vivant", "rex", ["piques_lueur", "chaines"], "fossile"),
        ("Empereur Dragon", "rex", ["ailes_dragon", "couronne", "cornes_demon", "armure", "flammes"], "empereur"),
        ("Spino Celeste", "thero", ["voile", "ailes_plumes", "halo"], "ciel_divin"),
        ("Triceratops du Neant", "cerato", ["grande_collerette", "cornes_avant", "noyau", "piques_lueur"], "vide"),
    ],
    "Eternel": [
        ("Kaiju du Vide", "rex", ["bras_multiples", "noyau", "piques_lueur"], "vide"),
        ("Dragon de Cristal Rose", "thero", ["ailes_dragon", "cristaux", "gemmes_corps", "cornes_demon"], "cristal_rose"),
        ("Rex Cosmique Eternel", "rex", ["ailes4", "aureole", "gemmes_corps", "halo"], "galaxie"),
        ("Leviathan Eternel", "marin", ["noyau", "aureole", "piques_lueur", "cornes_demon"], "abysse"),
        ("Sauro des Etoiles", "sauro", ["cristaux", "gemmes_corps", "halo", "epines_cou"], "galaxie"),
    ],
    "Divin": [
        ("Rex Seraphin", "rex", ["ailes4", "halo", "aureole", "armure", "lance"], "divin"),
        ("Raptor Paon Divin", "raptor", ["eventail_paon", "halo", "gemmes_corps"], "seraphin"),
        ("Ptero Seraphin", "ptero", ["aureole", "halo", "gemmes_corps", "flammes"], "seraphin"),
    ],
}
RARETES = ["Commun", "Peu commun", "Rare", "Epique", "Legendaire", "Mythique", "Secret", "Eternel", "Divin"]
LISSE = {"Epique", "Legendaire", "Mythique", "Secret", "Eternel", "Divin"}
TAILLE_RARETE = {"Commun": 0.85, "Peu commun": 0.95, "Rare": 1.05, "Epique": 1.15, "Legendaire": 1.25,
                 "Mythique": 1.35, "Secret": 1.45, "Eternel": 1.55, "Divin": 1.65}

GENERES = []
_n = 31
for _rar in RARETES:
    for _nom, _fam, _decos, _pal in LISTE[_rar]:
        GENERES.append(dict(numero=_n, nom=_nom, famille=_fam, decors=_decos, palette=_pal, rarete=_rar))
        _n += 1


def construire_genere(g):
    global OEIL_X, PUPILLE, R
    nettoyer()
    R = random.Random(g["numero"])
    random.seed(g["numero"])
    rar = g["rarete"]
    rang = RARETES.index(rar)
    OEIL_X = 1.45 if rang <= 1 else (1.25 if rang == 2 else 1.0)
    couleurs = theme(PALETTES[g["palette"]])
    PUPILLE = OEIL_X > 1.0 or sum(couleurs["Oeil"]) > 150
    fam = g["famille"]
    decos = list(g["decors"])
    if fam.startswith("ptero"):
        b = corps_ptero(petit=fam == "ptero_petit", crete="voile" if fam == "ptero_voile" else "pointe",
                        queue_longue="queue_longue" in decos)
        decos = [d for d in decos if d != "queue_longue"]
        fam_e = "ptero_petit" if fam == "ptero_petit" else "ptero"
    elif fam.startswith("marin"):
        sorte = "plesio" if "plesio" in fam else ("ichthyo" if "ichthyo" in fam else "mosa")
        b = corps_marin(sorte)
        fam_e = "marin_petit" if "petit" in fam else "marin"
    else:
        base = fam if fam != "stego_long" else "stego"
        d = varier(F[base], 0.1)
        if fam == "stego_long":
            d.update(cou=(1.1, 0.9, 0.8, 25), cou_n=3, cou_z=0.1)
        d["rainures"] = False
        if rang <= 2:  # dinos simples : pas de sourcils mechants
            d["arcade"] = False
        if rang >= 3:
            d["bandes"] = max(d.get("bandes", 0), 3) if base not in ("ankylo", "ankylo_petit", "stego") else 0
        if rang >= 4 and base in ("rex", "thero", "raptor"):  # gros bras et grosses griffes, style kaiju
            bw, bl, bh = d["bras"]
            d["bras"] = (bw * 1.6, bl * 1.3, bh * 1.4)
            d["griffe_main"] = d.get("griffe_main", 0.2) * 2.0
            d["doigts"] = 3
            cw, cl, ch = d["cuisse"]
            d["cuisse"] = (cw * 1.15, cl * 1.1, ch * 1.05)
        b = corps_bipede(d) if base in FAMILLES_BIPEDES else corps_quadrupede(d)
        fam_e = base
    for nom_deco in decos:
        DECORS[nom_deco](b)
    if fam.startswith("ptero"):
        sorte = "ptero"
    elif fam.startswith("marin"):
        sorte = "marin"
    else:
        sorte = "bipede" if fam_e in FAMILLES_BIPEDES else "quadrupede"
    os_ = squelette(b, sorte)
    lier_au_squelette(os_, b)
    echelle = ECHELLE_FAMILLE[fam_e] * TAILLE_RARETE[rar]
    slug = g["nom"].lower()
    for a_, b_ in (("'", ""), ("-", "_"), (" ", "_"), ("é", "e"), ("è", "e"), ("ï", "i")):
        slug = slug.replace(a_, b_)
    fichier = f"{g['numero']:03d}_{slug}"
    if rar in LISSE:
        # Epique : peau ronde. Legendaire et plus : grandes facettes, style massif
        res = finaliser_lisse(fichier, couleurs, echelle, squelette_os=os_, facettes=rang >= 4)
    else:
        res = finaliser(fichier, couleurs, echelle, squelette_os=os_)
    OEIL_X, PUPILLE = 1.0, False
    return res


# =====================================================================
#  SQUELETTE (articulations pour animer dans Roblox)
# =====================================================================
def squelette(b, sorte):
    """Liste d'os (nom, debut, fin, parent) calculee d'apres la forme du dino."""
    V = Vector
    w, l, h, hz = b["w"], b["l"], b["h"], b["hz"]
    os_ = [("Racine", V((0, 0, 0)), V((0, 0, 0.5)), None)]
    bassin = V((0, l * 0.35, hz))
    milieu = V((0, 0, hz))
    avant = V((0, -l * 0.42, hz + h * 0.15))
    os_ += [("Bassin", bassin, milieu, "Racine"), ("Torse", milieu, avant, "Bassin")]
    # cou
    parent, p = "Torse", avant
    for i, (o, c, cw, ch) in enumerate(b["cou"]):
        os_.append((f"Cou{i + 1}", p, c.copy(), parent))
        parent, p = f"Cou{i + 1}", c.copy()
    # tete + machoire
    tt = b["tete"]
    y0, z0 = tt.p(0.0, 0.3)
    y1, z1 = tt.p(1.0, 0.3)
    os_.append(("Tete", V((0, y0, z0)), V((0, y1, z1)), parent))
    if tt.objs and len(tt.objs) > 1:  # tete de carnivore : machoire mobile
        ya, za = tt.p(0.1, -0.05)
        yb, zb = tt.p(0.95, -0.3)
        os_.append(("Machoire", V((0, ya, za)), V((0, yb, zb)), "Tete"))
    # queue
    parent, p = "Bassin", bassin
    for i, (o, c, qw, qh) in enumerate(b["queue"]):
        os_.append((f"Queue{i + 1}", p, c.copy(), parent))
        parent, p = f"Queue{i + 1}", c.copy()
    if b["queue"]:
        os_.append(("BoutQueue", p, b["fin_queue"].copy(), parent))
    d = b["d"]
    if sorte == "bipede":
        cw, cl, ch = d["cuisse"]
        fw, fl, fh = d["pied"]
        for s, cote in ((-1, "R"), (1, "L")):
            x = s * (w / 2 + cw * 0.1)
            hy, hzz = l * 0.1, hz - h * 0.12
            genou = V((x, hy + cl * 0.22, hzz - ch * 0.4))
            py = hy + cl * 0.15 - fl * 0.25
            cheville = V((x, py + fl * 0.15, fh * 0.6))
            orteils = V((x, py - fl * 0.6, fh * 0.3))
            os_ += [(f"Cuisse.{cote}", V((x, hy, hzz + ch * 0.3)), genou, "Bassin"),
                    (f"Tibia.{cote}", genou, cheville, f"Cuisse.{cote}"),
                    (f"Pied.{cote}", cheville, orteils, f"Tibia.{cote}")]
            bw, bl, bh = d["bras"]
            xb = s * (w / 2 + bw * 0.05)
            yb, zb = -l * 0.42, hz - h * 0.02
            coude = V((xb, yb, zb - bh * 0.45))
            os_ += [(f"Bras.{cote}", V((xb, yb, zb + bh * 0.45)), coude, "Torse"),
                    (f"AvantBras.{cote}", coude, V((xb * 1.03, yb - bl, zb - bh * 0.45)), f"Bras.{cote}")]
    elif sorte == "quadrupede":
        av, ar = d.get("hauteur_pattes", (hz - h * 0.2, hz - h * 0.2))
        e = d["patte"]
        for s, cote in ((-1, "R"), (1, "L")):
            x = s * (w / 2 - e * 0.25)
            for nom, y, haut, par in (("Avant", -l * 0.32, av, "Torse"), ("Arriere", l * 0.3, ar, "Bassin")):
                genou = V((x, y, haut * 0.45))
                os_ += [(f"Patte{nom}.{cote}", V((x, y, haut)), genou, par),
                        (f"Pied{nom}.{cote}", genou, V((x, y - 0.1, 0.12)), f"Patte{nom}.{cote}")]
    elif sorte == "ptero":
        for s, cote in ((-1, "R"), (1, "L")):
            os_ += [(f"Aile.{cote}", V((s * 0.5, -0.45, hz + 0.3)), V((s * 2.4, -0.45, hz + 0.3)), "Torse"),
                    (f"BoutAile.{cote}", V((s * 2.4, -0.45, hz + 0.3)), V((s * 4.4, 0, hz + 0.3)), f"Aile.{cote}"),
                    (f"Jambe.{cote}", V((s * 0.35, 0.6, hz - 0.3)), V((s * 0.35, 1.2, hz - 1.3)), "Bassin")]
    elif sorte == "marin":
        for s, cote in ((-1, "R"), (1, "L")):
            for nom, y in (("Avant", -l * 0.25), ("Arriere", l * 0.25)):
                os_.append((f"Palme{nom}.{cote}", V((s * w * 0.4, y, hz - h * 0.3)),
                            V((s * (w * 0.4 + 1.8), y + 0.2, hz - h * 0.3)), "Torse" if nom == "Avant" else "Bassin"))
    return os_


# pieces qui suivent toujours la tete / restent fixes
SUIT_TETE = ("Tete", "Collerette", "Crete", "Dome", "Licorne", "CorneNez", "CorneDemon", "Halo", "Couronne",
             "Visiere", "Arcade", "Rainure", "Narine", "Bec", "Oeil", "Reflet", "Pupille", "Sourire", "Corne",
             "PointeCouronne")
FIXE = ("Socle", "Tige")


def _dist_segment(p, a, b_):
    ab = b_ - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (a + ab * t - p).length


def lier_au_squelette(os_, b):
    """Chaque piece suit l'os le plus proche (avec quelques regles par nom)."""
    noms_os = [o[0] for o in os_]
    tt = b["tete"]
    z_bouche = tt.p(0.5, 0.0)[1]
    for o in objets():
        nom = o.name.split(".")[0]
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        centre = sum(pts, Vector()) / 8
        if nom.startswith(FIXE):
            cible = "Racine"
        elif "Machoire" in noms_os and (nom.startswith(("Machoire", "Langue"))
                                         or (nom.startswith("Dent") and centre.z < z_bouche
                                             and centre.y < tt.y0)):
            cible = "Machoire"
        elif nom.startswith(SUIT_TETE) and _dist_segment(centre, *[x for x in os_ if x[0] == "Tete"][0][1:3]) < tt.L:
            cible = "Tete"
        elif nom.startswith(("Aile", "Os", "Baleine", "Aureole")) and "Aile.L" not in noms_os:
            cible = "Torse"
        else:
            cible = min(os_[1:], key=lambda x: _dist_segment(centre, x[1], x[2]))[0]
        vg = o.vertex_groups.new(name=cible)
        vg.add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')


def creer_armature(os_, decalage_z, echelle, mesh):
    arm = bpy.data.armatures.new("Squelette")
    ob = lier(bpy.data.objects.new("Squelette", arm))
    activer(ob)
    bpy.ops.object.mode_set(mode='EDIT')
    t = lambda v: (Vector(v) - Vector((0, 0, decalage_z))) * echelle
    for nom, a, b_, parent in os_:
        eb = arm.edit_bones.new(nom)
        eb.head = t(a)
        eb.tail = t(b_)
        if (eb.tail - eb.head).length < 1e-3:
            eb.tail = eb.head + Vector((0, 0, 0.1 * echelle))
        if parent:
            eb.parent = arm.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    mod = mesh.modifiers.new("Squelette", 'ARMATURE')
    mod.object = ob
    mesh.parent = ob
    return ob


# =====================================================================
#  50 OEUFS : chacun contient 3 ou 4 dinos, les 180 dinos sont repartis
# =====================================================================
# Themes visuels : couleurs de coquille, motif, socle et decors
THEMES_OEUFS = {
    "sable": dict(c=dict(Coquille=(238, 222, 176), Bande=(222, 200, 148), Tache=(204, 178, 120), Deco1=(176, 132, 74),
                         Deco2=(140, 100, 56)), socle="nid", decors=["crane"]),
    "prairie": dict(c=dict(Coquille=(170, 214, 120), Bande=(130, 180, 90), Tache=(250, 240, 160), Deco1=(90, 170, 70),
                           Deco2=(60, 130, 50)), socle="herbe", decors=["feuilles"]),
    "fougere": dict(c=dict(Coquille=(120, 170, 100), Bande=(80, 130, 70), Tache=(200, 230, 150), Deco1=(60, 140, 60),
                           Deco2=(40, 100, 40)), socle="herbe", decors=["feuilles", "lianes"]),
    "argile": dict(c=dict(Coquille=(210, 140, 100), Bande=(180, 110, 76), Tache=(236, 190, 150), Deco1=(160, 100, 70),
                          Deco2=(120, 76, 54)), socle="roche", decors=["rochers"]),
    "galet": dict(c=dict(Coquille=(190, 196, 204), Bande=(150, 156, 168), Tache=(230, 232, 236), Deco1=(140, 144, 150),
                         Deco2=(110, 114, 120)), socle="roche", decors=["rochers"]),
    "mousse": dict(c=dict(Coquille=(150, 180, 110), Bande=(110, 140, 80), Tache=(90, 120, 70), Deco1=(110, 160, 80),
                          Deco2=(80, 70, 50)), socle="nid", decors=["feuilles"]),
    "terre": dict(c=dict(Coquille=(170, 120, 80), Bande=(130, 90, 60), Tache=(210, 170, 120), Deco1=(120, 84, 56),
                         Deco2=(90, 64, 44)), socle="nid", decors=["os"]),
    "paille": dict(c=dict(Coquille=(240, 226, 150), Bande=(220, 196, 110), Tache=(250, 240, 200), Deco1=(220, 190, 100),
                          Deco2=(180, 150, 70)), socle="nid", decors=[]),
    "marais": dict(c=dict(Coquille=(92, 156, 150), Bande=(60, 112, 108), Tache=(166, 210, 120), Deco1=(108, 128, 60),
                          Deco2=(70, 110, 150), Lueur=(120, 82, 50)), socle="eau", decors=["roseaux"]),
    "riviere": dict(c=dict(Coquille=(140, 190, 230), Bande=(90, 150, 210), Tache=(230, 240, 250), Deco1=(150, 150, 160),
                           Deco2=(70, 130, 200), Lueur=(120, 82, 50)), socle="eau", decors=["rochers", "roseaux"]),
    "savane": dict(c=dict(Coquille=(236, 196, 110), Bande=(200, 150, 70), Tache=(150, 100, 50), Deco1=(200, 180, 90),
                          Deco2=(160, 130, 60)), socle="herbe", decors=["os"]),
    "bambou": dict(c=dict(Coquille=(200, 230, 150), Bande=(140, 190, 90), Tache=(100, 160, 70), Deco1=(130, 180, 80),
                          Deco2=(90, 140, 60), Lueur=(120, 170, 80)), socle="herbe", decors=["roseaux", "feuilles"]),
    "desert": dict(c=dict(Coquille=(244, 210, 150), Bande=(230, 170, 100), Tache=(200, 120, 70), Deco1=(110, 170, 90),
                          Deco2=(200, 170, 120)), socle="roche", decors=["cactus", "crane"]),
    "ambre": dict(c=dict(Coquille=(240, 170, 50), Bande=(200, 120, 30), Tache=(255, 220, 120), Deco1=(150, 100, 50),
                         Deco2=(110, 70, 40), Lueur=(255, 200, 80), Gemme=(255, 190, 60)), socle="roche",
                  decors=["cristaux"]),
    "canyon": dict(c=dict(Coquille=(196, 120, 84), Bande=(160, 90, 62), Tache=(226, 168, 120), Deco1=(150, 140, 130),
                          Deco2=(110, 102, 96)), socle="roche", decors=["fissures", "rochers"]),
    "grotte": dict(c=dict(Coquille=(110, 110, 130), Bande=(80, 80, 100), Tache=(150, 220, 255), Deco1=(90, 90, 110),
                          Deco2=(60, 60, 76), Lueur=(130, 220, 255), Gemme=(130, 220, 255)), socle="roche",
                   decors=["cristaux", "lueurs"]),
    "glace": dict(c=dict(Coquille=(196, 228, 248), Bande=(140, 196, 236), Tache=(250, 252, 255), Deco1=(248, 250, 255),
                         Deco2=(228, 238, 248), Lueur=(110, 220, 255), Gemme=(150, 230, 255)), socle="neige",
                  decors=["cristaux", "lueurs"]),
    "jade": dict(c=dict(Coquille=(80, 180, 130), Bande=(250, 210, 90), Tache=(150, 230, 180), Deco1=(60, 150, 100),
                        Deco2=(250, 210, 90), Lueur=(160, 255, 200), Gemme=(140, 255, 190)), socle="or",
                 decors=["gemmes", "cristaux"]),
    "rubis": dict(c=dict(Coquille=(200, 40, 60), Bande=(250, 200, 70), Tache=(255, 120, 130), Deco1=(130, 20, 40),
                         Deco2=(250, 200, 70), Lueur=(255, 90, 110), Gemme=(255, 60, 90)), socle="or",
                  decors=["gemmes", "cristaux"]),
    "orage": dict(c=dict(Coquille=(110, 100, 170), Bande=(236, 236, 250), Tache=(80, 70, 140), Deco1=(244, 244, 252),
                         Deco2=(206, 210, 230), Lueur=(255, 226, 60)), socle="nuage", decors=["eclairs"]),
    "lave": dict(c=dict(Coquille=(34, 26, 28), Bande=(108, 24, 26), Tache=(150, 30, 30), Deco1=(108, 24, 26),
                        Deco2=(54, 34, 34), Lueur=(255, 110, 50), Gemme=(255, 140, 40)), socle="lave",
                 decors=["flammes", "lueurs"]),
    "neon": dict(c=dict(Coquille=(30, 30, 46), Bande=(255, 60, 220), Tache=(60, 255, 200), Deco1=(60, 255, 200),
                        Deco2=(40, 40, 60), Lueur=(60, 255, 200), Gemme=(255, 60, 220)), socle="vide",
                 decors=["lueurs", "piques"]),
    "toxique": dict(c=dict(Coquille=(50, 60, 46), Bande=(140, 255, 60), Tache=(100, 200, 50), Deco1=(140, 255, 60),
                           Deco2=(40, 50, 40), Lueur=(140, 255, 60), Gemme=(170, 255, 80)), socle="eau",
                    decors=["lueurs", "bulles"]),
    "abysses": dict(c=dict(Coquille=(30, 54, 110), Bande=(20, 36, 78), Tache=(60, 220, 230), Deco1=(250, 110, 140),
                           Deco2=(250, 170, 80), Lueur=(80, 240, 255), Gemme=(80, 240, 255)), socle="corail",
                    decors=["coraux", "lueurs"]),
    "aurore": dict(c=dict(Coquille=(90, 200, 190), Bande=(170, 100, 230), Tache=(150, 255, 210), Deco1=(220, 240, 255),
                          Deco2=(150, 200, 240), Lueur=(140, 255, 210), Gemme=(220, 140, 255)), socle="neige",
                   decors=["cristaux", "etoiles"]),
    "amethyste": dict(c=dict(Coquille=(140, 80, 200), Bande=(200, 150, 250), Tache=(90, 50, 140), Deco1=(110, 70, 160),
                             Deco2=(70, 50, 100), Lueur=(220, 170, 255), Gemme=(200, 130, 255)), socle="cristal",
                      decors=["cristaux", "gemmes"]),
    "soleil": dict(c=dict(Coquille=(250, 200, 70), Bande=(255, 150, 40), Tache=(255, 240, 160), Deco1=(250, 220, 120),
                          Deco2=(230, 150, 50), Lueur=(255, 236, 140), Gemme=(255, 120, 40)), socle="or",
                   decors=["rayons", "halo"]),
    "lune": dict(c=dict(Coquille=(200, 210, 240), Bande=(130, 140, 200), Tache=(240, 244, 255), Deco1=(60, 66, 110),
                        Deco2=(40, 44, 80), Lueur=(220, 230, 255), Gemme=(180, 200, 255)), socle="vide",
                 decors=["etoiles", "halo"]),
    "dragon": dict(c=dict(Coquille=(150, 26, 34), Bande=(40, 20, 24), Tache=(250, 200, 70), Deco1=(200, 50, 50),
                          Deco2=(90, 16, 24), Lueur=(255, 170, 40), Gemme=(255, 170, 40), Corne=(240, 220, 180)),
                   socle="lave", decors=["ailes_dragon", "cornes", "flammes"]),
    "phenix": dict(c=dict(Coquille=(255, 140, 40), Bande=(255, 210, 80), Tache=(255, 80, 40), Deco1=(255, 200, 70),
                          Deco2=(200, 60, 30), Lueur=(255, 220, 90), Gemme=(255, 90, 30)), socle="lave",
                   decors=["ailes_plumes", "flammes", "halo"]),
    "titan": dict(c=dict(Coquille=(120, 126, 140), Bande=(240, 190, 50), Tache=(70, 76, 90), Deco1=(190, 196, 210),
                         Deco2=(70, 76, 90), Lueur=(255, 220, 90), Gemme=(255, 220, 90)), socle="or",
                  decors=["armure", "gemmes", "piques"]),
    "kraken": dict(c=dict(Coquille=(60, 40, 110), Bande=(30, 20, 60), Tache=(120, 255, 220), Deco1=(110, 70, 170),
                          Deco2=(40, 30, 80), Lueur=(120, 255, 220), Gemme=(120, 255, 220)), socle="corail",
                   decors=["tentacules", "lueurs"]),
    "galaxie": dict(c=dict(Coquille=(30, 24, 70), Bande=(150, 80, 230), Tache=(255, 240, 160), Deco1=(70, 50, 130),
                           Deco2=(30, 24, 60), Lueur=(255, 240, 170), Gemme=(255, 120, 220)), socle="vide",
                    decors=["etoiles", "anneau", "lueurs"]),
    "demon": dict(c=dict(Coquille=(40, 20, 24), Bande=(120, 16, 24), Tache=(210, 30, 40), Deco1=(210, 30, 40),
                         Deco2=(30, 20, 20), Lueur=(255, 200, 40), Gemme=(255, 200, 40), Corne=(30, 20, 20)),
                  socle="lave", decors=["ailes_dragon", "cornes", "chaines", "couronne"]),
    "golem": dict(c=dict(Coquille=(190, 140, 50), Bande=(40, 36, 34), Tache=(220, 170, 60), Deco1=(40, 36, 34),
                         Deco2=(150, 110, 40), Lueur=(255, 220, 90), Gemme=(255, 220, 90)), socle="or",
                  decors=["armure", "noyau", "piques"]),
    "vide": dict(c=dict(Coquille=(22, 24, 48), Bande=(12, 12, 28), Tache=(60, 70, 140), Deco1=(60, 70, 140),
                        Deco2=(20, 22, 40), Lueur=(120, 240, 255), Gemme=(120, 240, 255)), socle="vide",
                 decors=["noyau", "fissures_lueur", "anneau"]),
    "cristal_rose": dict(c=dict(Coquille=(236, 150, 215), Bande=(180, 80, 180), Tache=(255, 210, 245),
                                Deco1=(250, 190, 240), Deco2=(170, 80, 170), Lueur=(255, 200, 250),
                                Gemme=(255, 170, 240)), socle="cristal", decors=["cristaux", "ailes_dragon", "gemmes"]),
    "divin": dict(c=dict(Coquille=(250, 248, 240), Bande=(240, 200, 80), Tache=(255, 236, 150), Deco1=(255, 220, 100),
                         Deco2=(240, 200, 80), Lueur=(255, 236, 150), Gemme=(255, 255, 255), Accent=(255, 220, 100)),
                  socle="nuage", decors=["ailes_plumes", "halo", "anneau", "gemmes", "couronne"]),
    "arcenciel": dict(c=dict(Coquille=(250, 250, 255), Bande=(240, 70, 80), Tache=(80, 160, 250), Deco1=(250, 210, 60),
                             Deco2=(80, 220, 120), Lueur=(190, 100, 240), Gemme=(80, 160, 250)), socle="nuage",
                      decors=["arcenciel", "etoiles", "halo"]),
}

# Les 50 oeufs : (nom, theme), du plus simple au plus fou
NOMS_OEUFS = [
    ("Oeuf de Sable", "sable"), ("Oeuf de Prairie", "prairie"), ("Oeuf de Fougere", "fougere"),
    ("Oeuf d'Argile", "argile"), ("Oeuf de Galet", "galet"), ("Oeuf de Mousse", "mousse"), ("Oeuf de Terre", "terre"),
    ("Oeuf de Paille", "paille"), ("Oeuf du Marais", "marais"), ("Oeuf de Riviere", "riviere"),
    ("Oeuf de Savane", "savane"), ("Oeuf de Bambou", "bambou"), ("Oeuf du Desert", "desert"),
    ("Oeuf d'Ambre", "ambre"), ("Oeuf de Canyon", "canyon"), ("Oeuf de la Grotte", "grotte"),
    ("Oeuf des Fossiles", "terre"), ("Oeuf de Glace", "glace"), ("Oeuf de Jade", "jade"), ("Oeuf de Rubis", "rubis"),
    ("Oeuf d'Orage", "orage"), ("Oeuf des Cimes", "galet"), ("Oeuf de la Jungle Sauvage", "fougere"),
    ("Oeuf des Dunes", "desert"), ("Oeuf du Glacier", "glace"), ("Oeuf de Lave", "lave"), ("Oeuf Neon", "neon"),
    ("Oeuf Toxique", "toxique"), ("Oeuf des Abysses", "abysses"), ("Oeuf d'Aurore", "aurore"),
    ("Oeuf d'Amethyste", "amethyste"), ("Oeuf de Tempete", "orage"), ("Oeuf du Soleil", "soleil"),
    ("Oeuf de Lune", "lune"), ("Oeuf du Dragon", "dragon"), ("Oeuf du Phenix", "phenix"), ("Oeuf du Titan", "titan"),
    ("Oeuf du Kraken", "kraken"), ("Oeuf du Volcan Ancien", "lave"), ("Oeuf Galactique", "galaxie"),
    ("Oeuf du Golem", "golem"), ("Oeuf Demoniaque", "demon"), ("Oeuf de Cristal Rose", "cristal_rose"),
    ("Oeuf des Profondeurs", "kraken"), ("Oeuf du Vide", "vide"), ("Oeuf Eternel", "galaxie"),
    ("Oeuf de l'Infini", "vide"), ("Oeuf Arc-en-ciel", "arcenciel"), ("Oeuf Celeste", "divin"), ("Oeuf Divin", "divin"),
]
assert len(NOMS_OEUFS) == 50


def tous_les_dinos():
    """Les 180 dinos (numero, nom, rarete), classes du plus commun au plus rare."""
    liste = [(num, nom, rar) for num, nom, rar, *_ in DINOS] + [(g["numero"], g["nom"], g["rarete"]) for g in GENERES]
    return sorted(liste, key=lambda x: (RARETES.index(x[2]), x[0]))


def _arrondi(x):
    """Garde 2 chiffres significatifs : 2 534 -> 2 500."""
    e = 10 ** max(0, int(math.log10(x)) - 1)
    return int(round(x / e) * e)


def repartir_oeufs():
    """30 oeufs de 4 dinos puis 20 oeufs de 3 : les 180 dinos, chacun dans un seul oeuf."""
    dinos = tous_les_dinos()
    tailles = [4] * 30 + [3] * 20
    assert sum(tailles) == len(dinos) == 180
    chances = {4: [50, 30, 15, 5], 3: [60, 30, 10]}
    oeufs, i = [], 0
    for k, n in enumerate(tailles):
        groupe = dinos[i:i + n]
        i += n
        nom, theme_ = NOMS_OEUFS[k]
        oeufs.append(dict(numero=k + 1, nom=nom, theme=theme_, rarete=groupe[0][2],
                          prix=_arrondi(100 * 1.38 ** k),
                          dinos=[(d[0], d[1], d[2], c) for d, c in zip(groupe, chances[n])]))
    return oeufs


# ---------- decors d'oeufs ----------
def _autour(n, rayon, z, decal=0.0):
    for k in range(n):
        a = 2 * math.pi * k / n + decal
        yield a, Vector((rayon * math.cos(a), rayon * math.sin(a), z))


def socle_oeuf(sorte, R_):
    if sorte == "nid":
        nid_batons(14, R_ * 1.05, 0.35, 2.2, "Deco1", "Deco2")
        nid_batons(10, R_ * 0.7, 0.55, 1.6, "Deco2", "Deco1")
    elif sorte == "herbe":
        socle(R_ * 1.05, 0.45, "Deco2")
    elif sorte == "eau":
        socle(R_ * 1.3, 0.35, "Deco2", n=2)
    elif sorte == "roche":
        socle(R_ * 1.1, 0.45, "Deco2")
        for _ in range(12):
            a = R.uniform(0, 2 * math.pi)
            r = R.uniform(R_ * 0.9, R_ * 1.3)
            t_ = R.uniform(0.35, 0.75)
            boite("Rocher", (r * math.cos(a), r * math.sin(a), 0.4 + t_ / 2), (t_, t_ * 1.2, t_), R.choice(("Deco1", "Deco2")),
                  lacet=R.uniform(0, 90))
    elif sorte == "neige":
        socle(R_ * 1.15, 0.5, "Deco1", n=2)
    elif sorte == "nuage":
        for a, p in _autour(16, R_ * 1.2, 0.45):
            t_ = R.uniform(0.6, 1.0)
            boite("Nuage", p, (t_ * 1.3, t_, t_ * 0.8), R.choice(("Deco1", "Deco2")), biseau=0.15, lacet=math.degrees(a))
    elif sorte == "corail":
        socle(R_ * 1.15, 0.5, "Bande", n=2)
    elif sorte == "lave":
        socle(R_ * 1.2, 0.5, "Deco2", n=2)
        for a, p in _autour(10, R_ * 1.15, 0.52):
            boite("Fissure", p, (0.5, 0.14, 0.06), "Lueur", biseau=0, lacet=math.degrees(a))
    elif sorte == "or":
        socle(R_ * 1.15, 0.5, "Deco2", n=2)
        socle(R_ * 0.95, 0.75, "Deco1")
    elif sorte == "vide":
        socle(R_ * 1.15, 0.45, "Deco2", n=2)
        for a, p in _autour(12, R_ * 1.25, 0.47):
            boite("Lueur", p, (0.25, 0.25, 0.08), "Lueur", biseau=0)
    elif sorte == "cristal":
        socle(R_ * 1.1, 0.45, "Deco2", n=2)
        eclats(8, R_ * 1.1, 0.4, 1.6, "Gemme", "Deco1", inclinaison=20, largeur=0.4)


def decor_oeuf(nom, c, R_, H, bas, force):
    """force : de 0 (oeuf simple) a 1 (oeuf le plus fou)."""
    haut = bas + H
    if nom == "crane":
        crane_fossile(c, bas + H * 0.35)
    elif nom == "os":
        for a, p in _autour(4, R_ * 1.15, 0.6, 0.4):
            boite("Os", p, (0.9, 0.22, 0.22), "Os", biseau=0.05, lacet=math.degrees(a) + 90)
            for s in (-1, 1):
                ellipse("Os", p + Vector((-math.sin(a), math.cos(a), 0)) * 0.45 * s, (0.17, 0.17, 0.17), "Os", seg=6,
                        anneaux=4)
    elif nom == "feuilles":
        for k in range(9):
            feuille(2 * math.pi * k / 9, R_ * 0.6, 0.5, 1.8, "Deco1" if k % 2 else "Deco2")
    elif nom == "lianes":
        for k in range(3):
            a = 2 * math.pi * k / 3 + 0.4
            for z in np.linspace(bas + 0.4, haut - 0.6, 6):
                aa = a + z * 0.4
                loc, _ = toucher(c, (math.cos(aa) * 20, math.sin(aa) * 20, z), (-math.cos(aa), -math.sin(aa), 0))
                if loc:
                    boite("Liane", loc, (0.22, 0.22, 0.42), "Deco2", biseau=0.03)
    elif nom == "roseaux":
        for a, p in _autour(10, R_ * 1.25, 0, 0.2):
            h = R.uniform(1.6, 2.6)
            boite("Roseau", p + Vector((0, 0, h / 2)), (0.14, 0.14, h), "Deco1", biseau=0.02)
            boite("Massette", p + Vector((0, 0, h - 0.1)), (0.24, 0.24, 0.55), "Lueur", biseau=0.04)
    elif nom == "rochers":
        pass  # deja dans le socle "roche"
    elif nom == "cactus":
        for a, p in _autour(3, R_ * 1.25, 0.4, 1.2):
            boite("Cactus", p + Vector((0, 0, 0.8)), (0.4, 0.4, 1.6), "Deco1", biseau=0.06)
            boite("Cactus", p + Vector((0.35, 0, 1.0)), (0.3, 0.3, 0.6), "Deco1", biseau=0.05)
    elif nom == "cristaux":
        blocs_surface(c, int(6 + 10 * force), 0.3, "Gemme", bas + 0.4, haut - 0.4, saillie=0.6)
        eclats(int(6 + 4 * force), R_ * 1.1, 0.35, 1.4 + force, "Gemme", "Lueur", inclinaison=22, largeur=0.42)
    elif nom == "lueurs":
        blocs_surface(c, int(8 + 12 * force), 0.28, "Lueur", bas + 0.4, haut - 0.3, saillie=0.6)
    elif nom == "gemmes":
        for a, p in _autour(6, R_ * 0.98, bas + H * 0.45):
            loc, n = toucher(c, (math.cos(a) * 20, math.sin(a) * 20, bas + H * 0.45), (-math.cos(a), -math.sin(a), 0))
            if loc:
                gemme(loc, 0.25, "Gemme")
    elif nom == "fissures":
        for a0 in (0.3, 2.4, 4.2):
            z, a = bas + 0.5, a0
            while z < haut - 0.4:
                d = Vector((math.cos(a), math.sin(a), 0))
                loc, _ = toucher(c, Vector((0, 0, z)) + d * 20, -d)
                if loc:
                    boite("Fissure", loc, (0.14, 0.14, 0.36), "Noir", biseau=0)
                z += 0.3
                a += R.choice((-0.12, 0.12))
    elif nom == "fissures_lueur":
        for a0 in (0.3, 1.5, 2.6, 3.8, 5.0):
            z, a = bas + 0.4, a0
            while z < haut - 0.3:
                d = Vector((math.cos(a), math.sin(a), 0))
                loc, _ = toucher(c, Vector((0, 0, z)) + d * 20, -d)
                if loc:
                    boite("Fissure", loc, (0.14, 0.14, 0.36), "Lueur", biseau=0)
                z += 0.3
                a += R.choice((-0.15, 0.15))
    elif nom == "eclairs":
        for a in (0.2, 2.3, 4.3):
            eclair(R_ * 1.15 * math.cos(a), R_ * 1.15 * math.sin(a), bas + 0.9, math.degrees(a) + 90, 1.6, "Lueur")
    elif nom == "flammes":
        eclats(int(6 + 4 * force), R_ * 1.1, 0.3, 1.8 + force, "Lueur", "Deco1", inclinaison=18, largeur=0.5)
    elif nom == "coraux":
        for a, p in _autour(7, R_ * 1.1, 0.5, 0.3):
            mat = "Deco1" if int(a * 10) % 2 else "Deco2"
            h = R.uniform(1.0, 1.8)
            boite("Corail", p + Vector((0, 0, h / 2)), (0.3, 0.3, h), mat, biseau=0.04)
            for s in (-1, 1):
                boite("Branche", p + Vector((s * 0.3 * math.sin(a), -s * 0.3 * math.cos(a), h * 0.75)),
                      (0.22, 0.22, h * 0.5), mat, biseau=0.03)
    elif nom == "bulles":
        for _ in range(10):
            a = R.uniform(0, 2 * math.pi)
            r = R.uniform(R_ * 1.1, R_ * 1.4)
            ellipse("Bulle", (r * math.cos(a), r * math.sin(a), R.uniform(0.6, haut)), (0.18,) * 3, "Lueur", seg=8,
                    anneaux=6)
    elif nom == "etoiles":
        for _ in range(int(10 + 10 * force)):
            a = R.uniform(0, 2 * math.pi)
            r = R.uniform(R_ * 1.25, R_ * 1.7)
            boite("Etoile", (r * math.cos(a), r * math.sin(a), R.uniform(0.8, haut + 0.5)), (0.22, 0.22, 0.22), "Lueur",
                  biseau=0, lacet=45, roulis=45)
    elif nom in ("halo", "anneau"):
        z = haut + 0.9 if nom == "halo" else bas + H * 0.45
        r = R_ * 0.6 if nom == "halo" else R_ * 1.45
        n = 14 if nom == "halo" else 22
        for a, p in _autour(n, r, z):
            boite("Halo", p, (0.35, 0.3, 0.14), "Lueur", biseau=0.02, lacet=math.degrees(a))
    elif nom == "rayons":
        for a, p in _autour(12, R_ * 1.3, bas + H * 0.5):
            o = cone("Rayon", p, 0.25, 1.2, "Lueur", (math.cos(a), math.sin(a), 0.2), sommets=4)
    elif nom == "cornes":
        for s in (-1, 1):
            for k, (dx, dz, h) in enumerate(((0.45, haut + 0.1, 0.9), (0.65, haut + 0.8, 0.8), (0.75, haut + 1.45, 0.7))):
                boite("Corne", (s * dx, 0, dz), (0.45, 0.45, h), "Deco1" if k < 2 else "Lueur", biseau=0.04,
                      roulis=s * (12 + k * 10))
    elif nom == "couronne":
        z = haut - 0.1
        boite("Couronne", (0, 0, z), (1.2, 1.2, 0.35), "Deco1", biseau=0.04)
        for a, p in _autour(6, 0.5, z + 0.3):
            cone("Pointe", p, 0.14, 0.5, "Deco1", (0, 0, 1), sommets=4)
        gemme((0, -0.62, z), 0.16, "Gemme")
    elif nom == "chaines":
        for s in (-1, 1):
            for k in range(10):
                t_ = k / 9
                a = s * 1.2 + t_ * 2.5
                z = bas + 0.5 + t_ * (H - 1)
                loc, _ = toucher(c, (math.cos(a) * 20, math.sin(a) * 20, z), (-math.cos(a), -math.sin(a), 0))
                if loc:
                    boite("Chaine", loc, (0.18, 0.32, 0.18) if k % 2 else (0.18, 0.18, 0.32), "Noir", biseau=0.03)
    elif nom == "ailes_dragon":
        for s in (-1, 1):
            aile_dragon(s, (s * R_ * 0.6, 0.1, bas + H * 0.45), 1.2, "Deco1", "Deco2")
    elif nom == "ailes_plumes":
        for s in (-1, 1):
            aile_plumes_v(s, (s * R_ * 0.6, 0.1, bas + H * 0.4), 1.25, "Deco1", "Gemme")
    elif nom == "armure":
        for z in (bas + H * 0.3, bas + H * 0.62):
            loc, _ = toucher(c, (0, 0, 50), (0, 0, -1))
            k = R_ * 2.08 * math.sqrt(max(0.1, 1 - ((z - bas) / H - 0.42) ** 2 / 0.35))
            boite("Bande", (0, 0, z), (k, k * 0.72, 0.3), "Deco1", biseau=0.04)
            boite("Bande", (0, 0, z), (k * 0.72, k, 0.3), "Deco1", biseau=0.04)
    elif nom == "noyau":
        loc, n = toucher(c, (0, -20, bas + H * 0.45), (0, 1, 0))
        if loc:
            gemme(loc + Vector((0, -0.1, 0)), 0.5, "Lueur")
    elif nom == "piques":
        for a, p in _autour(8, R_ * 0.9, bas + H * 0.55):
            loc, n = toucher(c, (math.cos(a) * 20, math.sin(a) * 20, bas + H * 0.55), (-math.cos(a), -math.sin(a), 0))
            if loc:
                cone("Pique", loc, 0.22, 0.8, "Deco1", (math.cos(a), math.sin(a), 0.4), sommets=4)
    elif nom == "tentacules":
        for a, p in _autour(6, R_ * 0.95, 0.4, 0.3):
            q = p.copy()
            for k in range(5):
                q = q + Vector((math.cos(a) * 0.35, math.sin(a) * 0.35, 0.25 + k * 0.05))
                boite("Tentacule", q, (0.42 - k * 0.06,) * 3, "Deco1", biseau=0.05)
    elif nom == "arcenciel":
        couleurs_ = ("Bande", "Deco1", "Deco2", "Tache", "Lueur", "Gemme")
        for k, m in enumerate(couleurs_):
            for a, p in _autour(10, R_ * 1.15 + k * 0.18, 0.4 + k * 0.05, k * 0.1):
                boite("Arc", p, (0.5, 0.25, 0.16), m, biseau=0.02, lacet=math.degrees(a))


def construire_oeuf_genere(oe):
    global R
    nettoyer()
    R = random.Random(500 + oe["numero"])
    th = THEMES_OEUFS[oe["theme"]]
    couleurs = theme(th["c"])
    k = (oe["numero"] - 1) / 49  # 0 -> 1 : de plus en plus gros et charge
    H = 3.4 + 1.4 * k
    R_ = 1.4 + 0.45 * k
    bas = 0.45 if th["socle"] != "nuage" else 0.7
    motif = oe["numero"] % 4
    bande = [lambda i: "Bande" if i % 3 == 1 else "Coquille", lambda i: "Bande" if i % 2 else "Coquille",
             lambda i: "Bande" if i in (3, 4, 8, 9) else "Coquille", lambda i: "Bande" if i % 4 == 2 else "Coquille"][motif]
    c = coquille(H, R_, 11 + int(3 * k), bas=bas, bande=bande)
    blocs_surface(c, int(14 + 14 * k), 0.3 + 0.1 * k, "Tache", bas + 0.4, bas + H - 0.2)
    blocs_surface(c, int(10 + 10 * k), 0.3, "Coquille", bas + 0.4, bas + H - 0.2)
    socle_oeuf(th["socle"], R_)
    for nom in th["decors"]:
        decor_oeuf(nom, c, R_, H, bas, k)
    slug = oe["nom"].lower()
    for a_, b_ in (("'", ""), ("-", "_"), (" ", "_")):
        slug = slug.replace(a_, b_)
    return finaliser(f"oeuf_{oe['numero']:02d}_{slug}", couleurs, 1.0,
                     dossier=os.path.join(os.path.expanduser("~"), "oeufs50"))


def construire(numero, bebe=False):
    global BEBE, PUPILLE
    BEBE = bebe
    for num, nom, rarete, echelle, couleurs, f in DINOS:
        if num == numero:
            nettoyer()
            random.seed(num)
            PUPILLE = num > 20 and sum(couleurs["Oeil"]) > 150
            f()
            fichier = f"{num:02d}_{nom.replace(' ', '_').replace('-', '_')}"
            if bebe:
                fichier = "bebe_" + fichier
                echelle *= 0.5
            d = finaliser(fichier, couleurs, echelle)
            BEBE = False
            return d


if __name__ == "__main__":
    versions = {"adultes": [False], "bebes": [True], "oeufs": [], "machine": [], "outils": [], "oeufs50": [],
                "nouveaux": []}.get(MODE, [False, True])
    if MODE in ("oeufs50", "tous"):
        for oe in repartir_oeufs():
            print(f"--- {oe['nom']} ({oe['rarete']}) ---")
            construire_oeuf_genere(oe)
    if MODE in ("nouveaux", "tous"):
        for g in GENERES:
            if SEULEMENT and g["numero"] not in SEULEMENT:
                continue
            print(f"--- {g['numero']} {g['nom']} ({g['rarete']}) ---")
            construire_genere(g)
    if MODE in ("outils", "tous"):
        for ou in OUTILS:
            if SEULEMENT and ou["numero"] not in SEULEMENT:
                continue
            print(f"--- Outil {ou['numero']:02d} {ou['nom']} ({ou['rarete']}) ---")
            construire_outil(ou)
    if MODE in ("machine", "tous"):
        print("--- Machine a fossiles ---")
        construire_machine()
    if MODE in ("oeufs", "tous"):
        for oe in OEUFS:
            print(f"--- {oe['nom']} ({oe['rarete']}) ---")
            construire_oeuf(oe)
    for bebe in versions:
        for num, nom, rarete, *_ in DINOS:
            if SEULEMENT and num not in SEULEMENT:
                continue
            print(f"--- {num:02d} {nom} ({rarete}){' bebe' if bebe else ''} ---")
            construire(num, bebe)
