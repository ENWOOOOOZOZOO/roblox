# POWER A CITY - fumee des cheminees (OPTIONNEL)
#
# N'ajoute ce fichier qu'apres avoir cree l'effet de fumee "VFX_Fumee" (un Niagara System a la
# racine du dossier Content de ton projet, voir INSTALL.md). Sans cet effet, ce fichier ne compile pas.
#
# A chaque batiment pose, une fumee apparait en haut de chacune de ses cheminees (PointsFumee).

using { /Fortnite.com/Devices }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /UnrealEngine.com/Assets }

fumee_device := class(creative_device):

    # le device power_city de la map
    @editable
    PowerCity : power_city = power_city{}

    OnBegin<override>()<suspends> : void =
        loop:
            Pose := PowerCity.BatimentPose.Await()
            Batiment := Pose(0)
            T := Pose(1)
            for (Point : Batiment.PointsFumee):
                SpawnParticleSystem(VFX_Fumee, T.Translation + T.Rotation.RotateVector(Point))
