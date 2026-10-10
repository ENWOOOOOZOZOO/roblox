"""Power a City : batiments producteurs d'energie (style low-poly Roblox), generes dans Blender.

Utilisation : Blender > onglet "Scripting" > Open (ce fichier) > Run Script.
Sortie : dossier "poweracity_modeles" de ton dossier utilisateur, un .fbx par mesh (+ .glb).

Chaque batiment tient sur 1 case de 5 m (512 cm). Le pivot de chaque mesh est au point (0, 0, 0) :
  Eolienne_Mat       : socle + mat + nacelle. Pivot au sol, au centre.
  Eolienne_Rotor     : moyeu + 3 pales. Pivot au centre du moyeu (pour le faire tourner).
                       A placer a X = +265 cm, Z = +1310 cm par rapport a Eolienne_Mat.
  Panneau_Solaire    : pied + panneau incline. Pivot au sol, au centre.
  Plante_Bio         : petite centrale biomasse (batiment, silo, cheminee, cuve). Pivot au sol.
  Case_Sol           : dalle d'herbe de 512 x 512 cm (une case de la grille), dessus a Z = 0.
Texture "studs" facon Roblox (fin contour en carre arrondi) sur le sol, le pied du panneau et la plante
bio : 1 case = 6 studs. L'eolienne est lisse (gris uni + fenetres carrees), comme dans le jeu.
Les textures sont dans les .fbx (et aussi en .png dans le dossier "textures").
Dans UEFN : importe les .fbx, puis Collision Complexity = "Use Complex Collision As Simple".
"""
import bpy
import bmesh
import math
import os
import numpy as np
from mathutils import Vector, Matrix

SORTIE = os.environ.get("POWERACITY_SORTIE", os.path.join(os.path.expanduser("~"), "poweracity_modeles"))
APERCU = os.environ.get("POWERACITY_APERCU", "")   # chemin d'une image d'apercu (optionnel)
TEXTURES = os.path.join(SORTIE, "textures")

# Texture "studs" facon Roblox : 1 case de la grille (512 cm) = 6 studs, donc 1 stud = 85 cm
# (meme taille par rapport aux batiments que dans le jeu Roblox).
STUD = 5.12 / 6
STUDS_PAR_TEXTURE = 2         # la texture des batiments couvre 2 x 2 studs
PX_STUD = 128                 # resolution : pixels par stud
# Les studs vont sur le sol, le pied du panneau et la plante bio (l'eolienne reste lisse).
# Mets False pour enlever les studs de tous les batiments.
STUDS_SUR_BATIMENTS = True

# ---------------------------------------------------------------------------
#  OUTILS
# ---------------------------------------------------------------------------
MATS = {}


def motif_studs(n, px, aleatoire=False):
    """Facteur de luminosite (n*px x n*px) : sur chaque stud, un carre aux coins arrondis grave dans la
    surface (comme la texture du jeu Roblox), eclaire d'en haut a gauche. Pas de quadrillage entre les studs."""
    t = (np.arange(px) + 0.5) / px - 0.5
    x, y = np.meshgrid(t, t)
    demi, coin, w = 0.24, 0.11, 0.028
    qx, qy = np.abs(x) - (demi - coin), np.abs(y) - (demi - coin)
    d = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - coin
    sillon = np.exp(-(d / w) ** 2)
    h = -sillon
    gy, gx = np.gradient(h)
    k = px / 10.0
    nrm = np.dstack((-gx * k, -gy * k, np.ones_like(h)))
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    lum = np.array([-1.0, -1.0, 1.4])
    lum /= np.linalg.norm(lum)
    ombre = (nrm @ lum) / lum[2]
    # texture simple : un fin contour plus sombre, a peine en relief
    f = np.clip(1 + 0.15 * (ombre - 1), 0.85, 1.15) * (1 - 0.22 * sillon)
    tuile = np.tile(f, (n, n))
    if aleatoire:
        # taches plus foncees : des groupes de studs colles (motif fixe qui se raccorde sans couture)
        rng = np.random.default_rng(11)
        tache = rng.random((n, n)) < 0.10
        for _ in range(2):
            voisins = (np.roll(tache, 1, 0) | np.roll(tache, -1, 0) | np.roll(tache, 1, 1) | np.roll(tache, -1, 1))
            tache = tache | (voisins & (rng.random((n, n)) < 0.4))
        teinte = np.where(tache, 0.80, 1.0)
        tuile *= np.kron(teinte, np.ones((px, px)))
    return tuile


def vers_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def texture_studs(nom, couleur, n=STUDS_PAR_TEXTURE, px=PX_STUD, aleatoire=False):
    f = motif_studs(n, px, aleatoire)
    rgb = np.dstack([vers_srgb(couleur[i] * f) for i in range(3)])
    rgba = np.dstack((rgb, np.ones_like(f)))
    taille = n * px
    img = bpy.data.images.new("T_" + nom, taille, taille, alpha=False)
    img.pixels.foreach_set(rgba[::-1].astype(np.float32).ravel())
    os.makedirs(TEXTURES, exist_ok=True)
    img.filepath_raw = os.path.join(TEXTURES, "T_" + nom + ".png")
    img.file_format = 'PNG'
    img.save()
    return img


def matiere(nom, couleur, metal=0.0, rugo=0.6, emission=0.0, studs=None, n=STUDS_PAR_TEXTURE,
            aleatoire=False):
    if nom in MATS:
        return MATS[nom]
    if studs is None:
        studs = STUDS_SUR_BATIMENTS
    m = bpy.data.materials.new(nom)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*couleur, 1.0)
    m["studs"] = n if studs else 0          # taille de la texture en studs (pour les UV)
    if studs:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = texture_studs(nom, couleur, n, PX_STUD, aleatoire)
        tex.interpolation = 'Linear'
        nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
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


def uv_monde(o):
    """UV calculees a partir de la position dans le monde (projection par face), pour que les studs
    gardent la meme taille partout et tombent pile sur la grille de 512 cm."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        mat = o.data.materials[f.material_index] if o.data.materials else None
        n_studs = (mat.get("studs", 0) if mat else 0) or STUDS_PAR_TEXTURE
        ech = 1.0 / (n_studs * STUD)
        nx, ny, nz = (abs(c) for c in f.normal)
        for l in f.loops:
            co = l.vert.co
            if nz >= nx and nz >= ny:
                l[uv].uv = (co.x * ech, co.y * ech)
            elif nx >= ny:
                l[uv].uv = (co.y * ech, co.z * ech)
            else:
                l[uv].uv = (co.x * ech, co.z * ech)
    bm.to_mesh(o.data)
    bm.free()


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
    uv_monde(o)
    return o


bpy.ops.wm.read_factory_settings(use_empty=True)

# ---------------------------------------------------------------------------
#  COULEURS (facon Roblox : couleurs franches, peu de details)
# ---------------------------------------------------------------------------
GRIS_MAT = matiere("Gris_Mat", (0.58, 0.62, 0.68), metal=0.2, rugo=0.45)
GRIS_FONCE = matiere("Gris_Fonce", (0.20, 0.22, 0.26), rugo=0.7)
BETON = matiere("Beton", (0.55, 0.55, 0.58), rugo=0.9)
MUR_BIO = matiere("Mur_Bio", (0.38, 0.38, 0.44), rugo=0.8)
TOIT_BIO = matiere("Toit_Bio", (0.25, 0.25, 0.30), rugo=0.8)
VERT_BIO = matiere("Vert_Bio", (0.15, 0.55, 0.20), rugo=0.5)
ORANGE = matiere("Orange_Porte", (0.85, 0.40, 0.10), rugo=0.6)
VERT_LUM = matiere("Vert_Lumiere", (0.30, 1.0, 0.30), emission=3.0, studs=False)
# sol des cases : herbe Roblox avec studs, 1 texture = 1 case de 512 cm (6 x 6 studs)
SOL = matiere("Sol_Herbe", (0.20, 0.72, 0.03), rugo=0.9, studs=True, n=6, aleatoire=True)


# ---------------------------------------------------------------------------
#  EOLIENNE (tout en blocs, facon Roblox)
# ---------------------------------------------------------------------------
H_SOCLE = 0.5
H_MAT = 12.0
L_MAT = 1.2                          # le mat est un pave carre de 1,2 m de cote
H_NAC = 1.2                          # nacelle : pave de 3,4 x 1,2 x 1,2 m pose sur le mat
L_NAC = 3.4
X_NAC = 0.5                          # la nacelle depasse vers l'avant (+X), cote rotor
Z_NACELLE = H_SOCLE + H_MAT + H_NAC / 2
X_MOYEU = X_NAC + L_NAC / 2 + 0.45   # centre du moyeu (pivot du rotor)
# l'eolienne est lisse (gris uni + fenetres carrees), comme dans le jeu
GRIS_EOL = matiere("Gris_Eolienne", (0.55, 0.58, 0.66), metal=0.1, rugo=0.55, studs=False)
GRIS_SOCLE = matiere("Gris_Socle", (0.62, 0.64, 0.70), rugo=0.6, studs=False)
GRIS_FENETRE = matiere("Gris_Fenetre", (0.34, 0.36, 0.43), rugo=0.7, studs=False)

# orientation du coupeur (cone a 4 cotes) pour creuser vers l'interieur de chaque face
ORIENT = {(1, 0, 0): (0, -90, 0), (-1, 0, 0): (0, 90, 0), (0, 1, 0): (90, 0, 0),
          (0, -1, 0): (-90, 0, 0), (0, 0, 1): (180, 0, 0)}


def fenetre(centre, normale, taille, prof):
    """Coupeur pour une fenetre carree creusee, aux bords en biais (comme dans le jeu)."""
    marge = 0.1
    longueur = prof + marge
    n = Vector(normale)
    c = Vector(centre) + n * (marge - prof) / 2
    r = taille * 0.7071 * (1 + 0.15 * marge / longueur)
    o = cylindre(r, r * 0.55, longueur, c, GRIS_FENETRE, cotes=4, rot=(0, 0, math.radians(45)))
    o.rotation_euler = tuple(math.radians(v) for v in ORIENT[normale])
    return finir(o, GRIS_FENETRE)


def decouper(obj, coupeurs):
    """Creuse obj avec les coupeurs (boolean difference), puis supprime les coupeurs."""
    c = fusion(coupeurs, "Coupeurs")
    mod = obj.modifiers.new("trous", 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = c
    mod.solver = 'EXACT'
    mod.material_mode = 'TRANSFER'      # le fond des fenetres prend la couleur du coupeur
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(c, do_unlink=True)


def chanfrein(o, largeur):
    mod = o.modifiers.new("chanfrein", 'BEVEL')
    mod.width = largeur
    mod.segments = 1
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return o


def eolienne():
    parts = [boite((2.2, 2.2, H_SOCLE), (0, 0, H_SOCLE / 2), GRIS_SOCLE)]
    # mat : pave droit, une colonne de fenetres creusees sur chaque face
    mat = boite((L_MAT, L_MAT, H_MAT), (0, 0, H_SOCLE + H_MAT / 2), GRIS_EOL)
    coupeurs = []
    z = H_SOCLE + 0.9
    while z < H_SOCLE + H_MAT - 0.6:
        for nrm in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)):
            coupeurs.append(fenetre(Vector(nrm) * L_MAT / 2 + Vector((0, 0, z)), nrm, 0.5, 0.14))
        z += 1.05
    decouper(mat, coupeurs)
    parts.append(mat)
    # nacelle : long pave sur le dessus du mat, avec des fenetres sur les cotes et le dessus
    nac = boite((L_NAC, L_MAT, H_NAC), (X_NAC, 0, Z_NACELLE), GRIS_EOL)
    coupeurs = []
    for x in (-0.7, 0.45, 1.6):
        for nrm in ((0, 1, 0), (0, -1, 0)):
            coupeurs.append(fenetre((x, nrm[1] * L_MAT / 2, Z_NACELLE), nrm, 0.5, 0.12))
        coupeurs.append(fenetre((x, 0, Z_NACELLE + H_NAC / 2), (0, 0, 1), 0.5, 0.12))
    coupeurs.append(fenetre((X_NAC - L_NAC / 2, 0, Z_NACELLE), (-1, 0, 0), 0.5, 0.12))
    decouper(nac, coupeurs)
    parts.append(nac)
    mat = fusion(parts, "Eolienne_Mat")

    # rotor : construit autour de (0, 0, 0) = centre du moyeu, pales dans le plan YZ
    moyeu = chanfrein(boite((0.9, 1.1, 1.1), (0, 0, 0), GRIS_EOL), 0.18)
    rot = [moyeu]
    for k in range(3):
        a = math.radians(120 * k)
        long = 7.5
        # pale pointue : section en losange aplati, un peu vrillee
        p = cylindre(0.4, 0.02, long, (0, 0, 0), GRIS_EOL, cotes=4)
        p.scale = (0.3, 1.0, 1.0)
        finir(p, GRIS_EOL)
        p.rotation_euler = (0, 0, math.radians(25))
        finir(p, GRIS_EOL)
        p.location = (0.05, -math.sin(a) * (long / 2 + 0.35), math.cos(a) * (long / 2 + 0.35))
        p.rotation_euler = (a, 0, 0)
        finir(p, GRIS_EOL)
        bpy.ops.object.transform_apply(location=True)
        rot.append(p)
    rotor = fusion(rot, "Eolienne_Rotor")
    return mat, rotor


# ---------------------------------------------------------------------------
#  PANNEAU SOLAIRE
# ---------------------------------------------------------------------------
BLEU_VIF = matiere("Bleu_Vif", (0.01, 0.06, 0.80), metal=0.0, rugo=0.5, studs=False)
LAVANDE = matiere("Lavande", (0.80, 0.80, 1.0), metal=0.2, rugo=0.4, studs=False)
ACIER = matiere("Acier_Fonce", (0.30, 0.32, 0.38), metal=0.2, rugo=0.6)


def tube(points, rayons, mat, nom, cotes=8, alea=0.0, graine=0):
    """Tube qui suit une ligne de points (rayon different a chaque point), bords un peu irreguliers."""
    rng = np.random.default_rng(graine)
    pts = [Vector(p) for p in points]
    bm = bmesh.new()
    anneaux = []
    for i, (p, r) in enumerate(zip(pts, rayons)):
        tg = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        haut = Vector((1, 0, 0)) if abs(tg.z) < 0.9 else Vector((0, 1, 0))
        u = tg.cross(haut).normalized()
        v = tg.cross(u).normalized()
        anneau = []
        for k in range(cotes):
            ang = 2 * math.pi * (k + 0.5) / cotes
            rr = r * (1 + rng.uniform(-alea, alea))
            anneau.append(bm.verts.new(p + (u * math.cos(ang) + v * math.sin(ang)) * rr))
        anneaux.append(anneau)
    for i in range(len(anneaux) - 1):
        for k in range(cotes):
            bm.faces.new((anneaux[i][k], anneaux[i][(k + 1) % cotes],
                          anneaux[i + 1][(k + 1) % cotes], anneaux[i + 1][k]))
    bm.faces.new(list(reversed(anneaux[0])))
    bm.faces.new(anneaux[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(nom)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(nom, me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(mat)
    return o


Z_PANNEAU = 3.7


def panneau_solaire():
    pied = []
    # base large et irreguliere, puis un tronc qui monte en se courbant (comme un arbre)
    pied.append(tube([(0, 0, 0), (0, 0, 0.3), (0, 0, 0.6), (0, 0, 0.95), (0.05, 0, 1.3)],
                     [1.35, 1.3, 1.0, 0.62, 0.45], ACIER, "Base", cotes=10, alea=0.12, graine=3))
    pied.append(tube([(0.05, 0, 1.2), (0.25, 0.05, 2.0), (0.5, 0.1, 2.7), (0.45, 0.05, Z_PANNEAU - 0.35)],
                     [0.45, 0.34, 0.27, 0.25], ACIER, "Tronc", cotes=8, alea=0.06, graine=4))
    # deux bras fins qui partent du tronc vers les bouts du panneau
    pied.append(tube([(0.3, 0.05, 2.2), (-0.8, 0.0, 2.9), (-1.9, 0.0, Z_PANNEAU - 0.1)],
                     [0.11, 0.09, 0.07], ACIER, "Bras1", cotes=6))
    pied.append(tube([(0.45, 0.08, 2.4), (1.5, 0.0, 3.1), (2.6, 0.0, Z_PANNEAU - 0.1)],
                     [0.11, 0.09, 0.07], ACIER, "Bras2", cotes=6))
    pied.append(boite((0.5, 0.5, 0.15), (0.45, 0, Z_PANNEAU - 0.4), ACIER))

    # plaque longue : 8 x 4 cellules en 2 moities, inclinee sur son grand cote
    L, P, EP, joint, milieu = 6.4, 3.4, 0.12, 0.05, 0.12
    pan = [boite((L, P, EP), (0, 0, 0), LAVANDE)]
    cols, lignes = 4, 4
    for moitie in (0, 1):
        x0 = -L / 2 if moitie == 0 else milieu / 2
        lm = L / 2 - milieu / 2
        lc = (lm - (cols + 0.5) * joint) / cols
        pc = (P - (lignes + 1) * joint) / lignes
        for c in range(cols):
            for l in range(lignes):
                x = x0 + (joint if moitie == 0 else joint / 2) + lc / 2 + c * (lc + joint)
                y = -P / 2 + joint + pc / 2 + l * (pc + joint)
                pan.append(boite((lc, pc, 0.04), (x, y, EP / 2 + 0.005), BLEU_VIF))
    plaque = fusion(pan, "Plaque")
    plaque.rotation_euler = (math.radians(35), 0, 0)   # incline vers -Y
    plaque.location = (0.4, 0, Z_PANNEAU)
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
#  CASE DE SOL (dalle de 512 x 512 cm pour la grille 6x6)
# ---------------------------------------------------------------------------
def case_sol():
    d = boite((5.12, 5.12, 0.2), (0, 0, -0.1), SOL)   # le dessus est a Z = 0
    return fusion([d], "Case_Sol")


# ---------------------------------------------------------------------------
#  APERCU (rendu des 3 batiments cote a cote)
# ---------------------------------------------------------------------------
def apercu(objs, chemin):
    sc = bpy.context.scene
    # copies temporaires placees cote a cote (les originaux restent a (0, 0, 0) pour l'export)
    places = {"Eolienne_Mat": (0, 0, 0), "Eolienne_Rotor": (X_MOYEU, 0, Z_NACELLE),
              "Panneau_Solaire": (3, 8, 0), "Plante_Bio": (-6, -7, 0), "Case_Sol": (0, 0, -5)}
    copies = []
    for o in objs:
        c = o.copy()
        c.data = o.data.copy()
        sc.collection.objects.link(c)
        c.location = places[o.name]
        copies.append(c)
        o.hide_render = True
    bpy.ops.mesh.primitive_plane_add(size=5.12 * 12, location=(0, 0, 0))
    sol = finir(bpy.context.active_object, SOL)
    sol.name = "Plane_Sol"
    uv_monde(sol)

    w = bpy.data.worlds.new("Ciel")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.85, 0.88, 0.92, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.55
    sc.world = w
    bpy.ops.object.light_add(type='SUN', rotation=(math.radians(40), math.radians(15), math.radians(-30)))
    bpy.context.active_object.data.energy = 3.0

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
    sol = case_sol()
    objs = [mat, rotor, solaire, bio, sol]

    os.makedirs(SORTIE, exist_ok=True)
    for o in objs:
        tri = sum(len(f.vertices) - 2 for f in o.data.polygons)
        print("MESH", o.name, tri, "triangles")
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.export_scene.fbx(filepath=os.path.join(SORTIE, o.name + ".fbx"), use_selection=True,
                                 object_types={'MESH'}, mesh_smooth_type='FACE',
                                 path_mode='COPY', embed_textures=True)
        bpy.ops.export_scene.gltf(filepath=os.path.join(SORTIE, o.name + ".glb"), use_selection=True,
                                  export_format='GLB')
    print("Export OK :", SORTIE)
    if APERCU:
        apercu(objs, APERCU)
        if os.environ.get("POWERACITY_VUES"):
            d = os.path.dirname(APERCU)
            # meme angle que les captures du jeu (pour comparer)
            vue(objs, os.path.join(d, "vue_eolienne.png"),
                {"Eolienne_Mat": (0, 0, 0)}, (9, -9, 15.5), (1.0, 0, 11.0), 30)
            rotor = bpy.data.objects["Eolienne_Rotor"]
            c = rotor.copy(); c.data = rotor.data.copy(); c.name = "Vue_Rotor"
            bpy.context.scene.collection.objects.link(c)
            c.location = (X_MOYEU, 0, Z_NACELLE)
            c.hide_render = False
            bpy.context.scene.render.filepath = os.path.join(d, "vue_eolienne.png")
            bpy.ops.render.render(write_still=True)
            bpy.data.objects.remove(c, do_unlink=True)
            vue(objs, os.path.join(d, "vue_solaire.png"),
                {"Panneau_Solaire": (0, 0, 0)}, (-8, -6, 6), (0.5, 0, 2.6), 35)


main()
