-- Contenu des oeufs : chaque oeuf contient 3 a 5 dinos, avec une chance en %.
-- Les noms correspondent aux modeles importes (blender/dinos/*.glb, blender/oeufs/*.glb).

local Oeufs = {}

Oeufs.Liste = {
	{
		Nom = "Oeuf de Sable", Rarete = "Commun", Prix = 100, Modele = "oeuf_1_sable",
		Dinos = {
			{ Nom = "Compsognathus", Chance = 40 },
			{ Nom = "Eoraptor", Chance = 30 },
			{ Nom = "Microceratus", Chance = 20 },
			{ Nom = "Protoceratops", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf de Jungle", Rarete = "Commun", Prix = 500, Modele = "oeuf_2_jungle",
		Dinos = {
			{ Nom = "Gallimimus", Chance = 35 },
			{ Nom = "Iguanodon", Chance = 30 },
			{ Nom = "Hypsilophodon", Chance = 25 },
			{ Nom = "Pachycephalosaurus", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf du Marais", Rarete = "Peu commun", Prix = 2000, Modele = "oeuf_3_marais",
		Dinos = {
			{ Nom = "Parasaurolophus", Chance = 35 },
			{ Nom = "Psittacosaurus", Chance = 30 },
			{ Nom = "Oviraptor", Chance = 25 },
			{ Nom = "Dilophosaurus", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf de Canyon", Rarete = "Rare", Prix = 7500, Modele = "oeuf_4_canyon",
		Dinos = {
			{ Nom = "Minmi", Chance = 35 },
			{ Nom = "Ankylosaurus", Chance = 30 },
			{ Nom = "Stegosaurus", Chance = 25 },
			{ Nom = "Velociraptor", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf de Glace", Rarete = "Rare", Prix = 25000, Modele = "oeuf_5_glace",
		Dinos = {
			{ Nom = "Troodon", Chance = 45 },
			{ Nom = "Triceratops", Chance = 35 },
			{ Nom = "Brachiosaurus", Chance = 20 },
		},
	},
	{
		Nom = "Oeuf de Tempete", Rarete = "Epique", Prix = 100000, Modele = "oeuf_6_tempete",
		Dinos = {
			{ Nom = "Pteranodon", Chance = 35 },
			{ Nom = "Archaeopteryx", Chance = 30 },
			{ Nom = "Carnotaurus", Chance = 25 },
			{ Nom = "Allosaurus", Chance = 10 },
		},
	},
	{
		Nom = "Oeuf des Abysses", Rarete = "Legendaire", Prix = 400000, Modele = "oeuf_7_abysses",
		Dinos = {
			{ Nom = "Baryonyx", Chance = 45 },
			{ Nom = "Spinosaurus", Chance = 35 },
			{ Nom = "Dracorex", Chance = 20 },
		},
	},
	{
		Nom = "Oeuf de Volcan", Rarete = "Mythique", Prix = 1500000, Modele = "oeuf_8_volcan",
		Dinos = {
			{ Nom = "T-Rex", Chance = 50 },
			{ Nom = "Giganotosaurus", Chance = 30 },
			{ Nom = "Microraptor", Chance = 19 },
			{ Nom = "Indominus Rex", Chance = 1 },
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
