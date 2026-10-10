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
