# SAKURA - AM I PRETTY?   (jeu d'horreur pour l'hopital psychiatrique, UEFN / Verse)
#
# But du jeu : trouver les fusibles caches dans l'hopital, les poser dans la boite a fusibles
# pour rallumer le courant, puis s'echapper par la porte EXIT... sans se faire attraper.
#
# Kuchisake-onna fait sa ronde. Si elle te voit, elle te poursuit. Si elle t'attrape, elle demande
# "AM I PRETTY?" et tu dois choisir :
#   NO                   -> elle te tue
#   YES                  -> elle enleve son masque : "EVEN NOW?" ... (oui ou non = elle te tue)
#   YOU LOOK... AVERAGE  -> elle ne sait plus quoi dire : tu as 6 secondes pour fuir (1 fois par joueur)
#   THROW A CANDY        -> elle ramasse le bonbon : 10 secondes pour fuir (il faut en avoir trouve)
#   pas de reponse       -> elle te tue
#
# Installation : voir JEU.md (a cote de ce fichier).

using { /Fortnite.com/Devices }
using { /Fortnite.com/Characters }
using { /Fortnite.com/AI }
using { /Fortnite.com/UI }
using { /Verse.org/Simulation }
using { /Verse.org/Random }
using { /Verse.org/Colors }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /UnrealEngine.com/Temporary/UI }

TexteUI<localizes>(S : string) : message = "{S}"

# Un objet a ramasser (fusible ou bonbon) : un bouton (pour le prendre) + le prop qu'on voit.
objet_a_ramasser := class<concrete>:
    @editable
    Bouton : button_device = button_device{}

    @editable
    Modele : creative_prop = creative_prop{}

# Sert a savoir quel objet a ete ramasse quand on appuie sur son bouton.
ramassage := class:
    Jeu : sakura_jeu
    Objet : objet_a_ramasser
    EstUnFusible : logic

    Quand(Agent : agent) : void =
        Jeu.Ramasser(Agent, Objet, EstUnFusible)


sakura_jeu := class(creative_device):

    # ---------------- Kuchisake-onna ----------------
    # le NPC Spawner qui fait apparaitre Kuchisake
    @editable
    Kuchisake : npc_spawner_device = npc_spawner_device{}

    # des petits props invisibles poses dans les couloirs et les salles : son chemin de ronde
    @editable
    PointsDeRonde : []creative_prop = array{}

    # distance a laquelle elle te voit (en cm : 1500 = 15 m)
    @editable
    DistanceDeVue : float = 1500.0

    # distance a laquelle elle t'attrape
    @editable
    DistanceAttrape : float = 220.0

    # temps (secondes) pour repondre a sa question
    @editable
    TempsPourRepondre : float = 8.0

    # ---------------- objectifs ----------------
    # tous les endroits possibles pour les fusibles (le jeu en choisit quelques-uns au hasard)
    @editable
    Fusibles : []objet_a_ramasser = array{}

    @editable
    NombreDeFusibles : int = 3

    # les bonbons a ramasser
    @editable
    Bonbons : []objet_a_ramasser = array{}

    # le bouton de la boite a fusibles
    @editable
    BoiteAFusibles : button_device = button_device{}

    # la barriere invisible devant la porte EXIT (elle disparait quand le courant revient)
    @editable
    PorteDeSortie : barrier_device = barrier_device{}

    # la zone juste derriere la porte EXIT
    @editable
    ZoneDeSortie : trigger_device = trigger_device{}

    @editable
    Victoire : end_game_device = end_game_device{}

    @editable
    Defaite : end_game_device = end_game_device{}

    # ---------------- ambiance ----------------
    # tous les neons de l'hopital (Customizable Light)
    @editable
    Lampes : []customizable_light_device = array{}

    @editable
    SonCoeur : audio_player_device = audio_player_device{}

    # sa voix : "Am I pretty?"
    @editable
    SonQuestion : audio_player_device = audio_player_device{}

    @editable
    SonCri : audio_player_device = audio_player_device{}

    @editable
    SonChuchotement : audio_player_device = audio_player_device{}

    @editable
    SonCourant : audio_player_device = audio_player_device{}

    # screamer quand elle te tue (Cinematic Sequence : Kuchisake bouche ouverte devant la camera)
    @editable
    ScreamerMort : cinematic_sequence_device = cinematic_sequence_device{}

    # elle enleve son masque (Cinematic Sequence avec l'animation "Jolie")
    @editable
    EnleveSonMasque : cinematic_sequence_device = cinematic_sequence_device{}

    # ---------------- etat du jeu ----------------
    var KuchiPerso : ?fort_character = false
    var FusiblesTrouves : int = 0
    var Courant : logic = false
    var Occupee : logic = false
    var PointActuel : int = 0
    var VueActuelle : float = 0.0
    var BonbonsDe : [player]int = map{}
    var MoyenneUtilisee : [player]logic = map{}
    var Objectifs : [player]text_block = map{}
    var Annonces : [player]text_block = map{}

    OnBegin<override>()<suspends> : void =
        set VueActuelle = DistanceDeVue
        Kuchisake.SpawnedEvent.Subscribe(QuandKuchisakeApparait)
        BoiteAFusibles.InteractedWithEvent.Subscribe(QuandBoiteAFusibles)
        ZoneDeSortie.TriggeredEvent.Subscribe(QuandSortie)
        PorteDeSortie.Enable()
        PreparerObjets()
        for (P : GetPlayspace().GetPlayers()):
            CreerHud(P)
        GetPlayspace().PlayerAddedEvent().Subscribe(CreerHud)
        Kuchisake.Spawn()
        Sleep(2.0)
        Annoncer("FIND {NombreDeFusibles} FUSES AND RESTORE THE POWER")
        Sleep(4.0)
        Annoncer("DON'T LET HER CATCH YOU...")
        spawn{ Lumieres() }
        spawn{ Coeur() }
        spawn{ Apparitions() }
        BoucleKuchisake()

    # ---------------- objets ----------------
    PreparerObjets() : void =
        Melange := Shuffle(Fusibles)
        for (I -> F : Melange):
            if (I < NombreDeFusibles):
                F.Modele.Show()
                F.Bouton.Enable()
                F.Bouton.InteractedWithEvent.Subscribe(ramassage{Jeu := Self, Objet := F, EstUnFusible := true}.Quand)
            else:
                F.Modele.Hide()
                F.Bouton.Disable()
        for (B : Bonbons):
            B.Modele.Show()
            B.Bouton.Enable()
            B.Bouton.InteractedWithEvent.Subscribe(ramassage{Jeu := Self, Objet := B, EstUnFusible := false}.Quand)

    Ramasser(Agent : agent, Objet : objet_a_ramasser, EstUnFusible : logic) : void =
        Objet.Modele.Hide()
        Objet.Bouton.Disable()
        if (EstUnFusible?):
            set FusiblesTrouves += 1
            Annoncer("FUSE FOUND ({FusiblesTrouves}/{NombreDeFusibles})")
        else if (P := player[Agent]):
            Avant := if (N := BonbonsDe[P]) then N else 0
            if (set BonbonsDe[P] = Avant + 1) {}
        for (P -> T : Objectifs):
            MettreAJourHud(P)

    QuandBoiteAFusibles(Agent : agent) : void =
        if (Courant?):
            return
        if (FusiblesTrouves >= NombreDeFusibles):
            set Courant = true
            set VueActuelle = 100000.0          # maintenant elle sait ou tu es...
            SonCourant.Play()
            PorteDeSortie.Disable()
            for (L : Lampes):
                L.TurnOn()
            Annoncer("POWER RESTORED! RUN TO THE EXIT!")
            for (P -> T : Objectifs):
                MettreAJourHud(P)
        else:
            Annoncer("YOU NEED {NombreDeFusibles} FUSES ({FusiblesTrouves}/{NombreDeFusibles})")

    QuandSortie(MaybeAgent : ?agent) : void =
        if (Courant?, Agent := MaybeAgent?):
            Victoire.Activate(Agent)

    # ---------------- interface ----------------
    CreerHud(P : player) : void =
        if (UI := GetPlayerUI[P]):
            Objectif := text_block{DefaultTextColor := NamedColors.White}
            Annonce := text_block{DefaultTextColor := NamedColors.Red}
            Cadre := canvas:
                Slots := array:
                    canvas_slot:
                        Anchors := anchors{Minimum := vector2{X := 0.03, Y := 0.06}, Maximum := vector2{X := 0.03, Y := 0.06}}
                        SizeToContent := true
                        Widget := Objectif
                    canvas_slot:
                        Anchors := anchors{Minimum := vector2{X := 0.5, Y := 0.25}, Maximum := vector2{X := 0.5, Y := 0.25}}
                        Alignment := vector2{X := 0.5, Y := 0.5}
                        SizeToContent := true
                        Widget := Annonce
            UI.AddWidget(Cadre)
            if (set Objectifs[P] = Objectif, set Annonces[P] = Annonce) {}
            MettreAJourHud(P)

    MettreAJourHud(P : player) : void =
        Nb := if (N := BonbonsDe[P]) then N else 0
        if (T := Objectifs[P]):
            if (Courant?):
                T.SetText(TexteUI("RUN TO THE EXIT!      CANDIES: {Nb}"))
            else:
                T.SetText(TexteUI("FUSES: {FusiblesTrouves}/{NombreDeFusibles}      CANDIES: {Nb}"))

    Annoncer(Texte : string) : void =
        for (P -> T : Annonces):
            T.SetText(TexteUI(Texte))
        spawn{ EffacerAnnonce(Texte) }

    EffacerAnnonce(Texte : string)<suspends> : void =
        Sleep(4.0)
        for (P -> T : Annonces):
            T.SetText(TexteUI(""))

    # La question de Kuchisake : renvoie 1 = YES, 2 = NO, 3 = AVERAGE, 4 = CANDY, 0 = pas de reponse
    Question(Victime : player, Texte : string)<suspends> : int =
        if (UI := GetPlayerUI[Victime]):
            Titre := text_block{DefaultText := TexteUI(Texte), DefaultTextColor := NamedColors.Red}
            BoutonOui := button_loud{DefaultText := TexteUI("YES")}
            BoutonNon := button_loud{DefaultText := TexteUI("NO")}
            BoutonMoyenne := button_quiet{DefaultText := TexteUI("YOU LOOK... AVERAGE")}
            BoutonBonbon := button_quiet{DefaultText := TexteUI("THROW A CANDY")}
            Marge := margin{Left := 25.0, Right := 25.0}
            var Choix : []stack_box_slot = array:
                stack_box_slot{Widget := BoutonOui, Padding := Marge}
                stack_box_slot{Widget := BoutonNon, Padding := Marge}
            if (not MoyenneUtilisee[Victime]?):
                set Choix += array{stack_box_slot{Widget := BoutonMoyenne, Padding := Marge}}
            if (N := BonbonsDe[Victime], N > 0):
                set Choix += array{stack_box_slot{Widget := BoutonBonbon, Padding := Marge}}
            Ecran := canvas:
                Slots := array:
                    canvas_slot:
                        Anchors := anchors{Minimum := vector2{X := 0.5, Y := 0.35}, Maximum := vector2{X := 0.5, Y := 0.35}}
                        Alignment := vector2{X := 0.5, Y := 0.5}
                        SizeToContent := true
                        Widget := Titre
                    canvas_slot:
                        Anchors := anchors{Minimum := vector2{X := 0.5, Y := 0.65}, Maximum := vector2{X := 0.5, Y := 0.65}}
                        Alignment := vector2{X := 0.5, Y := 0.5}
                        SizeToContent := true
                        Widget := stack_box{Orientation := orientation.Horizontal, Slots := Choix}
            UI.AddWidget(Ecran, player_ui_slot{InputMode := ui_input_mode.All})
            Reponse := race:
                block:
                    BoutonOui.OnClick().Await()
                    1
                block:
                    BoutonNon.OnClick().Await()
                    2
                block:
                    BoutonMoyenne.OnClick().Await()
                    3
                block:
                    BoutonBonbon.OnClick().Await()
                    4
                block:
                    Sleep(TempsPourRepondre)
                    0
            UI.RemoveWidget(Ecran)
            Reponse
        else:
            0

    # ---------------- Kuchisake-onna ----------------
    QuandKuchisakeApparait(Agent : agent) : void =
        if (C := Agent.GetFortCharacter[]):
            set KuchiPerso = option{C}

    JoueurLePlusProche(Pos : vector3) : ?player =
        var Meilleur : ?player = false
        var DMin : float = 100000000.0
        for (P : GetPlayspace().GetPlayers(), C := P.GetFortCharacter[], C.IsActive[]):
            D := Distance(Pos, C.GetTransform().Translation)
            if (D < DMin):
                set DMin = D
                set Meilleur = option{P}
        Meilleur

    BoucleKuchisake()<suspends> : void =
        loop:
            Sleep(0.2)
            if (Kuchi := KuchiPerso?, Nav := Kuchi.GetNavigatable[]):
                Pos := Kuchi.GetTransform().Translation
                if (Victime := JoueurLePlusProche(Pos)?, VC := Victime.GetFortCharacter[]):
                    D := Distance(Pos, VC.GetTransform().Translation)
                    if (D < DistanceAttrape):
                        Nav.StopNavigation()
                        Attraper(Victime, Nav)
                    else if (D < VueActuelle):
                        race:
                            Nav.NavigateTo(MakeNavigationTarget(Victime), ?MovementType := movement_types.Running)
                            Sleep(0.4)
                    else:
                        Ronde(Kuchi, Nav)
                else:
                    Ronde(Kuchi, Nav)

    Ronde(Kuchi : fort_character, Nav : navigatable)<suspends> : void =
        if (Point := PointsDeRonde[PointActuel]):
            Cible := Point.GetTransform().Translation
            if (Distance(Kuchi.GetTransform().Translation, Cible) < 250.0):
                set PointActuel = GetRandomInt(0, PointsDeRonde.Length - 1)
            race:
                Nav.NavigateTo(MakeNavigationTarget(Cible), ?MovementType := movement_types.Walking)
                Sleep(0.5)
        else:
            Sleep(0.5)

    Attraper(Victime : player, Nav : navigatable)<suspends> : void =
        set Occupee = true
        SonQuestion.Play()
        Reponse := Question(Victime, "AM I PRETTY?")
        if (Reponse = 1):
            # elle enleve son masque...
            EnleveSonMasque.Play(Victime)
            Sleep(2.5)
            SonQuestion.Play()
            Reponse2 := Question(Victime, "EVEN NOW?")
            if (Reponse2 = 3 or Reponse2 = 4):
                Echapper(Victime, Reponse2, Nav)
            else:
                Mourir(Victime)
        else if (Reponse = 3 or Reponse = 4):
            Echapper(Victime, Reponse, Nav)
        else:
            Mourir(Victime)
        set Occupee = false

    Echapper(Victime : player, Reponse : int, Nav : navigatable)<suspends> : void =
        Nav.StopNavigation()
        if (Reponse = 3):
            if (set MoyenneUtilisee[Victime] = true) {}
            AnnoncerA(Victime, "SHE DOESN'T KNOW WHAT TO SAY... RUN!")
            Sleep(6.0)
        else:
            Avant := if (N := BonbonsDe[Victime]) then N else 0
            if (set BonbonsDe[Victime] = Max(0, Avant - 1)) {}
            MettreAJourHud(Victime)
            AnnoncerA(Victime, "SHE PICKS UP THE CANDY... RUN!")
            Sleep(10.0)

    AnnoncerA(P : player, Texte : string) : void =
        if (T := Annonces[P]):
            T.SetText(TexteUI(Texte))
        spawn{ EffacerAnnonce(Texte) }

    Mourir(Victime : player)<suspends> : void =
        ScreamerMort.Play(Victime)
        SonCri.Play()
        Sleep(1.2)
        if (C := Victime.GetFortCharacter[]):
            C.Damage(1000.0)
        Sleep(1.0)
        Vivants := for (P : GetPlayspace().GetPlayers(), C := P.GetFortCharacter[], C.IsActive[]):
            P
        if (Vivants.Length = 0):
            Defaite.Activate(Victime)

    # ---------------- ambiance ----------------
    # les neons clignotent pres d'elle (et un peu partout tant qu'il n'y a pas de courant)
    Lumieres()<suspends> : void =
        loop:
            Sleep(GetRandomFloat(0.08, 0.35))
            PosK := if (C := KuchiPerso?) then C.GetTransform().Translation else vector3{X := 0.0, Y := 0.0, Z := -100000.0}
            for (L : Lampes):
                D := Distance(L.GetTransform().Translation, PosK)
                if (D < 1200.0, GetRandomInt(0, 2) = 0):
                    L.TurnOff()
                else if (not Courant?, GetRandomInt(0, 15) = 0):
                    L.TurnOff()
                else:
                    L.TurnOn()

    # battement de coeur quand elle est a moins de 15 m d'un joueur
    Coeur()<suspends> : void =
        var Joue : logic = false
        loop:
            Sleep(0.5)
            Proche : logic = if (C := KuchiPerso?, P := JoueurLePlusProche(C.GetTransform().Translation)?,
                                 PC := P.GetFortCharacter[],
                                 Distance(C.GetTransform().Translation, PC.GetTransform().Translation) < 1500.0) then true else false
            if (Proche?, not Joue?):
                SonCoeur.Play()
                set Joue = true
            else if (not Proche?, Joue?):
                SonCoeur.Stop()
                set Joue = false

    # de temps en temps, elle disparait et reapparait pas loin d'un joueur (8 a 20 m)
    Apparitions()<suspends> : void =
        loop:
            Sleep(GetRandomFloat(60.0, 100.0))
            Joueurs := GetPlayspace().GetPlayers()
            if (Kuchi := KuchiPerso?, not Occupee?, Joueurs.Length > 0,
                Victime := Joueurs[GetRandomInt(0, Joueurs.Length - 1)],
                VC := Victime.GetFortCharacter[], VC.IsActive[]):
                PV := VC.GetTransform().Translation
                var Choisi : ?vector3 = false
                for (Pt : Shuffle(PointsDeRonde)):
                    Q := Pt.GetTransform().Translation
                    D := Distance(Q, PV)
                    if (D > 800.0, D < 2000.0, not Choisi?):
                        set Choisi = option{Q}
                if (Q := Choisi?):
                    SonChuchotement.Play()
                    if (Kuchi.TeleportTo[Q, Kuchi.GetTransform().Rotation]) {}
