"""T-Rex "en blocs" style Roblox : boites biseautees + texture a studs carres.

Utilisation : Blender > onglet "Scripting" > Open (ce fichier) > Run Script (triangle).
(La texture est calculee par Blender : ca peut prendre une minute.)
Pour voir les couleurs dans Blender : mode d'affichage "Material Preview" (touche Z).

Exporte un .glb par theme (trex_blocs_vert.glb, ...) dans ton dossier utilisateur.
Dans Roblox Studio : Avatar > Import 3D.
"""
import bpy
import bmesh
import math
import os
import numpy as np
from mathutils import Vector

# ---------------- themes (sRGB 0-255) ----------------
THEMES = {
    "vert": {
        "Peau": (128, 146, 78), "Rayure": (86, 102, 54), "Ventre": (232, 228, 218),
        "Dent": (255, 255, 255), "Bouche": (206, 24, 36), "Oeil": (12, 12, 14),
        "Reflet": (255, 255, 255), "Griffe": (240, 238, 230),
    },
    "bleu": {
        "Peau": (62, 96, 168), "Rayure": (36, 58, 112), "Ventre": (212, 222, 242),
        "Dent": (255, 255, 255), "Bouche": (190, 24, 40), "Oeil": (10, 12, 20),
        "Reflet": (140, 230, 255), "Griffe": (226, 234, 250),
    },
    "or": {
        "Peau": (232, 180, 48), "Rayure": (168, 108, 26), "Ventre": (255, 244, 208),
        "Dent": (255, 255, 245), "Bouche": (170, 22, 30), "Oeil": (20, 12, 6),
        "Reflet": (255, 255, 255), "Griffe": (92, 60, 30),
    },
    "lave": {
        "Peau": (58, 52, 54), "Rayure": (246, 104, 22), "Ventre": (112, 94, 88),
        "Dent": (255, 242, 222), "Bouche": (255, 92, 20), "Oeil": (255, 140, 20),
        "Reflet": (255, 236, 160), "Griffe": (255, 160, 50),
    },
}
AVEC_STUDS = {"Peau", "Rayure", "Ventre"}
STUDS_PAR_UNITE = 5.0
TEXTURE = 1024


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
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
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


def boite(nom, centre, taille, mat, biseau=0.1, arriere=(1, 1), avant=(1, 1), tangage=0.0):
    """Boite biseautee. `arriere`/`avant` = retrecissement (x, z) du bout +Y / -Y.
    `tangage` en degres : positif = l'arriere monte."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    o = bpy.context.active_object
    o.name = nom
    sx, sy, sz = taille
    for v in o.data.vertices:
        x, y, z = v.co
        fx, fz = arriere if y > 0 else avant
        v.co = (x * sx * fx, y * sy, z * sz * fz)
    o.data.materials.append(matiere(mat))
    biseauter(o, biseau)
    o.rotation_euler = (math.radians(tangage), 0, 0)
    o.location = centre
    return o


def profil(nom, points, largeur, mat, biseau=0.1, effile=None):
    """Forme de profil (y, z) extrudee sur la largeur (axe X). effile(y) -> facteur de largeur."""
    me = bpy.data.meshes.new(nom)
    bm = bmesh.new()
    a = [bm.verts.new((-largeur / 2, y, z)) for y, z in points]
    b = [bm.verts.new((largeur / 2, y, z)) for y, z in points]
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    n = len(points)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    if effile:
        for v in bm.verts:
            v.co.x *= effile(v.co.y)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    o = lier(bpy.data.objects.new(nom, me))
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


def cone(nom, pos, rayon, hauteur, mat, direction, sommets=4):
    d = Vector(direction).normalized()
    bpy.ops.mesh.primitive_cone_add(vertices=sommets, radius1=rayon, radius2=0, depth=hauteur,
                                    location=Vector(pos) + d * (hauteur / 2))
    o = bpy.context.active_object
    o.name = nom
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    o.data.materials.append(matiere(mat))
    return o


def le_long(points, pas):
    """Points regulierement espaces le long d'une ligne brisee (y, z)."""
    res = []
    reste = 0.0
    for (y0, z0), (y1, z1) in zip(points, points[1:]):
        L = math.hypot(y1 - y0, z1 - z0)
        t = reste
        while t <= L:
            k = t / L
            res.append((y0 + (y1 - y0) * k, z0 + (z1 - z0) * k))
            t += pas
        reste = t - L
    return res


def toucher(obj, origine, direction):
    """Point de la surface de `obj` touche par un rayon (coordonnees du monde)."""
    mw = obj.matrix_world
    inv = mw.inverted()
    o_loc = inv @ Vector(origine)
    d_loc = (inv.to_3x3() @ Vector(direction)).normalized()
    ok, loc, normale, _ = obj.ray_cast(o_loc, d_loc)
    if not ok:
        return None, None
    return mw @ loc, (mw.to_3x3().inverted().transposed() @ normale).normalized()


# ================================================================
#  CONSTRUCTION
# ================================================================
nettoyer()

# ---------- tete : profil decoupe, large a l'arriere, museau plus etroit ----------
LARGEUR_TETE = 2.35


def effile_tete(y):
    return 1.0 - 0.28 * max(0.0, min(1.0, (-y - 3.5) / 1.6))


ligne_haut = [(-5.05, 3.82), (-4.4, 3.64), (-3.7, 3.6), (-3.0, 3.68), (-2.45, 3.92)]  # bord des dents du haut
tete = profil("Tete", [
    (-1.85, 4.55), (-2.3, 5.15), (-3.3, 5.22), (-4.3, 4.88), (-4.95, 4.58), (-5.18, 4.22),
] + ligne_haut[::1] + [(-2.0, 4.1)], LARGEUR_TETE, "Peau", biseau=0.12, effile=effile_tete)

# ---------- machoire du bas en sourire ----------
ligne_bas = [(-4.95, 3.62), (-4.4, 3.44), (-3.7, 3.4), (-3.0, 3.48), (-2.5, 3.72)]
machoire = profil("Machoire", ligne_bas[::-1] + [
    (-5.12, 3.4), (-5.02, 3.12), (-4.55, 2.86), (-3.85, 2.72), (-3.1, 2.78), (-2.45, 3.08), (-2.15, 3.55),
][::-1][::-1], 2.15, "Peau", biseau=0.1, effile=effile_tete)

# interieur rouge de la bouche
boite("Bouche", (0, -3.7, 3.55), (1.65, 2.6, 0.42), "Bouche", biseau=0.05)


# ---------- dents serrees ----------
def rangee_dents(ligne, sens, largeur, longueur, rayon, decalage=0.0):
    pts = le_long(ligne, 0.19)
    for k, (y, z) in enumerate(pts):
        y += decalage
        demi = largeur / 2 * effile_tete(y) - 0.13
        for s in (-1, 1):
            cone("Dent", (s * demi, y, z - sens * 0.04), rayon, longueur, "Dent", (0, 0, sens))
    # dents de devant
    y0, z0 = ligne[0]
    demi = largeur / 2 * effile_tete(y0) - 0.13
    for x in np.linspace(-demi * 0.7, demi * 0.7, 4):
        cone("Dent", (x, y0 + 0.08, z0 - sens * 0.04), rayon, longueur, "Dent", (0, 0, sens))


rangee_dents(ligne_haut, -1, LARGEUR_TETE, 0.32, 0.1)
rangee_dents(ligne_bas, 1, 2.15, 0.28, 0.09, decalage=0.095)

# ---------- oeil noir ovale + reflet, arcade, narines ----------
for s in (-1, 1):
    loc, n = toucher(tete, (s * 5, -3.45, 4.62), (-s, 0, 0))
    if loc:
        q = n.to_track_quat('Z', 'Y')
        ellipse("Oeil", loc, (0.17, 0.25, 0.06), "Oeil", rot=q)
        ellipse("Reflet", loc + n * 0.05 + Vector((0, -0.05, 0.1)), (0.05, 0.06, 0.02), "Reflet", rot=q, seg=8, anneaux=4)
    boite("Arcade", (s * 0.98, -3.5, 5.0), (0.5, 1.05, 0.26), "Peau", biseau=0.06, avant=(0.7, 0.6), tangage=-8)
    boite("Narine", (s * 0.42, -4.85, 4.62), (0.18, 0.32, 0.1), "Rayure", biseau=0.03, tangage=-20)
    # deux rainures sombres sur la joue
    for y in (-2.75, -3.0):
        boite("RainureJoue", (s * (LARGEUR_TETE / 2 + 0.005), y, 4.45), (0.04, 0.12, 0.7), "Rayure", biseau=0.0)

# ---------- cou, corps, queue ----------
boite("Cou", (0, -1.85, 4.1), (2.15, 1.2, 1.7), "Peau", biseau=0.18, tangage=-15)
corps = boite("Corps", (0, -0.4, 3.5), (2.85, 3.0, 2.55), "Peau", biseau=0.3, avant=(0.92, 0.92))
queue = [
    # centre, taille, retrecissement arriere, tangage
    ((0, 1.8, 3.75), (2.35, 1.8, 2.05), (0.74, 0.74), 6),
    ((0, 3.3, 4.02), (1.74, 1.65, 1.5), (0.68, 0.66), 10),
    ((0, 4.65, 4.33), (1.18, 1.5, 1.0), (0.45, 0.45), 14),
]
segments = []
for c, t, arr, tg in queue:
    segments.append(boite("Queue", c, t, "Peau", biseau=0.14, arriere=arr, tangage=tg))


# bandes sombres en relief sur le dos (posees par lancer de rayons sur chaque bloc)
def bande(obj, y, largeur, hauteur):
    loc, _ = toucher(obj, (0, y, 20), (0, 0, -1))
    if loc is None:
        return
    boite("Bande", (0, y, loc.z - hauteur / 2 + 0.03), (largeur, 0.2, hauteur), "Rayure", biseau=0.04)


for y in (-1.2, -0.5, 0.2):
    bande(corps, y, 2.91, 1.55)
for obj, (c, t, arr, tg) in zip(segments, queue):
    for k in (-0.25, 0.2):
        y = c[1] + k * t[1]
        f = 1 + (arr[0] - 1) * (k + 0.5)
        bande(obj, y, t[0] * f + 0.06, t[2] * f * 0.7)

# ---------- pattes accroupies ----------
for s in (-1, 1):
    boite("Cuisse", (s * 1.38, 0.3, 2.85), (1.2, 1.9, 2.0), "Peau", biseau=0.2, avant=(0.9, 0.85), tangage=-10)
    boite("Tibia", (s * 1.45, 0.62, 1.3), (0.9, 0.9, 1.75), "Peau", biseau=0.14, tangage=22)
    boite("Pied", (s * 1.45, 0.1, 0.26), (1.2, 1.5, 0.52), "Peau", biseau=0.12, avant=(1.0, 0.8))
    for dx in (-0.36, 0, 0.36):
        boite("Orteil", (s * 1.45 + dx, -0.78, 0.2), (0.32, 0.5, 0.38), "Peau", biseau=0.06)
        cone("Griffe", (s * 1.45 + dx, -1.0, 0.2), 0.12, 0.32, "Griffe", (0, -1, -0.35))
    # petits bras (costauds)
    boite("Bras", (s * 1.42, -1.6, 3.15), (0.45, 0.52, 0.85), "Peau", biseau=0.08, tangage=20)
    boite("AvantBras", (s * 1.47, -1.98, 2.75), (0.42, 0.75, 0.4), "Peau", biseau=0.08)
    for dx in (-0.1, 0.1):
        cone("GriffeMain", (s * 1.47 + dx, -2.35, 2.75), 0.07, 0.22, "Griffe", (0, -1, -0.5))

# ---------- poser au sol ----------
bas = min((o.matrix_world @ v.co).z for o in bpy.data.objects if o.type == 'MESH' for v in o.data.vertices)
for o in bpy.data.objects:
    o.location.z -= bas

# ================================================================
#  FUSION + ventre clair + UV
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
me = trex.data

# le dessous du corps, de la queue et de la machoire devient clair
noms = [m.name.split(".")[0] for m in me.materials]
if "Ventre" not in noms:
    me.materials.append(matiere("Ventre"))
    noms.append("Ventre")
i_peau, i_ventre = noms.index("Peau"), noms.index("Ventre")
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
print("Triangles :", sum(len(p.vertices) - 2 for p in me.polygons))

# ================================================================
#  TEXTURE A STUDS CARRES (bake)
# ================================================================
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 1

pts = [v.co for v in me.vertices]
mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
taille = max(max(p.x for p in pts) - mn.x, max(p.y for p in pts) - mn.y, max(p.z for p in pts) - mn.z)


def passe(mode, theme=None):
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
masque = passe("masque")[..., 0]
P = passe("position") * taille + np.array(mn)
N = passe("normale") * 2 - 1

# studs carres : projection sur le plan le plus en face de chaque facette
axe = np.argmax(np.abs(N), axis=-1)
u = np.where(axe == 0, P[..., 1], P[..., 0]) * STUDS_PAR_UNITE
v = np.where(axe == 2, P[..., 1], P[..., 2]) * STUDS_PAR_UNITE
qu = u - np.floor(u) - 0.5
qv = v - np.floor(v) - 0.5
m = np.maximum(np.abs(qu), np.abs(qv))
dedans = np.clip((0.31 - m) / 0.03, 0, 1)
bord = np.clip(1 - np.abs(m - 0.3) / 0.06, 0, 1)
lumiere = np.where(np.abs(qv) >= np.abs(qu), np.sign(qv), 0.5 * np.sign(-qu))  # haut clair, bas fonce
motif = 1 + 0.05 * dedans + bord * 0.2 * lumiere - 0.06 * (1 - dedans)
facteur = (1 + masque * (motif - 1))[..., None]


def vers_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


images = {}
for nom_theme, theme in THEMES.items():
    rgb = vers_srgb(passe("couleur", theme) * facteur)
    rgba = np.concatenate([rgb, np.ones((TEXTURE, TEXTURE, 1))], axis=-1).astype(np.float32)
    img = bpy.data.images.new("TRexBlocs_" + nom_theme, TEXTURE, TEXTURE, alpha=False)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    images[nom_theme] = img

# ================================================================
#  MATERIAU FINAL + EXPORT
# ================================================================
final = bpy.data.materials.new("TRexBlocs")
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
    chemin = os.path.join(os.path.expanduser("~"), f"trex_blocs_{nom_theme}.glb")
    try:
        bpy.ops.export_scene.gltf(filepath=chemin, use_selection=True, export_format='GLB')
        print("Export OK :", chemin)
    except Exception as e:
        print("Export impossible :", e)

tex.image = images["vert"]
