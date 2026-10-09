# Hôpital psychiatrique Sakura : guide des screamers (UEFN)

## 1. Mettre la map dans ton île

1. Content Browser > **Import** > `hopital.fbx`.
2. Glisse les 4 meshes dans la map (`Murs_Sols`, `Plafonds_Toit`, `Mobilier`, `Ecritures`).
   Mets-les **tous** à la position **0, 0, 0** : tout s'emboîte tout seul.
3. Pour chaque mesh : double-clic > **Collision Complexity = Use Complex Collision As Simple**.
   Sinon on passe à travers les murs.
4. Les textures `*_normal` : double-clic > coche **Flip Green Channel**.
5. Les lumières : pose des **Customizable Light** sous les néons du plafond.
   **Ne mets aucune lumière dans le couloir est** (entre la DAY ROOM et les SHOWERS / OPERATING ROOM) :
   c'est la **zone noire**, on y avance à la lampe torche.

## 2. Les cachettes

- **6 casiers** dans le couloir ouest (entre DIRECTOR / ARCHIVES et la DAY ROOM). Le 3e est grand ouvert.
- **4 casiers** dans le vestiaire des SHOWERS.
- La **grande armoire** du bureau du DIRECTOR.
- Sous les lits du DORMITORY.

## 3. Les screamers (un par endroit)

Pour chaque screamer, il te faut :

- un **Trigger** (la zone où le joueur marche) ;
- un **Cinematic Sequence** (l'apparition de Kuchisake) ;
- un **Audio Player** (le cri).

Ensuite, ajoute une ligne dans le device Verse `kuchisake_screamers`.

| # | Où | Le déclencheur | Ce qui se passe |
|---|----|----------------|-----------------|
| 1 | Sortie de la RECEPTION vers le couloir | en passant sous l'arche | Les néons clignotent. Elle est au fond du couloir sous un néon (anim **Attente**). Noir d'1 s, puis elle a disparu. |
| 2 | L'**éboulement** (plafond effondré au milieu du couloir) | dans le passage étroit, devant la ROOM 7 | Elle se jette hors de la ROOM 7 (anim **Attaque**) + cri. |
| 3 | ROOM 6 (« HELP ME ») | au fond de la chambre, devant l'écriture | Quand le joueur se retourne, elle est dans l'encadrement de la porte (anim **Regard**). |
| 4 | Les **casiers** du couloir ouest | en passant devant le casier ouvert | Une porte de casier claque, elle sort du casier (anim **Attaque**). |
| 5 | Le **rideau** du DORMITORY (le lit près du mur du fond) | à 2 m du rideau | Sa silhouette derrière le rideau, les lumières s'éteignent, elle surgit. |
| 6 | Le **grand miroir** des SHOWERS | devant les lavabos | Elle apparaît 0,5 s **derrière le joueur** : on ne la voit que dans le miroir. |
| 7 | **« AM I PRETTY? »** (mur du fond de la DAY ROOM) | devant l'écriture | Noir. On entend « Am I pretty? ». Les lumières reviennent : elle est juste derrière (version masque, anim **Jolie**). |
| 8 | La **MORGUE** | près de la table d'autopsie | Le corps sous le drap sur le brancard se redresse : c'est elle (anim **Attaque**). |
| 9 | L'**OPERATING ROOM** | en entrant | La machine à électrochocs grésille, elle est assise sur la table d'opération. |
| 10 | La cellule **ISOLATION** (murs couverts de « AM I PRETTY? ») | au milieu de la cellule | La porte claque, noir de 3 s, rire. |
| 11 | La porte **EXIT** condamnée (fond du couloir ouest) | devant la porte | Elle frappe contre le hublot de la porte, son visage collé à la vitre. |

### Faire une apparition (Cinematic Sequence)

1. Pose Kuchisake (le Skeletal Mesh) à l'endroit du screamer. Dans ses détails, coche **Actor Hidden In Game**.
2. Crée un **Level Sequence**, et ajoute Kuchisake dedans (+ Track > Actor).
3. Ajoute une piste **Visibility** : visible à 0 s, cachée à la fin (vers 1,5 s).
4. Ajoute une piste **Animation** avec l'anim voulue (Attaque, Regard, Jolie…).
5. Mets ce Level Sequence dans un **Cinematic Sequence device**, puis relie ce device au screamer dans le device Verse.

### Les réglages qui font peur

- **Attente** : 0,5 à 1,5 s. Le joueur croit qu'il ne s'est rien passé, et là…
- **DureeDuNoir** : 1 à 3 s de noir total pendant le cri.
- **Recharge** = 0 : chaque screamer ne marche qu'**une fois**. C'est plus fort quand on ne s'y attend pas.
- **BruitsAuHasard** : chuchotements, pas, rires d'enfant, porte qui grince, battements de cœur.
  Ils se jouent toutes les 20 à 50 s, sans rien qui se passe : le joueur stresse tout le temps.
- **LampesQuiClignotent** : mets 3-4 néons du couloir principal et du hall.

Dans la bibliothèque audio d'UEFN, cherche : `scream`, `whisper`, `heartbeat`, `door slam`, `electric`, `footsteps`.
