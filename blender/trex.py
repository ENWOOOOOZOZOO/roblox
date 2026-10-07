"""T-Rex mignon et arrondi (low poly lisse) pour Blender.

Utilisation : Blender > onglet "Scripting" > Open (ouvrir ce fichier) > Run Script (triangle).
Le dino regarde vers -Y (vue "Front" = numpad 1). Il mesure environ 5 unites de long.
A la fin, un fichier trex.fbx est exporte dans ton dossier utilisateur.
"""
import bpy
import math
import os

# ---------- outils ----------

def nettoyer():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def matiere(nom, rgb, rugosite=0.55):
    m = bpy.data.materials.new(nom)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1)
    b.inputs["Roughness"].default_value = rugosite
    return m


def lisser(o):
    for p in o.data.polygons:
        p.use_smooth = True


def ellipse(nom, pos, demi, mat, rot=(0, 0, 0)):
    """Ellipsoide : demi = demi-axes (x, y, z)."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=1, location=pos)
    o = bpy.context.active_object
    o.name = nom
    o.scale = demi
    o.rotation_euler = [math.radians(a) for a in rot]
    o.data.materials.append(mat)
    lisser(o)
    return o


def boule(nom, pos, rayon, mat):
    return ellipse(nom, pos, (rayon, rayon, rayon), mat)


def cone(nom, pos, rayon, hauteur, mat, rot=(0, 0, 0), sommets=8, echelle=(1, 1, 1)):
    """Cone dont la pointe est vers +Z (avant rotation)."""
    bpy.ops.mesh.primitive_cone_add(vertices=sommets, radius1=rayon, radius2=0, depth=hauteur, location=pos)
    o = bpy.context.active_object
    o.name = nom
    o.scale = echelle
    o.rotation_euler = [math.radians(a) for a in rot]
    o.data.materials.append(mat)
    lisser(o)
    return o


# rotations utiles pour les cones : (90,0,0) pointe vers -Y, (180,0,0) pointe vers le bas
VERS_AVANT = (90, 0, 0)
VERS_BAS = (180, 0, 0)

# ---------- scene ----------
nettoyer()

VERT = matiere("Vert", (0.25, 0.62, 0.28))
VERT_FONCE = matiere("VertFonce", (0.12, 0.38, 0.17))
CREME = matiere("Creme", (0.95, 0.88, 0.62))
BLANC = matiere("Blanc", (1, 1, 1), 0.3)
NOIR = matiere("Noir", (0.02, 0.02, 0.03), 0.2)
ROUGE = matiere("Rouge", (0.8, 0.12, 0.15))
ROSE = matiere("Rose", (1.0, 0.45, 0.55))
AMBRE = matiere("Ambre", (0.95, 0.6, 0.08), 0.3)

# ----- corps -----
ellipse("Corps", (0, 0, 1.6), (0.9, 1.3, 0.9), VERT)
ellipse("Ventre", (0, -0.2, 1.15), (0.72, 1.15, 0.5), CREME)
ellipse("Poitrail", (0, -1.0, 1.7), (0.65, 0.5, 0.65), VERT)

# ----- queue (chaine d'ellipsoides qui s'amincit) -----
queue = [
    # (nom, y, z, demi_x, demi_y, demi_z, matiere)
    ("Queue1", 1.9, 1.55, 0.65, 0.9, 0.6, VERT),
    ("Queue2", 2.9, 1.40, 0.50, 0.9, 0.45, VERT),
    ("Queue3", 3.8, 1.25, 0.36, 0.8, 0.33, VERT),
    ("Queue4", 4.6, 1.15, 0.24, 0.7, 0.22, VERT),
    ("BoutQueue", 5.2, 1.10, 0.18, 0.3, 0.18, CREME),
]
for n, y, z, sx, sy, sz, m in queue:
    ellipse(n, (0, y, z), (sx, sy, sz), m)

# ----- cou et tete -----
ellipse("Cou", (0, -1.2, 2.3), (0.6, 0.7, 0.6), VERT)
ellipse("Tete", (0, -2.0, 2.7), (0.85, 1.0, 0.65), VERT)
ellipse("Museau", (0, -2.9, 2.55), (0.6, 0.7, 0.4), VERT)
ellipse("Gorge", (0, -1.8, 1.95), (0.7, 0.5, 0.3), VERT)

# machoire du bas, plus basse : la bouche est grande ouverte
ellipse("MachoireMilieu", (0, -2.15, 1.6), (0.55, 0.5, 0.25), VERT)
ellipse("MachoireBas", (0, -2.5, 1.45), (0.6, 0.9, 0.22), VERT)
# interieur de la bouche
ellipse("PaletteRouge", (0, -2.3, 2.12), (0.55, 0.8, 0.1), ROUGE)
ellipse("Langue", (0, -2.5, 1.7), (0.35, 0.7, 0.1), ROSE)

# ----- dents du haut (pointent vers le bas) et du bas (vers le haut) -----
def demi_largeur(y):
    return 0.55 if y < -2.6 else 0.7

for i in range(7):
    y = -3.3 + i * 0.23
    for s in (-1, 1):
        cone("DentHaut", (s * demi_largeur(y), y, 2.1), 0.09, 0.32, BLANC, VERS_BAS)
for x in (-0.3, 0, 0.3):
    cone("DentHautAvant", (x, -3.55, 2.2), 0.09, 0.32, BLANC, VERS_BAS)

for i in range(6):
    y = -3.2 + i * 0.22
    for s in (-1, 1):
        cone("DentBas", (s * (demi_largeur(y) - 0.12), y, 1.8), 0.08, 0.28, BLANC)
for x in (-0.25, 0.25):
    cone("DentBasAvant", (x, -3.35, 1.8), 0.08, 0.28, BLANC)

# ----- yeux -----
for s in (-1, 1):
    ex, ey, ez = s * 0.55, -2.45, 3.1
    boule("Oeil", (ex, ey, ez), 0.2, BLANC)
    boule("Iris", (ex + s * 0.03, ey - 0.10, ez + 0.02), 0.15, AMBRE)
    boule("Pupille", (ex + s * 0.05, ey - 0.16, ez + 0.03), 0.10, NOIR)
    boule("Reflet", (ex + s * 0.06, ey - 0.23, ez + 0.09), 0.04, BLANC)
    boule("Narine", (s * 0.2, -3.46, 2.75), 0.06, NOIR)
    ellipse("Joue", (s * 0.8, -2.4, 2.45), (0.06, 0.18, 0.18), ROSE)

# ----- petits bras avec griffes -----
for s in (-1, 1):
    ellipse("Bras", (s * 0.7, -1.5, 1.3), (0.13, 0.4, 0.13), VERT_FONCE)
    for dx in (-0.06, 0.06):
        cone("GriffeBras", (s * 0.7 + dx, -1.95, 1.3), 0.04, 0.15, CREME, VERS_AVANT)

# ----- pattes -----
for s in (-1, 1):
    x = s * 0.85
    ellipse("Hanche", (x, 0.3, 1.4), (0.5, 0.7, 0.6), VERT_FONCE)
    ellipse("Cuisse", (x, 0.35, 0.85), (0.4, 0.5, 0.6), VERT_FONCE)
    ellipse("Tibia", (x, 0.2, 0.4), (0.25, 0.3, 0.4), VERT)
    ellipse("Pied", (x, -0.2, 0.12), (0.3, 0.6, 0.14), VERT_FONCE)
    for dx in (-0.2, 0, 0.2):
        cone("Griffe", (x + dx, -0.85, 0.1), 0.08, 0.3, CREME, VERS_AVANT)

# ----- plaques sur le dos -----
# (cy, cz, sy, sz) des ellipsoides du corps/queue pour trouver la hauteur du dos
dos = [(0, 1.6, 1.3, 0.9)] + [(y, z, sy, sz) for _, y, z, _, sy, sz, _ in queue[:4]]

def hauteur_dos(y):
    h = None
    for cy, cz, sy, sz in dos:
        t = (y - cy) / sy
        if abs(t) < 1:
            top = cz + sz * math.sqrt(1 - t * t)
            h = top if h is None else max(h, top)
    return h

ys = [-0.9, -0.3, 0.3, 0.9, 1.6, 2.3, 3.0, 3.7, 4.3]
for i, y in enumerate(ys):
    h = hauteur_dos(y)
    if h is None:
        continue
    taille = max(0.14, 0.42 - i * 0.03)
    cone("Plaque", (0, y, h + taille * 0.25), taille * 0.55, taille, VERT_FONCE, sommets=4, echelle=(0.5, 1, 1))

# ---------- export ----------
bpy.ops.object.select_all(action='SELECT')
chemin = os.path.join(os.path.expanduser("~"), "trex.fbx")
try:
    bpy.ops.export_scene.fbx(filepath=chemin, use_selection=True)
    print("Export OK :", chemin)
except Exception as e:
    print("Export impossible (", e, ") - tu peux exporter a la main : File > Export > FBX")
