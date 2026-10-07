"""T-Rex "monstre" style Roblox : low poly a facettes + texture a studs.

Utilisation : Blender > onglet "Scripting" > Open (ce fichier) > Run Script (triangle).
(La texture est calculee par Blender : ca peut prendre une ou deux minutes.)
Pour voir les couleurs dans Blender : mode d'affichage "Material Preview" (touche Z).

Exporte un .glb par theme de couleur (trex_vert.glb, trex_bleu.glb, ...) dans ton
dossier utilisateur. Dans Roblox Studio : Avatar > Import 3D.
"""
import bpy
import math
import os
import random
import numpy as np
from mathutils import Vector, Quaternion

random.seed(3)

# ---------------- themes de couleurs (sRGB 0-255) ----------------
THEMES = {
    "vert": {
        "Dos": (58, 104, 48), "Flanc": (92, 146, 66), "Ventre": (226, 226, 206),
        "Rayure": (38, 74, 34), "Pique": (232, 232, 218), "Griffe": (244, 244, 236),
        "Dent": (255, 255, 255), "Bouche": (196, 28, 40), "Langue": (226, 90, 110),
        "Oeil": (255, 226, 40), "Noir": (16, 16, 20),
    },
    "bleu": {
        "Dos": (28, 42, 88), "Flanc": (46, 72, 132), "Ventre": (172, 188, 218),
        "Rayure": (18, 26, 58), "Pique": (204, 214, 238), "Griffe": (226, 232, 246),
        "Dent": (255, 255, 255), "Bouche": (170, 24, 36), "Langue": (210, 80, 100),
        "Oeil": (90, 226, 255), "Noir": (10, 12, 20),
    },
    "or": {
        "Dos": (176, 122, 24), "Flanc": (226, 176, 48), "Ventre": (255, 238, 176),
        "Rayure": (110, 62, 16), "Pique": (60, 40, 28), "Griffe": (60, 40, 28),
        "Dent": (255, 255, 240), "Bouche": (150, 20, 30), "Langue": (210, 80, 90),
        "Oeil": (255, 60, 40), "Noir": (20, 10, 6),
    },
    "lave": {
        "Dos": (34, 30, 32), "Flanc": (58, 50, 52), "Ventre": (120, 96, 90),
        "Rayure": (240, 90, 20), "Pique": (255, 140, 40), "Griffe": (255, 170, 60),
        "Dent": (255, 240, 220), "Bouche": (255, 80, 20), "Langue": (255, 140, 60),
        "Oeil": (255, 200, 40), "Noir": (10, 6, 6),
    },
}
AVEC_STUDS = {"Dos", "Flanc", "Ventre", "Rayure", "Pique", "Griffe"}
STUDS_PAR_UNITE = 2.4   # densite des studs
TEXTURE = 1024          # taille max acceptee par Roblox


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
        c = lineaire(THEMES["vert"][nom])
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


def ellipse(nom, pos, demi, mat, rot=None, seg=10, anneaux=6):
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
    """Cone a facettes dont la pointe suit `direction`. `pos` = centre de la base."""
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


ECHELLE_META = 1 / 0.575  # rayon de metaball -> rayon visible (stiffness 2, threshold 0.6)


def blob(nom, elements, max_triangles, resolution=0.14):
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
    nb = sum(len(p.vertices) - 2 for p in o.data.polygons)
    mod = o.modifiers.new("Facettes", 'DECIMATE')
    mod.ratio = min(1.0, max_triangles / nb)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return o


def toucher(obj, origine, direction):
    ok, loc, normale, _ = obj.ray_cast(Vector(origine), Vector(direction).normalized())
    return (loc, normale) if ok else (None, None)


def colorer(o, rayures=True):
    """Couleur par facette : dos, flancs, ventre et rayures en chevrons."""
    me = o.data
    me.materials.clear()
    for n in ("Flanc", "Dos", "Ventre", "Rayure"):
        me.materials.append(matiere(n))
    for p in me.polygons:
        nz, c = p.normal.z, p.center
        i = 2 if nz < -0.35 else (1 if nz > 0.6 else 0)
        # bandes sombres en travers du dos (pas sur la tete ni le ventre)
        if rayures and i != 2 and -2.0 < c.y < 5.0 and math.sin(c.y * 2.4) > 0.55:
            i = 3
        p.material_index = i


# ================================================================
#  CONSTRUCTION
# ================================================================
nettoyer()

corps_el = [
    # tronc trapu, poitrine haute
    ((0, 0.4, 3.1), 1.0, (0.95, 1.15, 1.0)),
    ((0, -0.7, 3.2), 1.15, (0.95, 1.05, 1.05)),
    ((0, -1.6, 3.5), 0.95, None),
    # cou
    ((0, -2.3, 4.0), 0.8, None),
    # grosse tete haute et carree
    ((0, -3.0, 4.5), 1.05, (1.0, 1.0, 1.05)),
    ((0, -3.85, 4.4), 0.82, (0.9, 1.05, 0.85)),
    ((0, -4.45, 4.25), 0.6, (0.9, 0.9, 0.85)),
    # arcades sourcilieres
    ((0.5, -3.25, 5.2), 0.3, None),
    ((-0.5, -3.25, 5.2), 0.3, None),
]
# queue qui remonte un peu (pose dynamique)
N = 14
for i in range(N):
    t = i / (N - 1)
    corps_el.append(((0, 1.3 + t * 5.0, 3.1 + t * 0.35), 0.85 * (1 - t) ** 1.1 + 0.18, None))
for s in (-1, 1):
    corps_el += [
        ((s * 0.85, 0.35, 2.4), 1.0, (0.75, 1.0, 1.25)),    # cuisse
        ((s * 0.95, 0.7, 1.3), 0.52, (0.8, 0.85, 1.5)),      # tibia
        ((s * 0.95, 0.5, 0.6), 0.36, (0.9, 0.9, 1.2)),       # cheville
        ((s * 0.95, 0.1, 0.22), 0.45, (1.0, 1.6, 0.5)),      # pied
        ((s * 0.85, -1.5, 2.9), 0.3, (0.8, 0.8, 1.4)),       # bras
        ((s * 0.95, -1.8, 2.45), 0.25, (0.8, 1.3, 0.8)),     # avant-bras
    ]
corps = blob("Corps", corps_el, 2600)
colorer(corps)

# machoire grande ouverte (il rugit)
machoire = blob("Machoire", [
    ((0, -2.9, 3.65), 0.72, (0.95, 1.0, 0.7)),
    ((0, -3.7, 3.2), 0.64, (0.88, 1.2, 0.5)),
    ((0, -4.4, 2.85), 0.5, (0.88, 1.1, 0.5)),
], 900, resolution=0.1)
colorer(machoire, rayures=False)

ellipse("Bouche", (0, -3.6, 3.7), (0.55, 1.1, 0.5), "Bouche")
loc, _ = toucher(machoire, (0, -3.9, 9), (0, 0, -1))
if loc:
    ellipse("Langue", loc + Vector((0, 0, 0.02)), (0.32, 0.75, 0.1), "Langue", seg=8, anneaux=4)


# ---------------- dents ----------------
def rangee(obj, n, largeur, longueur, y_fond, z_depart, vers_le_haut, rayon, hauteur):
    for i in range(n):
        a = -math.pi / 2 + math.pi * (i + 0.5) / n
        x = largeur * math.sin(a)
        y = y_fond - longueur * math.cos(a)
        sens = 1 if vers_le_haut else -1
        loc, _ = toucher(obj, (x, y, z_depart), (0, 0, -sens))
        if loc is None:
            continue
        h = hauteur * random.uniform(0.75, 1.15)
        cone("Dent", loc - Vector((0, 0, sens)) * h * 0.25, rayon, h, "Dent", (0, 0.15, sens), sommets=4)


rangee(corps, 12, 0.55, 1.7, -3.3, 1.0, False, 0.1, 0.42)
rangee(machoire, 10, 0.5, 1.5, -3.3, 9.0, True, 0.09, 0.36)

# ---------------- yeux lumineux, sourcils mechants ----------------
centre_tete = Vector((0, -3.2, 4.75))
for s in (-1, 1):
    d = Vector((s * 0.8, -0.5, 0.35)).normalized()
    loc, n = toucher(corps, centre_tete + d * 5, -d)
    if loc is None:
        continue
    q = n.to_track_quat('Z', 'Y') @ Quaternion((0, 0, 1), math.radians(25 * s))
    ellipse("Oeil", loc, (0.24, 0.12, 0.07), "Oeil", rot=q, seg=8, anneaux=4)
    ellipse("Pupille", loc + n * 0.04, (0.04, 0.09, 0.05), "Noir", rot=q, seg=6, anneaux=4)
    # corne au-dessus de l'oeil
    lc, nc = toucher(corps, (s * 0.5, -3.1, 9), (0, 0, -1))
    if lc:
        cone("Corne", lc - Vector((0, 0, 0.1)), 0.18, 0.6, "Pique", (s * 0.3, 0.9, 0.7))

# narines
for s in (-1, 1):
    loc, n = toucher(corps, (s * 0.25, -9, 4.5), (0, 1, 0))
    if loc:
        ellipse("Narine", loc, (0.09, 0.06, 0.04), "Noir", rot=n.to_track_quat('Z', 'Y'), seg=6, anneaux=4)

# ---------------- grosses piques sur le dos ----------------
y = -2.5
i = 0
while y < 6.0:
    loc, n = toucher(corps, (0, y, 12), (0, 0, -1))
    if loc:
        t = (y + 2.5) / 8.5
        h = 0.85 * (1 - 0.7 * t) + 0.12
        cone("Pique", loc - Vector((0, 0, h * 0.2)), h * 0.5, h, "Pique", (0, 0.6, 1), echelle=(0.35, 1, 1))
        # petites piques laterales une fois sur deux
        if i % 2 == 0 and t < 0.75:
            for s in (-1, 1):
                ls, ns = toucher(corps, (s * 6, y + 0.2, loc.z - 0.35), (-s, 0, 0))
                if ls:
                    cone("PiqueCote", ls - ns * 0.05, h * 0.22, h * 0.45, "Pique", ns + Vector((0, 0.8, 0.3)))
    y += 0.6
    i += 1

# ---------------- griffes ----------------
for s in (-1, 1):
    for dx in (-0.28, 0, 0.28):
        loc, _ = toucher(corps, (s * 0.95 + dx, -9, 0.2), (0, 1, 0))
        if loc:
            cone("Griffe", loc + Vector((0, 0.08, 0)), 0.13, 0.42, "Griffe", (0, -1, -0.5))
    for dx in (-0.1, 0.1):
        loc, _ = toucher(corps, (s * 0.95 + dx, -9, 2.4), (0, 1, 0))
        if loc:
            cone("GriffeMain", loc + Vector((0, 0.05, 0)), 0.07, 0.28, "Griffe", (0, -0.6, -1))
    # pique au coude
    lc, nc = toucher(corps, (s * 6, -1.5, 2.9), (-s, 0, 0))
    if lc:
        cone("PiqueCoude", lc, 0.1, 0.35, "Pique", (s, 0.8, 0.2))

# ---------------- poser au sol ----------------
bas = min((o.matrix_world @ v.co).z for o in bpy.data.objects if o.type == 'MESH' for v in o.data.vertices)
for o in bpy.data.objects:
    o.location.z -= bas

# ================================================================
#  FUSION + UV
# ================================================================
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
    if o.type == 'MESH':
        o.select_set(True)
bpy.context.view_layer.objects.active = corps
bpy.ops.object.join()
trex = bpy.context.active_object
trex.name = "TRex"
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for p in trex.data.polygons:
    p.use_smooth = False  # facettes bien nettes
me = trex.data
while me.uv_layers:
    me.uv_layers.remove(me.uv_layers[0])
me.uv_layers.new(name="UV")
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
bpy.ops.object.mode_set(mode='OBJECT')
print("Triangles :", sum(len(p.vertices) - 2 for p in me.polygons))

# ================================================================
#  TEXTURE A STUDS (bake)
# ================================================================
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 1

pts = [v.co for v in me.vertices]
mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
taille = max(max(p.x for p in pts) - mn.x, max(p.y for p in pts) - mn.y, max(p.z for p in pts) - mn.z)


def passe(mode, theme=None):
    """Bake une 'passe' (couleur, masque, position ou normale) dans une image flottante."""
    img = bpy.data.images.new("bake_" + mode, TEXTURE, TEXTURE, alpha=False, float_buffer=True)
    for slot in me.materials:
        nom = slot.name.split(".")[0]
        nt = slot.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        em = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        if mode == "couleur":
            em.inputs["Color"].default_value = lineaire(theme[nom])
        elif mode == "masque":
            em.inputs["Color"].default_value = (1, 1, 1, 1) if nom in AVEC_STUDS else (0, 0, 0, 1)
        elif mode == "position":
            tc = nt.nodes.new("ShaderNodeTexCoord")
            mp = nt.nodes.new("ShaderNodeMapping")
            mp.inputs["Scale"].default_value = (1 / taille,) * 3
            mp.inputs["Location"].default_value = -mn / taille
            nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
            nt.links.new(mp.outputs[0], em.inputs["Color"])
        elif mode == "normale":
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
    activer(trex)
    bpy.ops.object.bake(type='EMIT', margin=4, use_clear=True)
    a = np.empty(TEXTURE * TEXTURE * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(TEXTURE, TEXTURE, 4)[..., :3]


print("Calcul de la texture...")
masque = passe("masque")[..., 0:1]
P = passe("position") * taille + np.array(mn)
N = passe("normale") * 2 - 1

# motif de studs : projection sur le plan le plus en face de chaque facette
axe = np.argmax(np.abs(N), axis=-1)
u = np.where(axe == 0, P[..., 1], P[..., 0]) * STUDS_PAR_UNITE
v = np.where(axe == 2, P[..., 1], P[..., 2]) * STUDS_PAR_UNITE
qu = u - np.floor(u) - 0.5
qv = v - np.floor(v) - 0.5
d = np.sqrt(qu * qu + qv * qv)
lumiere = np.clip((qv - qu) * 3, -1, 1)                    # cote eclaire / cote ombre
dedans = np.clip((0.27 - d) / 0.04 + 0.5, 0, 1)
bord = np.clip(1 - np.abs(d - 0.29) / 0.045, 0, 1)
motif = 1 + 0.10 * dedans + bord * (0.26 * lumiere - 0.10)
facteur = (1 + masque[..., 0] * (motif - 1))[..., None]


def vers_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


images = {}
for nom_theme, theme in THEMES.items():
    couleur = passe("couleur", theme)
    rgb = vers_srgb(couleur * facteur)
    rgba = np.concatenate([rgb, np.ones((TEXTURE, TEXTURE, 1))], axis=-1).astype(np.float32)
    img = bpy.data.images.new("TRex_" + nom_theme, TEXTURE, TEXTURE, alpha=False)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    images[nom_theme] = img

# ================================================================
#  MATERIAU FINAL + EXPORT
# ================================================================
final = bpy.data.materials.new("TRexStuds")
final.use_nodes = True
nodes = final.node_tree.nodes
tex = nodes.new("ShaderNodeTexImage")
bsdf = nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.6
final.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
me.materials.clear()
me.materials.append(final)
for p in me.polygons:
    p.material_index = 0

activer(trex)
for nom_theme, img in images.items():
    tex.image = img
    chemin = os.path.join(os.path.expanduser("~"), f"trex_{nom_theme}.glb")
    try:
        bpy.ops.export_scene.gltf(filepath=chemin, use_selection=True, export_format='GLB')
        print("Export OK :", chemin)
    except Exception as e:
        print("Export impossible :", e)

tex.image = images["vert"]
