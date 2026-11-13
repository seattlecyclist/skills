"""Cutting-board species: illustration colour of the end grain, Janka hardness (lbf), tangential and
radial shrinkage (% green to oven dry) and notes. Numbers are typical values from the Wood Database
(wood-database.com) and the USDA Wood Handbook; individual boards vary.

Colours are what the end grain reads as after oil, used for diagrams and the render guide. End grain
reads darker and more saturated than face grain of the same board.
"""

SPECIES = {
    # key: (name, end-grain colour, long-grain colour, janka, tangential %, radial %, notes)
    "maple":       ("Hard maple",        "#e6cf9f", "#efdcb4", 1450, 9.9, 4.8, "The standard board wood: hard, tight pores, pale."),
    "walnut":      ("Black walnut",      "#4f3222", "#5e3d2a", 1010, 7.8, 5.5, "Dark contrast wood; a little soft, so keep it to accents or pair it with cherry."),
    "cherry":      ("Cherry",            "#a95a37", "#b8693f", 950,  7.1, 3.7, "Medium tone that darkens with light; soft side of acceptable."),
    "white-oak":   ("White oak",         "#b08a5e", "#bf9a6c", 1350, 10.5, 5.6, "Tyloses close the pores, so it is fine; red oak is not."),
    "ash":         ("White ash",         "#d6c294", "#e0cda2", 1320, 7.8, 4.9, "Pale with strong rings; open pores, better as long grain than end grain."),
    "purpleheart": ("Purpleheart",       "#6b2a4a", "#7b3456", 2520, 6.4, 3.2, "Vivid purple that browns with UV; very hard on tools."),
    "padauk":      ("African padauk",    "#b5402a", "#c24a2e", 1970, 5.2, 3.3, "Orange-red; dust is an irritant, and it can bleed red into maple: wipe with solvent before glue."),
    "jatoba":      ("Jatoba",            "#86391f", "#943f22", 2690, 8.0, 4.2, "Hard red-brown; stable."),
    "yellowheart": ("Yellowheart",       "#dcb546", "#e5c152", 1820, 6.9, 3.7, "Bright yellow accent."),
    "sapele":      ("Sapele",            "#84452a", "#924c2e", 1410, 7.2, 4.6, "Medium brown, a harder stand-in for mahogany."),
    "bloodwood":   ("Bloodwood",         "#8a1d18", "#981f1a", 2900, 6.8, 4.8, "Deep red; very hard."),
    "wenge":       ("Wenge",             "#3a2a20", "#43312a", 1630, 9.0, 5.6, "Near black, but splinters and the splinters fester: avoid for working surfaces or use sparingly."),
    "yellow-birch": ("Yellow birch",     "#dcc092", "#e3c79a", 1260, 9.5, 7.3, "Pale, close grain; moves a lot."),
    "beech":       ("European beech",    "#d2a982", "#d9b48c", 1300, 11.9, 5.5, "Classic board wood but moves the most of these; avoid pairing with low-movement exotics."),
    "canarywood":  ("Canarywood",        "#c8974f", "#d4a35a", 1520, 7.5, 3.5, "Yellow to orange with streaks."),
    "teak":        ("Teak",              "#9c7144", "#a67b4b", 1070, 5.8, 2.6, "Oily and stable; silica dulls blades."),
}

AVOID = {
    "red-oak": "Open pores run straight through end grain and wick moisture and bacteria.",
    "spalted": "Spalting is fungal decay: soft and not food-safe.",
    "cocobolo": "Strong sensitiser; not for food contact.",
    "pine": "Softwoods cut up quickly and resin can taste.",
    "cedar": "Soft, aromatic oils, not for food contact.",
    "mdf": "Not wood.",
}


def get(key):
    k = key.lower().replace(" ", "-")
    if k in SPECIES:
        n, ce, cl, j, t, r, note = SPECIES[k]
        return {"key": k, "name": n, "end": ce, "long": cl, "janka": j, "tan": t, "rad": r, "note": note}
    if k in AVOID:
        raise SystemExit(f"{key}: not a cutting-board species ({AVOID[k]}). Pick another; see references/species.md.")
    # unknown: allow with a custom colour in the design (species_colors) and a warning
    return {"key": k, "name": key, "end": "#999999", "long": "#aaaaaa", "janka": None, "tan": None, "rad": None,
            "note": "Not in the species table: check hardness (over about 950 lbf), closed pores and food safety."}
