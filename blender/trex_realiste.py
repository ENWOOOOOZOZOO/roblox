"""T-Rex realiste pour Blender 4.x / 5.x.

Utilisation : Blender > onglet "Scripting" > Open (ce fichier) > Run Script (triangle).
Le dino regarde vers -Y (vue de face = touche 1 du pave numerique).

Corps en metaballs (peau lisse sans jointures) + relief de peau (bosses),
couleurs reparties selon l'orientation de la peau (dos fonce, flancs,
ventre clair, rayures). Dents irregulieres, yeux a pupille fendue.

Export : UN mesh avec une texture "palette" -> trex_realiste.glb dans ton
dossier utilisateur. Dans Roblox Studio : Avatar > Import 3D.
"""
import bpy
import math
import os
import random
from mathutils import Vector, Quaternion

random.seed(7)

# ---------------- couleurs (sRGB 0-255) ----------------
COULEURS = {
    "Flanc": (106, 98, 66),
    "Dos": (66, 66, 44),
    "Rayure": (44, 42, 30),
    "Ventre": (178, 160, 120),
    "Bouche": (110, 32, 36),
    "Langue": (150, 70, 72),
    "Dent": (226, 214, 176),
    "Griffe": (52, 46, 38),
    "Iris": (214, 150, 30),
    "Noir": (14, 12, 10),
    "Ecaille": (82, 76, 50),
}


def lineaire(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (f(c[0]), f(c[1]), f(c[2]), 1)


# ---------------- outils ----------------
def nettoyer():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.metaballs, bpy.data.materials, bpy.data.images, bpy.data.textures):
        for d in list(coll):
            coll.remove(d)


MATS = {}


def matiere(nom):
    if nom not in MATS:
        m = bpy.data.materials.new(nom)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = lineaire(COULEURS[nom])
        b.inputs["Roughness"].default_value = 0.75
        m.diffuse_color = lineaire(COULEURS[nom])
        MATS[nom] = m
    return MATS[nom]


def lier(o):
    bpy.context.scene.collection.objects.link(o)
    return o


def activer(o):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def lisser(o):
    for p in o.data.polygons:
        p.use_smooth = True


def appliquer(o, mod):
    activer(o)
    bpy.ops.object.modifier_apply(modifier=mod.name)


def ellipse(nom, pos, demi, mat, rot=None, seg=16, anneaux=10):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=anneaux, radius=1, location=pos)
    o = bpy.context.active_object
    o.name = nom
    o.scale = demi
    if rot is not None:
        o.rotation_mode = 'QUATERNION'
        o.rotation_quaternion = rot
    o.data.materials.append(matiere(mat))
    lisser(o)
    return o


def cone(nom, pos, rayon, hauteur, mat, direction, sommets=6, echelle=(1, 1, 1)):
    """Cone dont la pointe suit `direction`. `pos` = centre de la base."""
    d = Vector(direction).normalized()
    bpy.ops.mesh.primitive_cone_add(vertices=sommets, radius1=rayon, radius2=0, depth=hauteur,
                                    location=Vector(pos) + d * (hauteur / 2))
    o = bpy.context.active_object
    o.name = nom
    o.scale = echelle
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    o.data.materials.append(matiere(mat))
    lisser(o)
    return o


# Avec stiffness 2 et threshold 0.6, une metaball de rayon 1 fait 0.575 de rayon visible.
ECHELLE_META = 1 / 0.575


def blob(nom, elements, mat, max_triangles, relief=0.0, resolution=0.05, colorer=None):
    """Metaball -> mesh. elements : (pos, rayon visible, (sx, sy, sz) ou None)."""
    mb = bpy.data.metaballs.new(nom)
    mb.resolution = resolution
    mb.render_resolution = resolution
    mb.threshold = 0.6
    o = lier(bpy.data.objects.new(nom, mb))
    for pos, r, taille in elements:
        e = mb.elements.new()
        e.co = pos
        e.radius = r * ECHELLE_META
        e.stiffness = 2.0
        if taille:
            e.type = 'ELLIPSOID'
            e.size_x, e.size_y, e.size_z = taille
    activer(o)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.active_object
    o.name = nom
    o.data.materials.clear()
    o.data.materials.append(matiere(mat))
    if colorer:
        colorer(o)  # avant le relief : les couleurs suivent la forme lisse
    if relief:
        # peau bosselee : petites bosses aleatoires
        tex = bpy.data.textures.new(nom + "Peau", 'VORONOI')
        tex.noise_scale = 0.09
        mod = o.modifiers.new("Relief", 'DISPLACE')
        mod.texture = tex
        mod.strength = relief
        mod.mid_level = 0.5
        appliquer(o, mod)
    nb = sum(len(p.vertices) - 2 for p in o.data.polygons)
    if nb > max_triangles:
        mod = o.modifiers.new("Decimate", 'DECIMATE')
        mod.ratio = max_triangles / nb
        appliquer(o, mod)
    lisser(o)
    return o


def toucher(obj, origine, direction):
    ok, loc, normale, _ = obj.ray_cast(Vector(origine), Vector(direction).normalized())
    return (loc, normale) if ok else (None, None)


def colorer_peau(o, rayures=True):
    """Dos fonce, flancs, ventre clair et rayures sombres sur le dos et le haut des flancs."""
    me = o.data
    me.materials.clear()
    noms = ["Flanc", "Dos", "Rayure", "Ventre"]
    for n in noms:
        me.materials.append(matiere(n))
    for p in me.polygons:
        nz = p.normal.z
        c = p.center
        if nz < -0.35:
            i = 3
        elif nz > 0.5:
            i = 1
        else:
            i = 0
        # rayures transversales (sur le dos et le haut des flancs, pas sur la tete)
        if rayures and nz > 0.05 and c.y > -2.6:
            bande = math.sin(c.y * 3.4 + 0.6 * math.sin(c.z * 2.0))
            if bande > 0.62:
                i = 2
        p.material_index = i


# ================================================================
nettoyer()

# ---------------- corps ----------------
corps_el = [
    # bassin, cage thoracique profonde, poitrine
    ((0, 0.3, 2.75), 0.95, (0.9, 1.2, 1.0)),
    ((0, -0.8, 2.55), 1.1, (0.85, 1.1, 1.05)),
    ((0, -1.75, 2.65), 0.85, (0.8, 1.0, 1.0)),
    # cou en S
    ((0, -2.5, 3.05), 0.68, None),
    ((0, -3.05, 3.4), 0.6, None),
    # crane : large a l'arriere, long museau
    ((0, -3.6, 3.7), 0.82, (0.95, 1.05, 1.0)),
    ((0, -4.35, 3.65), 0.7, (0.82, 1.15, 0.92)),
    ((0, -5.1, 3.5), 0.56, (0.75, 1.15, 0.85)),
    ((0, -5.65, 3.38), 0.42, (0.82, 1.0, 0.85)),
    # arcades sourcilieres et bosses sur le museau
    ((0.4, -3.95, 4.25), 0.19, None),
    ((-0.4, -3.95, 4.25), 0.19, None),
    ((0.22, -4.65, 4.1), 0.12, None),
    ((-0.22, -4.65, 4.1), 0.12, None),
    ((0.16, -5.2, 3.9), 0.1, None),
    ((-0.16, -5.2, 3.9), 0.1, None),
    # joues musclees a l'arriere du crane
    ((0.5, -3.55, 3.35), 0.38, None),
    ((-0.5, -3.55, 3.35), 0.38, None),
]
# queue lourde, presque droite, qui tombe legerement
N = 20
for i in range(N):
    t = i / (N - 1)
    corps_el.append(((0, 1.1 + t * 5.6, 2.75 - t * 0.55), 0.82 * (1 - t) ** 1.15 + 0.13, None))
# pattes arriere puissantes
for s in (-1, 1):
    corps_el += [
        ((s * 0.72, 0.25, 2.1), 0.85, (0.72, 1.0, 1.25)),   # cuisse
        ((s * 0.78, 0.65, 1.15), 0.42, (0.75, 0.85, 1.35)),  # tibia
        ((s * 0.82, 0.62, 0.48), 0.27, (0.85, 0.85, 1.5)),   # metatarse
        ((s * 0.82, 0.05, 0.13), 0.3, (0.95, 1.7, 0.45)),    # pied
    ]
    for dx in (-0.2, 0, 0.2):                               # 3 orteils
        corps_el.append(((s * 0.82 + dx, -0.45, 0.11), 0.12, (0.9, 1.6, 0.8)))
# bras minuscules
for s in (-1, 1):
    corps_el += [
        ((s * 0.62, -2.0, 2.15), 0.17, (0.8, 0.8, 1.5)),
        ((s * 0.66, -2.2, 1.8), 0.12, (0.8, 1.4, 0.8)),
    ]
corps = blob("Corps", corps_el, "Flanc", 9000, relief=0.035, colorer=colorer_peau)

# ---------------- machoire (entrouverte, en train de rugir) ----------------
machoire = blob("Machoire", [
    ((0, -3.65, 3.0), 0.62, (0.95, 1.0, 0.75)),
    ((0, -4.4, 2.68), 0.52, (0.82, 1.25, 0.55)),
    ((0, -5.2, 2.45), 0.4, (0.82, 1.15, 0.55)),
], "Flanc", 2200, relief=0.025, colorer=lambda o: colorer_peau(o, rayures=False))

# ---------------- interieur de la bouche ----------------
ellipse("Bouche", (0, -4.4, 3.0), (0.46, 1.1, 0.36), "Bouche")
loc, _ = toucher(machoire, (0, -4.5, 8), (0, 0, -1))
if loc:
    ellipse("Langue", loc + Vector((0, 0, 0.01)), (0.24, 0.65, 0.07), "Langue")


# ---------------- dents irregulieres ----------------
def rangee(obj, n, largeur, longueur, y_fond, z_depart, vers_le_haut, rayon, hauteur):
    for i in range(n):
        a = -math.pi / 2 + math.pi * (i + 0.5) / n
        x = largeur * math.sin(a)
        y = y_fond - longueur * math.cos(a)
        sens = 1 if vers_le_haut else -1
        loc, _ = toucher(obj, (x, y, z_depart), (0, 0, -sens))
        if loc is None:
            continue
        h = hauteur * random.uniform(0.6, 1.15)
        # dents courbees vers l'arriere de la bouche, legerement vers l'exterieur
        direction = Vector((math.copysign(0.12, x) if abs(x) > 0.05 else 0, 0.3, sens))
        cone("Dent", loc - Vector((0, 0, sens)) * h * 0.3, rayon * random.uniform(0.85, 1.1), h,
             "Dent", direction, sommets=6, echelle=(1, 0.75, 1))


rangee(corps, 20, 0.46, 1.7, -3.95, 1.0, False, 0.07, 0.34)
rangee(machoire, 18, 0.42, 1.55, -3.95, 8.0, True, 0.06, 0.28)

# ---------------- yeux (petits, sur le cote, sous l'arcade) ----------------
centre_tete = Vector((0, -3.95, 3.9))
for s in (-1, 1):
    d = Vector((s * 1.0, -0.35, 0.3)).normalized()
    loc, normale = toucher(corps, centre_tete + d * 4, -d)
    if loc is None:
        continue
    oeil = loc - normale * 0.05
    regard = (normale + Vector((0, -0.6, 0))).normalized()
    ellipse("Oeil", oeil, (0.14, 0.14, 0.14), "Iris", seg=12, anneaux=8)
    # pupille fendue verticale
    ellipse("Pupille", oeil + regard * 0.1, (0.025, 0.025, 0.08), "Noir",
            rot=regard.to_track_quat('Y', 'Z'), seg=8, anneaux=6)
    # paupiere epaisse au-dessus de l'oeil
    ellipse("Paupiere", oeil + Vector((0, 0, 0.1)) + normale * 0.02, (0.16, 0.18, 0.06), "Dos",
            rot=normale.to_track_quat('Z', 'Y'), seg=12, anneaux=6)

# narines
for s in (-1, 1):
    loc, normale = toucher(corps, (s * 0.18, -8, 3.6), (0, 1, 0))
    if loc:
        ellipse("Narine", loc, (0.06, 0.09, 0.03), "Noir", rot=normale.to_track_quat('Z', 'Y'), seg=8, anneaux=6)

# ---------------- griffes ----------------
for s in (-1, 1):
    for dx in (-0.2, 0, 0.2):
        loc, _ = toucher(corps, (s * 0.82 + dx, -8, 0.11), (0, 1, 0))
        if loc:
            cone("Griffe", loc + Vector((0, 0.05, 0)), 0.07, 0.22, "Griffe", (0, -1, -0.45))
    for dz in (-0.04, 0.06):
        loc, _ = toucher(corps, (s * 0.66, -8, 1.8 + dz), (0, 1, 0))
        if loc:
            cone("GriffeBras", loc + Vector((0, 0.03, 0)), 0.035, 0.12, "Griffe", (0, -1, -0.6))

# ---------------- ecailles (osteodermes) le long du dos ----------------
y = -3.3
while y < 6.4:
    for s in (-1, 1):
        loc, normale = toucher(corps, (s * 0.12, y, 10), (0, 0, -1))
        if loc:
            t = max(0.0, min(1.0, (y + 3.3) / 9.7))
            r = 0.08 * (1 - 0.6 * t) + 0.03
            ellipse("Ecaille", loc - normale * r * 0.3, (r, r * 1.3, r * 0.7), "Ecaille",
                    rot=normale.to_track_quat('Z', 'Y'), seg=8, anneaux=5)
    y += 0.32

# ---------------- poser au sol ----------------
bas = min((o.matrix_world @ v.co).z for o in bpy.data.objects if o.type == 'MESH' for v in o.data.vertices)
for o in bpy.data.objects:
    o.location.z -= bas


# ================================================================
# Export Roblox : un seul mesh + texture palette
# ================================================================
def exporter_roblox(nom_fichier):
    noms = list(COULEURS)
    cote = 4
    taille = 64
    img = bpy.data.images.new("Palette", taille, taille, alpha=False)
    px = [0.0] * (taille * taille * 4)
    case = taille // cote
    for i, nom in enumerate(noms):
        r, g, b = (c / 255 for c in COULEURS[nom])
        cx, cy = i % cote, i // cote
        for yy in range(cy * case, (cy + 1) * case):
            for xx in range(cx * case, (cx + 1) * case):
                k = (yy * taille + xx) * 4
                px[k:k + 4] = [r, g, b, 1.0]
    img.pixels = px
    img.pack()

    copies = []
    for o in [o for o in bpy.data.objects if o.type == 'MESH']:
        c = o.copy()
        c.data = o.data.copy()
        lier(c)
        copies.append(c)
    bpy.ops.object.select_all(action='DESELECT')
    for c in copies:
        c.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    fusion = bpy.context.active_object
    fusion.name = "TRex"
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    me = fusion.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    uv = me.uv_layers.new(name="Palette")
    me.uv_layers.active = uv
    mats = [m.name.split(".")[0] for m in me.materials]
    for poly in me.polygons:
        i = noms.index(mats[poly.material_index])
        u = ((i % cote) + 0.5) / cote
        v = ((i // cote) + 0.5) / cote
        for li in poly.loop_indices:
            uv.data[li].uv = (u, v)

    m = bpy.data.materials.new("TRexPalette")
    m.use_nodes = True
    nodes = m.node_tree.nodes
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = 'Closest'
    m.node_tree.links.new(tex.outputs["Color"], nodes["Principled BSDF"].inputs["Base Color"])
    nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.75
    me.materials.clear()
    me.materials.append(m)
    for poly in me.polygons:
        poly.material_index = 0

    print("Triangles :", sum(len(p.vertices) - 2 for p in me.polygons))
    chemin = os.path.join(os.path.expanduser("~"), nom_fichier)
    activer(fusion)
    try:
        bpy.ops.export_scene.gltf(filepath=chemin, use_selection=True, export_format='GLB')
        print("Export OK :", chemin)
    except Exception as e:
        print("Export impossible :", e)
    bpy.data.objects.remove(fusion, do_unlink=True)


exporter_roblox("trex_realiste.glb")
