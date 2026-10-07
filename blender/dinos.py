"""30 dinos et 8 oeufs "en blocs" style Roblox (du plus commun au plus rare).
1 a 20 : les grands dinos. 21 a 30 : les petits dinos. Oeufs : voir OEUFS plus bas.

Utilisation : Blender > onglet "Scripting" > Open (dinos.py) > Run Script (triangle).
Construit chaque dino, calcule sa texture a studs, l'exporte en .glb dans
le dossier "dinos" de ton dossier utilisateur, puis passe au suivant.
(Compter quelques minutes pour les 20.)
Pour n'en faire qu'un : mets son numero dans SEULEMENT, par exemple SEULEMENT = [18].
MODE : "adultes", "bebes" (versions bebe mignonnes, dans le dossier "bebes"),
"oeufs" (dans le dossier "oeufs") ou "tous".

Dans Roblox Studio : Avatar > Import 3D.
"""
import bpy
import bmesh
import math
import os
import random
import numpy as np
from mathutils import Vector, Quaternion

SEULEMENT = []          # vide = les 20
MODE = "tous"           # "adultes", "bebes", "oeufs" ou "tous"
DOSSIER = os.path.join(os.path.expanduser("~"), "dinos")
DOSSIER_BEBES = os.path.join(os.path.expanduser("~"), "bebes")
DOSSIER_OEUFS = os.path.join(os.path.expanduser("~"), "oeufs")
BEBE = False            # change pendant la construction
PUPILLE = False         # ajoute une pupille noire quand l'oeil est colore
STUDS_PAR_UNITE = 5.0
TEXTURE = 1024
AVEC_STUDS = {"Peau", "Rayure", "Ventre", "Accent", "Coquille", "Bande", "Tache", "Deco1", "Deco2"}

COULEURS_DE_BASE = {
    "Peau": (128, 146, 78), "Rayure": (86, 102, 54), "Ventre": (232, 228, 218),
    "Accent": (200, 120, 60), "Corne": (236, 226, 196), "Dent": (255, 255, 255),
    "Bouche": (206, 24, 36), "Oeil": (12, 12, 14), "Reflet": (255, 255, 255),
    "Griffe": (240, 238, 230), "Pupille": (12, 12, 14),
    # oeufs
    "Coquille": (236, 222, 176), "Bande": (214, 194, 140), "Tache": (196, 170, 116), "Deco1": (150, 110, 64),
    "Deco2": (120, 86, 50), "Lueur": (255, 90, 80), "Os": (244, 240, 226), "Noir": (24, 22, 22),
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
    return {"corps": corps, "cou": cou, "tete": tete, "queue": queue, "fin_queue": fin, "w": w, "l": l, "h": h, "hz": hz}


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
    return {"corps": corps, "cou": cou, "tete": tete, "queue": queue, "fin_queue": fin, "w": w, "l": l, "h": h, "hz": hz}


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
    boite("Socle", (0, 0.3, 0.3), (1.6, 1.6, 0.6), "Rayure")
    boite("Tige", (0, 0.3, 1.2), (0.25, 0.25, 1.6), "Rayure", biseau=0.04)


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
def finaliser(nom_fichier, couleurs, echelle, dossier=None):
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
    d.scale = (echelle,) * 3
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

    dossier = dossier or (DOSSIER_BEBES if BEBE else DOSSIER)
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, nom_fichier + ".glb")
    activer(d)
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


def theme(**kw):
    c = dict(COULEURS_DE_BASE)
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
    versions = {"adultes": [False], "bebes": [True], "oeufs": []}.get(MODE, [False, True])
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
