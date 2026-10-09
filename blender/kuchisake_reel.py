"""Kuchisake-onna realiste (horreur) a partir du corps humain MakeHuman (CC0).

Utilisation : Blender > onglet "Scripting" > Open (ce fichier) > Run Script.
Le dossier "makehuman" (base.obj + morphs) doit etre a cote de ce fichier
(sinon le script les telecharge depuis le depot MakeHuman, licence CC0).

Sortie dans le dossier "horreur" de ton dossier utilisateur, deux versions :
  kuchisake_sourire.fbx / .glb  -> la bouche fendue jusqu'aux oreilles
  kuchisake_masque.fbx  / .glb  -> avec le masque (les cicatrices depassent)
  kuchisake_*.png               -> textures (couleur + normal map peau / kimono, cheveux)
                                   aussi incluses dans les fichiers

Fortnite (UEFN) : Content Browser > Import > kuchisake_*.fbx (Skeletal Mesh, avec les animations).
Taille : 2,27 m avec les geta. Squelette humain (23 os) + 7 animations :
  Attente, Marche, Course, Regard, Attaque, Jolie, Sourire.
Cheveux : dans la matiere "Cheveux", mettre Blend Mode = Masked et brancher l'alpha de la texture
sur Opacity Mask (sinon les meches sont pleines).

Corps : MakeHuman (makehumancommunity.org), CC0.
"""
import bpy
import bmesh
import math
import os
import random
import urllib.request
import numpy as np
from mathutils import Vector, Quaternion, Matrix
from mathutils.bvhtree import BVHTree

ICI = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
DOSSIER_MH = os.path.join(ICI, "makehuman")
SORTIE = os.path.join(os.path.expanduser("~"), "horreur")
SOURCE_MH = "https://raw.githubusercontent.com/makehumancommunity/makehuman/master/makehuman/data/"
FICHIERS_MH = {
    "base.obj": "3dobjs/base.obj",
    "femme_mince.target": "targets/macrodetails/universal-female-young-minmuscle-minweight.target",
    "grande.target": "targets/macrodetails/height/female-young-minmuscle-minweight-maxheight.target",
}
HAUTEUR = 2.2        # en metres (Fortnite : un joueur fait environ 1,9 m)
GETA = 0.07          # hauteur des sandales en bois : tout le corps est remonte d'autant
TEXTURE = 2048
VARIANTES = ("sourire", "masque")

COULEURS = {
    "Peau": (214, 212, 210), "Oeil": (3, 2, 3), "Dent": (214, 204, 172),
    "Cheveux": (9, 8, 10), "Cheveux2": (17, 16, 20), "Robe": (92, 10, 18), "RobeSombre": (34, 5, 8), "Obi": (14, 12, 14),
    "Col": (10, 9, 10), "SousCol": (222, 216, 202), "Cordon": (176, 140, 80), "Gorge": (14, 3, 5), "Ongle": (16, 12, 14),
    "Iris": (178, 176, 168), "Pupille": (3, 2, 3), "Tabi": (214, 208, 192), "Bois": (110, 78, 50),
    "Hanao": (70, 8, 14), "Calotte": (9, 8, 10), "Masque": (226, 230, 232),
}


def lineaire(c):
    f = lambda v: (v / 255) / 12.92 if v / 255 <= 0.04045 else ((v / 255 + 0.055) / 1.055) ** 2.4
    return (f(c[0]), f(c[1]), f(c[2]), 1)


def lisse01(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------
#  Outils Blender
# ---------------------------------------------------------------------------
def fichier_mh(nom):
    chemin = os.path.join(DOSSIER_MH, nom)
    if not os.path.exists(chemin):
        os.makedirs(DOSSIER_MH, exist_ok=True)
        print("Telechargement", nom)
        urllib.request.urlretrieve(SOURCE_MH + FICHIERS_MH[nom], chemin)
    return chemin


MATS = {}


def matiere(nom, rugosite=0.5):
    if nom not in MATS:
        m = bpy.data.materials.new(nom)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = lineaire(COULEURS[nom])
        b.inputs["Roughness"].default_value = rugosite
        m.diffuse_color = lineaire(COULEURS[nom])
        MATS[nom] = m
    return MATS[nom]


def lier(o):
    bpy.context.scene.collection.objects.link(o)
    return o


def activer(*objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[-1]


def nettoyer():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.armatures, bpy.data.actions):
        for d in list(c):
            c.remove(d)
    MATS.clear()


def mesh_depuis(nom, verts, faces, mats):
    me = bpy.data.meshes.new(nom)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    o = lier(bpy.data.objects.new(nom, me))
    for m in mats:
        me.materials.append(matiere(m))
    return o


def appliquer_modif(o, mod):
    activer(o)
    bpy.ops.object.modifier_apply(modifier=mod.name)


def bvh(o):
    return BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())


# ---------------------------------------------------------------------------
#  1) LE CORPS (MakeHuman, avec ses UV)
# ---------------------------------------------------------------------------
def corps():
    V, VT, G, g = [], [], {}, None
    for l in open(fichier_mh("base.obj")):
        if l.startswith("v "):
            V.append([float(x) for x in l.split()[1:4]])
        elif l.startswith("vt "):
            VT.append([float(x) for x in l.split()[1:3]])
        elif l.startswith("g "):
            g = l.split()[1]
            G.setdefault(g, [])
        elif l.startswith("f "):
            G[g].append([[int(y) - 1 for y in x.split("/")[:2]] for x in l.split()[1:]])
    V = np.array(V)
    for nom, poids in (("femme_mince.target", 1.0), ("grande.target", 0.8)):
        for l in open(fichier_mh(nom)):
            if l[:1].isdigit():
                i, dx, dy, dz = l.split()
                V[int(i)] += poids * np.array([float(dx), float(dy), float(dz)])
    # MakeHuman : y vers le haut, z vers l'avant  ->  Blender : z vers le haut, regarde vers -Y
    B = np.stack([V[:, 0], -V[:, 2], V[:, 1]], axis=1)
    faces = G["body"]
    utiles = sorted(set(v for f in faces for v, _ in f))
    sol, haut = B[utiles, 2].min(), B[utiles, 2].max()
    B = (B - np.array([0, 0, sol])) * (HAUTEUR / (haut - sol)) + np.array([0, 0, GETA])
    centre = lambda grp: Vector(B[sorted(set(v for f in G[grp] for v, _ in f))].mean(axis=0))
    J = {g[6:]: centre(g) for g in G if g.startswith("joint-")}
    J["levres"] = (centre("helper-upper-teeth") + centre("helper-lower-teeth")) / 2
    idx = {o: n for n, o in enumerate(utiles)}
    o = mesh_depuis("Corps", B[utiles], [[idx[v] for v, _ in f] for f in faces], ["Peau"])
    for f in o.data.polygons:
        f.use_smooth = True
    uv = o.data.uv_layers.new(name="UV")
    k = 0
    for f in faces:
        for _, t in f:
            uv.data[k].uv = VT[t]
            k += 1
    return o, J


# ---------------------------------------------------------------------------
#  2) LE SQUELETTE (cale sur les articulations MakeHuman)
# ---------------------------------------------------------------------------
def squelette(J):
    colonne = sorted([J[n] for n in ("spine-4", "spine-3", "spine-2", "spine-1")], key=lambda v: v.z)
    os_ = [("Racine", Vector((0, 0, 0)), Vector((0, 0, 0.15)), None),
           ("Bassin", J["pelvis"], colonne[1], "Racine"),
           ("Ventre", colonne[1], colonne[2], "Bassin"),
           ("Poitrine", colonne[2], colonne[3], "Ventre"),
           ("Haut", colonne[3], J["neck"], "Poitrine"),
           ("Cou", J["neck"], J["head"], "Haut"),
           ("Tete", J["head"], J["head-2"], "Cou"),
           ("Machoire", J["mouth"], J["jaw"], "Tete"),
           ("Masque", J["mouth"], J["mouth"] + Vector((0, -0.08, 0)), "Tete")]   # pour enlever le masque
    for c, s in (("L", "l"), ("R", "r")):
        bout = J[f"{s}-hand"] + ((J[f"{s}-hand-2"] + J[f"{s}-hand-3"]) / 2 - J[f"{s}-hand"]) * 2.2
        os_ += [(f"Clavicule.{c}", J[f"{s}-clavicle"], J[f"{s}-shoulder"], "Haut"),
                (f"Bras.{c}", J[f"{s}-shoulder"], J[f"{s}-elbow"], f"Clavicule.{c}"),
                (f"AvantBras.{c}", J[f"{s}-elbow"], J[f"{s}-hand"], f"Bras.{c}"),
                (f"Main.{c}", J[f"{s}-hand"], bout, f"AvantBras.{c}"),
                (f"Cuisse.{c}", J[f"{s}-upper-leg"], J[f"{s}-knee"], "Bassin"),
                (f"Tibia.{c}", J[f"{s}-knee"], J[f"{s}-ankle"], f"Cuisse.{c}"),
                (f"Pied.{c}", J[f"{s}-ankle"], J[f"{s}-foot-2"], f"Tibia.{c}")]
    arm = bpy.data.armatures.new("Squelette")
    ob = lier(bpy.data.objects.new("Squelette", arm))
    activer(ob)
    bpy.ops.object.mode_set(mode='EDIT')
    for nom, a, b, p in os_:
        eb = arm.edit_bones.new(nom)
        eb.head, eb.tail = a, b
        if (b - a).length < 1e-3:
            eb.tail = a + Vector((0, 0, 0.03))
        eb.roll = 0
        if p:
            eb.parent = arm.edit_bones[p]
            eb.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob


def rot_os(arm, nom, axe_monde, degres):
    """Rotation (en pose) d'un os autour d'un axe exprime dans le monde."""
    b = arm.data.bones[nom]
    axe = (b.matrix_local.to_3x3().inverted() @ Vector(axe_monde)).normalized()
    return Quaternion(axe, math.radians(degres))


def point_os(arm, nom, p_repos):
    """Ou se trouve, dans la pose actuelle, un point (donne au repos) attache a un os."""
    return arm.pose.bones[nom].matrix @ arm.data.bones[nom].matrix_local.inverted() @ Vector(p_repos)


def ik_bras(arm, c, cible, pole):
    """Plie le bras pour que le poignet arrive sur la cible, le coude du cote du 'pole'."""
    pb1, pb2 = arm.pose.bones[f"Bras.{c}"], arm.pose.bones[f"AvantBras.{c}"]
    S = pb1.head.copy()
    L1, L2 = pb1.length, pb2.length
    d = cible - S
    dist = max(1e-4, min(d.length, (L1 + L2) * 0.999))
    dn = d.normalized()
    th = math.acos(max(-1.0, min(1.0, (L1 * L1 + dist * dist - L2 * L2) / (2 * L1 * dist))))
    perp = (pole - dn * pole.dot(dn)).normalized()
    coude = S + (dn * math.cos(th) + perp * math.sin(th)) * L1
    for pb, vers in ((pb1, coude), (pb2, S + dn * dist)):
        M = pb.matrix.copy()
        tete_os = pb.head.copy()
        R = M.to_3x3().col[1].normalized().rotation_difference((vers - tete_os).normalized()).to_matrix()
        pb.matrix = Matrix.Translation(tete_os) @ (R @ M.to_3x3()).to_4x4()
        bpy.context.view_layer.update()


def poser(arm, rotations, positions=None, ik=None):
    """rotations : {os: [(axe du monde, degres), ...]}   positions : {os: deplacement dans le monde}
    ik : {cote: (fonction qui donne la cible du poignet, direction du coude)}"""
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion()
        pb.location = (0, 0, 0)
    for nom, liste in rotations.items():
        q = Quaternion()
        for axe, deg in liste:
            q = rot_os(arm, nom, axe, deg) @ q
        arm.pose.bones[nom].rotation_quaternion = q
    for nom, d in (positions or {}).items():
        arm.pose.bones[nom].location = arm.data.bones[nom].matrix_local.to_3x3().inverted() @ Vector(d)
    bpy.context.view_layer.update()
    for c, (cible, pole) in (ik or {}).items():
        ik_bras(arm, c, cible(), Vector(pole))


def pose_A(corps_, arm, J):
    """Les bras de MakeHuman sont presque a l'horizontale : on les descend (pose en A, 50 degres),
    et les jambes sont resserrees. Les reperes des mains et des pieds suivent."""
    rot = {}
    for c, s in (("L", 1), ("R", -1)):
        b = arm.data.bones[f"Bras.{c}"]
        d = (b.tail_local - b.head_local).normalized()
        angle = math.degrees(math.atan2(-d.z, abs(d.x)))
        rot[f"Bras.{c}"] = [((0, 1, 0), s * (50 - angle))]
        b = arm.data.bones[f"Cuisse.{c}"]
        d = (arm.data.bones[f"Tibia.{c}"].tail_local - b.head_local).normalized()
        rot[f"Cuisse.{c}"] = [((0, 1, 0), s * (math.degrees(math.atan2(abs(d.x), -d.z)) - 2))]  # jambes serrees
    poser(arm, rot)
    for c, s in (("L", "l"), ("R", "r")):
        for os_nom, prefixes in ((f"Main.{c}", (f"{s}-hand", f"{s}-finger")), (f"AvantBras.{c}", (f"{s}-elbow",)),
                                 (f"Pied.{c}", (f"{s}-ankle", f"{s}-foot", f"{s}-toe")), (f"Tibia.{c}", (f"{s}-knee",))):
            M = arm.pose.bones[os_nom].matrix @ arm.data.bones[os_nom].matrix_local.inverted()
            for k in list(J):
                if k.startswith(prefixes):
                    J[k] = M @ J[k]
    mod = next(m for m in corps_.modifiers if m.type == 'ARMATURE')
    activer(corps_)
    bpy.ops.object.modifier_copy(modifier=mod.name)
    bpy.ops.object.modifier_apply(modifier=corps_.modifiers[-1].name)
    activer(arm)
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def mains_longues(corps_, J):
    """Doigts plus longs (+22 %) et plus fins : des mains osseuses."""
    me = corps_.data
    noms = {g.index: g.name for g in corps_.vertex_groups}
    for c, s in (("L", "l"), ("R", "r")):
        doigts = []
        for k in range(1, 6):
            a, b = J[f"{s}-finger-{k}-1"], J[f"{s}-finger-{k}-4"]
            doigts.append((a, (b - a).length, (b - a).normalized()))
        for v in me.vertices:
            g = max(v.groups, key=lambda g: g.weight, default=None)
            if g is None or noms[g.group] != f"Main.{c}":
                continue
            p = v.co.copy()
            meilleur = None
            for a, L, d in doigts:
                t = (p - a).dot(d) / L
                dist = (p - (a + d * (max(0.0, min(1.0, t)) * L))).length
                if meilleur is None or dist < meilleur[0]:
                    meilleur = (dist, t, a, d, L)
            _, t, a, d, L = meilleur
            if t <= 0:
                continue
            axe = a + d * (t * L)
            v.co = axe + d * (t * L * 0.22) + (p - axe) * (1 - 0.12 * min(1.0, t * 3))
        for k in range(1, 6):
            a, L, d = doigts[k - 1]
            for j in (3, 4):
                q = J[f"{s}-finger-{k}-{j}"]
                J[f"{s}-finger-{k}-{j}"] = q + d * ((q - a).dot(d) * 0.22)
    me.update()


def griffes(J):
    """Longs ongles noirs et pointus au bout de chaque doigt."""
    bm = bmesh.new()
    nb = {}
    for c, s in (("L", "l"), ("R", "r")):
        avant = len(bm.verts)
        for k in range(1, 6):
            D, T = J[f"{s}-finger-{k}-3"], J[f"{s}-finger-{k}-4"]
            d = (T - D).normalized()
            base = D + (T - D) * 0.5
            pointe = T + d * (0.022 if k == 1 else 0.032) - Vector((0, 0, 0.004))
            a = d.orthogonal().normalized()
            b = d.cross(a)
            anneau = [bm.verts.new(base + (a * math.cos(t) + b * math.sin(t)) * 0.0045)
                      for t in np.linspace(0, 2 * math.pi, 7)[:-1]]
            pv = bm.verts.new(pointe)
            for i in range(6):
                bm.faces.new((anneau[i], anneau[(i + 1) % 6], pv))
            bm.faces.new(anneau[::-1])
        nb[c] = (avant, len(bm.verts))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("Griffes")
    bm.to_mesh(me)
    bm.free()
    o = lier(bpy.data.objects.new("Griffes", me))
    me.materials.append(matiere("Ongle", 0.25))
    for c, (a, b) in nb.items():
        o.vertex_groups.new(name=f"Main.{c}").add(list(range(a, b)), 1.0, 'REPLACE')
    return [o]


# ---------------------------------------------------------------------------
#  3) LE VISAGE
# ---------------------------------------------------------------------------
class Visage:
    """Reperes du visage (pose de repos, la tete regarde vers -Y)."""

    def __init__(self, corps_, J):
        self.yeux = [J["l-eye"], J["r-eye"]]
        self.e = (self.yeux[0] - self.yeux[1]).length          # ecart des yeux : l'unite du visage
        lv = J["levres"]
        self.M = bvh(corps_).ray_cast(Vector((0, lv.y - 10 * self.e, lv.z)), Vector((0, 1, 0)))[0]
        co = np.array([v.co for v in corps_.data.vertices])
        t = co[(co[:, 2] > self.M.z - 1.4 * self.e) & (np.abs(co[:, 0]) < 2.2 * self.e)]
        self.C = Vector((0, (t[:, 1].min() + t[:, 1].max()) / 2, self.yeux[0].z + 0.3 * self.e))
        self.cou = J["neck"].z
        self.larg = 1.08 * self.e                               # le sourire va jusqu'aux oreilles

    # le sourire : une courbe qui remonte vers les oreilles, plus ouverte au milieu
    def courbe(self, t):
        return self.e * (0.03 + 0.52 * np.abs(t) ** 2.1)

    def demi(self, t):
        return self.e * (0.012 + 0.115 * np.clip(1 - np.abs(t) ** 1.6, 0, 1))


def subdiviser_tete(corps_, V):
    """Deux fois plus de details sur la tete (pour creuser la bouche et les orbites)."""
    bm = bmesh.new()
    bm.from_mesh(corps_.data)
    faces = [f for f in bm.faces if all(v.co.z > V.cou - 0.3 * V.e for v in f.verts)]
    aretes = list({e for f in faces for e in f.edges})
    bmesh.ops.subdivide_edges(bm, edges=aretes, cuts=1, use_grid_fill=True, smooth=0.6)
    bm.to_mesh(corps_.data)
    bm.free()
    corps_.data.update()


def sculpter(corps_, V):
    """Orbites enfoncees, joues creuses, une fente creusee le long du sourire et des bords de plaie gonfles."""
    me = corps_.data
    e = V.e
    for v in me.vertices:
        p = v.co
        if p.z < V.cou or p.y > V.C.y:
            continue
        pousse = 0.0
        for y in V.yeux:
            dx, dz = (p.x - y.x) / (0.4 * e), (p.z - y.z) / (0.32 * e)
            r = math.hypot(dx, dz)
            if r < 1.6:
                f = (1 - r / 1.6) ** 1.4 * (0.55 if dz > 0.7 else 1.0)
                pousse = max(pousse, 0.06 * e * f)
        for sgn in (1, -1):                                   # joues creusees
            r = math.hypot(p.x - (V.M.x + sgn * 0.8 * e), p.z - (V.M.z + 0.05 * e)) / (0.45 * e)
            if r < 1:
                pousse = max(pousse, 0.05 * e * (1 - r) ** 2)
        gonfle = 0.0
        t = (p.x - V.M.x) / V.larg
        if abs(t) < 1.12:
            dz = abs(p.z - V.M.z - V.courbe(t))
            h = V.demi(t) + 0.035 * e
            if dz < h:
                prof = e * (0.035 + 0.11 * max(0.0, 1 - abs(t)))
                pousse = max(pousse, prof * (1 - (dz / h) ** 2))
            elif dz < h + 0.06 * e:                           # bords de la plaie gonfles
                gonfle = 0.018 * e * (1 - abs(dz - h - 0.03 * e) / (0.03 * e))
        if pousse or gonfle:
            v.co = p + Vector((0, pousse - gonfle, 0))
    me.update()


def bruit(P, freq, graine, n=7):
    rng = np.random.default_rng(graine)
    s = np.zeros(P.shape[0])
    for _ in range(n):
        k = rng.normal(size=3)
        k = k / np.linalg.norm(k) * freq * rng.uniform(0.6, 1.6)
        s += np.sin(P @ k + rng.uniform(0, 6.28))
    return s / math.sqrt(n / 2)


def cuire(o, fabrique=None, type_='EMIT', echantillons=1):
    """Cuit une valeur dans une image (selon les UV de l'objet) et la renvoie en tableau numpy (pixels, 4)."""
    img = bpy.data.images.new("cuisson", TEXTURE, TEXTURE, alpha=True, float_buffer=True)
    img.colorspace_settings.name = "Non-Color"
    for i, m in enumerate(o.data.materials):
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        if fabrique:
            em = nt.nodes.new("ShaderNodeEmission")
            nt.links.new(fabrique(nt, i), em.inputs["Color"])
            nt.links.new(em.outputs[0], out.inputs["Surface"])
        else:
            d = nt.nodes.new("ShaderNodeBsdfDiffuse")
            nt.links.new(d.outputs[0], out.inputs["Surface"])
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        nt.nodes.active = tex
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = echantillons
    activer(o)
    bpy.ops.object.bake(type=type_, margin=8, use_clear=True)
    a = np.empty(TEXTURE * TEXTURE * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(-1, 4)


def _vecteur(sortie, mul, add):
    def f(nt, i):
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        ma = nt.nodes.new("ShaderNodeVectorMath")
        ma.operation = 'MULTIPLY_ADD'
        ma.inputs[1].default_value = tuple(mul)
        ma.inputs[2].default_value = tuple(add)
        nt.links.new(geo.outputs[sortie], ma.inputs[0])
        return ma.outputs[0]
    return f


def position_pixels(o):
    co = np.array([o.matrix_world @ v.co for v in o.data.vertices])
    mn, mx = co.min(0) - 0.01, co.max(0) + 0.01
    return cuire(o, _vecteur("Position", 1 / (mx - mn), -mn / (mx - mn)))[:, :3] * (mx - mn) + mn


def normale_pixels(o):
    return cuire(o, _vecteur("Normal", (0.5,) * 3, (0.5,) * 3))[:, :3] * 2 - 1


def occlusion_pixels(o, distance, echantillons=24):
    """Ombre des creux (orbites, plis...) : donne beaucoup de relief a la texture."""
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new("Monde")
    sc.world.light_settings.distance = distance
    return cuire(o, None, 'AO', echantillons)[:, 0]


def poser_texture(o, nom, rgb, rugosite):
    """Enregistre l'image (png + incluse dans le fichier) et en fait l'unique matiere de l'objet."""
    rgb = np.clip(rgb, 0, 1)
    img = bpy.data.images.new(nom, TEXTURE, TEXTURE, alpha=False)
    img.pixels.foreach_set(np.concatenate([rgb, np.ones((rgb.shape[0], 1))], 1).astype(np.float32).ravel())
    os.makedirs(SORTIE, exist_ok=True)
    img.filepath_raw = os.path.join(SORTIE, nom + ".png")
    img.file_format = 'PNG'
    img.save()
    img.pack()
    m = bpy.data.materials.new(nom)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rugosite
    tx = m.node_tree.nodes.new("ShaderNodeTexImage")
    tx.image = img
    m.node_tree.links.new(tx.outputs["Color"], b.inputs["Base Color"])
    o.data.materials.clear()
    o.data.materials.append(m)
    for p in o.data.polygons:
        p.material_index = 0


def carte_normale(o, hauteur, distance, nom):
    """Relief fin (pores, rides, coutures, broderies...) : la hauteur calculee pour chaque pixel
    devient une normal map (cuite par Blender), branchee sur la matiere et exportee avec elle."""
    T = TEXTURE
    h = np.clip(hauteur, -1, 1) * 0.5 + 0.5
    img_h = bpy.data.images.new(nom + "_hauteur", T, T, alpha=False, float_buffer=True)
    img_h.colorspace_settings.name = "Non-Color"
    img_h.pixels.foreach_set(np.stack([h, h, h, np.ones_like(h)], 1).astype(np.float32).ravel())
    m = o.data.materials[0]
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    th = nt.nodes.new("ShaderNodeTexImage")
    th.image = img_h
    th.interpolation = 'Cubic'
    bosse = nt.nodes.new("ShaderNodeBump")
    bosse.inputs["Distance"].default_value = distance
    nt.links.new(th.outputs["Color"], bosse.inputs["Height"])
    nt.links.new(bosse.outputs["Normal"], bsdf.inputs["Normal"])
    img_n = bpy.data.images.new(nom, T, T, alpha=False)
    img_n.colorspace_settings.name = "Non-Color"
    tn = nt.nodes.new("ShaderNodeTexImage")
    tn.image = img_n
    nt.nodes.active = tn
    sc = bpy.context.scene
    sc.cycles.samples = 4
    activer(o)
    bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', margin=8, use_clear=True)
    nt.nodes.remove(bosse)
    nt.nodes.remove(th)
    bpy.data.images.remove(img_h)
    img_n.filepath_raw = os.path.join(SORTIE, nom + ".png")
    img_n.file_format = 'PNG'
    img_n.save()
    img_n.pack()
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.uv_map = "UV"
    nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])


def melange(col, couleur, alpha):
    alpha = np.clip(alpha, 0, 1)[:, None]
    return col * (1 - alpha) + np.array(couleur) * alpha


def dist_segment(px, pz, a, b):
    ab = np.array(b) - np.array(a)
    t = np.clip(((px - a[0]) * ab[0] + (pz - a[1]) * ab[1]) / (ab @ ab), 0, 1)
    return np.hypot(px - a[0] - t * ab[0], pz - a[1] - t * ab[1])


def peindre_peau(corps_, V, J):
    """Le visage est peint pixel par pixel a partir de la position 3D de chaque pixel de la texture.
    En meme temps on calcule le relief (normal map) : pores, rides, bords de plaie, fils de suture."""
    P = position_pixels(corps_)
    ao = occlusion_pixels(corps_, 0.6 * V.e, 32)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    e = V.e
    # peau : blanc grisatre, marbree, avec des pores
    col = np.tile(np.array([0.80, 0.80, 0.80]), (P.shape[0], 1))
    col = col * (1 + 0.035 * bruit(P, 9 / e, 1)[:, None] + 0.02 * bruit(P, 140 / e, 4)[:, None]) \
        + np.array([-0.02, 0.0, 0.025]) * bruit(P, 3 / e, 2)[:, None]
    haut = 0.06 * bruit(P, 260 / e, 41) + 0.05 * bruit(P, 90 / e, 42)
    devant = lisse01(V.C.y + 0.3 * e, V.C.y - 0.3 * e, y) * (z > V.cou - 0.2 * e)
    fx, fz = x - V.M.x, z - V.M.z
    # veines bleutees (un peu en relief) : tempes, cotes du visage, cou
    veine = lisse01(0.1, 0.0, np.abs(bruit(P, 22 / e, 7)))
    zone = np.maximum(lisse01(0.7 * e, 1.2 * e, np.abs(x)) * (z > V.M.z),
                      lisse01(V.cou + 0.4 * e, V.cou, z) * lisse01(V.cou - 1.6 * e, V.cou - 0.8 * e, z))
    col = melange(col, (0.40, 0.42, 0.56), veine * zone * 0.4)
    haut += 0.3 * veine * zone
    # rides du front
    for k in range(3):
        zc = V.yeux[0].z + (0.85 + 0.13 * k) * e + 0.03 * e * np.sin(x / e * 4 + k)
        haut -= 0.35 * lisse01(0.016 * e, 0.0, np.abs(z - zc)) * np.clip(1 - np.abs(x) / (0.9 * e), 0, 1) * devant
    for k, oe in enumerate(V.yeux):
        r = np.sqrt(((x - oe.x) / (0.42 * e)) ** 2 + ((z - oe.z) / (0.32 * e)) ** 2)
        # cernes violets, orbites noires, paupieres rougies
        col = melange(col, (0.42, 0.33, 0.38), lisse01(2.3, 1.2, r) * 0.75 * devant)
        col = melange(col, (0.02, 0.01, 0.015), lisse01(1.45, 0.75, r) * devant)
        col = melange(col, (0.45, 0.14, 0.18), lisse01(0.95, 1.1, r) * lisse01(1.4, 1.2, r) * 0.3 * devant)
        # rides sous les yeux (poches)
        dx = (x - oe.x) / (0.45 * e)
        for j in range(3):
            zc = oe.z - (0.42 + 0.09 * j) * e + 0.12 * e * dx ** 2
            haut -= 0.4 * lisse01(0.014 * e, 0.0, np.abs(z - zc)) * np.clip(1 - np.abs(dx) / 1.1, 0, 1) * devant
        # larmes noires
        rng = np.random.default_rng(10 + k)
        for _ in range(3):
            xs = oe.x + rng.uniform(-0.18, 0.18) * e
            lg = rng.uniform(0.5, 1.1) * e
            w = rng.uniform(0.018, 0.03) * e
            d0 = oe.z - 0.2 * e
            u = np.clip((d0 - z) / lg, 0, 1)
            trait = (np.abs(x - xs - 0.04 * e * np.sin(u * 5)) < w * (1 - 0.7 * u)) & (z < d0) & (z > d0 - lg)
            col = melange(col, (0.04, 0.02, 0.03), trait * 0.85 * devant)
    # sourire dechire jusqu'aux oreilles
    t = fx / V.larg
    dzs = np.abs(fz - V.courbe(t))
    dem = V.demi(t) * (1 + 0.35 * bruit(P, 40 / e, 3))
    dans = (np.abs(t) < 1.12) * devant * lisse01(1.12, 0.95, np.abs(t))
    col = melange(col, (0.82, 0.55, 0.56), lisse01(dem + 0.16 * e, dem + 0.05 * e, dzs) * dans * 0.7)
    col = melange(col, (0.48, 0.05, 0.08), lisse01(dem + 0.06 * e, dem + 0.03 * e, dzs) * dans)
    col = melange(col, (0.20, 0.02, 0.04), lisse01(dem, dem * 0.6, dzs) * dans)
    col = melange(col, (0.06, 0.0, 0.01), lisse01(dem * 0.7, dem * 0.2, dzs) * dans)
    haut -= 0.9 * lisse01(dem + 0.01 * e, dem * 0.5, dzs) * dans
    haut += 0.7 * np.exp(-((dzs - dem - 0.035 * e) / (0.02 * e)) ** 2) * dans * (1 + 0.4 * bruit(P, 80 / e, 43))
    # points de suture en croix sur les joues (fils en relief, trous, peau qui tire)
    for sgn in (1, -1):
        for tk in np.arange(0.45, 1.07, 0.075):
            xk, zc = sgn * tk * V.larg, float(V.courbe(tk))
            hk = float(V.demi(tk)) + 0.06 * e
            sel = (np.abs(fx - xk) < 0.12 * e) & (np.abs(fz - zc) < hk + 0.04 * e) & (devant > 0.5)
            if not sel.any():
                continue
            for a, b in (((xk - 0.045 * e, zc - hk), (xk + 0.045 * e, zc + hk)),
                         ((xk + 0.045 * e, zc - hk), (xk - 0.045 * e, zc + hk))):
                d = dist_segment(fx[sel], fz[sel], a, b)
                fil = np.zeros(len(x))
                fil[sel] = lisse01(0.014 * e, 0.007 * e, d)
                col = melange(col, (0.07, 0.05, 0.06), fil)
                haut += 0.8 * fil
                for bout in (a, b):
                    rr = np.hypot(fx[sel] - bout[0], fz[sel] - bout[1])
                    trou = np.zeros(len(x))
                    trou[sel] = lisse01(0.03 * e, 0.012 * e, rr)
                    col = melange(col, (0.45, 0.08, 0.1), trou * 0.6)
                    pli = np.zeros(len(x))
                    ang = np.arctan2(fz[sel] - bout[1], fx[sel] - bout[0])
                    pli[sel] = 0.25 * np.sin(ang * 7) * lisse01(0.07 * e, 0.02 * e, rr)
                    haut += pli - 0.6 * trou
    # quelques coulures sous la bouche
    rng = np.random.default_rng(5)
    for _ in range(7):
        ts = rng.uniform(-0.85, 0.85)
        xs = ts * V.larg
        zs = V.courbe(ts) - V.demi(ts) - 0.02 * e
        lg = rng.uniform(0.15, 0.55) * e
        w = rng.uniform(0.012, 0.022) * e
        u = np.clip((zs - fz) / lg, 0, 1)
        trait = (np.abs(fx - xs) < w * (1.2 - 0.5 * u)) & (fz < zs) & (fz > zs - lg)
        col = melange(col, (0.30, 0.02, 0.04), trait * devant * 0.9)
        haut += 0.15 * trait * devant
    # mains sales : crasse vers le bout des doigts, sang sous les ongles, articulations marquees
    for s in "lr":
        W = J[f"{s}-hand"]
        bout = sum((J[f"{s}-finger-{k}-4"] for k in range(2, 6)), Vector()) / 4
        d = bout - W
        L = d.length
        d = d.normalized()
        rel = P - np.array(W)
        t = rel @ np.array(d) / L
        dist = np.linalg.norm(rel - np.outer(t * L, np.array(d)), axis=1)
        main = (t > -0.1) & (t < 1.3) & (dist < 0.08)
        crasse = lisse01(0.25, 1.0, t) * lisse01(0.7, 1.5, bruit(P, 120, 51) + 1.0) * main
        col = melange(col, (0.33, 0.28, 0.26), crasse * 0.7)
        col = melange(col, (0.32, 0.03, 0.05), lisse01(0.85, 1.0, t) * main * 0.6)
        for k in range(2, 6):
            a = J[f"{s}-finger-{k}-2"]
            rr = np.linalg.norm(P - np.array(a), axis=1)
            col = melange(col, (0.55, 0.42, 0.45), lisse01(0.012, 0.004, rr) * 0.5)
            haut -= 0.4 * lisse01(0.012, 0.0, rr) * (0.5 + 0.5 * np.sin((P @ np.array(d)) * 2500))
    col *= (0.5 + 0.5 * ao)[:, None]
    poser_texture(corps_, "kuchisake_peau", col, 0.45)
    carte_normale(corps_, haut, 0.0015, "kuchisake_peau_normal")


def gorge(V):
    """Fond de bouche noir : quand la machoire s'ouvre, on ne voit pas a travers la tete."""
    e = V.e
    centre = V.M + Vector((0, 0.85 * e, -0.12 * e))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=1.0, location=centre)
    o = bpy.context.active_object
    o.name = "Gorge"
    o.scale = (0.55 * e, 0.5 * e, 0.5 * e)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.shade_smooth()
    o.data.materials.append(matiere("Gorge", 0.3))
    gt, gm = o.vertex_groups.new(name="Tete"), o.vertex_groups.new(name="Machoire")
    for v in o.data.vertices:
        s = float(lisse01(0.1 * e, -0.2 * e, v.co.z - centre.z))
        gt.add([v.index], 1 - s, 'REPLACE')
        gm.add([v.index], s, 'REPLACE')
    return [o]


def masque(corps_, V):
    """Masque chirurgical tendu (il ne colle pas a la peau), avec ses trois plis et ses elastiques."""
    e = V.e
    arbre = bvh(corps_)
    nx, nz = 36, 28
    demi_l = 1.08 * e
    z_bas, z_haut = V.M.z - 1.0 * e, V.M.z + (V.yeux[0].z - V.M.z) * 0.62
    X = np.linspace(-demi_l, demi_l, nx + 1)
    F = np.linspace(0, 1, nz + 1)
    Y = np.zeros((nz + 1, nx + 1))
    Z = np.zeros((nz + 1, nx + 1))
    for i, xx in enumerate(X):
        q = (xx / demi_l) ** 2
        zb, zh = z_bas + 0.25 * e * q, z_haut - 0.3 * e * q
        for j, f in enumerate(F):
            Z[j, i] = zb + (zh - zb) * f
            hit = arbre.ray_cast(Vector((V.M.x + xx, V.M.y - 6 * e, Z[j, i])), Vector((0, 1, 0)))[0]
            Y[j, i] = hit.y if hit else np.nan
    Y = np.where(np.isnan(Y), np.nanmax(Y), Y)

    def voisins(A, op):
        B = np.pad(A, 1, mode="edge")
        return op([B[1 + dj:1 + dj + A.shape[0], 1 + di:1 + di + A.shape[1]] for dj in (-1, 0, 1) for di in (-1, 0, 1)], axis=0)

    T = Y.copy()
    for _ in range(3):
        T = voisins(T, np.min)          # le tissu se tend sur le nez et le menton
    for _ in range(8):
        T = voisins(T, np.mean)
    T = np.minimum(T, Y) - 0.05 * e
    for c in (0.33, 0.5, 0.67):         # plis horizontaux
        T -= 0.03 * e * np.exp(-((F[:, None] - c) / 0.035) ** 2)
    vs = [(V.M.x + X[i], T[j, i], Z[j, i]) for j in range(nz + 1) for i in range(nx + 1)]
    fs = [[j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i]
          for j in range(nz) for i in range(nx)]
    o = mesh_depuis("Masque", vs, fs, ["Masque"])
    s = o.modifiers.new("Epaisseur", 'SOLIDIFY')
    s.thickness = 0.02 * e
    appliquer_modif(o, s)
    bpy.ops.object.shade_smooth()
    o.vertex_groups.new(name="Masque").add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
    objs = [o]
    for sgn, i in ((1, nx), (-1, 0)):
        for j in (int(nz * 0.85), int(nz * 0.15)):
            a = Vector(vs[j * (nx + 1) + i])
            b = Vector((V.M.x + sgn * 1.15 * e, V.C.y + 0.15 * e, V.yeux[0].z - (0.1 if j > nz / 2 else 0.6) * e))
            d = b - a
            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=1.0)
            rot = d.to_track_quat('Z', 'Y').to_matrix()
            for v in bm.verts:
                v.co = rot @ Vector((v.co.x * 0.03 * e, v.co.y * 0.03 * e, v.co.z * d.length)) + (a + b) / 2
            me = bpy.data.meshes.new("Elastique")
            bm.to_mesh(me)
            bm.free()
            el = lier(bpy.data.objects.new("Elastique", me))
            me.materials.append(matiere("Masque"))
            el.vertex_groups.new(name="Masque").add(list(range(8)), 1.0, 'REPLACE')
            objs.append(el)
    return objs


def yeux_noirs(V):
    """Globes noirs et brillants (humides), avec un iris laiteux minuscule : elle te fixe."""
    objs = []
    e = V.e
    for y in V.yeux:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=0.23 * e,
                                             location=y + Vector((0, 0.02 * e, 0)))
        o = bpy.context.active_object
        o.name = "Oeil"
        o.data.materials.append(matiere("Oeil", 0.05))
        bpy.ops.object.shade_smooth()
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        o.vertex_groups.new(name="Tete").add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
        objs.append(o)
        # iris pale + pupille en tete d'epingle, poses sur l'avant du globe
        bm = bmesh.new()
        c = y + Vector((0, 0.02 * e - 0.23 * e - 0.004 * e, 0))
        creux = lambda r: r * r / (2 * 0.23 * e)
        n = 24
        centre = bm.verts.new(c)
        r1 = [bm.verts.new(c + Vector((math.cos(a) * 0.028 * e, creux(0.028 * e), math.sin(a) * 0.028 * e)))
              for a in np.linspace(0, 2 * math.pi, n + 1)[:-1]]
        r2 = [bm.verts.new(c + Vector((math.cos(a) * 0.075 * e, creux(0.075 * e), math.sin(a) * 0.075 * e)))
              for a in np.linspace(0, 2 * math.pi, n + 1)[:-1]]
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((centre, r1[i], r1[j]))
            f.material_index = 1
            bm.faces.new((r1[i], r2[i], r2[j], r1[j]))
        me = bpy.data.meshes.new("Iris")
        bm.to_mesh(me)
        bm.free()
        ir = lier(bpy.data.objects.new("Iris", me))
        me.materials.append(matiere("Iris", 0.05))
        me.materials.append(matiere("Pupille", 0.05))
        ir.vertex_groups.new(name="Tete").add(list(range(len(me.vertices))), 1.0, 'REPLACE')
        objs.append(ir)
    return objs


def dents(corps_, V):
    """Deux rangees de petites dents pointues dans la fente."""
    arbre = bvh(corps_)
    e = V.e
    bm = bmesh.new()
    nb = {1: 0, -1: 0}
    rng = random.Random(4)
    n = 24
    for sens in (1, -1):
        for k in range(n):
            t = -0.9 + 1.8 * (k + (0.5 if sens < 0 else 0)) / n
            if abs(t) > 0.92:
                continue
            zc = V.M.z + V.courbe(t)
            dm = V.demi(t)
            loc = arbre.ray_cast(Vector((V.M.x + t * V.larg, V.M.y - 6 * e, zc + sens * dm * 0.9)), Vector((0, 1, 0)))[0]
            if loc is None:
                continue
            w = 1.8 * V.larg / n * 0.45
            L = dm * rng.uniform(0.85, 1.0)
            base = loc + Vector((0, 0.025 * e, 0))
            pointe = base - Vector((0, 0, sens * L)) + Vector((0, -0.01 * e, 0))
            ep = w * 0.8
            q = [bm.verts.new(base + Vector(d)) for d in ((-w, -ep, 0), (w, -ep, 0), (w, ep, 0), (-w, ep, 0))]
            p = [bm.verts.new(pointe + Vector(d)) for d in ((-w * 0.2, -ep * 0.3, 0), (w * 0.2, -ep * 0.3, 0),
                                                          (w * 0.2, ep * 0.3, 0), (-w * 0.2, ep * 0.3, 0))]
            for i in range(4):
                j = (i + 1) % 4
                bm.faces.new([q[i], q[j], p[j], p[i]])
            bm.faces.new(p)
            bm.faces.new(q[::-1])
            nb[sens] += 8
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("Dents")
    bm.to_mesh(me)
    bm.free()
    o = lier(bpy.data.objects.new("Dents", me))
    me.materials.append(matiere("Dent", 0.35))
    o.vertex_groups.new(name="Tete").add(list(range(nb[1])), 1.0, 'REPLACE')
    o.vertex_groups.new(name="Machoire").add(list(range(nb[1], nb[1] + nb[-1])), 1.0, 'REPLACE')
    return [o]


def poids_machoire(corps_, V):
    """Le bas du visage (sous la fente) suit la machoire : elle peut s'ouvrir en grand."""
    gt = corps_.vertex_groups["Tete"]
    gm = corps_.vertex_groups.get("Machoire") or corps_.vertex_groups.new(name="Machoire")
    for v in corps_.data.vertices:
        p = v.co
        if p.z < V.cou - 0.5 * V.e:
            continue
        w_t = sum(g.weight for g in v.groups if g.group in (gt.index, gm.index))
        if w_t <= 0:
            continue
        t = max(-1.1, min(1.1, (p.x - V.M.x) / V.larg))
        sous = V.M.z + V.courbe(t) - p.z
        s = float(lisse01(-0.02 * V.e, 0.08 * V.e, sous)) * float(lisse01(V.C.y + 0.2 * V.e, V.C.y - 0.5 * V.e, p.y))
        gt.add([v.index], w_t * (1 - s), 'REPLACE')
        gm.add([v.index], w_t * s, 'REPLACE')


# ---------------------------------------------------------------------------
#  4) MASQUE, ROBE, CHEVEUX
# ---------------------------------------------------------------------------
def coquille(corps_, garder, decalage, nom, mat, lissage=8, epaisseur=None):
    """Copie d'une partie de la peau, decollee vers l'exterieur puis lissee (vetements, masque)."""
    me = corps_.data
    verts, faces, idx = [], [], {}
    for p in me.polygons:
        if not garder(p):
            continue
        f = []
        for vi in p.vertices:
            if vi not in idx:
                v = me.vertices[vi]
                d = decalage(v.co) if callable(decalage) else decalage
                idx[vi] = len(verts)
                verts.append(v.co + v.normal * d)
            f.append(idx[vi])
        faces.append(f)
    o = mesh_depuis(nom, verts, faces, [mat])
    if lissage:
        s = o.modifiers.new("Lisse", 'LAPLACIANSMOOTH')
        s.iterations = lissage
        s.lambda_factor = 0.6
        s.lambda_border = 0.0
        appliquer_modif(o, s)
    if epaisseur:
        s = o.modifiers.new("Epaisseur", 'SOLIDIFY')
        s.thickness = epaisseur
        s.offset = -1
        appliquer_modif(o, s)
    activer(o)
    bpy.ops.object.shade_smooth()
    return o


def simuler_tissu(o, epingles, images=40):
    """Simulation de tissu (soie) : la piece tombe sous son poids, fait des plis et se pose sur le corps.
    epingles : {indice de sommet: poids} des sommets qui restent accroches."""
    vg = o.vertex_groups.new(name="Epingle")
    for i, w in epingles.items():
        vg.add([i], w, 'REPLACE')
    mod = o.modifiers.new("Tissu", 'CLOTH')
    st = mod.settings
    st.quality = 7
    st.mass = 0.15
    st.air_damping = 2.0
    st.tension_stiffness = 20
    st.compression_stiffness = 20
    st.shear_stiffness = 8
    st.bending_stiffness = 0.08
    st.vertex_group_mass = "Epingle"
    cs = mod.collision_settings
    cs.distance_min = 0.004
    cs.use_self_collision = True
    cs.self_distance_min = 0.003
    mod.point_cache.frame_start = 1
    mod.point_cache.frame_end = images
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, images
    for f in range(1, images + 1):
        sc.frame_set(f)
    activer(o)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    o.vertex_groups.remove(o.vertex_groups["Epingle"])
    sc.frame_set(1)


def tube(nom, anneaux, mats, epaisseur, poids=None, mat_anneau=None, epingles=None):
    """Surface faite d'anneaux de points (manches, jupe, obi), avec une epaisseur.
    epingles(anneau, i) -> poids : si donne, la piece est simulee comme un vrai tissu."""
    n = len(anneaux[0])
    vs = [tuple(p) for a in anneaux for p in a]
    fs = []
    for a in range(len(anneaux) - 1):
        for i in range(n):
            j = (i + 1) % n
            fs.append([a * n + i, (a + 1) * n + i, (a + 1) * n + j, a * n + j])
    o = mesh_depuis(nom, vs, fs, mats)
    if mat_anneau:
        for p in o.data.polygons:
            p.material_index = mat_anneau(p.index // n)
    if poids:
        for a in range(len(anneaux)):
            for g, w in poids(a).items():
                vg = o.vertex_groups.get(g) or o.vertex_groups.new(name=g)
                vg.add(list(range(a * n, (a + 1) * n)), w, 'REPLACE')
    activer(o)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    if epingles:
        simuler_tissu(o, {a * n + i: epingles(a, i) for a in range(len(anneaux)) for i in range(n)
                          if epingles(a, i) > 0})
    s = o.modifiers.new("Epaisseur", 'SOLIDIFY')
    s.thickness = epaisseur
    s.offset = -1
    appliquer_modif(o, s)
    bpy.ops.object.shade_smooth()
    return o


def boite_arrondie(nom, centre, taille, mat, arrondi=0.004):
    bpy.ops.mesh.primitive_cube_add(size=1, location=centre)
    o = bpy.context.active_object
    o.name = nom
    o.scale = taille
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    b = o.modifiers.new("Arrondi", 'BEVEL')
    b.width = arrondi
    b.segments = 2
    appliquer_modif(o, b)
    bpy.ops.object.shade_smooth()
    o.data.materials.append(matiere(mat))
    return o


def cordelette(nom, pts, rayon, mat):
    anneaux = []
    for i, p in enumerate(pts):
        tg = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        a = tg.orthogonal().normalized()
        b = tg.cross(a)
        anneaux.append([p + (a * math.cos(t) + b * math.sin(t)) * rayon for t in np.linspace(0, 2 * math.pi, 9)[:-1]])
    return tube(nom, anneaux, [mat], rayon * 0.3)


def ruban(nom, pts, normales, largeur, mat, epaisseur):
    """Bande posee sur une surface (col du kimono)."""
    vs, fs, N = [], [], len(pts)
    prec = None
    for i, p in enumerate(pts):
        tg = (pts[min(i + 1, N - 1)] - pts[max(i - 1, 0)]).normalized()
        w = tg.cross(normales[i]).normalized()
        if prec is not None and w.dot(prec) < 0:
            w = -w
        prec = w
        vs += [p - w * largeur / 2, p + w * largeur / 2]
    for i in range(N - 1):
        fs.append([2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2])
    o = mesh_depuis(nom, vs, fs, [mat])
    s = o.modifiers.new("Epaisseur", 'SOLIDIFY')
    s.thickness = epaisseur
    appliquer_modif(o, s)
    bpy.ops.object.shade_smooth()
    return o


def eroder(me, faces, fois):
    for _ in range(fois):
        bord = set()
        for p in me.polygons:
            if p.index not in faces:
                bord.update(p.vertices)
        faces = {f for f in faces if not any(v in bord for v in me.polygons[f].vertices)}
    return faces


def kimono(corps_, V, J, arm):
    """Kimono rouge sombre : col croise noir sur un sous-col blanc, grandes manches qui pendent,
    large obi noir avec son cordon et un gros noeud dans le dos, jupe droite jusqu'aux chevilles."""
    e = V.e
    me = corps_.data
    noms = {g.index: g.name for g in corps_.vertex_groups}
    dominant = []
    for v in me.vertices:
        g = max(v.groups, key=lambda g: g.weight, default=None)
        dominant.append(noms[g.group] if g else "")
    ob = arm.data.bones
    z_col = J["neck"].z + 0.2 * (J["head"].z - J["neck"].z)
    z0 = ob["Ventre"].head_local.z + 0.3 * e          # la taille
    z_obi = z0 + 2.4 * e                              # le haut de l'obi
    z_croise = J["neck"].z - 1.7 * e                  # la ou les deux pans du col se croisent
    sy = J["neck"].y
    larg_cou = 0.75 * e
    bras = {c: (ob[f"Bras.{c}"].head_local, ob[f"AvantBras.{c}"].head_local, ob[f"Main.{c}"].head_local) for c in "LR"}

    def le_long(co, a, b):
        return (co - a).dot(b - a) / (b - a).length_squared

    def dans_v(c):
        return c.y < sy and c.z > z_croise and abs(c.x) < larg_cou * (c.z - z_croise) / (z_col - z_croise)

    def couvert(p):
        c = p.center
        if c.z > z_col or c.z < z0 - 1.2 * e or dans_v(c):
            return False
        doms = {dominant[i] for i in p.vertices}
        if any(d.startswith(("Main", "Tete", "Machoire", "AvantBras")) for d in doms):
            return False
        for cc in "LR":
            if "Bras." + cc in doms and le_long(c, bras[cc][0], bras[cc][1]) > 0.35:
                return False
        return True

    objs = []
    collision = corps_.modifiers.new("Collision", 'COLLISION')
    corps_.collision.thickness_outer = 0.004
    peau = bvh(corps_)
    haut = coquille(corps_, couvert, 0.12 * e, "Kimono", "Robe", lissage=12, epaisseur=0.03 * e)
    objs.append(haut)
    caches = {p.index for p in me.polygons if couvert(p)}

    # --- grandes manches -------------------------------------------------------
    BAS = Vector((0, 0, -1))
    manche_bas = 99.0
    for c in "LR":
        S, E, W = bras[c]
        L1, L2 = (E - S).length, (W - E).length
        anneaux, info = [], []
        K, M = 24, 40
        for k in range(K + 1):
            u = k / K
            s = 0.2 * L1 + u * (L1 + L2 - 0.2 * L1 - 0.03 * L2)
            if s < L1:
                centre = S + (E - S) * (s / L1)
                T = (E - S).normalized()
            else:
                centre = E + (W - E) * ((s - L1) / L2)
                T = (W - E).normalized()
            if abs(s - L1) < 0.25 * L1:            # coude adouci
                T = ((E - S).normalized() + (W - E).normalized()).normalized()
            dp = (BAS - T * BAS.dot(T)).normalized()
            cote = T.cross(dp)
            r = e * (0.75 + 0.45 * u)
            pend = e * (0.6 + 3.0 * u ** 0.7)
            ann = []
            for i in range(M):
                a = 2 * math.pi * i / M
                d = cote * math.cos(a) + dp * math.sin(a)
                ann.append(centre + d * r + dp * pend * max(0.0, math.sin(a)) ** 1.3)
            anneaux.append(ann)
            f2 = max(0.0, (s - L1) / L2)
            wa = float(lisse01(0.0, 0.35, f2))
            info.append({f"Bras.{c}": 1 - wa, f"AvantBras.{c}": wa})
        objs.append(tube(f"Manche.{c}", anneaux, ["Robe"], 0.03 * e, poids=lambda a, info=info: info[a],
                         epingles=lambda a, i, M=M: 1.0 if a == 0 or math.sin(2 * math.pi * i / M) < 0.1 else 0.0))
        manche_bas = min(manche_bas, min(p.z for ann in anneaux for p in ann))
        for p in me.polygons:   # le bras sous la manche ne se voit pas
            doms = {dominant[i] for i in p.vertices}
            if doms <= {f"Bras.{c}", f"AvantBras.{c}"} and le_long(p.center, E, W) < 0.75:
                caches.add(p.index)

    # --- jupe droite --------------------------------------------------------------
    jambes = {"Bassin", "Ventre", "Cuisse.L", "Cuisse.R", "Tibia.L", "Tibia.R", "Pied.L", "Pied.R"}
    polys = [list(p.vertices) for p in me.polygons if all(dominant[i] in jambes for i in p.vertices)]
    arbre = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], polys)
    z_haut_jupe = z0 + 0.4 * e
    z1 = J["l-ankle"].z + 0.45 * e
    cy = J["pelvis"].y
    n, nb = 96, 40
    R, prec = [], None
    for a in range(nb + 1):
        z = z_haut_jupe + (z1 - z_haut_jupe) * a / nb
        r = []
        for i in range(n):
            ang = 2 * math.pi * i / n
            d = Vector((math.cos(ang), math.sin(ang), 0))
            hit = arbre.ray_cast(Vector((0, cy, z)) + d * 3.0, -d)[0]
            r.append((Vector((hit.x, hit.y - cy, 0)).length if hit else 0.0) + 0.14 * e)
        r = np.array(r)
        for _ in range(3):
            r = np.maximum(np.maximum(np.roll(r, 1), r), np.roll(r, -1))
        for _ in range(3):
            r = (np.roll(r, 1) + r + np.roll(r, -1)) / 3
        if prec is not None:
            r = np.maximum(r, prec + 0.012 * e)
        prec = r
        R.append(r)
    ph = np.random.default_rng(8).uniform(0, 6.28, 2)
    anneaux = []
    for a, r in enumerate(R):
        t = a / nb
        z = z_haut_jupe + (z1 - z_haut_jupe) * t
        ann = []
        for i in range(n):
            ang = 2 * math.pi * i / n
            pli = 1 + t * (0.035 * math.sin(ang * 9 + ph[0]) + 0.02 * math.sin(ang * 4 + ph[1]))
            ann.append(Vector((math.cos(ang) * r[i] * pli, cy + math.sin(ang) * r[i] * pli, z)))
        anneaux.append(ann)
    hanche = abs(J["l-upper-leg"].x)

    def poids_jupe(a):
        t = a / nb
        return {"Bassin": 1 - 0.55 * t, "Cuisse.L": 0.275 * t, "Cuisse.R": 0.275 * t}

    jupe = tube("Jupe", anneaux, ["Robe", "RobeSombre"], 0.03 * e, poids=poids_jupe,
                mat_anneau=lambda a: 1 if a >= nb - 1 else 0, epingles=lambda a, i: 1.0 if a <= 1 else 0.0)
    for v in jupe.data.vertices:      # chaque cote suit sa jambe
        t = float(np.clip((z_haut_jupe - v.co.z) / (z_haut_jupe - z1), 0, 1))
        cote = float(lisse01(-1.5 * hanche, 1.5 * hanche, v.co.x))
        jupe.vertex_groups["Cuisse.L"].add([v.index], 0.55 * t * cote, 'REPLACE')
        jupe.vertex_groups["Cuisse.R"].add([v.index], 0.55 * t * (1 - cote), 'REPLACE')
    objs.append(jupe)
    # bord du pan de devant (le kimono se croise aussi en bas)
    sj = bvh(jupe)
    pts, nrm = [], []
    for k in range(nb + 1):
        t = k / nb
        z = z_haut_jupe + (z1 - z_haut_jupe) * t
        ang = -math.pi / 2 + 0.3 + 0.25 * t
        d = Vector((math.cos(ang), math.sin(ang), 0))
        hit, nn, _, _ = sj.ray_cast(Vector((0, cy, z)) + d * 3.0, -d)
        if hit:
            pts.append(hit + nn * 0.004 * e)
            nrm.append(nn)
    objs.append(ruban("Pan", pts, nrm, 0.14 * e, "RobeSombre", 0.01 * e))
    for p in me.polygons:
        c = p.center
        if z1 + 1.2 * e < c.z < z_haut_jupe - 0.5 * e and {dominant[i] for i in p.vertices} <= jambes:
            caches.add(p.index)

    # --- obi + cordon + noeud dans le dos ------------------------------------------
    arbres = [bvh(haut), sj]
    prof = np.zeros(n)
    for z in np.linspace(z0 - 0.35 * e, z_obi, 6):
        for i in range(n):
            ang = 2 * math.pi * i / n
            d = Vector((math.cos(ang), math.sin(ang), 0))
            for ab in arbres:
                hit = ab.ray_cast(Vector((0, cy, z)) + d * 3.0, -d)[0]
                if hit:
                    prof[i] = max(prof[i], Vector((hit.x, hit.y - cy, 0)).length)
    for _ in range(4):
        prof = (np.roll(prof, 1) + prof + np.roll(prof, -1)) / 3
    prof += 0.05 * e

    def anneau(z, plus=0.0):
        return [Vector((math.cos(2 * math.pi * i / n) * (prof[i] + plus), cy + math.sin(2 * math.pi * i / n) * (prof[i] + plus), z))
                for i in range(n)]

    ventre = lambda a: {"Ventre": 1.0}
    objs.append(tube("Obi", [anneau(z0 - 0.35 * e), anneau(z0 + 1.0 * e, 0.01 * e), anneau(z_obi)],
                     ["Obi"], 0.06 * e, poids=ventre))
    zm = (z0 - 0.35 * e + z_obi) / 2
    objs.append(tube("Cordon", [anneau(zm - 0.07 * e, 0.03 * e), anneau(zm + 0.07 * e, 0.03 * e)],
                     ["Cordon"], 0.03 * e, poids=ventre))
    dos = cy + prof[n // 4]
    for nom, centre, taille in (("Noeud", (0, dos + 0.35 * e, z0 + 0.3 * e), (3.6 * e, 0.55 * e, 3.4 * e)),
                                ("Noeud2", (0, dos + 0.2 * e, z_obi - 0.2 * e), (3.0 * e, 0.45 * e, 0.9 * e))):
        bpy.ops.mesh.primitive_cube_add(size=1, location=centre)
        o = bpy.context.active_object
        o.name = nom
        o.scale = taille
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        b = o.modifiers.new("Arrondi", 'BEVEL')
        b.width = 0.18 * e
        b.segments = 3
        appliquer_modif(o, b)
        bpy.ops.object.shade_smooth()
        o.data.materials.append(matiere("Obi"))
        o.vertex_groups.new(name="Ventre").add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
        objs.append(o)

    # --- tabi (chaussettes japonaises) et geta (sandales en bois) ---------------------
    z_cheville = J["l-ankle"].z + 0.6 * e

    def pied(p):
        doms = {dominant[i] for i in p.vertices}
        return doms <= {"Pied.L", "Pied.R", "Tibia.L", "Tibia.R"} and p.center.z < z_cheville

    tabi = coquille(corps_, pied, 0.04 * e, "Tabi", "Tabi", lissage=4, epaisseur=0.03)
    r = tabi.modifiers.new("Chaussette", 'REMESH')          # les orteils se fondent dans la chaussette
    r.mode = 'VOXEL'
    r.voxel_size = 0.004
    appliquer_modif(tabi, r)
    l = tabi.modifiers.new("Lisse", 'LAPLACIANSMOOTH')
    l.iterations = 4
    l.lambda_factor = 0.5
    appliquer_modif(tabi, l)
    d = tabi.modifiers.new("Alleger", 'DECIMATE')          # ~4000 triangles suffisent
    d.ratio = min(1.0, 4000 / max(1, sum(len(f.vertices) - 2 for f in tabi.data.polygons)))
    appliquer_modif(tabi, d)
    bpy.ops.object.shade_smooth()
    objs.append(tabi)
    caches |= {p.index for p in me.polygons if pied(p)}
    for c, sgn in (("L", 1), ("R", -1)):
        co = np.array([me.vertices[i].co for i, d in enumerate(dominant) if d == f"Pied.{c}"])
        x0, x1, y0, y1 = co[:, 0].min(), co[:, 0].max(), co[:, 1].min(), co[:, 1].max()
        xc, yc, Lp, Wp = (x0 + x1) / 2, (y0 + y1) / 2, y1 - y0, x1 - x0
        morceaux = [boite_arrondie("Geta", (xc, yc, GETA - 0.0135), (Wp + 0.02, Lp + 0.03, 0.022), "Bois")]
        for f in (0.2, 0.75):
            morceaux.append(boite_arrondie("Geta", (xc, y0 - 0.015 + f * (Lp + 0.03), (GETA - 0.024) / 2),
                                           (Wp + 0.02, 0.018, GETA - 0.024), "Bois"))
        A = Vector((xc - sgn * 0.2 * Wp, y0 + 0.14 * Lp, GETA - 0.002))
        hit = peau.ray_cast(Vector((xc, y0 + 0.4 * Lp, GETA + 0.3)), Vector((0, 0, -1)))[0]
        sommet = (hit if hit else Vector((xc, y0 + 0.4 * Lp, GETA + 0.05))) + Vector((0, 0, 0.009))
        for cx in (x0 - 0.005, x1 + 0.005):
            S = Vector((cx, y0 + 0.6 * Lp, GETA - 0.002))
            C = sommet * 2 - (A + S) / 2
            pts = [A * (1 - t) ** 2 + C * 2 * t * (1 - t) + S * t * t for t in np.linspace(0, 1, 14)]
            morceaux.append(cordelette("Hanao", pts, 0.005, "Hanao"))
        for o in morceaux:
            o.vertex_groups.new(name=f"Pied.{c}").add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
        objs += morceaux

    # --- col croise : bande noire sur un sous-col blanc ------------------------------

    def poser_sur(x, z, direction):
        d = direction.normalized()
        hit, nn, _, _ = peau.ray_cast(Vector((x, sy, z)) - d * 3.0, d)
        if hit is None:
            return None, None
        return hit + nn * 0.16 * e, nn

    for s in (1, -1):
        trajet = []
        for k in range(14):                                # derriere la nuque -> devant
            al = math.radians(110 * k / 13)
            trajet.append((s * math.sin(al) * 0.9 * e, z_col - 0.15 * e - 0.25 * e * k / 13,
                           Vector((-s * math.sin(al), -math.cos(al), 0))))
        bas = z_obi if s < 0 else z_croise - 0.3 * e
        for k in range(1, 21):                             # le V, puis le pan du dessus jusqu'a l'obi
            f = k / 20
            z = z_col - 0.4 * e + (bas - (z_col - 0.4 * e)) * f
            if z > z_croise:
                x = s * larg_cou * (z - z_croise) / (z_col - z_croise)
            else:
                x = -s * 0.5 * e * (z_croise - z) / (z_croise - z_obi)
            trajet.append((x, z, Vector((0, 1, 0))))
        for facteur, nom, larg, mat, ep, retrait in ((1.0, "Col", 0.36, "Col", 0.03, 0.0),
                                                     (0.8, "SousCol", 0.5, "SousCol", 0.02, 0.012)):
            pts, nrm = [], []
            for x, z, d in trajet:
                p, nn = poser_sur(x * facteur, z, d)
                if p is not None:
                    pts.append(p - nn * retrait * e)
                    nrm.append(nn)
            for _ in range(3):                             # trajet et normales adoucis
                pts = [pts[0]] + [(pts[i - 1] + pts[i] * 2 + pts[i + 1]) / 4 for i in range(1, len(pts) - 1)] + [pts[-1]]
                nrm = [nrm[0]] + [(nrm[i - 1] + nrm[i] * 2 + nrm[i + 1]).normalized() for i in range(1, len(nrm) - 1)] + [nrm[-1]]
            objs.append(ruban(nom, pts, nrm, larg * e, mat, ep * e))
    caches = eroder(me, caches, 3)
    corps_.modifiers.remove(collision)
    infos = dict(cy=cy, z1=z1, z_obi=z_obi, z_bas_obi=z0 - 0.35 * e, manche_bas=manche_bas, cou=J["neck"].z)
    return objs, caches, J["pelvis"].z + 2.5 * e, infos


def joindre(objs, nom):
    principal = objs[0]
    activer(*objs[1:], principal)
    bpy.ops.object.join()
    principal.name = nom
    principal.data.name = nom
    return principal


def seigaiha(u, z, R):
    """Motif japonais de vagues (ecailles) : distance au centre de l'ecaille visible (0..1)."""
    best = np.full(u.shape, 2.0)
    r0 = np.floor(z / (R / 2))
    for k in range(4):
        r = r0 - k
        zc = r * R / 2
        dec = np.mod(r, 2) * R
        uc = np.round((u - dec) / (2 * R)) * 2 * R + dec
        d = np.hypot(u - uc, z - zc) / R
        best = np.where(d < 1, d, best)
    return best


def higanbana(col, haut, sel, u, z, cu, cz, R, theta0, tige):
    """Lys araignee (fleur des morts) : 6 petales enroules noirs bordes d'or + longues etamines."""
    or_ = (0.62, 0.47, 0.22)
    noir = (0.05, 0.01, 0.015)
    # tige
    zone = sel & (z < cz) & (z > cz - tige) & (np.abs(u - cu) < 0.02)
    ondule = 0.006 * np.sin((cz - z) * 25)
    a = np.zeros(len(u))
    a[zone] = lisse01(0.0035, 0.002, np.abs(u[zone] - cu - ondule[zone]))
    col = melange(col, noir, a)
    haut += 0.4 * a
    zone = sel & (np.abs(u - cu) < 1.3 * R) & (np.abs(z - cz) < 1.3 * R)
    if not zone.any():
        return col, haut
    du, dz = (u[zone] - cu) / R, (z[zone] - cz) / R
    r = np.hypot(du, dz)
    th = np.arctan2(dz, du)
    petale = np.zeros(zone.sum())
    bord = np.zeros(zone.sum())
    for k in range(6):
        d = np.angle(np.exp(1j * (th - theta0 - k * np.pi / 3 - 0.9 * r ** 2)))
        large = 0.11 * np.clip(1 - (r / 0.72) ** 2, 0, 1)
        perp = r * np.abs(np.sin(d))
        ok = (np.cos(d) > 0) & (r < 0.75)
        petale = np.maximum(petale, ok * lisse01(large, large * 0.8, perp))
        bord = np.maximum(bord, ok * lisse01(large + 0.035, large + 0.02, perp))
    eta = np.zeros(zone.sum())
    for k in range(7):
        ts = theta0 + k * 2 * np.pi / 7 + 0.25
        d = np.angle(np.exp(1j * (th - ts - 0.7 * r)))
        eta = np.maximum(eta, (np.cos(d) > 0) * (r < 1.0) * lisse01(0.016, 0.008, r * np.abs(np.sin(d))))
        bx, bz = np.cos(ts + 0.7), np.sin(ts + 0.7)
        eta = np.maximum(eta, lisse01(0.05, 0.03, np.hypot(du - bx, dz - bz)))
    tmp = col[zone]
    tmp = melange(tmp, or_, bord)
    tmp = melange(tmp, noir, petale)
    tmp = melange(tmp, or_, eta * (1 - petale))
    col[zone] = tmp
    haut[zone] += 0.5 * petale + 0.8 * bord * (1 - petale) + 0.6 * eta * (1 - petale)
    return col, haut


def peindre_tissu(o, I, e):
    """Texture du kimono : motif de vagues ton sur ton, lys araignees noir et or en bas et sur les manches,
    obi noir a losanges dores, sous-col blanc tache, salissures, gouttes de sang, ombres des plis."""
    noms = [m.name.split(".")[0] for m in o.data.materials]
    nb = len(noms)

    def classe(nt, i):
        n = nt.nodes.new("ShaderNodeRGB")
        v = (i + 0.5) / nb
        n.outputs[0].default_value = (v, v, v, 1)
        return n.outputs[0]

    K = np.clip((cuire(o, classe)[:, 0] * nb).astype(int), 0, nb - 1)
    P = position_pixels(o)
    Nn = normale_pixels(o)
    ao = occlusion_pixels(o, 0.15, 24)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    u = np.arctan2(x, -(y - I["cy"])) * 0.25          # coordonnee "deroulee" autour du corps
    base = {"Robe": (0.36, 0.04, 0.07), "RobeSombre": (0.13, 0.02, 0.03), "Obi": (0.055, 0.047, 0.055),
            "Col": (0.04, 0.035, 0.04), "SousCol": (0.86, 0.84, 0.78), "Cordon": (0.69, 0.55, 0.31),
            "Tabi": (0.84, 0.82, 0.75), "Bois": (0.43, 0.31, 0.2), "Hanao": (0.27, 0.03, 0.05)}
    col = np.array([base.get(n, (0.5, 0.5, 0.5)) for n in noms])[K]
    est = {n: K == i for i, n in enumerate(noms)}
    vide = np.zeros(len(K), dtype=bool)
    robe = est.get("Robe", vide)
    # grain de la soie (serge) + variations
    serge = np.sin(2 * np.pi * (u * 0.7 + z) / 0.005)
    grain = 1 + 0.05 * bruit(P, 30, 31) + 0.035 * serge
    col *= grain[:, None]
    haut = 0.25 * serge + 0.1 * bruit(P, 300, 61)
    # vagues seigaiha, ton sur ton
    d = seigaiha(u, z, 0.035)
    anneau = np.abs(d * 4 - np.round(d * 4))
    col = np.where(robe[:, None], col * (1 - 0.28 * lisse01(0.1, 0.03, anneau))[:, None], col)
    haut -= 0.3 * lisse01(0.1, 0.03, anneau) * robe
    # lys araignees
    rng = np.random.default_rng(13)
    fleurs = []
    for _ in range(22):
        fleurs.append((rng.uniform(-0.7, 0.7), rng.uniform(I["z1"] + 0.1, I["z1"] + 0.5)))
    for _ in range(12):
        fleurs.append((rng.choice([-1, 1]) * rng.uniform(0.27, 0.5), rng.uniform(I["manche_bas"] + 0.04, I["manche_bas"] + 0.32)))
    for _ in range(3):
        fleurs.append((rng.choice([-1, 1]) * rng.uniform(0.1, 0.2), rng.uniform(I["z_obi"] + 0.05, I["z_obi"] + 0.15)))
    sel = robe & (np.abs(Nn[:, 2]) < 0.85)
    for cu, cz in fleurs:
        col, haut = higanbana(col, haut, sel, u, z, cu, cz, rng.uniform(0.07, 0.11), rng.uniform(0, 6.28),
                              rng.uniform(0.08, 0.3))
    # salissures en bas du kimono et des manches
    tache = lisse01(0.7, 1.4, bruit(P, 9, 21)) * np.maximum(lisse01(I["z1"] + 0.5, I["z1"], z),
                                                            lisse01(I["manche_bas"] + 0.25, I["manche_bas"], z))
    col = melange(col, (0.12, 0.03, 0.03), tache * 0.55 * (robe | est.get("RobeSombre", vide)))
    # obi : deux filets d'or et des losanges
    obi = est.get("Obi", vide)
    zr = (z - I["z_bas_obi"]) / (I["z_obi"] - I["z_bas_obi"])
    filet = (np.abs(zr - 0.1) < 0.025) | (np.abs(zr - 0.9) < 0.025)
    a = np.abs(np.mod(u / 0.045, 1) - 0.5) * 2
    b = np.abs(np.mod(z / 0.035, 1) - 0.5) * 2
    losange = lisse01(0.12, 0.05, np.abs(a + b - 1)) * ((zr > 0.2) & (zr < 0.8) | (zr < -0.05) | (zr > 1.05))
    col = melange(col, (0.55, 0.42, 0.2), (filet * 0.9 + losange * 0.6) * obi)
    haut += (0.8 * filet + 0.6 * losange) * obi
    cordon = est.get("Cordon", vide)
    torsade = np.sin(2 * np.pi * (u * 3 + z) / 0.012)
    col = np.where(cordon[:, None], col * (1 + 0.2 * torsade)[:, None], col)
    haut += 0.5 * torsade * cordon
    # tabi salis par le sol, bois des geta, lanieres en velours
    tabi = est.get("Tabi", vide)
    sol = lisse01(GETA + 0.06, GETA - 0.002, z) * (0.6 + 0.4 * lisse01(-0.5, 1.0, bruit(P, 60, 71)))
    col = melange(col, (0.33, 0.27, 0.22), sol * 0.85 * tabi)
    col = melange(col, (0.45, 0.42, 0.36), lisse01(0.6, 1.4, bruit(P, 25, 72)) * 0.5 * tabi)
    bois = est.get("Bois", vide)
    veine_bois = np.sin(2 * np.pi * (y * 90 + 1.5 * bruit(P, 20, 73)))
    col = np.where(bois[:, None], col * (0.85 + 0.15 * veine_bois)[:, None], col)
    haut += 0.35 * veine_bois * bois + 0.15 * bruit(P, 400, 74) * est.get("Hanao", vide)
    # gouttes de sang sur le col et la poitrine
    devant = Nn[:, 1] < -0.3
    for _ in range(45):
        cx = rng.uniform(-0.13, 0.13)
        cz = rng.uniform(I["cou"] - 0.34, I["cou"] - 0.03)
        r = rng.uniform(0.002, 0.009)
        etire = rng.uniform(1.0, 3.0)
        dz = (z - cz)
        g = devant & (np.abs(x - cx) < r * 1.5) & (dz < r * 1.5) & (dz > -r * etire * 1.5)
        if g.any():
            dd = np.hypot(x[g] - cx, np.where(dz[g] < 0, dz[g] / etire, dz[g]))
            a = np.zeros(len(x))
            a[g] = lisse01(r, r * 0.7, dd)
            col = melange(col, (0.28, 0.01, 0.03), a * 0.9)
    col *= (0.4 + 0.6 * ao)[:, None]
    poser_texture(o, "kuchisake_kimono", col, 0.55)
    carte_normale(o, haut, 0.0012, "kuchisake_kimono_normal")


def cacher_peau(corps_, caches):
    """Supprime la peau cachee sous le kimono (moins de triangles, rien ne traverse en animation)."""
    bm = bmesh.new()
    bm.from_mesh(corps_.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in caches], context='FACES')
    bm.to_mesh(corps_.data)
    bm.free()
    corps_.data.update()


def texture_cheveux():
    """Texture de meches : 4 bandes cote a cote, ~75 cheveux fins chacune (transparence entre les cheveux)."""
    W, H, ncol = 1024, 2048, 4
    alpha = np.zeros((H, W), np.float32)
    teinte = np.full((H, W), 0.02, np.float32)
    rng = np.random.default_rng(17)
    cw = W // ncol
    lignes = np.arange(H)
    for c in range(ncol):
        for _ in range(75):
            x0 = c * cw + rng.uniform(5, cw - 5)
            larg = rng.uniform(1.0, 3.2)
            fin = int(rng.uniform(0.0, 0.35) * H)           # la pointe (en bas de l'image)
            amp, fr, ph = rng.uniform(0, 4), rng.uniform(1, 4), rng.uniform(0, 6.28)
            lum = rng.uniform(0.025, 0.11)
            ys = lignes[fin:]
            xc = x0 + amp * np.sin(ys / H * fr * 2 * np.pi + ph)
            eff = larg * np.clip((ys - fin) / (0.12 * H), 0.15, 1) ** 0.6
            for dx in range(-4, 5):
                xi = np.clip(np.round(xc).astype(int) + dx, c * cw, (c + 1) * cw - 1)
                a = np.clip(1 - np.abs(xi - xc) / eff, 0, 1)
                cur = alpha[ys, xi]
                plus = a > cur
                teinte[ys[plus], xi[plus]] = lum
                alpha[ys, xi] = np.maximum(cur, a)
    rgba = np.stack([teinte, teinte, teinte * 1.08, alpha], -1)
    img = bpy.data.images.new("kuchisake_cheveux", W, H, alpha=True)
    img.pixels.foreach_set(rgba.astype(np.float32).ravel())
    os.makedirs(SORTIE, exist_ok=True)
    img.filepath_raw = os.path.join(SORTIE, "kuchisake_cheveux.png")
    img.file_format = 'PNG'
    img.save()
    img.pack()
    return img


def matiere_cheveux(nom, img, transparent):
    m = bpy.data.materials.new(nom)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.4
    t = m.node_tree.nodes.new("ShaderNodeTexImage")
    t.image = img
    m.node_tree.links.new(t.outputs["Color"], b.inputs["Base Color"])
    if transparent:
        m.node_tree.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
    return m


def cheveux(corps_, V, vetements, z_dos):
    """~450 meches (cartes avec une texture de cheveux fins), raie au milieu, quelques meches devant
    le visage et des cheveux rebelles qui partent dans tous les sens."""
    e = V.e
    tete = bvh(corps_)
    obst = [tete] + [bvh(o) for o in vetements if o.name.startswith("Noeud")]
    C = V.C
    rng = random.Random(11)

    def sur_crane(d, off):
        d = d.normalized()
        hit, n, _, _ = tete.ray_cast(C + d * 6 * e, -d)
        return None if hit is None else hit + n * off

    def dir_(theta, phi):
        return Vector((math.sin(theta) * math.sin(phi), math.sin(theta) * math.cos(phi), math.cos(theta)))

    def ecarter(p, off):
        for o in obst:
            loc, n, _, dist = o.find_nearest(p)
            if loc is not None and ((p - loc).dot(n) < 0 or dist < off):
                p = loc + n * off
        return p

    def adoucir(pts, fois=2):
        for _ in range(fois):
            pts = [pts[0]] + [(pts[i - 1] + pts[i] * 2 + pts[i + 1]) / 4 for i in range(1, len(pts) - 1)] + [pts[-1]]
        return pts

    meches = []
    for s in (1, -1):
        for k in range(225):
            u = rng.random() ** 0.8
            beta = math.radians(-58 + 122 * u)                 # du front (-) vers la nuque (+)
            racine = Vector((s * 0.02, math.sin(beta), math.cos(beta)))
            face = k < 6
            if face:                                           # meches devant le visage
                racine = Vector((s * 0.05, math.sin(math.radians(-45)), math.cos(math.radians(-45))))
                phi_fin = s * math.radians(rng.uniform(148, 165))
                off = e * rng.uniform(0.18, 0.26)
                larg = e * rng.uniform(0.12, 0.2)
            else:
                phi_fin = s * math.radians(118 - 108 * u + rng.uniform(-8, 8))
                off = e * (0.03 + 0.2 * rng.random() ** 1.6)
                larg = e * rng.uniform(0.3, 0.5)
            fin = dir_(math.radians(98 + rng.uniform(-4, 6)), phi_fin)
            pts = []
            for i in range(11):
                f = i / 10
                p = sur_crane(racine.lerp(fin, f), off * (0.4 + 0.6 * f))
                if p is not None:
                    pts.append(p)
            if len(pts) < 6:
                continue
            p = pts[-1]
            dehors = Vector((p.x - C.x, p.y - C.y, 0))
            dehors = dehors.normalized() if dehors.length > 1e-6 else Vector((s, 0, 0))
            devant = face or abs(phi_fin) > math.radians(105)
            bas = (V.M.z - rng.uniform(1.5, 4.5) * e) if devant else z_dos + rng.uniform(-1.5, 2.5) * e
            chute = p.z - bas
            if chute > 0:
                etapes = max(4, int(chute / (0.8 * e)))
                for i in range(1, etapes + 1):
                    f = i / etapes
                    q = p + Vector((0, 0, -chute * f)) + dehors * ((0.25 if devant else 0.5) * e * math.sqrt(f)) \
                        + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)) * 0.02 * e
                    pts.append(q if face else ecarter(q, off + 0.22 * e))
            meches.append((adoucir(pts), larg, rng.randrange(4)))
    # cheveux rebelles : fins, ils sortent de la masse et retombent
    for k in range(32):
        d = dir_(math.radians(rng.uniform(30, 100)), rng.uniform(-math.pi, math.pi))
        p = sur_crane(d, 0.05 * e)
        if p is None:
            continue
        sens = (p - C).normalized()
        pts = [p]
        for i in range(7):
            sens = (sens * 0.6 + Vector((rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), -0.6 - 0.15 * i))).normalized()
            pts.append(pts[-1] + sens * 0.3 * e)
        meches.append((adoucir(pts), e * rng.uniform(0.04, 0.07), rng.randrange(4)))
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UV")
    for pts, larg, colonne in meches:
        N = len(pts)
        ligne = []
        for i, p in enumerate(pts):
            tg = (pts[min(i + 1, N - 1)] - pts[max(i - 1, 0)]).normalized()
            dehors = Vector((p.x - C.x, p.y - C.y, (p.z - C.z) if p.z > V.M.z else 0)).normalized()
            w = tg.cross(dehors)
            w = w.normalized() if w.length > 1e-6 else Vector((1, 0, 0))
            h = larg / 2 * (1 - 0.5 * (i / (N - 1)) ** 2)
            v = 1 - 0.99 * i / (N - 1)
            ligne.append(((bm.verts.new(p - w * h), (colonne / 4 + 0.004, v)),
                          (bm.verts.new(p + w * h), ((colonne + 1) / 4 - 0.004, v))))
        for i in range(N - 1):
            coins = (ligne[i][0], ligne[i][1], ligne[i + 1][1], ligne[i + 1][0])
            f = bm.faces.new([c[0] for c in coins])
            for boucle, c in zip(f.loops, coins):
                boucle[uv].uv = c[1]
    # visibles des deux cotes : une copie retournee
    dup = bmesh.ops.duplicate(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:])
    bmesh.ops.reverse_faces(bm, faces=[g for g in dup["geom"] if isinstance(g, bmesh.types.BMFace)])
    me = bpy.data.meshes.new("Cheveux")
    bm.to_mesh(me)
    bm.free()
    o = lier(bpy.data.objects.new("Cheveux", me))
    img = texture_cheveux()
    me.materials.append(matiere_cheveux("Cheveux", img, True))
    activer(o)
    bpy.ops.object.shade_smooth()
    # calotte sous les meches (pour ne jamais voir le crane), avec la meme texture, sans transparence
    cal = coquille(corps_, lambda p: (p.center - C).length < 3.5 * e and (
        p.center.z > V.yeux[0].z + 0.95 * e or (p.center.y > C.y - 0.2 * e and p.center.z > V.M.z - 0.3 * e)),
        0.025 * e, "Calotte", "Calotte", lissage=6)
    cal.data.materials.clear()
    cal.data.materials.append(matiere_cheveux("Calotte", img, False))
    couche = cal.data.uv_layers.new(name="UV")
    for boucle in cal.data.loops:
        q = cal.data.vertices[boucle.vertex_index].co - C
        phi = math.atan2(q.x, q.y)
        theta = math.acos(max(-1.0, min(1.0, q.z / max(q.length, 1e-9))))
        couche.data[boucle.index].uv = ((phi / (2 * math.pi) + 0.5) * 3, 1 - theta / (0.75 * math.pi))
    # poids : la tete, puis le haut du dos pour les longueurs
    for ob in (o, cal):
        gt, gh = ob.vertex_groups.new(name="Tete"), ob.vertex_groups.new(name="Haut")
        for v in ob.data.vertices:
            w = float(lisse01(V.cou + 0.3 * e, V.cou - 1.5 * e, v.co.z))
            gt.add([v.index], 1 - w, 'REPLACE')
            gh.add([v.index], w, 'REPLACE')
    return [o, cal]


# ---------------------------------------------------------------------------
#  5) FINITION : poids, peau cachee, animations, export
# ---------------------------------------------------------------------------
def poids_depuis_corps(objs, corps_):
    for o in objs:
        mod = o.modifiers.new("Poids", 'DATA_TRANSFER')
        mod.object = corps_
        mod.use_vert_data = True
        mod.data_types_verts = {'VGROUP_WEIGHTS'}
        mod.vert_mapping = 'POLYINTERP_NEAREST'
        activer(o)
        bpy.ops.object.datalayout_transfer(modifier=mod.name)
        bpy.ops.object.modifier_apply(modifier=mod.name)


def animations(arm):
    """Animations (sur place, en boucle sauf Regard / Attaque / Jolie) :
    Attente  : tete penchee qui tremble, avec un sursaut
    Marche   : marche lente et saccadee, la tete qui tressaute
    Course   : course penchee en avant, bras qui trainent derriere
    Regard   : la tete se tourne d'un coup (vers la gauche du perso)
    Attaque  : le jumpscare (elle se jette en avant, bras tendus, bouche grande ouverte)
    Jolie    : "Est-ce que je suis jolie ?" : elle enleve son masque et ouvre la bouche
    Sourire  : la machoire s'ouvre en grand"""
    X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)

    def base(tilt=18, nod=10, souffle=0, bras=0):
        return {"Tete": [(Y, tilt), (X, nod * 0.5)], "Cou": [(X, nod)], "Haut": [(X, 6 + souffle)],
                "Poitrine": [(X, souffle)],
                "Bras.L": [(Y, 22 + bras)], "Bras.R": [(Y, -22 - bras)],
                "AvantBras.L": [(X, -8)], "AvantBras.R": [(X, -8)],
                "Clavicule.L": [(Y, 5)], "Clavicule.R": [(Y, -5)]}

    def avec(r, ajouts):
        r = {k: list(v) for k, v in r.items()}
        for k, v in ajouts.items():
            r[k] = r.get(k, []) + list(v)
        return r

    def action(nom, cles):
        arm.animation_data_create()
        act = bpy.data.actions.new(nom)
        act.use_fake_user = True
        arm.animation_data.action = act
        for cle in cles:
            frame, rot = cle[0], cle[1]
            poser(arm, rot, cle[2] if len(cle) > 2 else None, cle[3] if len(cle) > 3 else None)
            for pb in arm.pose.bones:
                pb.keyframe_insert("rotation_quaternion", frame=frame)
                pb.keyframe_insert("location", frame=frame)
        piste = arm.animation_data.nla_tracks.new()
        piste.name = nom
        piste.strips.new(nom, 1, act)
        piste.mute = True
        arm.animation_data.action = None

    def pas(phi, amp_h, amp_g, penche, balance, bob, r):
        pos = {"Racine": (0.02 * math.sin(2 * math.pi * phi), 0, bob * math.cos(4 * math.pi * phi))}
        r = avec(r, {"Haut": [(X, penche)], "Bassin": [(Z, 4 * math.sin(2 * math.pi * phi))]})
        for c, dec in (("L", 0.0), ("R", 0.5)):
            q = (phi + dec) % 1
            hanche = -amp_h * math.cos(2 * math.pi * q)
            genou = amp_g * math.sin(math.pi * (q - 0.5) / 0.5) if q > 0.5 else 4
            r = avec(r, {f"Cuisse.{c}": [(X, hanche)], f"Tibia.{c}": [(X, genou)],
                         f"Pied.{c}": [(X, -(hanche + genou) * 0.8)], f"Bras.{c}": [(X, -balance * hanche)]})
        return r, pos

    action("Attente", [(1, base(18, 10, 0, 0)), (20, base(21, 11, 2, 1)), (40, base(17, 9, 0, 0)),
                       (52, base(19, 10, 1, 0)), (54, base(34, 16, 1, 0)), (57, base(16, 9, 1, 0)),
                       (70, base(20, 11, 2, 1)), (90, base(18, 10, 0, 0))])
    cles = []
    for f in range(1, 42, 2):
        sursaut = 13 if (f // 8) % 3 == 1 else 0
        r, pos = pas((f - 1) / 40, 10, 12, 6, 0.35, 0.008, base(20 + sursaut, 12))
        cles.append((f, r, pos))
    action("Marche", cles)
    cles = []
    for f in range(1, 22, 2):
        r, pos = pas((f - 1) / 20, 18, 24, 24, 0.1, 0.025,
                     avec(base(25, 18), {"Ventre": [(X, 8)], "Bras.L": [(X, 40)], "Bras.R": [(X, 40)],
                                         "Machoire": [(X, 14)], "Masque": [(X, 8)]}))
        cles.append((f, r, pos))
    action("Course", cles)
    tourne = lambda a, tilt: avec(base(tilt, 10), {"Tete": [(Z, a * 0.6)], "Cou": [(Z, a * 0.4)]})
    action("Regard", [(1, base(18, 10)), (10, base(18, 10)), (13, tourne(95, 28)), (15, tourne(102, 30)),
                      (18, tourne(95, 27)), (30, tourne(96, 26)), (40, tourne(95, 29))])
    en_avant = lambda tilt, ouvre: avec(base(tilt, -15), {
        "Haut": [(X, 28)], "Ventre": [(X, 10)],
        "Bras.L": [(Y, 18), (X, -85)], "Bras.R": [(Y, -18), (X, -85)],
        "AvantBras.L": [(X, -10)], "AvantBras.R": [(X, -10)], "Main.L": [(X, 25)], "Main.R": [(X, 25)],
        "Machoire": [(X, ouvre)], "Masque": [(X, ouvre * 0.6)]})
    action("Attaque", [(1, base(18, 10)), (6, avec(base(14, 4), {"Haut": [(X, -8)]}), {"Racine": (0, 0.08, 0)}),
                       (11, en_avant(12, 38), {"Racine": (0, -0.55, -0.06)}),
                       (14, en_avant(17, 40), {"Racine": (0, -0.58, -0.06)}),
                       (17, en_avant(10, 38), {"Racine": (0, -0.57, -0.06)}),
                       (32, en_avant(13, 39), {"Racine": (0, -0.57, -0.06)})])
    h = arm.data.bones["Masque"].head_local
    prise = h + Vector((-0.075, -0.07, -0.03))           # bord droit du masque
    main = {"R": (lambda: point_os(arm, "Masque", prise) + Vector((-0.05, -0.07, -0.13)), (-1, 0.2, -1.2))}
    tenu = {"Masque": [(X, 80), (Z, -20)]}
    bas_m = {"Masque": (-0.1, -0.2, -0.38)}
    action("Jolie", [(1, base(18, 10)), (15, base(26, 6)),
                     (32, base(26, 6), {}, main),
                     (45, base(24, 6), {"Masque": (-0.05, -0.12, -0.2)}, main),
                     (58, avec(base(28, 6), tenu), bas_m, main),
                     (70, avec(base(30, 6), dict(tenu, Machoire=[(X, 12)])), bas_m, main),
                     (85, avec(base(34, -6), dict(tenu, Machoire=[(X, 36)])), bas_m, main),
                     (100, avec(base(32, -6), dict(tenu, Machoire=[(X, 37)])), bas_m, main)])
    ouvre = lambda a, tilt: avec(base(tilt, 4, 1, 0), {"Machoire": [(X, a)], "Masque": [(X, a * 0.6)]})
    action("Sourire", [(1, ouvre(0, 18)), (15, ouvre(6, 14)), (30, ouvre(32, 8)), (45, ouvre(34, 8)),
                       (60, ouvre(0, 18))])
    poser(arm, {})


def exporter(nom, arm, objs):
    activer(*objs, arm)
    os.makedirs(SORTIE, exist_ok=True)
    fbx = os.path.join(SORTIE, nom + ".fbx")
    bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'ARMATURE', 'MESH'},
                             add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=True,
                             bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True,
                             path_mode='COPY', embed_textures=True, mesh_smooth_type='FACE', use_tspace=True)
    glb = os.path.join(SORTIE, nom + ".glb")
    bpy.ops.export_scene.gltf(filepath=glb, use_selection=True, export_format='GLB', export_animations=True)
    tri = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
    print("Export OK :", fbx, "+ .glb", tri, "triangles")


def construire(variante):
    nettoyer()
    random.seed(7)
    corps_, J = corps()
    arm = squelette(J)
    activer(corps_, arm)
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    for g in ("Masque", "Racine"):            # ces os ne bougent pas la peau
        if g in corps_.vertex_groups:
            corps_.vertex_groups.remove(corps_.vertex_groups[g])
    pose_A(corps_, arm, J)
    mains_longues(corps_, J)
    V = Visage(corps_, J)
    subdiviser_tete(corps_, V)
    sculpter(corps_, V)
    poids_machoire(corps_, V)
    peindre_peau(corps_, V, J)
    objs = [corps_] + yeux_noirs(V) + gorge(V) + griffes(J)
    vet, caches, z_dos, infos = kimono(corps_, V, J, arm)
    poids_depuis_corps([o for o in vet if o.name.startswith(("Kimono", "Col", "SousCol", "Tabi"))], corps_)
    objs += dents(corps_, V)
    if variante == "masque":
        objs += masque(corps_, V)
    objs += cheveux(corps_, V, vet, z_dos)
    tissu = joindre(vet, "Kimono")
    tissu.data.uv_layers.new(name="UV")
    activer(tissu)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
    bpy.ops.object.mode_set(mode='OBJECT')
    peindre_tissu(tissu, infos, V.e)
    objs.append(tissu)
    cacher_peau(corps_, caches)
    for o in objs:
        for m in list(o.modifiers):
            o.modifiers.remove(m)
        o.parent = arm
        mod = o.modifiers.new("Squelette", 'ARMATURE')
        mod.object = arm
    animations(arm)
    exporter("kuchisake_" + variante, arm, objs)
    return arm, objs


if __name__ == "__main__":
    for v in VARIANTES:
        construire(v)
