"""Power a City : batiments producteurs d'energie (style low-poly Roblox), generes dans Blender.

Utilisation : Blender > onglet "Scripting" > Open (ce fichier) > Run Script.
Sortie : dossier "poweracity_modeles" de ton dossier utilisateur, un .fbx par mesh (+ .glb).

Chaque batiment tient sur 1 case de 5 m (512 cm), sauf l'usine electrique, le barrage et les 2 grandes centrales (2 x 2 cases). Le pivot de chaque mesh est au point (0, 0, 0) :
  Eolienne_Mat       : socle + mat + nacelle. Pivot au sol, au centre.
  Eolienne_Rotor     : moyeu + 3 pales. Pivot au centre du moyeu (pour le faire tourner).
                       A placer a X = +265 cm, Z = +1310 cm par rapport a Eolienne_Mat.
  Panneau_Solaire    : pied + panneau incline. Pivot au sol, au centre.
  Usine_Electrique   : 2 x 2 cases. Bloc a 2 cheminees, hangar, annexe, 2 tas. Pivot au centre.
  Ferme_Solaire      : 4 panneaux inclines sur socles + lampadaire. Pivot au centre.
  Centrale_Vapeur    : maison, cheminee a chevrons, generateur, tuyaux. Pivot au centre.
  Plante_Bio         : four, cheminee en briques, tas de charbon. Pivot au centre.
  Usine_Grise        : batiment a toit sombre, 3 cheminees, cuves. Pivot au centre.
  Station_Pompage    : machine bleue, bassin, tuyaux, cuves blanches. Pivot au centre.
  Barrage            : 2 x 2 cases. Plateau de terre, lac, mur de barrage courbe. Pivot au centre.
  Dirigeable         : tete beige qui flotte (centre a 9 m) + cable. Pivot au sol, au centre.
  Dirigeable_Helice  : helice a 8 pales. Pivot au moyeu, a placer a X = +205 cm, Z = +900 cm.
  Centrale_Rouge_Blanc : 2 x 2 cases. Cheminee en damier, grand batiment, cuves, tuyaux.
  Centrale_Tuyaux    : 2 x 2 cases. 2 cheminees inclinees, faisceau de tuyaux, cuves.
  1 case  : Centrale_Gaz, Grande_Station_Pompage.
  2 x 2   : Petite_Centrale_Nucleaire, Centrale_Nucleaire, Tour_Solaire, Grand_Barrage,
            Grande_Centrale_Nucleaire, Accelerateur_Particules, Plante_Trou_Noir, Plante_Noyau_Nova,
            Sphere_Dyson, Reacteur_Anti_Matiere, Usine_Fusion_Nucleaire, Barrage_Cybernetique,
            Champ_UV_Solaire, Sphere_Trou_Noir.
Pieces qui tournent (mesh a part, pivot au centre de rotation) et leur position par rapport au batiment :
  Eolienne_Rotor                 X = +265, Z = +1310 cm   tourne autour de l'axe X
  Dirigeable_Helice              X = +205, Z = +900 cm    tourne autour de l'axe X
  Accelerateur_Particules_Anneau Z = +100 cm              tourne autour de l'axe vertical
  Reacteur_Anti_Matiere_Anneau   Z = +200 cm              tourne autour de l'axe vertical
  Sphere_Dyson_Cage              Z = +460 cm              tourne autour de l'axe vertical
  Sphere_Trou_Noir_Cage          Z = +460 cm              tourne autour de l'axe vertical
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


def coord(px):
    t = (np.arange(px) + 0.5) / px
    return np.meshgrid(t, t)          # u (colonnes), v (lignes, de bas en haut)


def tuile_stud(px, plein=False):
    """Un stud : fin contour en carre aux coins arrondis (plein = carre rempli plus sombre)."""
    u, v = coord(px)
    x, y = u - 0.5, v - 0.5
    demi, coin, w = 0.24, 0.11, 0.028
    qx, qy = np.abs(x) - (demi - coin), np.abs(y) - (demi - coin)
    d = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - coin
    f = 1 - 0.22 * np.exp(-(d / w) ** 2)
    if plein:
        f *= 1 - 0.2 * np.clip(0.5 - d / 0.01, 0, 1)
    return f


def motif(genre, n, px, aleatoire=False, remplis=0.0):
    """Facteur de luminosite (n*px x n*px) qui se repete sans couture.
    studs    : carres arrondis (une part 'remplis' de carres pleins), taches foncees si aleatoire
    chevrons : des '^' empiles (cheminee de la centrale a vapeur)
    losanges : quadrillage en diagonale (cheminee en briques, toit vert, generateur)"""
    rng = np.random.default_rng(11)
    if genre == "studs":
        vide, plein = tuile_stud(px), tuile_stud(px, True)
        choix = rng.random((n, n)) < remplis
        f = np.vstack([np.hstack([plein if choix[i, j] else vide for j in range(n)]) for i in range(n)])
        if aleatoire:
            tache = rng.random((n, n)) < 0.10
            for _ in range(2):
                voisins = (np.roll(tache, 1, 0) | np.roll(tache, -1, 0) | np.roll(tache, 1, 1) | np.roll(tache, -1, 1))
                tache = tache | (voisins & (rng.random((n, n)) < 0.4))
            f = f * np.kron(np.where(tache, 0.80, 1.0), np.ones((px, px)))
        return f
    u, v = coord(px)
    if genre == "dalles":
        # grands carreaux : bord clair + croix plus discrete au milieu, teinte un peu differente par carreau
        bord = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
        milieu = np.minimum(np.abs(u - 0.5), np.abs(v - 0.5))
        f = (1 + 0.2 * np.exp(-(bord / 0.012) ** 2)) * (1 + 0.08 * np.exp(-(milieu / 0.008) ** 2))
        teinte = rng.choice([0.9, 1.0, 1.0, 1.08], size=(n, n))
        return np.tile(f, (n, n)) * np.kron(teinte, np.ones((px, px)))
    if genre == "chevrons":
        d = np.abs(v - (0.72 - 0.6 * np.abs(u - 0.5))) * 0.86
        f = 1 - 0.35 * np.exp(-(d / 0.03) ** 2)
    else:
        a, b = (u + v) % 1.0, (u - v) % 1.0
        da, db = np.minimum(a, 1 - a) * 0.707, np.minimum(b, 1 - b) * 0.707
        f = 1 - 0.3 * np.clip(np.exp(-(da / 0.025) ** 2) + np.exp(-(db / 0.025) ** 2), 0, 1)
    return np.tile(f, (n, n))


def vers_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def texture(nom, couleur, f):
    rgb = np.dstack([vers_srgb(couleur[i] * f) for i in range(3)])
    rgba = np.dstack((rgb, np.ones_like(f)))
    img = bpy.data.images.new("T_" + nom, f.shape[1], f.shape[0], alpha=False)
    img.pixels.foreach_set(rgba.astype(np.float32).ravel())
    os.makedirs(TEXTURES, exist_ok=True)
    img.filepath_raw = os.path.join(TEXTURES, "T_" + nom + ".png")
    img.file_format = 'PNG'
    img.save()
    return img


def texture_damier(nom, c1, c2, n, px):
    """Damier a 2 couleurs (cheminee rouge et blanche)."""
    u, v = coord(px * n)
    case = ((np.floor(u * n) + np.floor(v * n)) % 2)
    rgb = np.dstack([vers_srgb(c1[i] * case + c2[i] * (1 - case)) for i in range(3)])
    rgba = np.dstack((rgb, np.ones_like(case)))
    img = bpy.data.images.new("T_" + nom, px * n, px * n, alpha=False)
    img.pixels.foreach_set(rgba.astype(np.float32).ravel())
    os.makedirs(TEXTURES, exist_ok=True)
    img.filepath_raw = os.path.join(TEXTURES, "T_" + nom + ".png")
    img.file_format = 'PNG'
    img.save()
    return img


def matiere(nom, couleur, metal=0.0, rugo=0.6, emission=0.0, studs=None, motif_tex=None,
            n=STUDS_PAR_TEXTURE, tuile=STUD, aleatoire=False, remplis=0.0, couleur2=None):
    """Materiau de couleur unie + texture (studs par defaut, ou motif_tex = 'chevrons' / 'losanges').
    tuile = taille d'un motif en metres, n = nombre de motifs par cote de la texture."""
    if nom in MATS:
        return MATS[nom]
    if motif_tex is None:
        if studs is None:
            studs = STUDS_SUR_BATIMENTS
        motif_tex = "studs" if studs else ""
    m = bpy.data.materials.new(nom)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*couleur, 1.0)
    m["metres"] = n * tuile if motif_tex else 0.0      # taille de la texture dans le monde (pour les UV)
    if motif_tex:
        tex = nt.nodes.new("ShaderNodeTexImage")
        if motif_tex == "damier":
            tex.image = texture_damier(nom, couleur, couleur2, n, 64)
            tex.interpolation = 'Closest'
        else:
            tex.image = texture(nom, couleur, motif(motif_tex, n, PX_STUD, aleatoire, remplis))
        if motif_tex != "damier":
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
        metres = (mat.get("metres", 0.0) if mat else 0.0) or STUDS_PAR_TEXTURE * STUD
        ech = 1.0 / metres
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


def maillage(nom, sommets, faces, mat):
    me = bpy.data.meshes.new(nom)
    me.from_pydata(sommets, [], faces)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(nom, me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(mat)
    return o


def bloc8(bas, haut, mat, nom="Bloc"):
    """Bloc a 8 sommets : 4 en bas, 4 en haut (meme ordre). Pour les toits en pente et les troncs de pyramide."""
    faces = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return maillage(nom, list(bas) + list(haut), faces, mat)


def tronc_pyramide(cx, cy, z0, z1, l0, p0, l1, p1, mat):
    bas = [(cx - l0 / 2, cy - p0 / 2, z0), (cx + l0 / 2, cy - p0 / 2, z0),
           (cx + l0 / 2, cy + p0 / 2, z0), (cx - l0 / 2, cy + p0 / 2, z0)]
    haut = [(cx - l1 / 2, cy - p1 / 2, z1), (cx + l1 / 2, cy - p1 / 2, z1),
            (cx + l1 / 2, cy + p1 / 2, z1), (cx - l1 / 2, cy + p1 / 2, z1)]
    return bloc8(bas, haut, mat, "Toit")


def prisme(r, longueur, pos, mat, cotes=8, axe="X"):
    """Cylindre a facettes couche (axe X ou Y), avec une face plate en bas."""
    o = cylindre(r, r, longueur, (0, 0, 0), mat, cotes=cotes, rot=(0, 0, math.pi / cotes))
    o.rotation_euler = (0, math.radians(90), 0) if axe == "X" else (math.radians(90), 0, 0)
    finir(o, mat)
    o.location = pos
    return o


def dome(r, pos, mat, ech=(1, 1, 1), segments=12):
    """Demi-sphere a facettes posee au sol."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=6, radius=r, location=(0, 0, 0))
    o = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.01], context='VERTS')
    bmesh.ops.contextual_create(bm, geom=[e for e in bm.edges if e.is_boundary])
    bm.to_mesh(o.data)
    bm.free()
    o.scale = ech
    finir(o, mat)
    o.location = pos
    return o


def tas(pos, ech, mat, graine):
    """Tas bosselé (charbon) : sphere a facettes deformee au hasard, aplatie au sol."""
    rng = np.random.default_rng(graine)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0, location=(0, 0, 0))
    o = bpy.context.active_object
    for v in o.data.vertices:
        v.co *= 1 + rng.normal(0, 0.09)
        v.co.x *= ech[0]
        v.co.y *= ech[1]
        v.co.z = max(v.co.z * ech[2], 0.0)
    finir(o, mat)
    o.location = pos
    return o


def vitre(face, x, y, z, larg, haut, barres, verre, cadre):
    """Fenetre vitree avec des barreaux, collee sur un mur (face = '-Y', '+Y', '-X' ou '+X')."""
    e = 0.06
    parts = []
    if face in ("-Y", "+Y"):
        s = -1 if face == "-Y" else 1
        parts.append(boite((larg, e, haut), (x, y + s * e / 2, z), verre))
        for i in range(1, barres):
            parts.append(boite((0.05, e, haut), (x - larg / 2 + i * larg / barres, y + s * e, z), cadre))
        parts.append(boite((larg, e, 0.05), (x, y + s * e, z), cadre))
    else:
        s = -1 if face == "-X" else 1
        parts.append(boite((e, larg, haut), (x + s * e / 2, y, z), verre))
        for i in range(1, barres):
            parts.append(boite((e, 0.05, haut), (x + s * e, y - larg / 2 + i * larg / barres, z), cadre))
        parts.append(boite((e, larg, 0.05), (x + s * e, y, z), cadre))
    return parts


def decaler(objs, dx, dy):
    for o in objs:
        o.location.x += dx
        o.location.y += dy
    return objs


bpy.ops.wm.read_factory_settings(use_empty=True)

# ---------------------------------------------------------------------------
#  COULEURS (facon Roblox : couleurs franches, peu de details)
# ---------------------------------------------------------------------------
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
#  USINE ELECTRIQUE (2 x 2 cases) : bloc a 2 cheminees + hangar + annexe + 2 tas
# ---------------------------------------------------------------------------
NAVY = matiere("Bleu_Marine", (0.017, 0.032, 0.102), rugo=0.6)
NAVY_CHEM = matiere("Bleu_Cheminee", (0.021, 0.042, 0.141), rugo=0.5, studs=False)
TOIT_USINE = matiere("Toit_Usine", (0.141, 0.242, 0.485), rugo=0.7)
BORD_CLAIR = matiere("Bord_Clair", (0.546, 0.716, 0.871), rugo=0.5, studs=False)
VITRE = matiere("Vitre_Bleue", (0.115, 0.429, 0.913), rugo=0.2, studs=False)
VOLET = matiere("Volet_Fonce", (0.008, 0.015, 0.05), rugo=0.6, studs=False)
PORTE = matiere("Porte_Claire", (0.305, 0.429, 0.644), rugo=0.5, studs=False)
ANNEXE = matiere("Annexe_Usine", (0.115, 0.188, 0.376), rugo=0.6)
TAS_BLEU = matiere("Tas_Bleu", (0.013, 0.026, 0.080), rugo=0.8)


def usine():
    p = []
    # bloc principal (porte et fenetres face -Y), 2 cheminees l'une derriere l'autre
    bx0, bx1, by0, by1, h = -4.6, -0.6, -4.4, -0.4, 5.0
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    p.append(boite((bx1 - bx0, by1 - by0, h), (cx, cy, h / 2), NAVY))
    p.append(boite((bx1 - bx0 - 0.3, by1 - by0 - 0.3, 0.04), (cx, cy, h + 0.02), TOIT_USINE))
    L, P, e, hb = bx1 - bx0 + 0.1, by1 - by0 + 0.1, 0.32, 0.42          # rebord clair du toit
    p.append(boite((L, e, hb), (cx, by0 - 0.05 + e / 2, h + hb / 2 - 0.05), BORD_CLAIR))
    p.append(boite((L, e, hb), (cx, by1 + 0.05 - e / 2, h + hb / 2 - 0.05), BORD_CLAIR))
    p.append(boite((e, P, hb), (bx0 - 0.05 + e / 2, cy, h + hb / 2 - 0.05), BORD_CLAIR))
    p.append(boite((e, P, hb), (bx1 + 0.05 - e / 2, cy, h + hb / 2 - 0.05), BORD_CLAIR))
    for y in (-3.2, -1.45):
        p.append(cylindre(0.5, 0.5, 5.6, (cx - 0.4, y, h + 2.8), NAVY_CHEM, cotes=16))
        p.append(cylindre(0.7, 0.7, 0.4, (cx - 0.4, y, h + 0.2), BORD_CLAIR, cotes=16))
        p.append(cylindre(0.62, 0.62, 0.5, (cx - 0.4, y, h + 5.45), BORD_CLAIR, cotes=16))
        p.append(cylindre(0.45, 0.45, 0.06, (cx - 0.4, y, h + 5.68), VOLET, cotes=16))
    for x in (cx - 0.95, cx + 0.95):
        p += vitre("-Y", x, by0, 3.9, 1.5, 1.0, 4, VITRE, NAVY_CHEM)
        p += vitre("+Y", x, by1, 3.9, 1.5, 1.0, 4, VITRE, NAVY_CHEM)
    p.append(boite((bx1 - bx0 + 0.3, 0.6, 0.15), (cx, by0 - 0.3, 2.75), NAVY_CHEM))  # auvent
    p.append(boite((1.0, 0.08, 1.9), (cx - 0.7, by0 - 0.04, 0.95), PORTE))           # porte
    for dx in (-0.22, 0.22):
        p.append(boite((0.28, 0.06, 0.3), (cx - 0.7 + dx, by0 - 0.08, 1.5), VITRE))
    # hangar a droite, toit en pente (bas devant, haut derriere), 4 volets face -Y
    x0, x1, y0, y1 = -0.6, 4.9, -3.8, 1.8
    p.append(bloc8([(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)],
                   [(x0, y0, 3.0), (x1, y0, 3.0), (x1, y1, 3.6), (x0, y1, 3.6)], NAVY, "Hangar"))
    p.append(bloc8([(x0, y0 - 0.25, 2.95), (x1 + 0.12, y0 - 0.25, 2.95), (x1 + 0.12, y1 + 0.12, 3.55), (x0, y1 + 0.12, 3.55)],
                   [(x0, y0 - 0.25, 3.15), (x1 + 0.12, y0 - 0.25, 3.15), (x1 + 0.12, y1 + 0.12, 3.75), (x0, y1 + 0.12, 3.75)],
                   TOIT_USINE, "Toit_Hangar"))
    p.append(boite((x1 - x0, 0.3, 0.12), ((x0 + x1) / 2, y0 - 0.15, 0.06), NAVY_CHEM))  # marche
    for i in range(4):
        x = x0 + 0.75 + i * 1.32
        p.append(boite((1.1, 0.06, 1.3), (x, y0 - 0.03, 1.0), VOLET))
        for dz in (-0.35, 0.0, 0.35):
            p.append(boite((0.75, 0.06, 0.07), (x, y0 - 0.06, 1.0 + dz), VITRE))
    p.append(boite((0.6, 2.8, 2.8), (bx0 - 0.3, -2.4, 1.4), ANNEXE))                # annexe
    p.append(dome(1.25, (-3.6, 1.0, 0), TAS_BLEU, ech=(1, 1, 0.6)))                 # 2 tas derriere
    p.append(dome(1.0, (-1.7, 1.4, 0), TAS_BLEU, ech=(1, 1, 0.65)))
    return fusion(p, "Usine_Electrique")


# ---------------------------------------------------------------------------
#  FERME SOLAIRE (1 case) : 4 panneaux inclines sur socles + lampadaire au milieu
# ---------------------------------------------------------------------------
SOCLE_FERME = matiere("Socle_Ferme", (0.205, 0.283, 0.485), rugo=0.6)
SUPPORT = matiere("Support_Clair", (0.515, 0.716, 0.913), rugo=0.5, studs=False)
CELLULE = matiere("Cellule_Bleue", (0.010, 0.141, 0.913), rugo=0.3, studs=False)
CADRE_FERME = matiere("Cadre_Ferme", (0.610, 0.753, 1.0), rugo=0.4, studs=False)
POTEAU = matiere("Poteau_Fonce", (0.013, 0.032, 0.115), rugo=0.5, studs=False)
CYAN = matiere("Lumiere_Cyan", (0.102, 0.791, 1.0), emission=2.5, studs=False)


def plaque_ferme(larg, haut):
    parts = [boite((larg, haut, 0.08), (0, 0, 0), CADRE_FERME)]
    j = 0.035
    for moitie in (-1, 1):                                   # 2 demi-panneaux de 4 x 4 cellules
        lm = larg / 2 - j * 1.5
        xc0 = moitie * (j / 2 + lm / 2)
        lc, hc = (lm - 3 * j) / 4, (haut - 2 * j - 3 * j) / 4
        for c in range(4):
            for l in range(4):
                x = xc0 - lm / 2 + lc / 2 + c * (lc + j)
                y = -haut / 2 + j + hc / 2 + l * (hc + j)
                parts.append(boite((lc, hc, 0.03), (x, y, 0.05), CELLULE))
    return fusion(parts, "Plaque")


def ferme_solaire():
    p = []
    for cx, cy in ((-1.25, -1.2), (1.25, -1.2), (-1.25, 1.3), (1.25, 1.3)):
        socle = cylindre(1.0, 1.0, 0.18, (cx, cy, 0.09), SOCLE_FERME, cotes=8, rot=(0, 0, math.radians(22.5)))
        socle.scale = (1.15, 0.75, 1)
        p.append(finir(socle, SOCLE_FERME))
        for dx in (-0.55, 0.55):
            p.append(boite((0.36, 0.3, 0.12), (cx + dx, cy, 0.24), SUPPORT))
            p.append(boite((0.12, 0.18, 0.95), (cx + dx, cy + 0.05, 0.7), SUPPORT, rot=(math.radians(-15), 0, 0)))
        pl = plaque_ferme(2.2, 1.7)
        pl.rotation_euler = (math.radians(60), 0, 0)         # incline, face vers -Y
        bpy.ops.object.select_all(action='DESELECT')
        pl.select_set(True)
        bpy.context.view_layer.objects.active = pl
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        pl.location = (cx, cy + 0.15, 1.15)
        p.append(pl)
    # lampadaire avec anneaux lumineux
    p.append(cylindre(0.2, 0.2, 0.1, (0, 0.05, 0.05), POTEAU, cotes=8))
    p.append(cylindre(0.08, 0.08, 2.3, (0, 0.05, 1.15), POTEAU, cotes=8))
    for i, z in enumerate((2.0, 2.13, 2.26)):
        p.append(cylindre(0.15, 0.15, 0.07, (0, 0.05, z), CYAN, cotes=12))
        p.append(cylindre(0.11, 0.11, 0.06, (0, 0.05, z + 0.065), POTEAU, cotes=12))
    p.append(cylindre(0.13, 0.1, 0.12, (0, 0.05, 2.42), CADRE_FERME, cotes=12))
    return fusion(p, "Ferme_Solaire")


# ---------------------------------------------------------------------------
#  CENTRALE A VAPEUR (1 case) : maison + cheminee a chevrons + generateur + tuyaux
# ---------------------------------------------------------------------------
MUR_VAP = matiere("Mur_Vapeur", (0.171, 0.242, 0.402), rugo=0.6, remplis=0.25)
TOIT_VERT = matiere("Toit_Vert", (0.045, 0.242, 0.171), rugo=0.3, motif_tex="losanges", n=2, tuile=1.3)
TOIT_VERT_CLAIR = matiere("Toit_Vert_Clair", (0.115, 0.402, 0.305), rugo=0.3, studs=False)
CHEM_VAP = matiere("Cheminee_Chevrons", (0.305, 0.402, 0.578), rugo=0.6, motif_tex="chevrons", n=4, tuile=0.42)
BLOC_FONCE = matiere("Bloc_Fonce", (0.017, 0.038, 0.115), rugo=0.6)
JAUNE_LUM = matiere("Jaune_Lumiere", (1.0, 0.913, 0.0), emission=2.0, studs=False)
GENE = matiere("Generateur", (0.013, 0.032, 0.061), rugo=0.5, motif_tex="losanges", n=2, tuile=1.0)
REBORD_VERT = matiere("Rebord_Vert", (0.021, 0.155, 0.127), rugo=0.5, studs=False)
OCRE = matiere("Ocre", (0.680, 0.376, 0.021), rugo=0.5, motif_tex="losanges", n=1, tuile=1.4)
TUYAU = matiere("Tuyau_Argent", (0.429, 0.546, 0.680), metal=0.5, rugo=0.35, studs=False)
PLAQUE_GRISE = matiere("Plaque_Grise", (0.352, 0.429, 0.578), rugo=0.6, studs=False)


def centrale_vapeur():
    p = []
    # maison
    p.append(boite((2.2, 2.0, 2.2), (-0.2, 0.1, 1.1), MUR_VAP))
    p.append(boite((0.7, 0.06, 0.9), (0.35, -0.93, 0.45), BLOC_FONCE))                       # porte en arche
    p.append(cylindre(0.35, 0.35, 0.06, (0.35, -0.93, 0.9), BLOC_FONCE, cotes=12, rot=(math.radians(90), 0, 0)))
    p.append(tronc_pyramide(-0.2, 0.1, 2.2, 2.6, 2.75, 2.55, 1.5, 1.3, TOIT_VERT))
    p.append(boite((1.3, 1.1, 0.12), (-0.2, 0.1, 2.66), TOIT_VERT_CLAIR))
    # bloc fonce (fenetre jaune + conduit) et cheminee a chevrons
    p.append(boite((1.2, 2.8, 1.2), (1.5, 1.0, 0.6), BLOC_FONCE))
    p.append(boite((0.55, 0.05, 0.35), (1.5, -0.43, 0.75), JAUNE_LUM))
    p.append(boite((0.45, 0.5, 0.4), (2.32, 0.1, 0.65), BLOC_FONCE))
    p.append(cylindre(0.56, 0.56, 0.9, (1.5, 1.6, 1.65), CHEM_VAP, cotes=8, rot=(0, 0, math.radians(22.5))))
    p.append(cylindre(0.42, 0.42, 3.9, (1.5, 1.6, 4.05), CHEM_VAP, cotes=8, rot=(0, 0, math.radians(22.5))))
    p.append(cylindre(0.75, 0.75, 0.08, (1.5, 1.6, 4.4), CHEM_VAP, cotes=8, rot=(0, 0, math.radians(22.5))))
    p.append(cylindre(0.47, 0.47, 0.15, (1.5, 1.6, 6.05), CHEM_VAP, cotes=8, rot=(0, 0, math.radians(22.5))))
    # generateur octogonal couche, faces ocre aux 2 bouts
    gx, gy, gz = -1.9, 1.45, 0.92
    p.append(boite((1.9, 1.6, 0.1), (gx, gy, 0.05), PLAQUE_GRISE))
    p.append(prisme(0.8, 1.3, (gx, gy, gz), GENE))
    for s in (-1, 1):
        p.append(prisme(0.86, 0.12, (gx + s * 0.68, gy, gz), REBORD_VERT))
        p.append(prisme(0.7, 0.04, (gx + s * 0.75, gy, gz), OCRE))
    p.append(boite((0.5, 0.5, 0.3), (gx, gy, gz + 0.9), GENE))
    p.append(boite((0.16, 0.16, 0.6), (gx, gy, gz + 1.3), PLAQUE_GRISE))
    # 2 tuyaux argentes du bloc vers le generateur, + une vanne
    for z, dy in ((0.5, -0.17), (0.95, 0.17)):
        pts = [(0.9, 2.0, z), (0.4, 2.35, z), (-0.45, 2.3, z), (-0.9, 1.85, z), (-1.12, gy + dy, z)]
        p.append(tube(pts, [0.11] * 5, TUYAU, "Tuyau", cotes=8))
        p.append(prisme(0.16, 0.1, (-1.05, gy + dy, z), BLOC_FONCE))
    p.append(boite((0.45, 0.35, 0.3), (0.2, 2.05, 0.15), BLOC_FONCE))
    p.append(dome(0.2, (0.2, 2.05, 0.3), TUYAU))
    decaler(p, 0.0, -0.75)
    return fusion(p, "Centrale_Vapeur")


# ---------------------------------------------------------------------------
#  PETITE PLANTE BIOLOGIQUE (1 case) : four + cheminee en briques + tas de charbon
# ---------------------------------------------------------------------------
MAUVE = matiere("Mauve_Four", (0.205, 0.127, 0.205), rugo=0.7, remplis=0.3)
MAUVE_CLAIR = matiere("Mauve_Clair", (0.305, 0.205, 0.262), rugo=0.7)
BRIQUE = matiere("Brique_Losanges", (0.188, 0.102, 0.141), rugo=0.8, motif_tex="losanges", n=4, tuile=0.5)
ORANGE_LUM = matiere("Orange_Feu", (1.0, 0.262, 0.0), emission=0.8, studs=False)
CHARBON = matiere("Charbon", (0.026, 0.026, 0.031), rugo=0.9, studs=False)
METAL_GRIS = matiere("Metal_Gris", (0.305, 0.305, 0.352), metal=0.5, rugo=0.4, studs=False)


def plante_bio():
    p = []
    p.append(boite((1.7, 1.7, 1.9), (0, 0.5, 0.95), MAUVE))                       # four
    p.append(boite((1.8, 1.8, 0.12), (0, 0.5, 1.96), MAUVE_CLAIR))
    p.append(boite((0.9, 0.06, 0.6), (-0.1, -0.37, 1.25), ORANGE_LUM))            # feu
    p.append(boite((1.2, 0.04, 0.06), (0, -0.36, 0.55), BRIQUE))                  # tiroir a cendres
    p.append(boite((0.25, 0.06, 0.06), (0, -0.39, 0.45), METAL_GRIS))
    p.append(boite((0.6, 0.7, 0.5), (1.05, 0.6, 1.25), MAUVE_CLAIR, rot=(0, math.radians(-20), 0)))  # tremie
    p.append(cylindre(0.42, 0.5, 0.2, (0, 0.1, 2.12), METAL_GRIS, cotes=16))      # bol sur le dessus
    p.append(cylindre(0.36, 0.36, 0.02, (0, 0.1, 2.225), CHARBON, cotes=16))
    p.append(boite((1.5, 0.9, 0.7), (0, 0.95, 2.37), MAUVE))                      # pied de la cheminee
    r8 = (0, 0, math.radians(22.5))
    p.append(cylindre(0.66, 0.62, 2.9, (0, 0.95, 4.17), BRIQUE, cotes=8, rot=r8))
    p.append(cylindre(0.62, 0.78, 0.35, (0, 0.95, 5.79), BRIQUE, cotes=8, rot=r8))
    p.append(cylindre(0.78, 0.78, 0.12, (0, 0.95, 6.02), BRIQUE, cotes=8, rot=r8))
    p.append(tas((-0.75, -1.5, 0), (1.8, 1.15, 0.85), CHARBON, 5))                # tas de charbon
    p.append(tas((0.85, -1.65, 0), (1.55, 1.25, 1.05), CHARBON, 6))
    decaler(p, 0.0, 0.6)
    return fusion(p, "Plante_Bio")


# ---------------------------------------------------------------------------
#  USINE GRISE (1 case) : batiment a toit sombre, 3 cheminees, cuves sur le cote
# ---------------------------------------------------------------------------
GRIS_USINE = matiere("Gris_Usine", (0.43, 0.485, 0.578), rugo=0.6, remplis=0.2)
TOIT_NOIR = matiere("Toit_Noir", (0.017, 0.021, 0.037), rugo=0.6, studs=False)
CHEM_GRIS = matiere("Cheminee_Grise", (0.305, 0.352, 0.43), rugo=0.6)


def usine_grise():
    p = []
    x0, x1, y0, y1, ym = -2.3, 1.2, -1.0, 1.2, 0.25
    cx = (x0 + x1) / 2
    p.append(boite((x1 - x0, y1 - y0, 2.0), (cx, (y0 + y1) / 2, 1.0), GRIS_USINE))
    p.append(boite((x1 - x0, y1 - ym, 0.6), (cx, (ym + y1) / 2, 2.3), GRIS_USINE))          # partie haute derriere
    p.append(bloc8([(x0, y0, 2.0), (x1, y0, 2.0), (x1, ym, 2.0), (x0, ym, 2.0)],           # remplissage sous le toit
                   [(x0, y0, 2.01), (x1, y0, 2.01), (x1, ym, 2.6), (x0, ym, 2.6)], GRIS_USINE, "Pignon"))
    p.append(bloc8([(x0 - 0.1, y0 - 0.2, 1.88), (x1 + 0.1, y0 - 0.2, 1.88), (x1 + 0.1, ym + 0.05, 2.58), (x0 - 0.1, ym + 0.05, 2.58)],
                   [(x0 - 0.1, y0 - 0.2, 2.03), (x1 + 0.1, y0 - 0.2, 2.03), (x1 + 0.1, ym + 0.05, 2.73), (x0 - 0.1, ym + 0.05, 2.73)],
                   TOIT_NOIR, "Toit_Sombre"))
    r8 = (0, 0, math.radians(22.5))
    for x in (-1.65, -0.55, 0.55):                                                          # 3 cheminees
        p.append(cylindre(0.36, 0.36, 2.3, (x, 0.72, 3.75), CHEM_GRIS, cotes=8, rot=r8))
        p.append(cylindre(0.47, 0.47, 0.3, (x, 0.72, 2.75), CHEM_GRIS, cotes=8, rot=r8))
        p.append(cylindre(0.4, 0.4, 0.14, (x, 0.72, 4.88), CHEM_GRIS, cotes=8, rot=r8))
        p.append(cylindre(0.3, 0.3, 0.04, (x, 0.72, 4.95), TOIT_NOIR, cotes=8, rot=r8))
    for x in (-1.6, -0.55, 0.5):                                                            # 3 fenetres
        p += vitre("-Y", x, y0, 1.2, 0.85, 0.6, 3, VITRE, TOIT_NOIR)
    p.append(cylindre(0.5, 0.5, 2.0, (1.75, 0.6, 1.0), GRIS_USINE, cotes=8, rot=r8))       # cuves
    p.append(cylindre(0.52, 0.4, 0.2, (1.75, 0.6, 2.1), GRIS_USINE, cotes=8, rot=r8))
    p.append(cylindre(0.45, 0.45, 1.3, (1.85, -0.4, 0.65), GRIS_USINE, cotes=8, rot=r8))
    p.append(cylindre(0.47, 0.35, 0.18, (1.85, -0.4, 1.39), GRIS_USINE, cotes=8, rot=r8))
    p.append(tube([(2.2, -0.4, 0.7), (2.45, -0.4, 0.7), (2.5, -0.4, 0.5), (2.5, -0.4, 0.0)], [0.07] * 4,
                  CHEM_GRIS, "Tuyau", cotes=6))
    return fusion(p, "Usine_Grise")


# ---------------------------------------------------------------------------
#  STATION DE POMPAGE (1 case) : machine en blocs bleus + bassin + tuyaux + cuves blanches
# ---------------------------------------------------------------------------
BLEU_MACHINE = matiere("Bleu_Machine", (0.021, 0.102, 0.578), rugo=0.5, remplis=0.25)
BLEU_CLAIR_M = matiere("Bleu_Clair_Machine", (0.102, 0.305, 0.791), rugo=0.3, studs=False)
EAU = matiere("Eau_Cyan", (0.0, 0.871, 1.0), rugo=0.1, emission=0.5, studs=False)
BLANC_CUVE = matiere("Blanc_Cuve", (0.75, 0.79, 0.87), rugo=0.4, studs=False)


def station_pompage():
    p = []
    bassin = cylindre(1.3, 1.3, 0.04, (-1.15, 0.25, 0.02), EAU, cotes=10)                  # bassin
    bassin.scale = (1.0, 1.1, 1)
    p.append(finir(bassin, EAU))
    p.append(boite((2.7, 1.3, 0.45), (1.15, 0.4, 0.225), BLEU_MACHINE))                     # socle
    p.append(boite((0.9, 1.1, 0.55), (0.3, 0.4, 0.72), BLEU_MACHINE))                       # bloc avant
    p.append(boite((0.5, 0.45, 0.14), (0.3, 0.4, 1.06), BLEU_CLAIR_M))
    p.append(boite((0.8, 1.0, 0.3), (1.15, 0.4, 0.6), BLEU_MACHINE))                        # bloc du milieu
    p.append(boite((0.35, 0.3, 0.2), (1.25, 0.05, 0.85), BLEU_CLAIR_M))
    p.append(boite((1.0, 1.2, 0.6), (2.0, 0.4, 0.75), BLEU_MACHINE))                        # bloc arriere
    p.append(boite((0.45, 0.4, 0.15), (1.8, 0.15, 1.12), BLEU_MACHINE))
    p.append(dome(0.22, (2.2, 0.6, 1.05), BLEU_CLAIR_M))
    p.append(cylindre(0.09, 0.09, 1.5, (0.1, 0.75, 1.75), POTEAU, cotes=8))                 # pot d'echappement
    for z in (1.35, 1.95):
        p.append(cylindre(0.13, 0.13, 0.08, (0.1, 0.75, z), POTEAU, cotes=8))
    p.append(cylindre(0.12, 0.12, 0.08, (0.1, 0.75, 2.52), POTEAU, cotes=8))
    for y in (0.15, 0.65):                                                                  # tuyaux dans le bassin
        p.append(tube([(-0.1, y, 0.75), (-0.7, y, 0.75), (-0.95, y, 0.62), (-1.0, y, 0.35), (-1.0, y, 0.02)],
                      [0.1] * 5, TUYAU, "Tuyau", cotes=8))
        p.append(prisme(0.14, 0.1, (-0.12, y, 0.75), TUYAU))
    p.append(tube([(0.75, 0.2, 1.0), (1.15, 0.2, 1.0), (1.55, 0.2, 1.0)], [0.06] * 3, TUYAU, "Tuyau", cotes=6))
    for x in (0.95, 1.8):                                                                   # cuves blanches
        p.append(cylindre(0.42, 0.42, 0.55, (x, -0.65, 0.275), BLANC_CUVE, cotes=12))
        p.append(dome(0.42, (x, -0.65, 0.55), BLANC_CUVE, ech=(1, 1, 0.55)))
    return fusion(p, "Station_Pompage")


# ---------------------------------------------------------------------------
#  BARRAGE (2 x 2 cases) : plateau de terre et d'herbe, lac, mur de barrage courbe
# ---------------------------------------------------------------------------
TERRE = matiere("Terre", (0.205, 0.038, 0.007), rugo=0.9, motif_tex="dalles", n=2, tuile=1.024)
PIERRE = matiere("Pierre_Barrage", (0.155, 0.205, 0.352), rugo=0.7, remplis=0.3)
H_BAR = 2.4


def barrage(nom="Barrage", H=H_BAR, lac_i=(3, 6), lac_j=(3, 8), terre=TERRE, herbe=SOL, pierre=PIERRE,
            eau=EAU, neon=None, blocs=4):
    """Plateau de terre (bord d'herbe) en escaliers, lac au milieu, mur de barrage courbe devant.
    neon = materiau lumineux pour des bandes le long du mur (barrage cybernetique)."""
    p = []
    rng = np.random.default_rng(21)
    C = 10.24 / 10
    lac = lambda i, j: lac_i[0] <= i <= lac_i[1] and lac_j[0] <= j <= lac_j[1]
    ouverture = lambda i, j: lac_i[0] <= i <= lac_i[1] and j < lac_j[0]
    vides = [(i, j) for i in range(10) for j in range(10) if lac(i, j) or ouverture(i, j)]
    for i in range(10):
        for j in range(10):
            if (i, j) in vides:
                continue
            dist = min(max(abs(i - a), abs(j - b)) for a, b in vides)
            h = H if dist <= 2 else float(rng.choice([H, H, H - 0.7]))
            if (i in (0, 9) or j in (0, 9)) and rng.random() < 0.4:
                h = H - 0.7 if h == H else H - 1.4
            x, y = -5.12 + (i + 0.5) * C, -5.12 + (j + 0.5) * C
            p.append(boite((C, C, h - 0.25), (x, y, (h - 0.25) / 2), terre))
            p.append(boite((C, C, 0.25), (x, y, h - 0.125), herbe))
    # mur de barrage : arc creux vu de devant, plus epais en bas
    lx = (lac_i[1] - lac_i[0] + 1) * C / 2
    y_lac = -5.12 + lac_j[0] * C
    arc = lambda x: (y_lac - 1.35) + 1.0 * (1 - (x / lx) ** 2)
    xs = [-(lx + 0.4) + 2 * (lx + 0.4) * k / 16 for k in range(17)]

    def ruban(profil, mat, nom_r):
        som, faces = [], []
        for x in xs:
            som += [(x, arc(x) + dy, z) for dy, z in profil]
        for k in range(len(xs) - 1):
            for c in range(4):
                i0, i1 = 4 * k + c, 4 * k + (c + 1) % 4
                faces.append((i0, i1, i1 + 4, i0 + 4))
        faces.extend([(0, 1, 2, 3), tuple(range(4 * len(xs) - 1, 4 * len(xs) - 5, -1))])
        return maillage(nom_r, som, faces, mat)

    p.append(ruban([(-0.4, 0), (0, H + 0.05), (0.5, H + 0.05), (0.5, 0)], pierre, "Mur"))
    p.append(ruban([(-0.1, H), (-0.1, H + 0.2), (0.55, H + 0.2), (0.55, H)], pierre, "Rebord"))
    if neon:
        devant = lambda z: -0.4 * (1 - z / (H + 0.05))
        for z0 in [H * f for f in (0.25, 0.5, 0.75)]:
            z1 = z0 + 0.12
            p.append(ruban([(devant(z0) - 0.05, z0), (devant(z1) - 0.05, z1), (devant(z1) + 0.02, z1),
                            (devant(z0) + 0.02, z0)], neon, "Neon"))
        p.append(ruban([(-0.14, H + 0.05), (-0.14, H + 0.15), (-0.08, H + 0.15), (-0.08, H + 0.05)], neon, "Neon"))
    for x in np.linspace(-lx * 0.6, lx * 0.6, blocs):                                       # blocs sur le mur
        p.append(boite((0.42, 0.4, 0.5), (x, arc(x) + 0.22, H + 0.45), pierre))
    # lac : bandes d'eau du mur jusqu'au fond
    xe = [-lx + 2 * lx * k / 16 for k in range(17)]
    som = []
    for x in xe:
        som += [(x, arc(x) + 0.5, H - 0.2), (x, -5.12 + (lac_j[1] + 1) * C, H - 0.2)]
    faces = [(2 * k, 2 * k + 2, 2 * k + 3, 2 * k + 1) for k in range(len(xe) - 1)]
    p.append(maillage("Lac", som, faces, eau))
    return fusion(p, nom)


# ---------------------------------------------------------------------------
#  DIRIGEABLE EOLIEN (1 case) : tete beige a oreilles qui flotte, helice qui tourne, cable au sol
# ---------------------------------------------------------------------------
BEIGE = matiere("Beige_Dirigeable", (0.83, 0.578, 0.352), rugo=0.6, motif_tex="losanges", n=2, tuile=1.1)
PALE_CLAIRE = matiere("Pale_Claire", (0.716, 0.83, 0.955), rugo=0.4, studs=False)
FOND_HELICE = matiere("Fond_Helice", (0.402, 0.578, 0.791), rugo=0.5, studs=False)
CABLE = matiere("Cable_Noir", (0.01, 0.01, 0.012), rugo=0.6, studs=False)
Z_DIRIG = 9.0                      # hauteur du centre de la tete
X_HELICE = 2.05                    # helice devant la tete (+X)


def dirigeable():
    p = []
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=2.3, location=(0, 0, 0))
    corps = bpy.context.active_object
    corps.scale = (1.0, 1.1, 0.95)
    p.append(finir(corps, BEIGE))
    corps.location = (0, 0, Z_DIRIG)
    for s_ in (-1, 1):                                                                     # 2 oreilles
        o = cylindre(0.8, 0.05, 1.8, (-0.4, s_ * 1.2, Z_DIRIG + 2.3), BEIGE, cotes=4,
                     rot=(s_ * math.radians(-22), math.radians(-12), math.radians(45)))
        p.append(o)
    p.append(cylindre(1.45, 1.45, 0.5, (X_HELICE - 0.35, 0, Z_DIRIG), BEIGE, cotes=12,
                      rot=(0, math.radians(90), 0)))                                       # anneau autour de l'helice
    p.append(cylindre(1.25, 1.25, 0.1, (X_HELICE - 0.05, 0, Z_DIRIG), FOND_HELICE, cotes=12,
                      rot=(0, math.radians(90), 0)))
    p.append(tube([(0, 0, 0), (0.6, 0.3, 2.0), (0.2, 0.1, 4.2), (-0.3, -0.1, 5.8), (0, 0, Z_DIRIG - 2.0)],
                  [0.05] * 5, CABLE, "Cable", cotes=6))
    p.append(cylindre(0.2, 0.25, 0.12, (0, 0, 0.06), CABLE, cotes=8))                      # piquet au sol
    corps_obj = fusion(p, "Dirigeable")
    # helice : construite autour de (0, 0, 0) = son moyeu, pales dans le plan YZ
    h = [sphere(0.28, (0.05, 0, 0), POTEAU)]
    for k in range(8):
        a = math.radians(45 * k)
        pale = cylindre(0.28, 0.12, 1.0, (0, 0, 0), PALE_CLAIRE, cotes=4)
        pale.scale = (0.25, 1.0, 1.0)
        finir(pale, PALE_CLAIRE)
        pale.rotation_euler = (0, 0, math.radians(30))
        finir(pale, PALE_CLAIRE)
        pale.location = (0, -math.sin(a) * 0.72, math.cos(a) * 0.72)
        pale.rotation_euler = (a, 0, 0)
        finir(pale, PALE_CLAIRE)
        bpy.ops.object.transform_apply(location=True)
        h.append(pale)
    return corps_obj, fusion(h, "Dirigeable_Helice")


# ---------------------------------------------------------------------------
#  CENTRALE ROUGE ET BLANCHE (2 x 2 cases) : maison a cheminee en damier, grand batiment gris,
#  radiateur, 2 grosses cuves blanches, tuyaux au sol
# ---------------------------------------------------------------------------
MUR_GRIS_BLEU = matiere("Mur_Gris_Bleu", (0.262, 0.31, 0.43), rugo=0.6, remplis=0.15)
TOIT_ARDOISE = matiere("Toit_Ardoise", (0.045, 0.05, 0.08), rugo=0.7)
GRIS_CLAIR_C = matiere("Gris_Clair_Centrale", (0.33, 0.37, 0.46), rugo=0.6, remplis=0.15)
DAMIER = matiere("Damier_Rouge_Blanc", (0.3, 0.008, 0.01), rugo=0.5, motif_tex="damier", n=4, tuile=0.45,
                 couleur2=(0.86, 0.86, 0.9))
CUVE_BLANCHE = matiere("Cuve_Blanche", (0.82, 0.85, 0.9), rugo=0.5, remplis=0.1)
TUBE_GRIS = matiere("Tube_Gris", (0.25, 0.27, 0.32), metal=0.5, rugo=0.4, studs=False)


def centrale_rouge_blanc():
    p = []
    # maison a gauche, toit en croupe sombre
    p.append(boite((3.4, 3.4, 2.2), (-3.0, 1.6, 1.1), MUR_GRIS_BLEU))
    p.append(tronc_pyramide(-3.0, 1.6, 2.2, 3.4, 3.9, 3.9, 1.6, 0.4, TOIT_ARDOISE))
    p.append(boite((1.6, 1.4, 1.8), (-3.0, -0.6, 0.9), MUR_GRIS_BLEU))                       # avancee
    p.append(tronc_pyramide(-3.0, -0.6, 1.8, 2.5, 2.0, 1.8, 0.3, 0.6, TOIT_ARDOISE))
    for x, y, h in ((-3.3, 2.0, 7.5), (-2.75, 2.45, 6.3)):                                     # cheminees damier
        p.append(cylindre(0.38, 0.38, h - 2.6, (x, y, 2.6 + (h - 2.6) / 2), DAMIER, cotes=8,
                          rot=(0, 0, math.radians(22.5))))
        p.append(cylindre(0.42, 0.42, 0.15, (x, y, h), CUVE_BLANCHE, cotes=8, rot=(0, 0, math.radians(22.5))))
    # grand batiment gris a droite
    p.append(boite((4.4, 4.6, 3.0), (2.6, 2.4, 1.5), GRIS_CLAIR_C))
    p.append(boite((4.5, 4.7, 0.15), (2.6, 2.4, 3.07), TOIT_ARDOISE))
    p.append(boite((2.4, 2.6, 2.2), (2.2, 2.9, 4.2), GRIS_CLAIR_C))                          # bloc haut
    p.append(boite((2.5, 2.7, 0.15), (2.2, 2.9, 5.37), TOIT_ARDOISE))
    p.append(boite((0.35, 0.35, 1.2), (2.2, 2.9, 6.0), TOIT_ARDOISE))                          # 'T' sur le toit
    p.append(boite((1.6, 0.35, 0.35), (2.2, 2.9, 6.55), TOIT_ARDOISE))
    p.append(boite((1.3, 3.0, 2.2), (4.6, 1.2, 1.1), GRIS_CLAIR_C))                          # annexe
    p.append(boite((1.4, 3.1, 0.12), (4.6, 1.2, 2.26), TOIT_ARDOISE))
    # radiateur a ailettes devant
    p.append(boite((2.6, 1.0, 1.4), (2.3, -0.7, 1.3), GRIS_CLAIR_C))
    for k in range(9):
        p.append(boite((0.06, 1.05, 1.3), (1.1 + k * 0.3, -0.72, 1.3), TOIT_ARDOISE))
    for k in range(5):
        x = 1.3 + k * 0.5
        p.append(cylindre(0.06, 0.06, 0.6, (x, -1.0, 0.3), TUBE_GRIS, cotes=6))
    # 2 grosses cuves blanches octogonales
    for x in (-3.4, -0.6):
        p.append(cylindre(1.15, 1.15, 1.4, (x, -3.0, 0.7), CUVE_BLANCHE, cotes=8, rot=(0, 0, math.radians(22.5))))
        p.append(cylindre(1.15, 0.9, 0.25, (x, -3.0, 1.52), CUVE_BLANCHE, cotes=8, rot=(0, 0, math.radians(22.5))))
    # tuyaux au sol : des cuves jusqu'au radiateur
    p.append(tube([(-3.4, -4.3, 0.18), (3.3, -4.3, 0.18)], [0.07] * 2, TUBE_GRIS, "Tuyau", cotes=6))
    for x in (-3.4, -0.6):
        p.append(tube([(x, -4.3, 0.18), (x, -4.1, 0.4)], [0.07] * 2, TUBE_GRIS, "Tuyau", cotes=6))
    for k in range(5):
        x = 1.3 + k * 0.5
        p.append(tube([(x, -1.0, 0.05), (x, -1.4, 0.05), (x, -4.0 + k * 0.12, 0.05), (x, -4.3 + k * 0.03, 0.18)],
                      [0.06] * 4, TUBE_GRIS, "Tuyau", cotes=6))
    for x in (-2.4, -1.4, 0.4, 1.0, 2.0, 3.0):                                                # petits supports
        p.append(boite((0.12, 0.3, 0.12), (x, -4.3, 0.06), TOIT_ARDOISE))
    return fusion(p, "Centrale_Rouge_Blanc")


# ---------------------------------------------------------------------------
#  CENTRALE A TUYAUX (2 x 2 cases) : bloc gris clair, 2 grosses cheminees inclinees, faisceau de tuyaux
# ---------------------------------------------------------------------------
GRIS_PALE = matiere("Gris_Pale", (0.43, 0.515, 0.68), rugo=0.6, remplis=0.15)
GRIS_PALE_X = matiere("Gris_Pale_Losanges", (0.43, 0.515, 0.68), rugo=0.6, motif_tex="losanges", n=2, tuile=1.0)
BLANC_BLOC = matiere("Blanc_Bloc", (0.86, 0.9, 0.95), rugo=0.5, studs=False)


def centrale_tuyaux():
    p = []
    p.append(boite((9.4, 9.4, 0.25), (0, 0, 0.125), GRIS_PALE))                              # dalle
    p.append(boite((6.4, 4.0, 3.0), (-0.6, 2.4, 1.75), GRIS_PALE))                            # bloc principal
    p.append(boite((4.4, 2.6, 1.0), (-1.0, 3.0, 3.75), GRIS_PALE))
    p.append(boite((1.4, 1.0, 0.5), (-2.6, 1.6, 3.5), GRIS_PALE))
    p.append(boite((1.8, 1.4, 0.06), (-2.0, 0.37, 2.0), GRIS_PALE_X))                         # panneau en X
    p.append(boite((2.0, 3.6, 2.4), (-3.9, -0.2, 1.45), GRIS_PALE))                           # aile gauche
    p.append(boite((1.4, 0.06, 1.2), (-3.9, -2.03, 1.4), GRIS_PALE_X))
    # 2 grosses cheminees inclinees vers l'arriere
    for x in (-1.6, 1.4):
        a, b = Vector((x, 2.2, 3.4)), Vector((x, 4.6, 9.0))
        p.append(tube([a, (a + b) / 2, b], [0.6] * 3, GRIS_PALE_X, "Cheminee", cotes=12))
        p.append(tube([b - (b - a).normalized() * 0.4, b + (b - a).normalized() * 0.05], [0.7] * 2,
                      GRIS_PALE, "Bord", cotes=12))
        p.append(tube([b - (b - a).normalized() * 0.1, b + (b - a).normalized() * 0.07], [0.5] * 2,
                      TOIT_ARDOISE, "Trou", cotes=12))
        p.append(cylindre(0.9, 0.9, 0.5, (x, 2.2, 3.5), GRIS_PALE, cotes=12))
    # faisceau de tuyaux courbes qui descendent vers la plateforme avant
    for k, x in enumerate((-1.6, -0.9, -0.2, 0.5, 1.2, 1.9)):
        z0 = 2.2 - 0.15 * (k % 2)
        p.append(tube([(x, 0.4, z0), (x, -0.6, z0 + 0.1), (x + 0.2, -1.5, 1.2), (x + 0.3, -2.4, 0.6)],
                      [0.13] * 4, GRIS_PALE, "Tuyau", cotes=8))
    p.append(tube([(-2.2, -1.2, 1.35), (2.6, -1.2, 1.35)], [0.13] * 2, GRIS_PALE, "Tuyau", cotes=8))
    # plateforme avant avec des blocs blancs et des petits tuyaux debout
    p.append(boite((5.4, 2.4, 0.4), (0.8, -3.2, 0.45), GRIS_PALE))
    for x in (0.0, 1.5, 3.0):
        p.append(boite((1.0, 0.7, 0.35), (x, -3.9, 0.82), BLANC_BLOC))
    for x in (-1.2, 2.2, 3.3):
        p.append(cylindre(0.1, 0.1, 1.4, (x, -2.6, 1.35), GRIS_PALE, cotes=8))
    # 2 cuves octogonales basses
    for x in (-3.7, -2.0):
        p.append(cylindre(0.85, 0.85, 0.6, (x, -3.3, 0.55), GRIS_PALE, cotes=8, rot=(0, 0, math.radians(22.5))))
        p.append(cylindre(0.75, 0.75, 0.05, (x, -3.3, 0.875), GRIS_PALE_X, cotes=8, rot=(0, 0, math.radians(22.5))))
    return fusion(p, "Centrale_Tuyaux")


# ---------------------------------------------------------------------------
#  OUTILS POUR LES DERNIERS BATIMENTS
# ---------------------------------------------------------------------------
def anneau(R, r, pos, mat, rot=(0, 0, 0), seg=32, segm=6):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=seg, minor_segments=segm,
                                     location=pos, rotation=rot)
    return finir(bpy.context.active_object, mat)


def tour_refroidissement(cx, cy, r, h, mat, interieur, z0=0.0):
    """Tour de refroidissement (forme de diabolo), ouverte en haut."""
    zs = [z0, z0 + 0.25 * h, z0 + 0.55 * h, z0 + 0.8 * h, z0 + h]
    rs = [r, 0.82 * r, 0.66 * r, 0.65 * r, 0.72 * r]
    return [tube([(cx, cy, z) for z in zs], rs, mat, "Tour", cotes=20),
            cylindre(0.68 * r, 0.68 * r, 0.04, (cx, cy, z0 + h + 0.01), interieur, cotes=20)]


def bassin(cx, cy, r, eau, bord):
    return [cylindre(r + 0.3, r + 0.3, 0.06, (cx, cy, 0.03), bord, cotes=8, rot=(0, 0, math.radians(22.5))),
            cylindre(r, r, 0.08, (cx, cy, 0.05), eau, cotes=8, rot=(0, 0, math.radians(22.5)))]


def heliostat(cx, cy, angle, cadre, cellule, pied):
    """Petit panneau sur pied, tourne vers le centre (angle = position autour du centre)."""
    pl = fusion([boite((1.9, 1.25, 0.08), (0, 0, 0), cadre), boite((1.75, 1.1, 0.03), (0, 0, 0.05), cellule)], "Plaque")
    pl.rotation_euler = (math.radians(35), 0, angle - math.pi / 2)
    bpy.ops.object.select_all(action='DESELECT')
    pl.select_set(True)
    bpy.context.view_layer.objects.active = pl
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    pl.location = (cx, cy, 1.1)
    return [cylindre(0.1, 0.1, 1.0, (cx, cy, 0.5), pied, cotes=8), pl]


def cage(cx, cy, cz, R, mat, r=0.12):
    """Cage en anneaux autour d'une sphere (4 meridiens + 3 paralleles)."""
    p = [anneau(R, r, (cx, cy, cz), mat, rot=(math.radians(90), 0, math.radians(a)), segm=6) for a in (0, 45, 90, 135)]
    p.append(anneau(R, r, (cx, cy, cz), mat))
    for s_ in (-1, 1):
        p.append(anneau(R * 0.7071, r, (cx, cy, cz + s_ * R * 0.7071), mat))
    return p


R8 = (0, 0, math.radians(22.5))

GRIS_BETON = matiere("Gris_Beton", (0.3, 0.32, 0.37), rugo=0.7)
GRIS_CHEM_LISSE = matiere("Gris_Cheminee_Lisse", (0.33, 0.35, 0.4), rugo=0.6, studs=False)
DALLE_FONCEE = matiere("Dalle_Foncee", (0.03, 0.032, 0.04), rugo=0.7)
JAUNE_TUBE = matiere("Jaune_Tube", (0.9, 0.55, 0.0), rugo=0.4, studs=False)
EAU_BLEUE = matiere("Eau_Bleue", (0.0, 0.2, 0.85), rugo=0.1, emission=0.3, studs=False)
BORD_HERBE = matiere("Bord_Herbe", (0.35, 0.75, 0.02), rugo=0.8, studs=False)
TOUR_BETON = matiere("Tour_Beton", (0.5, 0.52, 0.56), rugo=0.8, studs=False)
NOIR_MAT = matiere("Noir_Mat", (0.008, 0.008, 0.01), rugo=0.5, studs=False)
ROSE_MAT = matiere("Rose_Machine", (0.6, 0.18, 0.45), rugo=0.6)
VIOLET_LUM = matiere("Violet_Lumiere", (0.55, 0.1, 1.0), emission=3.0, studs=False)
ROUGE_DOME = matiere("Rouge_Reacteur", (0.35, 0.01, 0.02), rugo=0.4)
BLEU_BOITE = matiere("Bleu_Boite", (0.05, 0.35, 0.9), rugo=0.5)
JAUNE_BOITE = matiere("Jaune_Boite", (0.6, 0.45, 0.02), rugo=0.5)
VIOLET_DALLE = matiere("Violet_Dalle", (0.08, 0.04, 0.2), rugo=0.6)
BETON_CLAIR = matiere("Beton_Clair", (0.45, 0.46, 0.5), rugo=0.8)
BLANC_LUM = matiere("Blanc_Lumiere", (1.0, 1.0, 1.0), emission=3.0, studs=False)
ROSE_LUM = matiere("Rose_Lumiere", (1.0, 0.15, 0.6), emission=3.0, studs=False)
VERT_NEON = matiere("Vert_Neon", (0.1, 1.0, 0.2), emission=3.0, studs=False)
JAUNE_SOLEIL = matiere("Jaune_Soleil", (1.0, 0.75, 0.02), emission=4.0, studs=False)
ROUGE_LUM = matiere("Rouge_Lumiere", (1.0, 0.02, 0.02), emission=3.0, studs=False)
GRIS_SOMBRE = matiere("Gris_Sombre", (0.04, 0.042, 0.05), rugo=0.5)
DAMIER_NB = matiere("Damier_Noir_Blanc", (0.01, 0.01, 0.012), rugo=0.5, motif_tex="damier", n=4, tuile=0.6,
                    couleur2=(0.85, 0.85, 0.88))
VIOLET_PANNEAU = matiere("Violet_Panneau", (0.12, 0.03, 0.2), rugo=0.5, studs=False)
VIOLET_CELL = matiere("Violet_Cellule", (0.5, 0.05, 0.9), emission=1.0, studs=False)
TERRE_SOMBRE = matiere("Terre_Sombre", (0.02, 0.02, 0.025), rugo=0.8, motif_tex="dalles", n=2, tuile=1.024)
DESSUS_SOMBRE = matiere("Dessus_Sombre", (0.05, 0.055, 0.07), rugo=0.6)
PIERRE_SOMBRE = matiere("Pierre_Sombre", (0.03, 0.035, 0.045), rugo=0.6, remplis=0.3)
EAU_CYBER = matiere("Eau_Cyber", (0.0, 0.45, 1.0), rugo=0.1, emission=0.8, studs=False)
CYAN_NEON = matiere("Cyan_Neon", (0.0, 0.85, 1.0), emission=4.0, studs=False)


# ---------------------------------------------------------------------------
#  1. CENTRALE A GAZ (1 case) : bloc gris, 2 hautes cheminees, tuyau jaune
# ---------------------------------------------------------------------------
def centrale_gaz():
    p = [boite((4.2, 3.4, 1.4), (0, 0.2, 0.7), GRIS_BETON), boite((3.0, 2.4, 0.25), (-0.3, 0.5, 1.525), DALLE_FONCEE)]
    for x, y in ((-1.0, 0.6), (0.5, 0.7)):
        p.append(cylindre(0.55, 0.55, 5.0, (x, y, 4.15), GRIS_CHEM_LISSE, cotes=16))
        p.append(cylindre(0.65, 0.65, 0.25, (x, y, 1.77), GRIS_CHEM_LISSE, cotes=16))
    p.append(tube([(-1.8, -0.85, 1.75), (1.0, -0.85, 1.75), (1.3, -0.6, 1.75), (1.3, 0.4, 1.75), (1.3, 0.6, 1.5)],
                  [0.1] * 5, JAUNE_TUBE, "Tuyau", cotes=8))
    p.append(cylindre(0.45, 0.45, 0.8, (1.6, -1.0, 1.8), GRIS_CHEM_LISSE, cotes=12))
    return fusion(p, "Centrale_Gaz")


# ---------------------------------------------------------------------------
#  2. GRANDE STATION DE POMPAGE (1 case) : 2 machines, tuyaux dans un bassin bleu
# ---------------------------------------------------------------------------
def grande_station_pompage():
    p = bassin(0, -0.9, 1.6, EAU_BLEUE, BORD_HERBE)
    for x in (-1.2, 1.2):
        p.append(boite((1.8, 1.3, 0.9), (x, 1.75, 0.45), NAVY))
        p.append(boite((1.2, 0.9, 0.4), (x, 1.85, 1.1), NAVY))
        for dx in (-0.5, 0.5):
            p.append(cylindre(0.25, 0.25, 0.5, (x + dx, 1.45, 1.15), BLANC_CUVE, cotes=10))
        for dx in (-0.35, 0.35):
            p.append(tube([(x + dx, 1.1, 0.6), (x + dx, 0.4, 0.6), (x + dx, 0.0, 0.3), (x + dx, -0.1, 0.05)],
                          [0.1] * 4, TUYAU, "Tuyau", cotes=8))
    return fusion(p, "Grande_Station_Pompage")


# ---------------------------------------------------------------------------
#  3. PETITE CENTRALE NUCLEAIRE (2 x 2) : tour de refroidissement, machine rose, tube violet
# ---------------------------------------------------------------------------
def petite_centrale_nucleaire():
    p = [boite((9.6, 9.6, 0.2), (0, 0, 0.1), BETON_CLAIR)]
    p += tour_refroidissement(-2.4, 1.6, 2.6, 8.0, TOUR_BETON, NOIR_MAT, z0=0.2)
    p.append(boite((3.0, 2.0, 1.0), (2.4, -1.8, 0.7), ROSE_MAT))
    p.append(boite((1.4, 1.2, 0.6), (2.0, -1.8, 1.5), ROSE_MAT))
    p.append(prisme(0.45, 1.6, (3.2, -0.3, 0.65), ROSE_MAT, cotes=10, axe="Y"))
    p.append(tube([(-0.6, 0.4, 0.6), (0.6, -0.4, 0.6), (0.9, -1.6, 0.6)], [0.22] * 3, VIOLET_LUM, "Tube", cotes=10))
    for x, y in ((0.4, -0.2), (1.0, -3.3)):
        p.append(cylindre(0.08, 0.08, 1.6, (x, y, 1.0), TUBE_GRIS, cotes=8))
        p.append(boite((0.4, 0.15, 0.15), (x, y, 1.8), TUBE_GRIS))
    return fusion(p, "Petite_Centrale_Nucleaire")


# ---------------------------------------------------------------------------
#  4. CENTRALE NUCLEAIRE (2 x 2) : tour, reacteur a dome rouge, boite bleue, cuve couchee
# ---------------------------------------------------------------------------
def centrale_nucleaire():
    p = [boite((9.6, 9.6, 0.2), (0, 0, 0.1), BETON_CLAIR)]
    p += tour_refroidissement(2.6, 1.8, 2.4, 7.5, TOUR_BETON, NOIR_MAT, z0=0.2)
    p.append(boite((4.2, 3.2, 0.15), (-0.8, -1.6, 0.27), VIOLET_DALLE))
    p.append(cylindre(1.3, 1.3, 1.4, (-0.8, -1.6, 1.05), ROUGE_DOME, cotes=16))
    p.append(dome(1.3, (-0.8, -1.6, 1.75), ROUGE_DOME))
    p.append(boite((2.4, 1.8, 1.0), (-3.2, 0.6, 0.7), BLEU_BOITE))
    p.append(prisme(0.7, 2.6, (-3.0, 3.3, 0.9), TOUR_BETON, cotes=12, axe="X"))
    p.append(boite((1.0, 0.8, 0.6), (0.2, 1.0, 0.5), JAUNE_BOITE))
    return fusion(p, "Centrale_Nucleaire")


# ---------------------------------------------------------------------------
#  5 et 15. TOUR SOLAIRE / CHAMP UV SOLAIRE (2 x 2) : tour au centre, anneau de panneaux
# ---------------------------------------------------------------------------
def champ_solaire(nom, mat_tour, mat_haut, cadre, cellule, n=8, rayon=3.6):
    p = [cylindre(0.9, 0.9, 0.3, (0, 0, 0.15), mat_tour, cotes=8, rot=R8),
         cylindre(0.55, 0.45, 6.0, (0, 0, 3.3), mat_tour, cotes=8, rot=R8),
         cylindre(0.75, 0.75, 0.9, (0, 0, 6.75), mat_haut, cotes=8, rot=R8),
         cylindre(0.5, 0.3, 0.4, (0, 0, 7.4), mat_tour, cotes=8, rot=R8)]
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        p += heliostat(rayon * math.cos(a), rayon * math.sin(a), a, cadre, cellule, mat_tour)
    return fusion(p, nom)


# ---------------------------------------------------------------------------
#  7. GRANDE CENTRALE NUCLEAIRE (2 x 2) : 2 tours, batiment blanc, tubes violets lumineux
# ---------------------------------------------------------------------------
def grande_centrale_nucleaire():
    p = [boite((9.8, 9.8, 0.2), (0, 0, 0.1), BETON_CLAIR)]
    p += tour_refroidissement(-3.0, 2.6, 2.0, 6.5, TOUR_BETON, NOIR_MAT, z0=0.2)
    p += tour_refroidissement(-3.3, -2.3, 1.8, 5.5, TOUR_BETON, NOIR_MAT, z0=0.2)
    p.append(boite((3.0, 2.4, 2.2), (2.6, 2.9, 1.3), BLANC_BLOC))
    p.append(boite((3.1, 2.5, 0.12), (2.6, 2.9, 2.46), TOUR_BETON))
    pts = [(-0.6, -3.6, 0.35), (3.9, -3.6, 0.35), (3.9, 0.9, 0.35), (-0.6, 0.9, 0.35), (-0.6, -3.6, 0.35)]
    for a, b in zip(pts, pts[1:]):
        p.append(tube([a, b], [0.12] * 2, VIOLET_LUM, "Tube", cotes=8))
    p.append(tube([(1.6, -3.6, 0.35), (1.6, 0.9, 0.35)], [0.12] * 2, VIOLET_LUM, "Tube", cotes=8))
    p.append(tube([(-0.6, -1.4, 0.35), (3.9, -1.4, 0.35)], [0.12] * 2, VIOLET_LUM, "Tube", cotes=8))
    p.append(boite((0.9, 0.9, 0.9), (2.7, -2.5, 0.65), BLEU_BOITE))
    p.append(boite((1.0, 1.0, 1.0), (0.5, -0.3, 0.7), BLANC_BLOC))
    p.append(boite((1.4, 1.0, 0.6), (0.5, -2.6, 0.5), TOUR_BETON))
    return fusion(p, "Grande_Centrale_Nucleaire")


# ---------------------------------------------------------------------------
#  8. ACCELERATEUR DE PARTICULES (2 x 2) : anneau rose lumineux, sphere rose, machines sombres
# ---------------------------------------------------------------------------
Z_ANNEAU_ACC = 1.0


def accelerateur():
    p = [cylindre(4.8, 4.8, 0.4, (0, 0, 0.2), GRIS_SOMBRE, cotes=8, rot=R8)]
    for k in range(8):
        a = 2 * math.pi * k / 8
        p.append(boite((0.55, 0.55, 0.45), (3.0 * math.cos(a), 3.0 * math.sin(a), 0.6), GRIS_SOMBRE, rot=(0, 0, a)))
    p.append(cylindre(1.0, 1.0, 1.2, (0, 0, 1.0), GRIS_SOMBRE, cotes=16))
    p.append(cylindre(0.6, 0.6, 0.1, (0, 0, 1.65), ROSE_LUM, cotes=16))
    p.append(cylindre(0.6, 0.7, 0.3, (-2.6, -3.3, 0.55), GRIS_SOMBRE, cotes=12))
    p.append(sphere(0.75, (-2.6, -3.3, 1.4), ROSE_LUM))
    p.append(boite((1.6, 1.2, 1.4), (2.9, 3.0, 1.1), GRIS_SOMBRE))
    p.append(boite((1.2, 1.4, 1.0), (1.0, 3.6, 0.9), GRIS_SOMBRE))
    for k in range(3):
        p.append(boite((1.0, 0.06, 0.12), (2.9, 2.37, 0.8 + k * 0.3), NOIR_MAT))
    p.append(boite((0.3, 0.06, 0.3), (1.0, 2.88, 1.1), ROSE_LUM))
    base = fusion(p, "Accelerateur_Particules")
    # anneau qui tourne (autour de l'axe vertical) : construit autour de (0, 0, 0)
    r = [anneau(3.0, 0.32, (0, 0, 0), ROSE_LUM, segm=8)]
    for k in range(6):
        a = 2 * math.pi * k / 6
        r.append(boite((0.45, 0.85, 0.85), (3.0 * math.cos(a), 3.0 * math.sin(a), 0), GRIS_SOMBRE, rot=(0, 0, a)))
    return base, fusion(r, "Accelerateur_Particules_Anneau")


# ---------------------------------------------------------------------------
#  9. PLANTE DU TROU NOIR (2 x 2) : plateforme en gradins, sphere noire, anneau et lumieres roses
# ---------------------------------------------------------------------------
def plante_trou_noir():
    p = [cylindre(4.7, 4.7, 0.6, (0, 0, 0.3), GRIS_SOMBRE, cotes=8, rot=R8),
         cylindre(3.6, 3.6, 0.6, (0, 0, 0.9), GRIS_SOMBRE, cotes=8, rot=R8),
         cylindre(2.6, 2.6, 0.6, (0, 0, 1.5), GRIS_SOMBRE, cotes=8, rot=R8)]
    p.append(sphere(1.7, (0, 0, 3.5), NOIR_MAT))
    p.append(anneau(2.1, 0.12, (0, 0, 1.9), ROSE_LUM))
    for r, z in ((4.42, 0.62), (3.36, 1.22)):
        for k in range(8):
            a = 2 * math.pi * k / 8
            p.append(boite((0.12, 0.7, 0.1), (r * math.cos(a), r * math.sin(a), z), ROSE_LUM, rot=(0, 0, a)))
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        x, y = 3.0 * math.cos(a), 3.0 * math.sin(a)
        p.append(cylindre(0.3, 0.3, 1.6, (x, y, 2.0), GRIS_SOMBRE, cotes=8))
        p.append(cylindre(0.32, 0.32, 0.15, (x, y, 2.85), ROSE_LUM, cotes=8))
    return fusion(p, "Plante_Trou_Noir")


# ---------------------------------------------------------------------------
#  10. PLANTE DU NOYAU NOVA (2 x 2) : reacteur sombre a anneaux blancs lumineux, 4 colonnes
# ---------------------------------------------------------------------------
def noyau_nova():
    p = [cylindre(4.6, 4.6, 0.4, (0, 0, 0.2), GRIS_SOMBRE, cotes=8, rot=R8)]
    p.append(cylindre(2.6, 2.6, 2.2, (0, 0, 1.5), GRIS_SOMBRE, cotes=16))
    p.append(dome(2.6, (0, 0, 2.6), GRIS_SOMBRE, ech=(1, 1, 0.55), segments=16))
    for z in (1.2, 2.2):
        p.append(anneau(2.65, 0.09, (0, 0, z), BLANC_LUM))
    p.append(anneau(1.4, 0.1, (0, 0, 3.8), BLANC_LUM, seg=24))
    p.append(cylindre(0.6, 0.6, 0.3, (0, 0, 4.1), BLANC_LUM, cotes=12))
    for x, y in ((-3.4, -3.4), (3.4, -3.4), (-3.4, 3.4), (3.4, 3.4)):
        p.append(cylindre(0.5, 0.5, 3.0, (x, y, 1.9), GRIS_SOMBRE, cotes=12))
        p.append(dome(0.5, (x, y, 3.4), BLANC_LUM))
        p.append(anneau(0.52, 0.06, (x, y, 2.6), BLANC_LUM, seg=16))
    return fusion(p, "Plante_Noyau_Nova")


# ---------------------------------------------------------------------------
#  11 et 16. SPHERE DYSON / SPHERE DE TROU NOIR (2 x 2) : sphere dans une cage, sur un socle
# ---------------------------------------------------------------------------
Z_SPHERE = 4.6


def sphere_cage(nom, mat_sphere, mat_cage, mat_base, mat_deco):
    p = [cylindre(3.6, 3.2, 1.0, (0, 0, 0.5), mat_base, cotes=16),
         cylindre(2.6, 2.0, 0.8, (0, 0, 1.4), mat_base, cotes=16)]
    for k in range(8):
        a = 2 * math.pi * k / 8
        p.append(boite((0.12, 0.7, 0.35), (3.42 * math.cos(a), 3.42 * math.sin(a), 0.5), mat_deco, rot=(0, 0, a)))
    p.append(sphere(2.5, (0, 0, Z_SPHERE), mat_sphere))
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        c, s_ = math.cos(a), math.sin(a)
        p.append(tube([(2.0 * c, 2.0 * s_, 1.7), (2.55 * c, 2.55 * s_, 3.0)], [0.12] * 2, mat_cage, "Pied", cotes=6))
    # la cage tourne autour de l'axe vertical : construite autour de (0, 0, 0)
    return fusion(p, nom), fusion(cage(0, 0, 0, 2.75, mat_cage), nom + "_Cage")


# ---------------------------------------------------------------------------
#  12. REACTEUR ANTI-MATIERE (2 x 2) : grand anneau sombre sur piliers, lumieres roses, coeur
# ---------------------------------------------------------------------------
Z_ANNEAU_AM = 2.0


def anti_matiere():
    p = [cylindre(4.6, 4.6, 0.4, (0, 0, 0.2), GRIS_SOMBRE, cotes=8, rot=R8)]
    for k in range(8):
        a = 2 * math.pi * k / 8
        c, s_ = math.cos(a), math.sin(a)
        p.append(boite((0.7, 0.7, 2.0), (3.2 * c, 3.2 * s_, 1.2), GRIS_SOMBRE, rot=(0, 0, a)))
        p.append(boite((0.08, 0.3, 1.4), (3.58 * c, 3.58 * s_, 1.1), ROSE_LUM, rot=(0, 0, a)))
    p.append(cylindre(1.2, 1.2, 2.4, (0, 0, 1.6), NOIR_MAT, cotes=16))
    p.append(anneau(1.3, 0.08, (0, 0, 2.0), ROSE_LUM, seg=24))
    p.append(cylindre(0.8, 0.8, 0.15, (0, 0, 2.85), ROSE_LUM, cotes=16))
    for k in range(4):
        a = k * math.pi / 2
        p.append(boite((1.4, 0.3, 0.3), (1.9 * math.cos(a), 1.9 * math.sin(a), 2.0), GRIS_SOMBRE, rot=(0, 0, a)))
    base = fusion(p, "Reacteur_Anti_Matiere")
    # grand anneau qui tourne (autour de l'axe vertical) : construit autour de (0, 0, 0)
    r = [anneau(3.2, 0.65, (0, 0, 0), GRIS_SOMBRE, seg=24, segm=8),
         anneau(3.2, 0.15, (0, 0, 0.75), GRIS_SOMBRE, seg=24)]
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        c, s_ = math.cos(a), math.sin(a)
        r.append(boite((0.5, 0.9, 0.35), (3.2 * c, 3.2 * s_, 0.6), GRIS_SOMBRE, rot=(0, 0, a)))
        r.append(boite((0.52, 0.3, 0.1), (3.2 * c, 3.2 * s_, 0.8), ROSE_LUM, rot=(0, 0, a)))
    return base, fusion(r, "Reacteur_Anti_Matiere_Anneau")


# ---------------------------------------------------------------------------
#  13. USINE DE FUSION NUCLEAIRE (2 x 2) : dome sombre a anneaux blancs, lumieres vertes, cuves blanches
# ---------------------------------------------------------------------------
def usine_fusion():
    p = [boite((9.6, 9.6, 0.3), (0, 0, 0.15), GRIS_SOMBRE)]
    p.append(cylindre(2.6, 2.4, 2.6, (0, 0.3, 1.6), GRIS_SOMBRE, cotes=16))
    p.append(dome(2.4, (0, 0.3, 2.9), GRIS_SOMBRE, ech=(1, 1, 0.7), segments=16))
    p.append(anneau(2.6, 0.1, (0, 0.3, 1.0), BLANC_LUM))
    p.append(anneau(2.45, 0.1, (0, 0.3, 2.3), BLANC_LUM))
    p.append(anneau(1.3, 0.1, (0, 0.3, 4.4), BLANC_LUM, seg=24))
    p.append(boite((1.4, 0.4, 1.6), (0, -2.15, 1.1), NOIR_MAT))
    p.append(boite((1.6, 0.42, 0.12), (0, -2.15, 1.95), BLANC_LUM))
    for k in range(5):
        a = math.radians(-150 + 30 * k)
        p.append(boite((0.2, 0.2, 0.2), (2.6 * math.cos(a), 0.3 + 2.6 * math.sin(a), 1.7), VERT_NEON))
    for x, y in ((-3.6, -3.4), (3.6, -3.4), (-3.6, 3.4), (3.6, 3.4)):
        p.append(cylindre(0.7, 0.7, 2.4, (x, y, 1.5), BLANC_BLOC, cotes=12))
        p.append(dome(0.7, (x, y, 2.7), BLANC_BLOC))
        p.append(anneau(0.72, 0.06, (x, y, 2.0), VERT_NEON, seg=16))
        p.append(tube([(x * 0.85, y * 0.85, 1.0), (x * 0.55, 0.3 + (y - 0.3) * 0.55, 1.0)], [0.15] * 2,
                      TUBE_GRIS, "Tuyau", cotes=8))
    return fusion(p, "Usine_Fusion_Nucleaire")


# ---------------------------------------------------------------------------
#  CASE DE SOL (dalle de 512 x 512 cm pour la grille 6x6)
# ---------------------------------------------------------------------------
def case_sol():
    d = boite((5.12, 5.12, 0.2), (0, 0, -0.1), SOL)   # le dessus est a Z = 0
    return fusion([d], "Case_Sol")


# ---------------------------------------------------------------------------
#  APERCU (rendu de tous les batiments)
# ---------------------------------------------------------------------------
PLACES = {"Usine_Electrique": (-17, 2, 0), "Centrale_Vapeur": (-8, 0, 0), "Eolienne_Mat": (0, 2, 0),
          "Eolienne_Rotor": (X_MOYEU, 2, Z_NACELLE), "Panneau_Solaire": (8, 0, 0),
          "Ferme_Solaire": (15, 1, 0), "Plante_Bio": (22, 0, 0),
          "Usine_Grise": (-20, 17, 0), "Station_Pompage": (-12, 17, 0), "Barrage": (-1, 18, 0),
          "Centrale_Rouge_Blanc": (11, 18, 0), "Centrale_Tuyaux": (23, 18, 0),
          "Dirigeable": (30, 3, 0), "Dirigeable_Helice": (30 + X_HELICE, 3, Z_DIRIG)}


def apercu(objs, chemin):
    sc = bpy.context.scene
    # copies temporaires placees cote a cote (les originaux restent a (0, 0, 0) pour l'export)
    for o in objs:
        if o.name in PLACES:
            c = o.copy()
            c.data = o.data.copy()
            sc.collection.objects.link(c)
            c.location = PLACES[o.name]
        o.hide_render = True
    bpy.ops.mesh.primitive_plane_add(size=5.12 * 22, location=(5, 8, 0))
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

    bpy.ops.object.camera_add(location=(5, -42, 30))
    cam = bpy.context.active_object
    cible = Vector((5, 8, 1.0))
    cam.rotation_euler = (cible - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 30
    sc.camera = cam

    sc.view_settings.view_transform = 'Standard'
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 48
    sc.cycles.device = 'CPU'
    sc.render.resolution_x, sc.render.resolution_y = 1600, 800
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
    sc.render.resolution_x, sc.render.resolution_y = 640, 640
    sc.cycles.samples = 32
    sc.render.filepath = chemin
    bpy.ops.render.render(write_still=True)


def main():
    mat, rotor = eolienne()
    solaire = panneau_solaire()
    dirig, helice = dirigeable()
    objs = [mat, rotor, solaire, usine(), ferme_solaire(), centrale_vapeur(), plante_bio(),
            usine_grise(), station_pompage(), barrage(), dirig, helice, centrale_rouge_blanc(),
            centrale_tuyaux(),
            centrale_gaz(), grande_station_pompage(), petite_centrale_nucleaire(), centrale_nucleaire(),
            champ_solaire("Tour_Solaire", GRIS_CHEM_LISSE, BLANC_LUM, CADRE_FERME, CELLULE),
            barrage("Grand_Barrage", H=3.2, lac_i=(2, 7), lac_j=(3, 8), blocs=6),
            grande_centrale_nucleaire(), *accelerateur(), plante_trou_noir(), noyau_nova(),
            *sphere_cage("Sphere_Dyson", JAUNE_SOLEIL, NOIR_MAT, NOIR_MAT, ROUGE_LUM),
            *anti_matiere(), usine_fusion(),
            barrage("Barrage_Cybernetique", H=2.8, lac_i=(2, 7), lac_j=(3, 8), terre=TERRE_SOMBRE,
                    herbe=DESSUS_SOMBRE, pierre=PIERRE_SOMBRE, eau=EAU_CYBER, neon=CYAN_NEON),
            champ_solaire("Champ_UV_Solaire", NOIR_MAT, ROSE_LUM, VIOLET_PANNEAU, VIOLET_CELL),
            *sphere_cage("Sphere_Trou_Noir", NOIR_MAT, BLANC_BLOC, DAMIER_NB, BLANC_LUM),
            case_sol()]

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
            vue(objs, os.path.join(d, "vue_usine.png"),
                {"Usine_Electrique": (0, 0, 0)}, (-12, -18, 11), (0, 0, 2.5), 32)
            vue(objs, os.path.join(d, "vue_ferme.png"),
                {"Ferme_Solaire": (0, 0, 0)}, (0.5, -7, 8), (0, 0, 0.6), 35)
            vue(objs, os.path.join(d, "vue_vapeur.png"),
                {"Centrale_Vapeur": (0, 0, 0)}, (-3, 9, 4.5), (0, -0.2, 1.8), 35)
            vue(objs, os.path.join(d, "vue_vapeur2.png"),
                {"Centrale_Vapeur": (0, 0, 0)}, (-4, -8, 4), (0, -0.2, 1.8), 35)
            vue(objs, os.path.join(d, "vue_grise.png"),
                {"Usine_Grise": (0, 0, 0)}, (-5, -8, 5.5), (0, 0, 1.8), 35)
            vue(objs, os.path.join(d, "vue_pompage.png"),
                {"Station_Pompage": (0, 0, 0)}, (1.5, -7, 4.5), (0.2, 0.2, 0.6), 35)
            vue(objs, os.path.join(d, "vue_barrage.png"),
                {"Barrage": (0, 0, 0)}, (0, -16, 4.5), (0, 0, 1.2), 32)
            vue(objs, os.path.join(d, "vue_barrage2.png"),
                {"Barrage": (0, 0, 0)}, (0, -9, 15), (0, 0, 0.5), 32)
            vue(objs, os.path.join(d, "vue_dirigeable.png"),
                {"Dirigeable": (0, 0, 0), "Dirigeable_Helice": (X_HELICE, 0, Z_DIRIG)}, (14, -9, 10), (0, 0, 6.5), 35)
            vue(objs, os.path.join(d, "vue_rouge_blanc.png"),
                {"Centrale_Rouge_Blanc": (0, 0, 0)}, (-4, -15, 13), (0, 0, 1.5), 35)
            vue(objs, os.path.join(d, "vue_tuyaux.png"),
                {"Centrale_Tuyaux": (0, 0, 0)}, (-3, -14, 12), (0, 0, 2.5), 35)
            petits = ("Centrale_Gaz", "Grande_Station_Pompage")
            tournants = {"Accelerateur_Particules": ("Accelerateur_Particules_Anneau", (0, 0, Z_ANNEAU_ACC)),
                         "Reacteur_Anti_Matiere": ("Reacteur_Anti_Matiere_Anneau", (0, 0, Z_ANNEAU_AM)),
                         "Sphere_Dyson": ("Sphere_Dyson_Cage", (0, 0, Z_SPHERE)),
                         "Sphere_Trou_Noir": ("Sphere_Trou_Noir_Cage", (0, 0, Z_SPHERE))}
            for nom in ("Centrale_Gaz", "Grande_Station_Pompage", "Petite_Centrale_Nucleaire",
                        "Centrale_Nucleaire", "Tour_Solaire", "Grand_Barrage", "Grande_Centrale_Nucleaire",
                        "Accelerateur_Particules", "Plante_Trou_Noir", "Plante_Noyau_Nova", "Sphere_Dyson",
                        "Reacteur_Anti_Matiere", "Usine_Fusion_Nucleaire", "Barrage_Cybernetique",
                        "Champ_UV_Solaire", "Sphere_Trou_Noir"):
                places = {nom: (0, 0, 0)}
                if nom in tournants:
                    places[tournants[nom][0]] = tournants[nom][1]
                if nom in petits:
                    vue(objs, os.path.join(d, "vue_" + nom + ".png"), places, (-6, -7.5, 5.5), (0, 0, 1.3), 35)
                else:
                    vue(objs, os.path.join(d, "vue_" + nom + ".png"), places, (-11, -13, 10), (0, 0, 2.2), 35)
            vue(objs, os.path.join(d, "vue_bio.png"),
                {"Plante_Bio": (0, 0, 0)}, (0.5, -9, 3.0), (0, 0, 2.6), 35)


main()
