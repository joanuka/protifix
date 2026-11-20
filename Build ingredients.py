"""
Builds ingredients.csv from a table of base ingredients, so every row is traceable.

PORTION BASIS (the same for every row): 100 g of cooked / as-served protein component,
the amount that stands in for ~100 g of cooked meat on a plate.

  protein_g, fat_g  = sum(grams of each ingredient used x its protein/fat per 100 g) + cooking oil
  cost              = sum(grams x price per kg) + cooking oil + a fixed seasoning/fuel kit per cooking style
                      (ingredient + kit cost only: NOT labour, rent, sauces or sides)
  co2               = sum(grams x kgCO2e per kg) + 0.03 for cooking fuel

Run:  py build_ingredients.py     (rewrites ingredients.csv)

Update PRICE values below when you collect real market prices, then re-run.
"""
import csv

# key: (label, protein g/100g, fat g/100g, price NGN/kg, kgCO2e/kg, availability 3/2/1, allergen, price confidence)
# protein/fat = as bought (dry beans, dry TSP, fresh mushrooms, firm tofu ...).
# price confidence: M = backed by a 2025-26 Nigerian market/NBS quote; L = estimate, VERIFY at market.
ING = {
    "cowpea":     ("Cowpea (dry)",            23.5, 1.3, 1600, 1.8, 3, "", "M"),
    "bambara":    ("Bambara groundnut (dry)", 20.0, 6.0, 2400, 1.8, 3, "", "L"),
    "pigeon":     ("Pigeon pea (dry)",        21.0, 1.5, 1800, 1.8, 2, "", "L"),
    "yambean":    ("African yam bean (dry)",  27.0, 3.5, 2500, 1.8, 2, "", "L"),
    "lima":       ("Lima bean (dry)",         22.0, 1.5, 2000, 1.8, 2, "", "L"),
    "soybean":    ("Soybean (dry)",           36.0, 19.0, 1100, 1.5, 3, "soy", "M"),
    "chickpea":   ("Chickpea (dry)",          19.0, 6.0, 3000, 1.8, 2, "", "L"),
    "lentil":     ("Lentil (dry)",            25.0, 1.0, 3200, 1.8, 1, "", "L"),
    "groundnut":  ("Groundnut (shelled)",     26.0, 49.0, 2200, 2.5, 3, "peanut", "L"),
    "egusi":      ("Egusi (melon seed)",      28.0, 50.0, 3500, 2.5, 3, "", "L"),
    "pumpkin":    ("Pumpkin (ugu) seed",      30.0, 49.0, 4500, 1.5, 2, "", "L"),
    "sesame":     ("Sesame (beniseed)",       22.0, 50.0, 3000, 2.0, 3, "sesame", "L"),
    "sunflower":  ("Sunflower seed",          21.0, 51.0, 4500, 2.0, 1, "", "L"),
    "cashew":     ("Cashew nut",              18.0, 44.0, 8000, 0.5, 2, "tree nut", "L"),
    "walnut":     ("African walnut (ukpa)",   22.0, 50.0, 5500, 0.5, 2, "tree nut", "L"),
    "tiger":      ("Tiger nut",                5.0, 24.0, 1500, 0.5, 3, "", "L"),
    "kuli":       ("Kuli-kuli",               35.0, 25.0, 3000, 2.5, 3, "peanut", "L"),
    "tsp":        ("Textured soy protein (dry)", 52.0, 1.0, 4000, 2.5, 3, "soy", "L"),
    "tofu":       ("Tofu / awara",            10.0, 5.3, 3500, 3.2, 3, "soy", "L"),
    "tofu_smk":   ("Smoked tofu",             14.0, 7.5, 5000, 3.2, 2, "soy", "L"),
    "tempeh":     ("Tempeh",                  19.0, 11.0, 10000, 2.0, 1, "soy", "L"),
    "seitan":     ("Seitan (wheat gluten)",   25.0, 1.8, 6000, 4.5, 2, "gluten", "L"),
    "oyster":     ("Oyster mushroom (fresh)",  3.3, 0.4, 4000, 1.5, 3, "", "L"),
    "oyster_dry": ("Oyster mushroom (dried)", 22.0, 2.0, 20000, 1.5, 2, "", "L"),
    "button":     ("Button mushroom",          3.1, 0.3, 5000, 1.5, 3, "", "L"),
    "shiitake":   ("Shiitake (fresh)",         2.2, 0.5, 12000, 2.0, 1, "", "L"),
    "kingoyster": ("King oyster mushroom",     3.3, 0.4, 9000, 2.0, 1, "", "L"),
    "jackfruit":  ("Young jackfruit",          2.8, 0.6, 2000, 0.8, 1, "", "L"),
    "jackseed":   ("Jackfruit seed (boiled)",  6.6, 0.4, 800, 0.8, 2, "", "L"),
    "blossom":    ("Banana blossom",           1.6, 0.6, 1500, 0.5, 1, "", "L"),
    "plantain":   ("Unripe plantain",          1.3, 0.4, 700, 0.8, 3, "", "M"),
    "flour":      ("Wheat flour",             10.0, 1.0, 1800, 1.4, 3, "gluten", "M"),
    "maize":      ("Maize (dry)",              9.0, 4.0, 1200, 1.0, 3, "", "M"),
    "iru":        ("Iru / dawadawa",          33.0, 16.0, 5000, 1.0, 3, "", "L"),
    "moringa":    ("Moringa leaf powder",     27.0, 2.0, 6000, 0.5, 2, "", "L"),
    "spirulina":  ("Spirulina powder",        57.0, 8.0, 30000, 1.0, 1, "", "L"),
    "ugba":       ("Ugba (oil bean)",         17.0, 22.0, 6000, 1.0, 2, "", "L"),
    "ukwa":       ("Ukwa (breadfruit seed)",  17.0, 13.0, 3500, 0.8, 2, "", "L"),
}
OIL_PRICE_PER_G = 2.5  # NGN per g of cooking oil (about N2,500 per litre, 2026 reports)
AVL = {3: "High", 2: "Medium", 1: "Low"}
DIFF = {1: "Easy", 2: "Medium", 3: "Hard"}

# cooking styles used to generate combinations: (label, oil g, kit NGN, d_chew, d_umami, d_fam, d_prep, d_diff, method)
FORMATS = {
    "suya":    ("Suya Strips", 4, 80, 0, 1, 1, 0, 0,
                "Skewered, rubbed with yaji and grilled hot, 3 to 4 minutes a side"),
    "shawarma": ("Shawarma Strips", 5, 110, 0, 0, 0, 5, 0,
                 "Sliced thin, seasoned and seared hard, then wrapped with sauce and cabbage"),
    "soup":    ("Pepper Soup Chunks", 0, 70, -1, 0, 1, 10, 0,
                "Simmered in pepper-soup broth, added for the last 10 to 15 minutes"),
    "stew":    ("Stew Pieces", 6, 90, -1, 0, 1, 10, 0,
                "Simmered in the stew base, added for the last 10 to 15 minutes"),
    "asun":    ("Asun-Style Peppered Bites", 5, 85, 0, 1, 0, 5, 0,
                "Peppered with ata rodo and scotch bonnet, then pan-roasted until charred"),
    "nuggets": ("Crispy Bites", 10, 90, -1, 0, 1, 10, 1,
                "Coated in seasoned flour or crumbs, then shallow-fried until golden"),
    "topper":  ("Jollof Rice Topper", 4, 60, -1, 0, 0, 5, 0,
                "Seared on its own with curry and thyme, then laid on the jollof rice"),
}

# bases for generated combinations: key: (label, category, recipe grams per 100 g served, chew, umami, fam, prep, diff)
BASES = {
    "tsp":      ("TSP (Soya Chunk)", "Soy",           {"tsp": 30},                 8, 6, 7, 15, 1),
    "tofu":     ("Tofu (Awara)",     "Soy",           {"tofu": 105},               6, 5, 9, 15, 1),
    "tempeh":   ("Tempeh",           "Soy",           {"tempeh": 95},              8, 8, 3, 25, 1),
    "seitan":   ("Seitan",           "Wheat gluten",  {"seitan": 100},             9, 7, 5, 25, 2),
    "oyster":   ("Oyster Mushroom",  "Fungi",         {"oyster": 150},             7, 9, 8, 15, 1),
    "cowpea":   ("Cowpea-Paste",     "Legume",        {"cowpea": 40},              4, 7, 10, 30, 2),
    "bambara":  ("Bambara-Paste",    "Legume",        {"bambara": 40},             5, 6, 8, 30, 2),
    "soycow":   ("Soy-Cowpea",       "Blend",         {"soybean": 15, "cowpea": 22}, 5, 7, 8, 30, 2),
    "jackfruit": ("Young Jackfruit", "Fruit/veg",     {"jackfruit": 120},          9, 3, 5, 30, 3),
}

# hand-built items: name, category, recipe, oil g, kit NGN, chew, umami, fam, prep, diff, method
MANUAL = [
    # beans and cowpea dishes
    ("Boiled Brown Beans (Ewa Oloyin)", "Legume", {"cowpea": 43}, 0, 40, 3, 6, 10, 45, 1, "Boiled soft with onion and pepper, topped with stew"),
    ("Ewa Agoyin (Mashed Beans)", "Legume", {"cowpea": 40}, 8, 70, 2, 8, 10, 50, 2, "Boiled very soft and mashed, served with fried agoyin pepper sauce"),
    ("Ekuru (Steamed White Bean Cake)", "Legume", {"cowpea": 38}, 0, 50, 3, 5, 9, 60, 2, "Peeled beans ground and steamed in leaf or foil"),
    ("Gbegiri (Bean Soup)", "Legume", {"cowpea": 30}, 5, 50, 1, 7, 9, 50, 2, "Boiled beans blended smooth, simmered with palm oil"),
    ("Adalu (Beans and Sweet Corn)", "Legume", {"cowpea": 28, "maize": 24}, 4, 55, 3, 6, 9, 50, 1, "Beans and corn boiled together, finished with palm oil and pepper"),
    ("Moi Moi (Steamed Bean Pudding)", "Legume", {"cowpea": 38}, 6, 60, 3, 7, 10, 60, 2, "Steamed in leaf or foil with pepper, onion and a little oil"),
    ("Moi Moi (Cowpea-Bambara Blend)", "Blend", {"cowpea": 20, "bambara": 18}, 6, 60, 3, 7, 8, 60, 2, "Steamed in leaf or foil, half cowpea and half bambara"),
    ("Okpa (Steamed Bambara Pudding)", "Legume", {"bambara": 38}, 8, 55, 3, 6, 8, 60, 2, "Bambara flour mixed with palm oil and steamed in leaf"),
    ("Boiled Bambara Nuts", "Legume", {"bambara": 45}, 0, 40, 5, 4, 8, 60, 1, "Boiled until tender, lightly salted"),
    ("Bambara Groundnut Cakes (Roasted)", "Legume", {"bambara": 38}, 6, 70, 6, 7, 9, 30, 2, "Steamed or roasted with a pepper crust"),
    ("Cowpea (Beans) Fritters (Akara)", "Legume", {"cowpea": 38}, 12, 60, 4, 7, 10, 25, 1, "Whipped bean batter deep-fried in hot oil"),
    ("Pigeon Pea (Fio-fio) Boiled", "Legume", {"pigeon": 45}, 0, 40, 4, 5, 6, 50, 1, "Boiled until soft, seasoned with onion and pepper"),
    ("Pigeon Pea Patties", "Legume", {"pigeon": 38}, 8, 60, 5, 6, 5, 30, 2, "Coarsely mashed, shaped and pan-fried"),
    ("African Yam Bean (Otili) Boiled", "Legume", {"yambean": 42}, 0, 40, 5, 5, 5, 70, 2, "Boiled long and slow until tender"),
    ("African Yam Bean Moi Moi", "Legume", {"yambean": 36}, 6, 60, 3, 7, 5, 70, 2, "Steamed in leaf or foil"),
    ("Lima Bean (Butter Bean) Stew", "Legume", {"lima": 40}, 6, 70, 4, 6, 6, 60, 2, "Boiled then simmered in stew base"),
    ("Lima Bean Patties", "Legume", {"lima": 38}, 8, 60, 5, 6, 5, 35, 2, "Boiled, mashed and pan-fried as patties"),
    ("Chickpea Falafel Balls", "Legume", {"chickpea": 38}, 14, 80, 5, 6, 6, 30, 2, "Deep-fried or baked herb-spiced balls"),
    ("Chickpea Shawarma-Style Strips", "Legume", {"chickpea": 36, "flour": 6}, 6, 110, 6, 6, 6, 30, 2, "Seasoned strips seared hard for wraps"),
    ("Boiled Chickpeas", "Legume", {"chickpea": 42}, 0, 40, 4, 4, 6, 60, 1, "Boiled until soft, seasoned"),
    ("Lentil Patties", "Legume", {"lentil": 32}, 8, 60, 5, 6, 4, 25, 2, "Pan-fried or baked patties"),
    ("Lentil Mince Stew Topper", "Legume", {"lentil": 33}, 5, 80, 4, 6, 4, 30, 2, "Simmered in thick stew, like a mince"),
    ("Boiled Whole Soybeans", "Soy", {"soybean": 42}, 0, 40, 4, 5, 6, 90, 2, "Soaked overnight then boiled until tender"),
    ("Soybean Fritters (Soy Akara)", "Soy", {"soybean": 36}, 12, 60, 4, 7, 6, 30, 2, "Soaked, ground and deep-fried like akara"),
    ("Soy-Cowpea Moi Moi", "Blend", {"soybean": 15, "cowpea": 22}, 6, 60, 3, 7, 8, 60, 2, "Steamed in leaf or foil"),
    ("Soy-Cowpea Burger Patty", "Blend", {"soybean": 15, "cowpea": 20, "flour": 6}, 8, 80, 5, 7, 7, 30, 2, "Shaped and pan-fried with onion and thyme"),
    # soy products
    ("Fried Awara (Hausa Tofu)", "Soy", {"tofu": 100}, 8, 70, 6, 6, 9, 20, 1, "Pressed tofu cubes fried until golden, rolled in yaji"),
    ("Tofu Scramble (Pepper and Onion)", "Soy", {"tofu": 90}, 6, 60, 3, 6, 6, 15, 1, "Crumbled and fried with pepper, onion and turmeric"),
    ("Smoked Tofu (Peppery Rub)", "Soy", {"tofu_smk": 100}, 4, 90, 8, 8, 7, 20, 1, "Sliced and grilled with a peppery rub"),
    ("Sesame-Crusted Tofu", "Soy", {"tofu": 85, "sesame": 8}, 6, 70, 6, 6, 5, 20, 1, "Pressed tofu rolled in sesame and pan-seared"),
    ("Kuli-kuli-Crusted Tofu", "Soy", {"tofu": 85, "kuli": 10}, 4, 70, 6, 6, 8, 20, 1, "Pressed tofu coated in crushed kuli-kuli and seared"),
    ("Dawadawa Spiced Soy Skewers", "Soy", {"tofu": 70, "iru": 8, "kuli": 4}, 4, 80, 7, 10, 7, 20, 1, "Skewered and grilled with an iru-yaji rub"),
    ("Soya-Dodo (Soy Gizdodo Style)", "Soy", {"tsp": 26, "plantain": 30}, 8, 90, 7, 6, 7, 25, 2, "Rehydrated soya diced and fried in pepper sauce with plantain"),
    ("Soya Kofta (Spiced Mince)", "Soy", {"tsp": 22, "flour": 8}, 6, 90, 6, 6, 5, 25, 2, "Rehydrated mince bound with flour, shaped and grilled"),
    ("Soy-Mushroom Blend Strips", "Blend", {"tsp": 15, "oyster": 60}, 5, 90, 8, 8, 6, 20, 1, "Half-rehydrated soya with seared mushroom, grilled in strips"),
    ("Moringa-TSP Strips", "Soy", {"tsp": 26, "moringa": 4}, 4, 90, 8, 6, 5, 20, 1, "Rehydrated soya strips with moringa powder, seared"),
    # fungi
    ("Oyster Mushroom and Cowpea Burger", "Blend", {"oyster": 50, "cowpea": 22, "flour": 4}, 8, 80, 6, 8, 6, 30, 2, "Seared mushroom folded into cowpea paste, pan-fried as patties"),
    ("Pulled Oyster Mushroom (Roasted)", "Fungi", {"oyster": 160}, 6, 90, 9, 9, 6, 25, 2, "Hand-shredded and roasted dry for wraps"),
    ("Dried Oyster Mushroom (Peppered)", "Fungi", {"oyster_dry": 14}, 6, 80, 7, 9, 4, 25, 2, "Soaked, squeezed dry and fried in pepper sauce"),
    ("Button Mushroom in Pepper Sauce", "Fungi", {"button": 150}, 8, 80, 6, 7, 7, 15, 1, "Sliced and pan-seared in pepper sauce"),
    ("Shiitake Slices (Pan-Seared)", "Fungi", {"shiitake": 150}, 6, 80, 7, 10, 3, 15, 1, "Sliced and seared hard in a hot pan"),
    ("King Oyster Mushroom Strips", "Fungi", {"kingoyster": 160}, 6, 80, 8, 8, 3, 15, 1, "Scored, seared and glazed with pepper sauce"),
    ("Mushroom and Tofu Suya Cubes", "Blend", {"oyster": 70, "tofu": 50}, 4, 80, 7, 8, 7, 20, 1, "Skewered mixed cubes grilled with yaji"),
    ("Mushroom Egusi Balls", "Blend", {"oyster": 60, "egusi": 18, "cowpea": 10}, 8, 70, 6, 8, 7, 30, 2, "Seared mushroom folded into egusi paste, fried as balls"),
    ("Mushroom and Groundnut Yaji Crumble", "Blend", {"oyster": 70, "groundnut": 15, "kuli": 8}, 4, 80, 6, 8, 7, 20, 1, "Mushroom roasted and tossed in groundnut yaji crumble"),
    # seeds and nuts
    ("Melon Seed (Egusi) Balls", "Seeds/nuts", {"egusi": 40}, 8, 70, 7, 8, 10, 25, 1, "Simmered in spicy broth or pan-seared"),
    ("Egusi-Cowpea Patties", "Blend", {"egusi": 20, "cowpea": 22}, 6, 70, 6, 8, 9, 30, 2, "Mixed paste shaped and pan-fried"),
    ("Egusi and Soya Pepper-Soup Dumplings", "Blend", {"egusi": 20, "tsp": 15}, 0, 70, 6, 8, 7, 30, 2, "Mixed dumplings simmered in pepper-soup broth"),
    ("Boiled Groundnuts", "Seeds/nuts", {"groundnut": 45}, 0, 40, 5, 4, 10, 60, 1, "Boiled in salted water until soft"),
    ("Groundnut Yaji Chunks", "Seeds/nuts", {"groundnut": 40, "kuli": 6}, 2, 70, 6, 7, 8, 15, 1, "Coated in yaji and roasted"),
    ("Groundnut-Cowpea Kofta", "Blend", {"groundnut": 12, "cowpea": 26}, 8, 70, 5, 7, 8, 30, 2, "Shaped and pan-fried"),
    ("Kuli-kuli Crumble (Coating)", "Seeds/nuts", {"kuli": 30}, 0, 20, 6, 6, 10, 5, 1, "Crushed as coating or filling"),
    ("Kuli-kuli Bean Burger", "Blend", {"kuli": 12, "cowpea": 24}, 6, 70, 5, 7, 9, 30, 2, "Mixed patty pan-fried"),
    ("African Walnut (Ukpa) Boiled", "Seeds/nuts", {"walnut": 60}, 0, 40, 5, 5, 6, 90, 1, "Boiled until the kernels soften"),
    ("Pumpkin Seed (Ugu Seed) Patties", "Blend", {"pumpkin": 28, "cowpea": 15, "flour": 5}, 6, 70, 5, 7, 5, 30, 2, "Ground seed and bean patties, pan-fried"),
    ("Pumpkin Seed Suya Crumble", "Seeds/nuts", {"pumpkin": 28, "kuli": 10}, 0, 70, 6, 7, 5, 15, 1, "Toasted seed with yaji, served as a crumble"),
    ("Sesame-Chickpea Kofta", "Blend", {"sesame": 12, "chickpea": 24}, 6, 70, 5, 7, 5, 30, 2, "Shaped and pan-fried"),
    ("Sunflower-Cowpea Burger", "Blend", {"sunflower": 15, "cowpea": 24}, 6, 70, 5, 6, 5, 30, 2, "Shaped and pan-fried"),
    ("Cashew and Tofu Pepper Pieces", "Blend", {"cashew": 15, "tofu": 70}, 5, 70, 6, 6, 5, 20, 1, "Pan-tossed in pepper sauce"),
    ("Tiger Nut and Soy Patties", "Blend", {"tiger": 20, "soybean": 20}, 6, 60, 5, 5, 6, 30, 2, "Mixed patties pan-fried"),
    ("Ukwa (African Breadfruit) Pepper-Tossed", "Seeds/nuts", {"ukwa": 45}, 5, 60, 6, 7, 7, 40, 3, "Boiled then pan-tossed with pepper"),
    ("Ukwa and Cowpea Mix", "Blend", {"ukwa": 25, "cowpea": 20}, 5, 60, 5, 7, 7, 45, 2, "Boiled together, finished with palm oil and pepper"),
    ("Ugba (Oil Bean Slices)", "Seeds/nuts", {"ugba": 40}, 6, 50, 5, 8, 5, 35, 2, "Tossed warm with spices and palm oil"),
    ("Ugba and Bean Salad", "Blend", {"ugba": 20, "cowpea": 18}, 4, 50, 5, 8, 5, 40, 2, "Warm salad of ugba and boiled beans"),
    # fruit, veg and boosters
    ("Jackfruit and Cowpea Burger", "Blend", {"jackfruit": 45, "cowpea": 20, "flour": 5}, 8, 80, 7, 6, 5, 35, 2, "Shredded jackfruit folded into cowpea paste, pan-fried"),
    ("Boiled Jackfruit Seeds", "Fruit/veg", {"jackseed": 60}, 0, 30, 6, 3, 5, 40, 1, "Boiled until soft, lightly salted"),
    ("Banana Blossom Fish-Style Fillets", "Fruit/veg", {"blossom": 70, "flour": 15}, 12, 90, 7, 4, 3, 30, 2, "Battered and fried like fish pieces"),
    ("Plantain and Bean Patties", "Blend", {"plantain": 30, "cowpea": 22}, 8, 60, 5, 5, 8, 25, 2, "Pan-fried patties"),
    ("Moringa and Bean Patties", "Blend", {"moringa": 5, "cowpea": 36}, 8, 60, 5, 6, 6, 25, 2, "Pan-fried patties"),
    ("Moringa Akara", "Legume", {"cowpea": 36, "moringa": 4}, 12, 60, 4, 7, 8, 25, 1, "Bean batter with moringa powder, deep-fried"),
    ("Spirulina-Boosted Bean Patties", "Blend", {"cowpea": 34, "spirulina": 3}, 8, 70, 5, 6, 3, 25, 2, "Pan-fried patties with spirulina powder"),
    ("Tiger Nut Patties", "Seeds/nuts", {"tiger": 35, "flour": 8}, 6, 60, 5, 4, 6, 20, 2, "Pan-seared patties"),
]


def calc(rec, oil, kit):
    protein = sum(g * ING[k][1] / 100 for k, g in rec.items())
    fat = sum(g * ING[k][2] / 100 for k, g in rec.items()) + oil
    cost = sum(g * ING[k][3] / 1000 for k, g in rec.items()) + oil * OIL_PRICE_PER_G + kit
    co2 = sum(g * ING[k][4] / 1000 for k, g in rec.items()) + 0.03
    main = [k for k, g in rec.items() if g >= 10] or list(rec)
    av = min(ING[k][5] for k in main)
    allergens = sorted({ING[k][6] for k in rec if ING[k][6]})
    conf = "Low" if any(ING[k][7] == "L" for k in main) else "Medium"
    basis = "; ".join(f"{g}g {ING[k][0]}" for k, g in rec.items())
    return protein, fat, cost, co2, av, "/".join(allergens), conf, basis


rows = []


def add(name, cat, rec, oil, kit, chew, umami, fam, prep, diff, method):
    p, f, c, co2, av, al, conf, basis = calc(rec, oil, kit)
    clamp = lambda v: max(1, min(10, v))
    rows.append([name, round(p, 1), round(f, 1), round(c / 10) * 10, clamp(chew), clamp(umami), int(prep),
                 clamp(fam), AVL[av], DIFF[min(3, diff)], method, round(co2, 2),
                 cat, "100 g cooked", al or "none", conf, basis])


for bk, (blabel, cat, rec, ch, um, fa, pr, df) in BASES.items():
    for fk, (flabel, oil, kit, dch, dum, dfa, dpr, ddf, method) in FORMATS.items():
        add(f"{blabel} {flabel}", cat, rec, oil, kit, ch + dch, um + dum, fa + dfa, pr + dpr, df + ddf, method)
for m in MANUAL:
    add(*m)

names = [r[0] for r in rows]
assert len(names) == len(set(names)), "duplicate names"
header = ["name", "protein_g", "fat_g", "cost_per_portion_ngn", "chewiness_score", "umami_score", "prep_time_mins",
          "familiarity_score", "availability_abuja", "cooking_difficulty", "best_cooking_method", "co2_kg_per_portion",
          "category", "portion_basis", "allergens", "price_confidence", "ingredient_basis"]
with open("ingredients.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(header)
    w.writerows(rows)

print(f"wrote {len(rows)} rows")