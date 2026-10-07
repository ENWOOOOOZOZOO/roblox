"""T-Rex mignon (v2) pour Blender 4.x / 5.x.

Utilisation : Blender > onglet "Scripting" > Open (ce fichier) > Run Script (triangle).
Le dino regarde vers -Y (vue de face = touche 1 du pave numerique).

Le corps est fait de metaballs (les formes fusionnent en une peau lisse),
puis converti en mesh. Les dents, yeux et plaques sont poses sur la surface
par lancer de rayons.

A la fin, tout est fusionne en UN mesh avec une petite texture "palette"
(les couleurs passent ainsi dans Roblox) et exporte en trex.glb dans ton
dossier utilisateur. Dans Roblox Studio : Avatar > Import 3D > trex.glb.
"""
import bpy
import math
import os
from mathutils import Vector, Quaternion

# ---------------- couleurs (sRGB 0-255) ----------------
COULEURS = {
    "Peau": (96, 178, 74),
    "PeauFoncee": (52, 118, 56),
    "Ventre": (246, 226, 170),
    "Bouche": (196, 38, 58),
    "Langue": (255, 122, 150),
    "Blanc": (255, 255, 255),
    "Noir": (20, 20, 26),
    "Iris": (250, 176, 30),
    "Griffe": (238, 228, 200),
    "Joue": (255, 150, 170),
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
    for coll in (bpy.data.meshes, bpy.data.metaballs, bpy.data.materials, bpy.data.images):
        for d in list(coll):
            coll.remove(d)


MATS = {}


def matiere(nom):
    if nom not in MATS:
        m = bpy.data.materials.new(nom)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = lineaire(COULEURS[nom])
        b.inputs["Roughness"].default_value = 0.5
        m.diffuse_color = lineaire(COULEURS[nom])  # couleur en mode Solid
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


def ellipse(nom, pos, demi, mat, rot=None, seg=18, anneaux=10):
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


def cone(nom, pos, rayon, hauteur, mat, direction, sommets=8, echelle=(1, 1, 1)):
    """Cone dont la pointe suit `direction`. `pos` = centre de la base."""
    d = Vector(direction).normalized()
    centre = Vector(pos) + d * (hauteur / 2)
    bpy.ops.mesh.primitive_cone_add(vertices=sommets, radius1=rayon, radius2=0, depth=hauteur, location=centre)
    o = bpy.context.active_object
    o.name = nom
    o.scale = echelle
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    o.data.materials.append(matiere(mat))
    return o


# Avec stiffness 2 et threshold 0.6, une metaball de rayon 1 fait 0.575 de rayon visible.
# On corrige pour que les rayons donnes ci-dessous soient les rayons VISIBLES.
ECHELLE_META = 1 / 0.575


def decimer(o, max_triangles):
    nb = sum(len(p.vertices) - 2 for p in o.data.polygons)
    if nb > max_triangles:
        mod = o.modifiers.new("Decimate", 'DECIMATE')
        mod.ratio = max_triangles / nb
        activer(o)
        bpy.ops.object.modifier_apply(modifier=mod.name)


def blob(nom, elements, mat, max_triangles, resolution=0.06):
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
    decimer(o, max_triangles)
    lisser(o)
    return o


def toucher(obj, origine, direction):
    """Point de la surface de `obj` touche par un rayon (obj sans transformation)."""
    ok, loc, normale, _ = obj.ray_cast(Vector(origine), Vector(direction).normalized())
    return (loc, normale) if ok else (None, None)


# ================================================================
nettoyer()

# ---------------- corps, cou, crane, pattes, queue ----------------
corps_el = [
    # tronc penche vers l'avant (la poitrine plus haute que les hanches)
    ((0, 0.7, 2.0), 1.0, None),
    ((0, -0.1, 2.25), 1.05, None),
    ((0, -0.8, 2.6), 0.95, None),
    # cou
    ((0, -1.35, 3.15), 0.75, None),
    # crane + museau : grosse tete carree
    ((0, -2.0, 3.85), 1.1, (1.0, 1.0, 0.8)),
    ((0, -2.8, 3.75), 0.9, (0.85, 1.0, 0.62)),
    ((0, -3.35, 3.65), 0.7, (0.85, 0.9, 0.6)),
]
# queue : une chaine de boules qui s'amincit et remonte un peu au bout
for i in range(9):
    t = i / 8
    corps_el.append(((0, 1.5 + t * 3.6, 2.0 - t * 0.55 + t * t * 0.35), 0.85 * (1 - t) + 0.24, None))
# pattes : grosse cuisse, tibia, pied
for s in (-1, 1):
    corps_el += [
        ((s * 0.85, 0.75, 1.55), 0.9, (0.8, 1.0, 1.1)),
        ((s * 0.9, 0.85, 0.75), 0.5, (0.75, 0.8, 1.1)),
        ((s * 0.9, 0.45, 0.22), 0.5, (0.85, 1.5, 0.5)),
    ]
# petits bras
for s in (-1, 1):
    corps_el += [
        ((s * 0.78, -1.35, 2.15), 0.28, None),
        ((s * 0.85, -1.65, 1.85), 0.22, None),
    ]
corps = blob("Corps", corps_el, "Peau", 7000)

# ---------------- machoire du bas (grande ouverte) ----------------
machoire = blob("Machoire", [
    ((0, -1.75, 2.8), 0.6, None),
    ((0, -2.45, 2.4), 0.8, (0.95, 1.15, 0.45)),
    ((0, -3.1, 2.1), 0.65, (0.95, 1.0, 0.45)),
], "Peau", 2500)

# ---------------- ventre ----------------
ellipse("Ventre", (0, -0.6, 1.9), (0.8, 1.2, 0.95), "Ventre",
        rot=Quaternion((1, 0, 0), math.radians(-30)))
ellipse("Gorge", (0, -1.6, 2.85), (0.5, 0.5, 0.4), "Ventre")

# ---------------- interieur de la bouche ----------------
ellipse("Bouche", (0, -2.35, 2.85), (0.52, 0.9, 0.42), "Bouche")
loc, _ = toucher(machoire, (0, -2.7, 6), (0, 0, -1))
if loc:
    ellipse("Langue", loc + Vector((0, 0, 0.02)), (0.38, 0.65, 0.12), "Langue")

# ---------------- dents ----------------
def rangee(obj, n, largeur, longueur, y_fond, z_depart, vers_le_haut, rayon, hauteur):
    """Dents le long d'un U (vu de dessus) sous le crane ou sur la machoire."""
    for i in range(n):
        a = -math.pi / 2 + math.pi * (i + 0.5) / n
        x = largeur * math.sin(a)
        y = y_fond - longueur * math.cos(a)
        direction = (0, 0, 1) if vers_le_haut else (0, 0, -1)
        loc, _ = toucher(obj, (x, y, z_depart), (0, 0, -direction[2]))
        if loc is None:
            continue
        base = loc - Vector(direction) * hauteur * 0.25
        cone("Dent", base, rayon, hauteur, "Blanc", direction, sommets=6)


# dents du haut : rayon tire depuis le bas vers le crane
rangee(corps, 16, 0.62, 1.1, -2.2, 2.2, False, 0.075, 0.26)
# dents du bas : rayon tire depuis le haut vers la machoire
rangee(machoire, 14, 0.58, 1.0, -2.2, 6.0, True, 0.065, 0.22)

# ---------------- yeux ----------------
centre_tete = Vector((0, -2.1, 3.9))
for s in (-1, 1):
    d = Vector((s * 0.55, -0.75, 0.38)).normalized()
    loc, normale = toucher(corps, centre_tete + d * 4, -d)
    if loc is None:
        continue
    oeil = loc - normale * 0.06
    regard = (normale + Vector((0, -1.5, 0))).normalized()  # il regarde devant lui
    ellipse("Oeil", oeil, (0.3, 0.3, 0.3), "Blanc", seg=16, anneaux=10)
    ellipse("Iris", oeil + regard * 0.14, (0.2, 0.2, 0.2), "Iris", seg=14, anneaux=8)
    ellipse("Pupille", oeil + regard * 0.22, (0.13, 0.13, 0.13), "Noir", seg=12, anneaux=8)
    ellipse("Reflet", oeil + regard * 0.3 + Vector((s * 0.03, 0, 0.08)), (0.05, 0.05, 0.05), "Blanc", seg=8, anneaux=6)
    # sourcil, pose sur la peau juste au-dessus de l'oeil
    ds = Vector((s * 0.45, -0.6, 0.65)).normalized()
    ls, ns = toucher(corps, centre_tete + ds * 4, -ds)
    if ls:
        ellipse("Sourcil", ls + ns * 0.02, (0.3, 0.1, 0.06), "PeauFoncee",
                rot=ns.to_track_quat('Z', 'Y') @ Quaternion((0, 0, 1), math.radians(-20 * s)))
    # joue rose
    dj = Vector((s * 0.9, -0.35, -0.1)).normalized()
    lj, nj = toucher(corps, centre_tete + dj * 4, -dj)
    if lj:
        ellipse("Joue", lj, (0.24, 0.24, 0.05), "Joue", rot=nj.to_track_quat('Z', 'Y'))

# narines
for s in (-1, 1):
    loc, normale = toucher(corps, (s * 0.25, -8, 4.0), (0, 1, 0))
    if loc:
        ellipse("Narine", loc, (0.08, 0.08, 0.04), "Noir", rot=normale.to_track_quat('Z', 'Y'), seg=8, anneaux=6)

# ---------------- griffes ----------------
for s in (-1, 1):
    for dx in (-0.28, 0, 0.28):
        loc, normale = toucher(corps, (s * 0.9 + dx, -6, 0.2), (0, 1, 0))
        if loc:
            cone("Griffe", loc - Vector((0, -0.08, 0)), 0.1, 0.3, "Griffe", (0, -1, -0.25))
    for dz in (-0.08, 0.1):
        loc, normale = toucher(corps, (s * 0.85, -6, 1.8 + dz), (0, 1, 0))
        if loc:
            cone("GriffeBras", loc - Vector((0, -0.05, 0)), 0.06, 0.18, "Griffe", (0, -1, -0.3))

# ---------------- plaques sur le dos ----------------
plaques = [-1.6, -0.9, -0.2, 0.5, 1.2, 1.9, 2.6, 3.3, 3.9, 4.5]
for i, y in enumerate(plaques):
    loc, normale = toucher(corps, (0, y, 10), (0, 0, -1))
    if loc is None:
        continue
    taille = 0.55 - i * 0.04
    cone("Plaque", loc - Vector((0, 0, taille * 0.25)), taille * 0.6, taille, "PeauFoncee",
         (0, 0, 1), sommets=4, echelle=(0.35, 1, 1))

# ---------------- taches sur le dos et les flancs ----------------
taches = [(0.0, 75), (0.9, 60), (-0.5, 50), (1.8, 70), (2.8, 65), (0.4, 35), (1.3, 40)]
for s in (-1, 1):
    for y, angle in taches:
        a = math.radians(angle)
        d = Vector((s * math.cos(a), 0, math.sin(a)))
        loc, normale = toucher(corps, Vector((0, y, 2.0)) + d * 6, -d)
        if loc:
            ellipse("Tache", loc - normale * 0.015, (0.2, 0.24, 0.035), "PeauFoncee", rot=normale.to_track_quat('Z', 'Y'),
                    seg=12, anneaux=8)

# ---------------- poser le dino au sol ----------------
bas = min((o.matrix_world @ v.co).z for o in bpy.data.objects if o.type == 'MESH' for v in o.data.vertices)
for o in bpy.data.objects:
    o.location.z -= bas

# ================================================================
# Export pour Roblox : un seul mesh + texture palette
# ================================================================
def exporter_roblox():
    noms = list(COULEURS)
    cote = 4  # palette de 4x4 cases (16 couleurs max)
    taille = 64
    img = bpy.data.images.new("PaletteTRex", taille, taille, alpha=False)
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

    # copie de tous les meshes, fusion en un seul objet
    sources = [o for o in bpy.data.objects if o.type == 'MESH']
    copies = []
    for o in sources:
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

    # UV : chaque face pointe au centre de la case de sa couleur
    me = fusion.data
    while me.uv_layers:  # les spheres ont leurs propres UV : on les enleve
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

    # un seul materiau avec la texture
    m = bpy.data.materials.new("TRexPalette")
    m.use_nodes = True
    nodes = m.node_tree.nodes
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = 'Closest'
    m.node_tree.links.new(tex.outputs["Color"], nodes["Principled BSDF"].inputs["Base Color"])
    me.materials.clear()
    me.materials.append(m)
    for poly in me.polygons:
        poly.material_index = 0

    nb_tri = sum(len(p.vertices) - 2 for p in me.polygons)
    print("Triangles :", nb_tri)

    chemin = os.path.join(os.path.expanduser("~"), "trex.glb")
    activer(fusion)
    try:
        bpy.ops.export_scene.gltf(filepath=chemin, use_selection=True, export_format='GLB')
        print("Export OK :", chemin)
    except Exception as e:
        print("Export impossible :", e)
    # on garde la scene en couleurs separees : on supprime la copie fusionnee
    bpy.data.objects.remove(fusion, do_unlink=True)


exporter_roblox()
