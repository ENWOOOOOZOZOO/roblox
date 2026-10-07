-- Les 30 outils pour casser, du moins fort au plus fort.
-- Puissance : degats par coup. Cadence : secondes entre deux coups. Prix : en Pieces.
-- Modele : nom du fichier .glb (blender/outils/).

local Outils = {}

Outils.Liste = {
	{ Numero = 1, Nom = "Pioche en bois", Rarete = "Commun", Prix = 0, Puissance = 1, Cadence = 1.0, Modele = "outil_01_pioche_en_bois" },
	{ Numero = 2, Nom = "Pelle en bois", Rarete = "Commun", Prix = 60, Puissance = 1, Cadence = 0.98, Modele = "outil_02_pelle_en_bois" },
	{ Numero = 3, Nom = "Pioche en pierre", Rarete = "Commun", Prix = 93, Puissance = 2, Cadence = 0.96, Modele = "outil_03_pioche_en_pierre" },
	{ Numero = 4, Nom = "Marteau de pierre", Rarete = "Commun", Prix = 140, Puissance = 2, Cadence = 0.93, Modele = "outil_04_marteau_de_pierre" },
	{ Numero = 5, Nom = "Pioche en cuivre", Rarete = "Commun", Prix = 220, Puissance = 3, Cadence = 0.91, Modele = "outil_05_pioche_en_cuivre" },
	{ Numero = 6, Nom = "Pelle en fer", Rarete = "Commun", Prix = 350, Puissance = 4, Cadence = 0.89, Modele = "outil_06_pelle_en_fer" },
	{ Numero = 7, Nom = "Pioche en fer", Rarete = "Peu commun", Prix = 540, Puissance = 6, Cadence = 0.87, Modele = "outil_07_pioche_en_fer" },
	{ Numero = 8, Nom = "Hache de fer", Rarete = "Peu commun", Prix = 830, Puissance = 8, Cadence = 0.85, Modele = "outil_08_hache_de_fer" },
	{ Numero = 9, Nom = "Marteau de géologue", Rarete = "Peu commun", Prix = 1300, Puissance = 11, Cadence = 0.82, Modele = "outil_09_marteau_de_geologue" },
	{ Numero = 10, Nom = "Pioche en or", Rarete = "Peu commun", Prix = 2000, Puissance = 15, Cadence = 0.8, Modele = "outil_10_pioche_en_or" },
	{ Numero = 11, Nom = "Masse en or", Rarete = "Peu commun", Prix = 3100, Puissance = 20, Cadence = 0.78, Modele = "outil_11_masse_en_or" },
	{ Numero = 12, Nom = "Pioche de glace", Rarete = "Rare", Prix = 4800, Puissance = 27, Cadence = 0.76, Modele = "outil_12_pioche_de_glace" },
	{ Numero = 13, Nom = "Foreuse a main", Rarete = "Rare", Prix = 7400, Puissance = 37, Cadence = 0.74, Modele = "outil_13_foreuse_a_main" },
	{ Numero = 14, Nom = "Pioche en os", Rarete = "Rare", Prix = 12000, Puissance = 49, Cadence = 0.71, Modele = "outil_14_pioche_en_os" },
	{ Numero = 15, Nom = "Pioche de jade", Rarete = "Rare", Prix = 18000, Puissance = 67, Cadence = 0.69, Modele = "outil_15_pioche_de_jade" },
	{ Numero = 16, Nom = "Marteau-piqueur", Rarete = "Rare", Prix = 28000, Puissance = 90, Cadence = 0.67, Modele = "outil_16_marteau_piqueur" },
	{ Numero = 17, Nom = "Pioche en diamant", Rarete = "Epique", Prix = 43000, Puissance = 120, Cadence = 0.65, Modele = "outil_17_pioche_en_diamant" },
	{ Numero = 18, Nom = "Hache double de rubis", Rarete = "Epique", Prix = 67000, Puissance = 160, Cadence = 0.63, Modele = "outil_18_hache_double_de_rubis" },
	{ Numero = 19, Nom = "Pioche en améthyste", Rarete = "Epique", Prix = 100000, Puissance = 220, Cadence = 0.6, Modele = "outil_19_pioche_en_amethyste" },
	{ Numero = 20, Nom = "Pioche de lave", Rarete = "Epique", Prix = 160000, Puissance = 300, Cadence = 0.58, Modele = "outil_20_pioche_de_lave" },
	{ Numero = 21, Nom = "Trident tellurique", Rarete = "Epique", Prix = 250000, Puissance = 400, Cadence = 0.56, Modele = "outil_21_trident_tellurique" },
	{ Numero = 22, Nom = "Pioche électrique", Rarete = "Legendaire", Prix = 380000, Puissance = 550, Cadence = 0.54, Modele = "outil_22_pioche_electrique" },
	{ Numero = 23, Nom = "Pioche T-Rex", Rarete = "Legendaire", Prix = 600000, Puissance = 740, Cadence = 0.52, Modele = "outil_23_pioche_t_rex" },
	{ Numero = 24, Nom = "Foreuse turbo", Rarete = "Legendaire", Prix = 920000, Puissance = 990, Cadence = 0.49, Modele = "outil_24_foreuse_turbo" },
	{ Numero = 25, Nom = "Faux de l'ombre", Rarete = "Legendaire", Prix = 1400000, Puissance = 1300, Cadence = 0.47, Modele = "outil_25_faux_de_lombre" },
	{ Numero = 26, Nom = "Marteau du tonnerre", Rarete = "Legendaire", Prix = 2200000, Puissance = 1800, Cadence = 0.45, Modele = "outil_26_marteau_du_tonnerre" },
	{ Numero = 27, Nom = "Pioche cosmique", Rarete = "Mythique", Prix = 3400000, Puissance = 2400, Cadence = 0.43, Modele = "outil_27_pioche_cosmique" },
	{ Numero = 28, Nom = "Pioche arc-en-ciel", Rarete = "Mythique", Prix = 5300000, Puissance = 3300, Cadence = 0.41, Modele = "outil_28_pioche_arc_en_ciel" },
	{ Numero = 29, Nom = "Pioche du dragon", Rarete = "Mythique", Prix = 8300000, Puissance = 4500, Cadence = 0.38, Modele = "outil_29_pioche_du_dragon" },
	{ Numero = 30, Nom = "Pioche du Roi Fossile", Rarete = "Secret", Prix = 13000000, Puissance = 6000, Cadence = 0.36, Modele = "outil_30_pioche_du_roi_fossile" },
}

function Outils.Trouver(nom)
	for _, outil in ipairs(Outils.Liste) do
		if outil.Nom == nom then
			return outil
		end
	end
	return nil
end

-- Degats par seconde, pratique pour comparer deux outils.
function Outils.DegatsParSeconde(outil)
	return outil.Puissance / outil.Cadence
end

return Outils
