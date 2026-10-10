"""Power a City : batiments producteurs d'energie (style low-poly Roblox), generes dans Blender.

Utilisation : Blender > onglet "Scripting" > Open (ce fichier) > Run Script.
Sortie : dossier "poweracity_modeles" de ton dossier utilisateur, un .fbx par mesh (+ .glb).

Chaque batiment tient sur 1 case de 5 m (512 cm). Le pivot de chaque mesh est au point (0, 0, 0) :
  Eolienne_Mat       : socle + mat + nacelle. Pivot au sol, au centre.
  Eolienne_Rotor     : moyeu + 3 pales. Pivot au centre du moyeu (pour le faire tourner).
                       A placer a X = +75 cm, Z = +1395 cm par rapport a Eolienne_Mat.
  Panneau_Solaire    : pied + panneau incline. Pivot au sol, au centre.
  Plante_Bio         : petite centrale biomasse (batiment, silo, cheminee, cuve). Pivot au sol.
Dans UEFN : importe les .fbx, puis Collision Complexity = "Use Complex Collision As Simple".
"""
import bpy
import math
import os
from mathutils import Vector, Matrix

SORTIE = os.environ.get("POWERACITY_SORTIE", os.path.join(os.path.expanduser("~"), "poweracity_modeles"))
APERCU = os.environ.get("POWERACITY_APERCU", "")   # chemin d'une image d'apercu (optionnel)

# ---------------------------------------------------------------------------
#  OUTILS
# ---------------------------------------------------------------------------
MATS = {}


def matiere(nom, couleur, metal=0.0, rugo=0.6, emission=0.0):
    if nom in MATS:
        return MATS[nom]
    m = bpy.data.materials.new(nom)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*couleur, 1.0)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rugo
    if emission:
        b.inputs["Emission Color"].default_value = (*couleur, 1.0)
        b.inputs["Emission Strength"].default_value = emission
    m.diffuse_color = (*couleur, 1.0)
    MATS[nom] = m
    return m


def finir(o, mat):
    o.data.materials.clear()
    o.data.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return o


def boite(taille, pos, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos, rotation=rot)
    o = bpy.context.active_object
    o.scale = taille
    return finir(o, mat)


def cylindre(r1, r2, haut, pos, mat, cotes=16, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=cotes, radius1=r1, radius2=r2, depth=haut,
                                    location=pos, rotation=rot)
    return finir(bpy.context.active_object, mat)


def sphere(r, pos, mat, ech=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=r, location=pos)
    o = bpy.context.active_object
    o.scale = ech
    return finir(o, mat)


def fusion(objs, nom):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = nom
    o.data.name = nom
    # pivot au point (0, 0, 0) du monde
    bpy.context.scene.cursor.location = (0, 0, 0)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    return o


bpy.ops.wm.read_factory_settings(use_empty=True)

# ---------------------------------------------------------------------------
#  COULEURS (facon Roblox : couleurs franches, peu de details)
# ---------------------------------------------------------------------------
GRIS_CLAIR = matiere("Gris_Clair", (0.72, 0.75, 0.80), rugo=0.5)
GRIS_MAT = matiere("Gris_Mat", (0.58, 0.62, 0.68), metal=0.2, rugo=0.45)
GRIS_FONCE = matiere("Gris_Fonce", (0.20, 0.22, 0.26), rugo=0.7)
BLANC = matiere("Blanc", (0.90, 0.91, 0.94), rugo=0.4)
BLEU_CELL = matiere("Bleu_Cellule", (0.03, 0.10, 0.75), metal=0.3, rugo=0.25)
CADRE = matiere("Cadre_Panneau", (0.78, 0.80, 0.95), metal=0.4, rugo=0.35)
BETON = matiere("Beton", (0.55, 0.55, 0.58), rugo=0.9)
MUR_BIO = matiere("Mur_Bio", (0.38, 0.38, 0.44), rugo=0.8)
TOIT_BIO = matiere("Toit_Bio", (0.25, 0.25, 0.30), rugo=0.8)
VERT_BIO = matiere("Vert_Bio", (0.15, 0.55, 0.20), rugo=0.5)
ORANGE = matiere("Orange_Porte", (0.85, 0.40, 0.10), rugo=0.6)
VERT_LUM = matiere("Vert_Lumiere", (0.30, 1.0, 0.30), emission=3.0)


# ---------------------------------------------------------------------------
#  EOLIENNE
# ---------------------------------------------------------------------------
H_SOCLE = 0.6
H_MAT = 13.0
R_BAS, R_HAUT = 1.0, 0.72           # rayon (au coin) du mat carre en bas et en haut
Z_NACELLE = H_SOCLE + H_MAT + 0.35
X_MOYEU = 0.75                       # le rotor est devant la nacelle, cote +X
GRIS_EOL = matiere("Gris_Eolienne", (0.55, 0.58, 0.66), metal=0.1, rugo=0.55)
GRIS_SOCLE = matiere("Gris_Socle", (0.66, 0.68, 0.74), rugo=0.6)


def decouper(obj, coupeurs):
    """Perce obj avec les coupeurs (boolean difference), puis supprime les coupeurs."""
    c = fusion(coupeurs, "Coupeurs")
    mod = obj.modifiers.new("trous", 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = c
    mod.solver = 'EXACT'
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(c, do_unlink=True)


def eolienne():
    parts = []
    parts.append(boite((2.0, 2.0, H_SOCLE), (0, 0, H_SOCLE / 2), GRIS_SOCLE))
    # mat carre qui s'affine (cone a 4 cotes tourne de 45 degres)
    mat = cylindre(R_BAS, R_HAUT, H_MAT, (0, 0, H_SOCLE + H_MAT / 2), GRIS_EOL, cotes=4,
                   rot=(0, 0, math.radians(45)))
    # treillis : 2 colonnes de trous carres qui traversent le mat de part en part, sur X et sur Y
    coupeurs = []
    nb = 16
    for i in range(nb):
        t = (i + 0.7) / (nb + 0.2)
        z = H_SOCLE + t * H_MAT
        demi = (R_BAS + (R_HAUT - R_BAS) * t) * math.cos(math.radians(45))
        cote = demi * 0.5
        for col in (-1, 1):
            dec = col * demi * 0.45
            coupeurs.append(boite((4.0, cote, cote), (0, dec, z), GRIS_EOL))
            coupeurs.append(boite((cote, 4.0, cote), (dec, 0, z), GRIS_EOL))
    decouper(mat, coupeurs)
    parts.append(mat)
    # coeur sombre a l'interieur : les trous paraissent sombres au lieu de laisser voir le ciel
    parts.append(cylindre(R_BAS * 0.62, R_HAUT * 0.62, H_MAT - 0.2, (0, 0, H_SOCLE + H_MAT / 2), GRIS_FONCE,
                          cotes=4, rot=(0, 0, math.radians(45))))
    # nacelle (petite) + moyeu arriere
    parts.append(boite((1.2, 0.6, 0.6), (-0.1, 0, Z_NACELLE), GRIS_EOL))
    mat = fusion(parts, "Eolienne_Mat")

    # rotor : construit autour de (0, 0, 0) = centre du moyeu, pales dans le plan YZ
    rot = []
    rot.append(sphere(0.32, (0.05, 0, 0), GRIS_EOL, ech=(1.3, 1, 1)))
    for k in range(3):
        a = math.radians(120 * k)
        long = 8.0
        # une pale = cone plat a 4 cotes, large pres du moyeu, fine au bout, un peu vrillee
        p = cylindre(0.26, 0.04, long, (0, 0, 0), GRIS_EOL, cotes=4)
        p.scale = (0.18, 1.0, 1.0)
        p.rotation_euler = (0, 0, math.radians(20))
        finir(p, GRIS_EOL)
        p.location = (0, -math.sin(a) * (long / 2 + 0.2), math.cos(a) * (long / 2 + 0.2))
        p.rotation_euler = (a, 0, 0)
        finir(p, GRIS_EOL)
        bpy.ops.object.transform_apply(location=True)
        rot.append(p)
    rotor = fusion(rot, "Eolienne_Rotor")
    return mat, rotor


# ---------------------------------------------------------------------------
#  PANNEAU SOLAIRE
# ---------------------------------------------------------------------------
BLEU_VIF = matiere("Bleu_Vif", (0.01, 0.06, 0.80), metal=0.0, rugo=0.5)
LAVANDE = matiere("Lavande", (0.80, 0.80, 1.0), metal=0.2, rugo=0.4)


ACIER = matiere("Acier_Fonce", (0.33, 0.35, 0.40), metal=0.5, rugo=0.45)


def panneau_solaire():
    pied = []
    # socle octogonal evase + colonne + tete qui s'elargit
    pied.append(cylindre(1.25, 0.85, 0.35, (0, 0, 0.175), ACIER, cotes=8))
    pied.append(cylindre(0.85, 0.30, 0.45, (0, 0, 0.575), ACIER, cotes=8))
    pied.append(cylindre(0.24, 0.18, 1.9, (0, 0, 1.75), ACIER, cotes=8))
    pied.append(cylindre(0.18, 0.42, 0.45, (0, 0, 2.9), ACIER, cotes=8))
    pied.append(boite((0.9, 0.9, 0.15), (0, 0, 3.15), ACIER))

    # plaque presque a plat (face vers le haut), 2 moities de 4 x 2 cellules
    L, P, EP, joint = 4.4, 4.4, 0.14, 0.06
    pan = [boite((L, P, EP), (0, 0, 0), LAVANDE)]
    cols = 4
    # moitie basse : 4 rangees, moitie haute : 3 rangees (comme dans le jeu)
    for moitie, lignes in ((0, 4), (1, 3)):
        y0 = -P / 2 if moitie == 0 else 0.0
        pm = P / 2
        lc = (L - (cols + 1) * joint) / cols
        pc = (pm - (lignes + 1) * joint) / lignes
        for c in range(cols):
            for l in range(lignes):
                x = -L / 2 + joint + lc / 2 + c * (lc + joint)
                y = y0 + joint + pc / 2 + l * (pc + joint)
                pan.append(boite((lc, pc, 0.04), (x, y, EP / 2 + 0.005), BLEU_VIF))
    plaque = fusion(pan, "Plaque")
    plaque.rotation_euler = (math.radians(25), 0, 0)   # incline vers -Y
    plaque.location = (0, 0, 3.6)
    bpy.ops.object.select_all(action='DESELECT')
    plaque.select_set(True)
    bpy.context.view_layer.objects.active = plaque
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return fusion(pied + [plaque], "Panneau_Solaire")


# ---------------------------------------------------------------------------
#  PETITE PLANTE BIOLOGIQUE
# ---------------------------------------------------------------------------
def plante_bio():
    p = []
    p.append(boite((4.4, 4.4, 0.2), (0, 0, 0.1), BETON))
    # batiment principal
    p.append(boite((2.6, 2.2, 2.0), (-0.6, -0.6, 1.2), MUR_BIO))
    p.append(boite((2.8, 2.4, 0.2), (-0.6, -0.6, 2.3), TOIT_BIO))
    p.append(boite((0.8, 0.05, 1.3), (-0.6, -1.72, 0.85), ORANGE))     # porte
    for x in (-1.5, 0.3):
        p.append(boite((0.5, 0.05, 0.4), (x, -1.72, 1.55), VERT_LUM))  # fenetres
    # silo / digesteur avec un dome
    p.append(cylindre(0.85, 0.85, 2.6, (1.1, 1.1, 1.5), VERT_BIO, cotes=16))
    p.append(sphere(0.85, (1.1, 1.1, 2.8), VERT_BIO, ech=(1, 1, 0.55)))
    for z in (0.7, 1.6, 2.5):
        p.append(cylindre(0.88, 0.88, 0.1, (1.1, 1.1, z), GRIS_FONCE, cotes=16))
    # cheminee
    p.append(cylindre(0.3, 0.24, 4.6, (-1.3, 0.5, 2.5), GRIS_MAT, cotes=12))
    p.append(cylindre(0.32, 0.32, 0.25, (-1.3, 0.5, 4.75), GRIS_FONCE, cotes=12))
    # cuve couchee + tuyau vers le silo
    p.append(cylindre(0.45, 0.45, 1.6, (1.2, -1.2, 0.65), GRIS_FONCE, cotes=12,
                      rot=(0, math.radians(90), 0)))
    p.append(cylindre(0.1, 0.1, 1.9, (1.2, -0.1, 0.9), GRIS_MAT, cotes=8,
                      rot=(math.radians(90), 0, 0)))
    return fusion(p, "Plante_Bio")


# ---------------------------------------------------------------------------
#  APERCU (rendu des 3 batiments cote a cote)
# ---------------------------------------------------------------------------
def apercu(objs, chemin):
    sc = bpy.context.scene
    # copies temporaires placees cote a cote (les originaux restent a (0, 0, 0) pour l'export)
    places = {"Eolienne_Mat": (0, 0, 0), "Eolienne_Rotor": (X_MOYEU, 0, Z_NACELLE),
              "Panneau_Solaire": (3, 8, 0), "Plante_Bio": (-6, -7, 0)}
    copies = []
    for o in objs:
        c = o.copy()
        c.data = o.data.copy()
        sc.collection.objects.link(c)
        c.location = places[o.name]
        copies.append(c)
        o.hide_render = True
    sol_mat = matiere("Herbe", (0.12, 0.45, 0.03), rugo=0.9)
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
    finir(bpy.context.active_object, sol_mat)

    w = bpy.data.worlds.new("Ciel")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.85, 0.88, 0.92, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
    sc.world = w
    bpy.ops.object.light_add(type='SUN', rotation=(math.radians(40), math.radians(15), math.radians(-30)))
    bpy.context.active_object.data.energy = 2.5

    bpy.ops.object.camera_add(location=(26, -24, 7))
    cam = bpy.context.active_object
    cible = Vector((0, 0, 7.0))
    cam.rotation_euler = (cible - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 35
    sc.camera = cam

    sc.view_settings.view_transform = 'Standard'
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 48
    sc.cycles.device = 'CPU'
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.render.filepath = chemin
    bpy.ops.render.render(write_still=True)
    print("Apercu :", chemin)


# ---------------------------------------------------------------------------
def vue(objs, chemin, places, cam_pos, cible, lens):
    sc = bpy.context.scene
    for o in list(sc.objects):
        if o.name.startswith("Vue_"):
            bpy.data.objects.remove(o, do_unlink=True)
    for o in sc.objects:
        if o.type == 'MESH' and not o.name.startswith("Plane"):
            o.hide_render = True
    for o in objs:
        if o.name in places:
            c = o.copy()
            c.data = o.data.copy()
            c.name = "Vue_" + o.name
            sc.collection.objects.link(c)
            c.location = places[o.name]
            c.rotation_euler = (0, 0, math.radians(-50))
            c.hide_render = False
    cam = sc.camera
    cam.location = cam_pos
    cam.rotation_euler = (Vector(cible) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    sc.render.resolution_x, sc.render.resolution_y = 800, 800
    sc.render.filepath = chemin
    bpy.ops.render.render(write_still=True)


def main():
    mat, rotor = eolienne()
    solaire = panneau_solaire()
    bio = plante_bio()
    objs = [mat, rotor, solaire, bio]

    os.makedirs(SORTIE, exist_ok=True)
    for o in objs:
        tri = sum(len(f.vertices) - 2 for f in o.data.polygons)
        print("MESH", o.name, tri, "triangles")
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.export_scene.fbx(filepath=os.path.join(SORTIE, o.name + ".fbx"), use_selection=True,
                                 object_types={'MESH'}, mesh_smooth_type='FACE')
        bpy.ops.export_scene.gltf(filepath=os.path.join(SORTIE, o.name + ".glb"), use_selection=True,
                                  export_format='GLB')
    print("Export OK :", SORTIE)
    if APERCU:
        apercu(objs, APERCU)
        if os.environ.get("POWERACITY_VUES"):
            d = os.path.dirname(APERCU)
            # meme angle que les captures du jeu (pour comparer)
            vue(objs, os.path.join(d, "vue_eolienne.png"),
                {"Eolienne_Mat": (0, 0, 0)}, (11, -11, 13), (0, 0, 8), 28)
            rotor = bpy.data.objects["Eolienne_Rotor"]
            c = rotor.copy(); c.data = rotor.data.copy(); c.name = "Vue_Rotor"
            bpy.context.scene.collection.objects.link(c)
            m = Matrix.Rotation(math.radians(-50), 4, 'Z')
            c.location = m @ Vector((X_MOYEU, 0, Z_NACELLE))
            c.rotation_euler = (0, 0, math.radians(-50))
            c.hide_render = False
            bpy.context.scene.render.filepath = os.path.join(d, "vue_eolienne.png")
            bpy.ops.render.render(write_still=True)
            bpy.data.objects.remove(c, do_unlink=True)
            vue(objs, os.path.join(d, "vue_solaire.png"),
                {"Panneau_Solaire": (0, 0, 0)}, (0, -9, 4.5), (0, 0, 2.6), 35)


main()
