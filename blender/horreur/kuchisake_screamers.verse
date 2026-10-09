# Screamers de Kuchisake-onna pour l'hopital psychiatrique (UEFN / Verse).
#
# 1. Verse Explorer > clic droit sur ton projet > "Add new Verse file" > colle tout ce fichier
# 2. Verse > "Build Verse Code"
# 3. Glisse le device "kuchisake_screamers" dans la map et remplis la liste "Screamers"
#    (une ligne par screamer : la zone, l'apparition, le cri, les lampes a eteindre).

using { /Fortnite.com/Devices }
using { /Verse.org/Simulation }
using { /Verse.org/Random }

# Un screamer = une zone qui declenche une apparition (sequence cinematique) + un cri.
screamer := class<concrete>:
    # la zone ou le joueur doit entrer (Trigger device)
    @editable
    Zone : trigger_device = trigger_device{}

    # la sequence ou Kuchisake apparait (Cinematic Sequence device)
    @editable
    Apparition : cinematic_sequence_device = cinematic_sequence_device{}

    # le cri / le bruit (Audio Player device)
    @editable
    Cri : audio_player_device = audio_player_device{}

    # les lampes qui s'eteignent pendant le screamer (Customizable Light devices)
    @editable
    LampesAEteindre : []customizable_light_device = array{}

    # attente avant le screamer, en secondes (0.5 a 2 = le joueur croit qu'il ne se passe rien)
    @editable
    Attente : float = 0.0

    # duree du noir (les lampes se rallument apres)
    @editable
    DureeDuNoir : float = 2.5

    # 0 = le screamer ne marche qu'une fois ; sinon il revient apres ce nombre de secondes
    @editable
    Recharge : float = 0.0


kuchisake_screamers := class(creative_device):

    # la liste des screamers de la map
    @editable
    Screamers : []screamer = array{}

    # les neons qui clignotent tout le temps
    @editable
    LampesQuiClignotent : []customizable_light_device = array{}

    # chuchotements, pas, rires... joues au hasard pendant la partie
    @editable
    BruitsAuHasard : []audio_player_device = array{}

    @editable
    BruitMin : float = 20.0

    @editable
    BruitMax : float = 50.0

    OnBegin<override>()<suspends> : void =
        for (S : Screamers):
            spawn{ Surveiller(S) }
        spawn{ Clignoter() }
        BruitsDeFond()

    Surveiller(S : screamer)<suspends> : void =
        loop:
            S.Zone.TriggeredEvent.Await()
            if (S.Attente > 0.0):
                Sleep(S.Attente)
            for (L : S.LampesAEteindre):
                L.TurnOff()
            S.Cri.Play()
            S.Apparition.Play()
            Sleep(S.DureeDuNoir)
            for (L : S.LampesAEteindre):
                L.TurnOn()
            if (S.Recharge <= 0.0):
                S.Zone.Disable()
                break
            Sleep(S.Recharge)

    Clignoter()<suspends> : void =
        loop:
            Sleep(GetRandomFloat(0.05, 0.6))
            for (L : LampesQuiClignotent):
                if (GetRandomInt(0, 4) = 0):
                    L.TurnOff()
                else:
                    L.TurnOn()

    BruitsDeFond()<suspends> : void =
        loop:
            Sleep(GetRandomFloat(BruitMin, BruitMax))
            if (BruitsAuHasard.Length > 0):
                Index := GetRandomInt(0, BruitsAuHasard.Length - 1)
                if (Bruit := BruitsAuHasard[Index]):
                    Bruit.Play()
