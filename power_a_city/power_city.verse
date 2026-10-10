# POWER A CITY  (UEFN / Verse)  -  grille de placement + production + jauge de Puissance
#
# Chaque joueur a une parcelle (4 au total). La parcelle est une grille de 8x8 cases maximum,
# dont 6x6 sont actives au depart. Chaque case a un bouton : on le "interagit" pour poser le
# batiment selectionne. Voir INSTALL.md pour monter les devices dans UEFN.

using { /Fortnite.com/Devices }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /UnrealEngine.com/Temporary/Diagnostics }

LargeurMax : int = 8

# Un type de batiment (a remplir dans le panneau de details du device).
batiment_def := class<concrete>:
    @editable
    Nom : string = "Eolienne"
    @editable
    Modele : creative_prop_asset = DefaultCreativePropAsset
    # nombre de cases occupees
    @editable
    Largeur : int = 1
    @editable
    Hauteur : int = 1
    @editable
    Prix : int = 100
    # Puissance fournie a la ville
    @editable
    Puissance : int = 2
    @editable
    ArgentParSeconde : int = 5

# Une case de la grille : un bouton + un prop invisible pose au centre de la case.
parcelle_case := class<concrete>:
    @editable
    Bouton : button_device = button_device{}
    @editable
    Repere : creative_prop = creative_prop{}

# Une parcelle (une par joueur). Les 64 cases vont dans l'ordre, ligne par ligne.
parcelle := class<concrete>:
    @editable
    Cases : []parcelle_case = array{}
    @editable
    Spawner : player_spawner_device = player_spawner_device{}
    @editable
    BoutonAgrandir : button_device = button_device{}

    var Proprietaire : ?agent = false
    var Taille : int = 6
    var Occupees : []logic = array{}

# Les donnees de chaque joueur.
joueur_data := class:
    var Argent : int
    var PuissanceProduite : int = 0
    var ArgentParSeconde : int = 0
    var Niveau : int = 1
    var Demande : int = 30

power_city := class(creative_device):

    @editable
    Parcelles : []parcelle = array{}
    @editable
    Batiments : []batiment_def = array{}
    # taille d'une case en cm (512 = 5 m)
    @editable
    TailleCase : float = 512.0
    @editable
    ArgentDepart : int = 1000
    @editable
    PrixAgrandirBase : int = 500
    # boutons de test : le bouton N choisit le batiment N (la Boutique appellera ChoisirBatiment)
    @editable
    BoutonsChoix : []button_device = array{}

    var Donnees : [agent]joueur_data = map{}
    var Selection : [agent]int = map{}

    OnBegin<override>()<suspends> : void =
        for (P : Parcelles):
            set P.Occupees = array{for (I := 0..LargeurMax * LargeurMax - 1): false}
            for (Index -> C : P.Cases):
                ActiverCase(P, Index)
                Handler(Agent : agent) : void = OnCase(P, Index, Agent)
                C.Bouton.InteractedWithEvent.Subscribe(Handler)
            HandlerSpawn(Agent : agent) : void = AssignerParcelle(P, Agent)
            P.Spawner.SpawnedEvent.Subscribe(HandlerSpawn)
            HandlerAgrandir(Agent : agent) : void = Agrandir(P, Agent)
            P.BoutonAgrandir.InteractedWithEvent.Subscribe(HandlerAgrandir)
        for (Index -> B : BoutonsChoix):
            HandlerChoix(Agent : agent) : void = ChoisirBatiment(Agent, Index)
            B.InteractedWithEvent.Subscribe(HandlerChoix)
        Boucle()

    # ---------- joueurs ----------
    DonneesDe(Agent : agent) : joueur_data =
        if (D := Donnees[Agent]):
            return D
        D := joueur_data{Argent := ArgentDepart}
        if (set Donnees[Agent] = D) {}
        return D

    AssignerParcelle(P : parcelle, Agent : agent) : void =
        if (not P.Proprietaire?):
            set P.Proprietaire = option{Agent}
            DonneesDe(Agent)
            Print("Parcelle assignee")

    # a appeler depuis la Boutique quand un joueur choisit un batiment
    ChoisirBatiment(Agent : agent, Index : int) : void =
        if (Batiments[Index]):
            if (set Selection[Agent] = Index) {}

    # ---------- grille ----------
    CaseActive(P : parcelle, Index : int)<decides><transacts> : void =
        X := Mod[Index, LargeurMax]
        Y := Quotient[Index, LargeurMax]
        X < P.Taille
        Y < P.Taille
        P.Occupees[Index] = false

    # active ou desactive le bouton selon que la case est dans la grille et libre
    ActiverCase(P : parcelle, Index : int) : void =
        if (C := P.Cases[Index]):
            if (CaseActive[P, Index]):
                C.Bouton.Enable()
            else:
                C.Bouton.Disable()

    # le batiment tient-il sur la grille, sur des cases libres ?
    PeutPoser(P : parcelle, X : int, Y : int, L : int, H : int)<decides><transacts> : void =
        X + L <= P.Taille
        Y + H <= P.Taille
        for (DY := 0..H - 1, DX := 0..L - 1):
            P.Occupees[(Y + DY) * LargeurMax + X + DX] = false

    OnCase(P : parcelle, Index : int, Agent : agent) : void =
        if (Proprio := P.Proprietaire?, Proprio = Agent,
            BIdx := Selection[Agent], B := Batiments[BIdx],
            X := Mod[Index, LargeurMax], Y := Quotient[Index, LargeurMax],
            D := Donnees[Agent], D.Argent >= B.Prix,
            PeutPoser[P, X, Y, B.Largeur, B.Hauteur],
            C := P.Cases[Index]):
            # marque les cases occupees
            for (DY := 0..B.Hauteur - 1, DX := 0..B.Largeur - 1):
                Cible := (Y + DY) * LargeurMax + X + DX
                if (set P.Occupees[Cible] = true) {}
                ActiverCase(P, Cible)
            # pose le modele, centre sur l'emprise du batiment
            T := C.Repere.GetTransform()
            Decalage := vector3{X := (B.Largeur - 1) * TailleCase / 2.0, Y := (B.Hauteur - 1) * TailleCase / 2.0, Z := 0.0}
            SpawnProp(B.Modele, T.Translation + Decalage, T.Rotation)
            set D.Argent -= B.Prix
            set D.PuissanceProduite += B.Puissance
            set D.ArgentParSeconde += B.ArgentParSeconde
            Print("{B.Nom} pose. Puissance {D.PuissanceProduite}/{D.Demande}, argent {D.Argent}")

    # agrandit la grille de 1 (6x6 -> 7x7 -> 8x8)
    Agrandir(P : parcelle, Agent : agent) : void =
        if (Proprio := P.Proprietaire?, Proprio = Agent, P.Taille < LargeurMax, D := Donnees[Agent]):
            Prix := PrixAgrandirBase * (P.Taille - 5)
            if (D.Argent >= Prix):
                set D.Argent -= Prix
                set P.Taille += 1
                for (Index -> _ : P.Cases):
                    ActiverCase(P, Index)
                Print("Parcelle agrandie : {P.Taille}x{P.Taille}")

    # ---------- economie et jauge de la ville ----------
    Boucle()<suspends> : void =
        loop:
            Sleep(1.0)
            for (Agent -> D : Donnees):
                set D.Argent += D.ArgentParSeconde
                if (D.PuissanceProduite >= D.Demande):
                    set D.Niveau += 1
                    set D.Demande += 15
                    Print("Ville niveau {D.Niveau} ! Nouvelle demande : {D.Demande}")
