-- Les 50 oeufs : chacun contient 3 ou 4 dinos, avec une chance en %.
-- Les 180 dinos sont repartis (chacun dans un seul oeuf), du plus commun au plus rare.
-- Modele : nom du fichier .glb (blender/oeufs50/).

local Oeufs = {}

Oeufs.Liste = {
	{
		Nom = "Oeuf de Sable", Rarete = "Commun", Prix = 100, Modele = "oeuf_01_oeuf_de_sable",
		Dinos = {
			{ Nom = "Compsognathus", Chance = 50 },
			{ Nom = "Protoceratops", Chance = 30 },
			{ Nom = "Gallimimus", Chance = 15 },
			{ Nom = "Iguanodon", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf de Prairie", Rarete = "Commun", Prix = 140, Modele = "oeuf_02_oeuf_de_prairie",
		Dinos = {
			{ Nom = "Eoraptor", Chance = 50 },
			{ Nom = "Microceratus", Chance = 30 },
			{ Nom = "Hypsilophodon", Chance = 15 },
			{ Nom = "Coelophysis", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf de Fougere", Rarete = "Commun", Prix = 190, Modele = "oeuf_03_oeuf_de_fougere",
		Dinos = {
			{ Nom = "Herrerasaurus", Chance = 50 },
			{ Nom = "Staurikosaurus", Chance = 30 },
			{ Nom = "Segisaurus", Chance = 15 },
			{ Nom = "Tawa", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf d'Argile", Rarete = "Commun", Prix = 260, Modele = "oeuf_04_oeuf_dargile",
		Dinos = {
			{ Nom = "Procompsognathus", Chance = 50 },
			{ Nom = "Lesothosaurus", Chance = 30 },
			{ Nom = "Heterodontosaurus", Chance = 15 },
			{ Nom = "Dryosaurus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf de Galet", Rarete = "Commun", Prix = 360, Modele = "oeuf_05_oeuf_de_galet",
		Dinos = {
			{ Nom = "Thescelosaurus", Chance = 50 },
			{ Nom = "Orodromeus", Chance = 30 },
			{ Nom = "Camptosaurus", Chance = 15 },
			{ Nom = "Tenontosaurus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf de Mousse", Rarete = "Commun", Prix = 500, Modele = "oeuf_06_oeuf_de_mousse",
		Dinos = {
			{ Nom = "Muttaburrasaurus", Chance = 50 },
			{ Nom = "Leptoceratops", Chance = 30 },
			{ Nom = "Bagaceratops", Chance = 15 },
			{ Nom = "Archaeoceratops", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf de Terre", Rarete = "Commun", Prix = 690, Modele = "oeuf_07_oeuf_de_terre",
		Dinos = {
			{ Nom = "Scelidosaurus", Chance = 50 },
			{ Nom = "Scutellosaurus", Chance = 30 },
			{ Nom = "Gargoyleosaurus", Chance = 15 },
			{ Nom = "Nodosaurus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf de Paille", Rarete = "Commun", Prix = 950, Modele = "oeuf_08_oeuf_de_paille",
		Dinos = {
			{ Nom = "Huayangosaurus", Chance = 50 },
			{ Nom = "Dacentrurus", Chance = 30 },
			{ Nom = "Plateosaurus", Chance = 15 },
			{ Nom = "Massospondylus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf du Marais", Rarete = "Commun", Prix = 1300, Modele = "oeuf_09_oeuf_du_marais",
		Dinos = {
			{ Nom = "Anchisaurus", Chance = 50 },
			{ Nom = "Riojasaurus", Chance = 30 },
			{ Nom = "Dimorphodon", Chance = 15 },
			{ Nom = "Rhamphorhynchus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf de Riviere", Rarete = "Commun", Prix = 1800, Modele = "oeuf_10_oeuf_de_riviere",
		Dinos = {
			{ Nom = "Pterodactylus", Chance = 50 },
			{ Nom = "Anurognathus", Chance = 30 },
			{ Nom = "Nothosaurus", Chance = 15 },
			{ Nom = "Mixosaurus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf de Savane", Rarete = "Peu commun", Prix = 2500, Modele = "oeuf_11_oeuf_de_savane",
		Dinos = {
			{ Nom = "Pachycephalosaurus", Chance = 50 },
			{ Nom = "Parasaurolophus", Chance = 30 },
			{ Nom = "Dilophosaurus", Chance = 15 },
			{ Nom = "Psittacosaurus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf de Bambou", Rarete = "Peu commun", Prix = 3500, Modele = "oeuf_12_oeuf_de_bambou",
		Dinos = {
			{ Nom = "Oviraptor", Chance = 50 },
			{ Nom = "Ceratosaurus", Chance = 30 },
			{ Nom = "Cryolophosaurus", Chance = 15 },
			{ Nom = "Monolophosaurus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf du Desert", Rarete = "Peu commun", Prix = 4800, Modele = "oeuf_13_oeuf_du_desert",
		Dinos = {
			{ Nom = "Guanlong", Chance = 50 },
			{ Nom = "Eustreptospondylus", Chance = 30 },
			{ Nom = "Megalosaurus", Chance = 15 },
			{ Nom = "Majungasaurus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf d'Ambre", Rarete = "Peu commun", Prix = 6600, Modele = "oeuf_14_oeuf_dambre",
		Dinos = {
			{ Nom = "Concavenator", Chance = 50 },
			{ Nom = "Sinraptor", Chance = 30 },
			{ Nom = "Corythosaurus", Chance = 15 },
			{ Nom = "Lambeosaurus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf de Canyon", Rarete = "Peu commun", Prix = 9100, Modele = "oeuf_15_oeuf_de_canyon",
		Dinos = {
			{ Nom = "Maiasaura", Chance = 50 },
			{ Nom = "Edmontosaurus", Chance = 30 },
			{ Nom = "Saurolophus", Chance = 15 },
			{ Nom = "Tsintaosaurus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf de la Grotte", Rarete = "Peu commun", Prix = 13000, Modele = "oeuf_16_oeuf_de_la_grotte",
		Dinos = {
			{ Nom = "Hypacrosaurus", Chance = 50 },
			{ Nom = "Stygimoloch", Chance = 30 },
			{ Nom = "Stegoceras", Chance = 15 },
			{ Nom = "Centrosaurus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf des Fossiles", Rarete = "Peu commun", Prix = 17000, Modele = "oeuf_17_oeuf_des_fossiles",
		Dinos = {
			{ Nom = "Chasmosaurus", Chance = 50 },
			{ Nom = "Pachyrhinosaurus", Chance = 30 },
			{ Nom = "Einiosaurus", Chance = 15 },
			{ Nom = "Euoplocephalus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf de Glace", Rarete = "Peu commun", Prix = 24000, Modele = "oeuf_18_oeuf_de_glace",
		Dinos = {
			{ Nom = "Edmontonia", Chance = 50 },
			{ Nom = "Diplodocus", Chance = 30 },
			{ Nom = "Camarasaurus", Chance = 15 },
			{ Nom = "Plesiosaurus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf de Jade", Rarete = "Peu commun", Prix = 33000, Modele = "oeuf_19_oeuf_de_jade",
		Dinos = {
			{ Nom = "Tapejara", Chance = 50 },
			{ Nom = "Velociraptor", Chance = 30 },
			{ Nom = "Ankylosaurus", Chance = 15 },
			{ Nom = "Stegosaurus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf de Rubis", Rarete = "Rare", Prix = 45000, Modele = "oeuf_20_oeuf_de_rubis",
		Dinos = {
			{ Nom = "Minmi", Chance = 50 },
			{ Nom = "Troodon", Chance = 30 },
			{ Nom = "Carcharodontosaurus", Chance = 15 },
			{ Nom = "Acrocanthosaurus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf d'Orage", Rarete = "Rare", Prix = 63000, Modele = "oeuf_21_oeuf_dorage",
		Dinos = {
			{ Nom = "Albertosaurus", Chance = 50 },
			{ Nom = "Daspletosaurus", Chance = 30 },
			{ Nom = "Tarbosaurus", Chance = 15 },
			{ Nom = "Yutyrannus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf des Cimes", Rarete = "Rare", Prix = 87000, Modele = "oeuf_22_oeuf_des_cimes",
		Dinos = {
			{ Nom = "Torvosaurus", Chance = 50 },
			{ Nom = "Utahraptor", Chance = 30 },
			{ Nom = "Deinonychus", Chance = 15 },
			{ Nom = "Therizinosaurus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf de la Jungle Sauvage", Rarete = "Rare", Prix = 120000, Modele = "oeuf_23_oeuf_de_la_jungle_sauvage",
		Dinos = {
			{ Nom = "Ouranosaurus", Chance = 50 },
			{ Nom = "Styracosaurus", Chance = 30 },
			{ Nom = "Kosmoceratops", Chance = 15 },
			{ Nom = "Torosaurus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf des Dunes", Rarete = "Rare", Prix = 160000, Modele = "oeuf_24_oeuf_des_dunes",
		Dinos = {
			{ Nom = "Kentrosaurus", Chance = 50 },
			{ Nom = "Tuojiangosaurus", Chance = 30 },
			{ Nom = "Miragaia", Chance = 15 },
			{ Nom = "Saichania", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf du Glacier", Rarete = "Rare", Prix = 230000, Modele = "oeuf_25_oeuf_du_glacier",
		Dinos = {
			{ Nom = "Pinacosaurus", Chance = 50 },
			{ Nom = "Amargasaurus", Chance = 30 },
			{ Nom = "Mamenchisaurus", Chance = 15 },
			{ Nom = "Dreadnoughtus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf de Lave", Rarete = "Rare", Prix = 310000, Modele = "oeuf_26_oeuf_de_lave",
		Dinos = {
			{ Nom = "Quetzalcoatlus", Chance = 50 },
			{ Nom = "Elasmosaurus", Chance = 30 },
			{ Nom = "Ichthyosaurus", Chance = 15 },
			{ Nom = "Liopleurodon", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf Neon", Rarete = "Epique", Prix = 430000, Modele = "oeuf_27_oeuf_neon",
		Dinos = {
			{ Nom = "Triceratops", Chance = 50 },
			{ Nom = "Brachiosaurus", Chance = 30 },
			{ Nom = "Pteranodon", Chance = 15 },
			{ Nom = "Carnotaurus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf Toxique", Rarete = "Epique", Prix = 600000, Modele = "oeuf_28_oeuf_toxique",
		Dinos = {
			{ Nom = "Archaeopteryx", Chance = 50 },
			{ Nom = "Mosasaurus", Chance = 30 },
			{ Nom = "Argentinosaurus", Chance = 15 },
			{ Nom = "Shonisaurus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf des Abysses", Rarete = "Epique", Prix = 830000, Modele = "oeuf_29_oeuf_des_abysses",
		Dinos = {
			{ Nom = "Deinocheirus", Chance = 50 },
			{ Nom = "Kronosaurus", Chance = 30 },
			{ Nom = "Patagotitan", Chance = 15 },
			{ Nom = "Tylosaurus", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf d'Aurore", Rarete = "Epique", Prix = 1100000, Modele = "oeuf_30_oeuf_daurore",
		Dinos = {
			{ Nom = "Raptor Neon", Chance = 50 },
			{ Nom = "Triceratops de Jade", Chance = 30 },
			{ Nom = "Stego Volcanique", Chance = 15 },
			{ Nom = "Ankylo de Fer", Chance = 5 },
		},
	},
	{
		Nom = "Oeuf d'Amethyste", Rarete = "Epique", Prix = 1600000, Modele = "oeuf_31_oeuf_damethyste",
		Dinos = {
			{ Nom = "Brachio Celeste", Chance = 60 },
			{ Nom = "Ptero Tempete", Chance = 30 },
			{ Nom = "Parasaur Corail", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf de Tempete", Rarete = "Epique", Prix = 2200000, Modele = "oeuf_32_oeuf_de_tempete",
		Dinos = {
			{ Nom = "Dilopho Venin", Chance = 60 },
			{ Nom = "Carno Infernal", Chance = 30 },
			{ Nom = "Allo Glacial", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf du Soleil", Rarete = "Epique", Prix = 3000000, Modele = "oeuf_33_oeuf_du_soleil",
		Dinos = {
			{ Nom = "Spino des Marais", Chance = 60 },
			{ Nom = "Pachy Cristal", Chance = 30 },
			{ Nom = "Styraco Royal", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf de Lune", Rarete = "Epique", Prix = 4100000, Modele = "oeuf_34_oeuf_de_lune",
		Dinos = {
			{ Nom = "Baryonyx Abyssal", Chance = 60 },
			{ Nom = "Ceratosaure Toxique", Chance = 30 },
			{ Nom = "Allosaurus", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf du Dragon", Rarete = "Legendaire", Prix = 5700000, Modele = "oeuf_35_oeuf_du_dragon",
		Dinos = {
			{ Nom = "Baryonyx", Chance = 60 },
			{ Nom = "Spinosaurus", Chance = 30 },
			{ Nom = "Dracorex", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf du Phenix", Rarete = "Legendaire", Prix = 7900000, Modele = "oeuf_36_oeuf_du_phenix",
		Dinos = {
			{ Nom = "Rex de Lave", Chance = 60 },
			{ Nom = "Spino Abyssal", Chance = 30 },
			{ Nom = "Giganoto Tonnerre", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf du Titan", Rarete = "Legendaire", Prix = 11000000, Modele = "oeuf_37_oeuf_du_titan",
		Dinos = {
			{ Nom = "Rex de Cristal", Chance = 60 },
			{ Nom = "Triceratops Titan", Chance = 30 },
			{ Nom = "Brachio Aurore", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf du Kraken", Rarete = "Legendaire", Prix = 15000000, Modele = "oeuf_38_oeuf_du_kraken",
		Dinos = {
			{ Nom = "Quetzal Solaire", Chance = 60 },
			{ Nom = "Mosasaure Royal", Chance = 30 },
			{ Nom = "Stego Cristallin", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf du Volcan Ancien", Rarete = "Legendaire", Prix = 21000000, Modele = "oeuf_39_oeuf_du_volcan_ancien",
		Dinos = {
			{ Nom = "Raptor Spectre", Chance = 60 },
			{ Nom = "Ankylo Forteresse", Chance = 30 },
			{ Nom = "Therizino Faucheur", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf Galactique", Rarete = "Legendaire", Prix = 29000000, Modele = "oeuf_40_oeuf_galactique",
		Dinos = {
			{ Nom = "Rex Aile", Chance = 60 },
			{ Nom = "Raptor de Feu", Chance = 30 },
			{ Nom = "Golem Rex", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf du Golem", Rarete = "Legendaire", Prix = 39000000, Modele = "oeuf_41_oeuf_du_golem",
		Dinos = {
			{ Nom = "Dilopho Dragon", Chance = 60 },
			{ Nom = "Allo Samourai", Chance = 30 },
			{ Nom = "T-Rex", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf Demoniaque", Rarete = "Mythique", Prix = 54000000, Modele = "oeuf_42_oeuf_demoniaque",
		Dinos = {
			{ Nom = "Giganotosaurus", Chance = 60 },
			{ Nom = "Microraptor", Chance = 30 },
			{ Nom = "Dragon Rex", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf de Cristal Rose", Rarete = "Mythique", Prix = 75000000, Modele = "oeuf_43_oeuf_de_cristal_rose",
		Dinos = {
			{ Nom = "Phenix Ptero", Chance = 60 },
			{ Nom = "Leviathan", Chance = 30 },
			{ Nom = "Rex Galaxie", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf des Profondeurs", Rarete = "Mythique", Prix = 100000000, Modele = "oeuf_44_oeuf_des_profondeurs",
		Dinos = {
			{ Nom = "Spino Fantome", Chance = 60 },
			{ Nom = "Titan de Jade", Chance = 30 },
			{ Nom = "Roi Demon Rex", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf du Vide", Rarete = "Mythique", Prix = 140000000, Modele = "oeuf_45_oeuf_du_vide",
		Dinos = {
			{ Nom = "Meca-Rex Dore", Chance = 60 },
			{ Nom = "Pegase Dino Dore", Chance = 30 },
			{ Nom = "Triceratops Infernal", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf Eternel", Rarete = "Secret", Prix = 200000000, Modele = "oeuf_46_oeuf_eternel",
		Dinos = {
			{ Nom = "Indominus Rex", Chance = 60 },
			{ Nom = "Ange-Demon Rex", Chance = 30 },
			{ Nom = "Dino Arc-en-ciel", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf de l'Infini", Rarete = "Secret", Prix = 270000000, Modele = "oeuf_47_oeuf_de_linfini",
		Dinos = {
			{ Nom = "Fossile Vivant", Chance = 60 },
			{ Nom = "Empereur Dragon", Chance = 30 },
			{ Nom = "Spino Celeste", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf Arc-en-ciel", Rarete = "Secret", Prix = 380000000, Modele = "oeuf_48_oeuf_arc_en_ciel",
		Dinos = {
			{ Nom = "Triceratops du Neant", Chance = 60 },
			{ Nom = "Kaiju du Vide", Chance = 30 },
			{ Nom = "Dragon de Cristal Rose", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf Celeste", Rarete = "Eternel", Prix = 520000000, Modele = "oeuf_49_oeuf_celeste",
		Dinos = {
			{ Nom = "Rex Cosmique Eternel", Chance = 60 },
			{ Nom = "Leviathan Eternel", Chance = 30 },
			{ Nom = "Sauro des Etoiles", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf Divin", Rarete = "Divin", Prix = 710000000, Modele = "oeuf_50_oeuf_divin",
		Dinos = {
			{ Nom = "Rex Seraphin", Chance = 60 },
			{ Nom = "Raptor Paon Divin", Chance = 30 },
			{ Nom = "Ptero Seraphin", Chance = 10 },
		},
	},
}

-- Tire un dino au hasard dans l'oeuf, selon les chances. A appeler cote serveur.
function Oeufs.Tirer(oeuf, rng)
	rng = rng or Random.new()
	local total = 0
	for _, d in ipairs(oeuf.Dinos) do
		total += d.Chance
	end
	local tirage = rng:NextNumber() * total
	for _, d in ipairs(oeuf.Dinos) do
		tirage -= d.Chance
		if tirage <= 0 then
			return d.Nom
		end
	end
	return oeuf.Dinos[#oeuf.Dinos].Nom
end

function Oeufs.Trouver(nom)
	for _, oeuf in ipairs(Oeufs.Liste) do
		if oeuf.Nom == nom then
			return oeuf
		end
	end
	return nil
end

return Oeufs
