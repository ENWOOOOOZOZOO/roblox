# Power a City - installation dans UEFN

Je n'ai pas acces a ton projet UEFN (je travaille dans un conteneur cloud) : ce code est a copier
chez toi. Il n'a pas encore ete compile, donc colle les erreurs de Verse ici et je les corrige.

1. Dans UEFN : Verse > Verse Explorer > clic droit sur ton projet > Ajouter un nouveau fichier Verse,
   puis colle `power_city.verse`. Build Verse Code (Ctrl+Shift+B).
2. Place le device `power_city` dans la map.
3. Pour chaque parcelle (4) : un Player Spawner, un Button pour "Agrandir", et 64 cases
   (8x8, ligne par ligne) = 1 Button + 1 prop invisible au centre de chaque case, espaces de 512 cm.
4. Dans `power_city` : remplis `Parcelles` (Cases, Spawner, BoutonAgrandir), `Batiments`
   (Nom, Modele, Largeur, Hauteur, Prix, Puissance, ArgentParSeconde) et `BoutonsChoix`
   (le bouton N choisit le batiment N, en attendant la Boutique).
5. Joue : le premier joueur qui apparait sur un spawner prend la parcelle.

Limites de cette premiere version : pas d'apercu fantome (Verse n'a pas de rayon camera, on
vise la case et on interagit avec son bouton), pas de HUD (les infos sortent en Print),
pas encore de marteau/retrait, ni de sauvegarde.

## Modeles 3D (28 batiments + case de sol)

Les .fbx sont dans `modeles/` (ou relance `batiments.py` dans Blender). Les textures sont incluses
dans les .fbx (et aussi en .png dans `modeles/textures/`). Apercu de tout : `tous_les_batiments.png`.
Chaque mesh a son pivot au sol, au centre de son emprise (sauf les pieces qui tournent, voir plus bas).

`Case_Sol` = une dalle d'herbe a studs de 512 x 512 cm (une case de la grille, 6 x 6 studs) :
pose-en 36 cote a cote pour faire la grille 6x6, avec le dessus a la hauteur du sol.

| Batiment (mesh)              | Cases | Batiment (mesh)              | Cases |
|------------------------------|-------|------------------------------|-------|
| Eolienne_Mat (+ rotor)       | 1x1   | Centrale_Gaz                 | 1x1   |
| Panneau_Solaire              | 1x1   | Grande_Station_Pompage       | 1x1   |
| Usine_Electrique             | 2x2   | Petite_Centrale_Nucleaire    | 2x2   |
| Ferme_Solaire                | 1x1   | Centrale_Nucleaire           | 2x2   |
| Centrale_Vapeur              | 1x1   | Tour_Solaire                 | 2x2   |
| Plante_Bio                   | 1x1   | Grand_Barrage                | 2x2   |
| Usine_Grise                  | 1x1   | Grande_Centrale_Nucleaire    | 2x2   |
| Station_Pompage              | 1x1   | Accelerateur_Particules (+ anneau) | 2x2 |
| Barrage                      | 2x2   | Plante_Trou_Noir             | 2x2   |
| Dirigeable (+ helice)        | 1x1   | Plante_Noyau_Nova            | 2x2   |
| Centrale_Rouge_Blanc         | 2x2   | Sphere_Dyson (+ cage)        | 2x2   |
| Centrale_Tuyaux              | 2x2   | Reacteur_Anti_Matiere (+ anneau) | 2x2 |
|                              |       | Usine_Fusion_Nucleaire       | 2x2   |
|                              |       | Barrage_Cybernetique         | 2x2   |
|                              |       | Champ_UV_Solaire             | 2x2   |
|                              |       | Sphere_Trou_Noir (+ cage)    | 2x2   |

Pour un batiment 2x2, mets Largeur = 2 et Hauteur = 2 dans son entree `Batiments`.

1. Dans UEFN, Content Browser > Import > choisis les .fbx. Pour chacun : Collision Complexity =
   "Use Complex Collision As Simple".
2. Clic droit sur chaque mesh > Create Blueprint Class (parent : creative_prop) pour obtenir un
   `creative_prop_asset` utilisable par Verse.
3. Dans `power_city` > Batiments, cree une entree par batiment (Modele = le mesh du batiment).

### Pieces qui tournent

Elles sont dans un mesh a part, avec le pivot au centre de rotation. Le script les fait apparaitre
avec le batiment et les fait tourner. Dans l'entree du batiment : AUnRotor = true, ModeleRotor = le
mesh qui tourne, puis :

| Batiment                | ModeleRotor                    | DecalageRotor  | RotorVertical | DureeTour |
|-------------------------|--------------------------------|----------------|---------------|-----------|
| Eolienne_Mat            | Eolienne_Rotor                 | (265, 0, 1310) | false         | 4         |
| Dirigeable              | Dirigeable_Helice              | (205, 0, 900)  | false         | 1.5       |
| Accelerateur_Particules | Accelerateur_Particules_Anneau | (0, 0, 100)    | true          | 3         |
| Reacteur_Anti_Matiere   | Reacteur_Anti_Matiere_Anneau   | (0, 0, 200)    | true          | 6         |
| Sphere_Dyson            | Sphere_Dyson_Cage              | (0, 0, 460)    | true          | 10        |
| Sphere_Trou_Noir        | Sphere_Trou_Noir_Cage          | (0, 0, 460)    | true          | 10        |

Si une piece apparait decalee sur le cote, inverse le signe de X dans DecalageRotor.
Pour les pieces qui tournent : ouvre le mesh > Collision > Remove Collision (rien ne doit bloquer
le joueur pendant que ca tourne).

### Collisions

Chaque .fbx contient des boites de collision simples (les objets `UCX_...`) qui suivent la forme
du batiment vue de dessus. UEFN les reconnait tout seul a l'import : ne change PAS Collision
Complexity (laisse "Project Default"). Les joueurs ne restent plus coinces dans les tuyaux.

### Lumieres

Les pieces lumineuses (neons roses, cyan, anneaux blancs, feu orange, soleil de la sphere Dyson)
ont une texture branchee sur Emissive Color : elles brillent des l'import. Pour les faire briller
plus fort, ouvre le materiau et multiplie l'emissive (Multiply par 5 a 20).

### Eau animee

L'eau (Eau_Cyan, Eau_Bleue, Eau_Cyber) a une texture de vagues. Pour la faire bouger : ouvre le
materiau, ajoute un noeud Panner (Speed X = 0.05, Speed Y = 0.02) branche sur le UV de la texture.

### Fumee (optionnel)

1. Content Browser > clic droit > FX > Niagara System > "New system from template" > Fountain.
   Nomme-le exactement `VFX_Fumee`, a la racine de Content. Reglages conseilles : couleur grise,
   vitesse vers le haut (Z = 150), gravite 0, taille qui grandit avec le temps, duree de vie 3 s.
2. Ajoute `fumee.verse` au projet, Build Verse Code, place le device `fumee_device` dans la map et
   choisis ton device `power_city` dans son champ PowerCity.
3. Pour chaque batiment a cheminee, recopie ses points dans PointsFumee (fichier
   `modeles/points_fumee.txt`, deja en cm et dans le repere UEFN).

### Materiau maitre (optionnel, pour aller plus loin)

Les .fbx marchent tels quels (une texture de couleur par materiau). Si tu preferes un seul
materiau maitre plus leger : le dossier `modeles/materiau_maitre/` contient les masques en niveaux
de gris (studs, losanges, chevrons, dalles, damier, vagues) et `materiaux.csv` (pour chaque
materiau : sa couleur, son masque, son intensite, son emission).
1. Importe les masques. Cree un materiau `M_PowerCity` : Texture Sample (parametre "Masque")
   x Vector Parameter "Couleur" x Scalar Parameter "Intensite" -> Base Color ;
   Vector Parameter "Couleur" x Scalar Parameter "Emission" -> Emissive Color.
2. Pour chaque ligne de `materiaux.csv`, cree une Material Instance de M_PowerCity avec la couleur,
   le masque, l'intensite et l'emission du tableau, et remplace le materiau du meme nom sur les meshes.
3. Changer une couleur = changer un parametre de l'instance, sans repasser par Blender.
