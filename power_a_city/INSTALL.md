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
Les lumieres (rose, cyan, blanc...) sont des materiaux "emission" : si elles ne brillent pas dans
UEFN, ouvre le materiau et branche la couleur sur Emissive Color.
