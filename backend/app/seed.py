"""Startwerte: Kategorien mit Haltbarkeit und die Zuordnung bekannter Bontexte.

Haltbarkeit (`shelf_days`) grob angelehnt an USDA FoodKeeper, für ungeöffnete
Ware ab Kauf. `use_days` ist die angenommene Verbrauchsdauer, solange es noch
kein persönliches Nachkaufintervall gibt (weniger als zwei Käufe).

Lagerorte: tiefkuehler, kuehlschrank, tuer, vorrat (alle im Kühlschrank-
bild), haushalt (nur Einkaufsliste), anschaffung (einmalig, wird nicht
verfolgt), hidden (Pfand, Sackerl).

Die Werte werden nur eingefügt, wenn sie fehlen. Änderungen in der
Datenbank bleiben also erhalten.
"""

# key: (Bezeichnung, Lagerort, shelf_days, use_days)
CATEGORIES = {
    "milch": ("Milch", "kuehlschrank", 7, 7),
    "kaese_frisch": ("Mozzarella & Frischkäse", "kuehlschrank", 10, 7),
    "kaese": ("Käse & Aufschnitt", "kuehlschrank", 21, 14),
    "aufstrich": ("Aufstriche & Dressings", "kuehlschrank", 14, 14),
    "fleisch": ("Fleisch & Laibchen", "kuehlschrank", 3, 3),
    "belegt": ("Belegtes & Fertigsalat", "kuehlschrank", 1, 1),
    "gemuese": ("Gemüse", "kuehlschrank", 5, 5),
    "shots": ("Säfte & Shots", "tuer", 14, 7),
    "tk": ("Tiefkühlgerichte", "tiefkuehler", 180, 30),
    "obst": ("Obst", "vorrat", 6, 6),
    "gebaeck": ("Gebäck & Brot", "vorrat", 2, 2),
    "nudeln": ("Nudeln", "vorrat", 365, 30),
    "sugo": ("Saucen", "vorrat", 365, 21),
    "suesses": ("Süßes & Snacks", "vorrat", 180, 14),
    "muesli": ("Müsli", "vorrat", 180, 30),
    "getraenke": ("Getränke", "vorrat", 365, 14),
    "drogerie": ("Drogerie", "haushalt", 730, 60),
    "haushalt": ("Haushalt", "haushalt", 730, 60),
    "anschaffung": ("Anschaffung", "anschaffung", 3650, 3650),
    "pfand": ("Pfand & Sackerl", "hidden", 0, 0),
}

# Bontext: (Produkt, Kategorie)
ALIASES = {
    "AIRWAVES": ("Airwaves Kaugummi", "suesses"),
    "ARIEL ALL-IN-1 PODS": ("Ariel Pods", "haushalt"),
    "ARIEL MAXPOWER PODS": ("Ariel Pods", "haushalt"),
    "AUSTRO BURGER GEFL.": ("Geflügelburger", "fleisch"),
    "AUTAN SPRAY 100ML": ("Autan Spray", "drogerie"),
    "BAHL.PICK UP 5ER": ("Bahlsen Pick Up", "suesses"),
    "BANANEN": ("Bananen", "obst"),
    "BIO BANANEN": ("Bananen", "obst"),
    "BAR.FUSILLI": ("Barilla Nudeln", "nudeln"),
    "BAR.MACCHER.": ("Barilla Nudeln", "nudeln"),
    "BARILLA GIRANDOLE": ("Barilla Nudeln", "nudeln"),
    "BARILLA SUGO": ("Barilla Sugo", "sugo"),
    "BERTAGNI RAGU BOLOG": ("Bertagni Sugo", "sugo"),
    "BERTAGNI SUGO TONNO": ("Bertagni Sugo", "sugo"),
    "BKISS CREMSEIF.500ML": ("Cremeseife", "drogerie"),
    "COCA-COLA 0,2L.DOSE": ("Coca-Cola", "getraenke"),
    "COCA-COLA 0,33L": ("Coca-Cola", "getraenke"),
    "COCA-COLA 0,5LFL.": ("Coca-Cola", "getraenke"),
    "DK ZAHNCREME 125ML": ("Zahncreme", "drogerie"),
    "DRANO GEL 500ML": ("Rohrreiniger", "haushalt"),
    "ENJ.STEIRERS. 240G": ("Steirerkas-Aufstrich", "aufstrich"),
    "ENJOY BUCHWEIZENWECK": ("Gebäck", "gebaeck"),
    "ENJOY CREME 240G": ("Aufstrich", "aufstrich"),
    "ENJOY DM DRESSING": ("Dressing", "aufstrich"),
    "ENJOY KORNSPITZ DACH": ("Gebäck", "gebaeck"),
    "ENJOY KORNSPITZ KAES": ("Gebäck", "gebaeck"),
    "ENJOY LAUGENCROISSAN": ("Laugencroissant", "gebaeck"),
    "ENJOY LAUGENST.NEUBU": ("Laugenstange", "gebaeck"),
    "ENJOY PUTENSCHNITZEL": ("Putenschnitzel", "fleisch"),
    "ENJOY RUSTIKALBAG.GO": ("Baguette", "gebaeck"),
    "ENJOY SAATENBAGUETTE": ("Baguette", "gebaeck"),
    "ENJOY SALAT THUNF.": ("Thunfischsalat", "belegt"),
    "ENJOY TOPFEN KORNW": ("Gebäck", "gebaeck"),
    "ETIK. K. 75X": ("Etiketten", "anschaffung"),
    "FROSTA BUTTER CHICK.": ("Frosta Gericht", "tk"),
    "FROSTA HENDLPFANNE": ("Frosta Gericht", "tk"),
    "FROSTA RAHMGESCHNETZ": ("Frosta Gericht", "tk"),
    "GEFLUEGEL LAIBCHEN": ("Laibchen", "fleisch"),
    "GLEM SHAMPOO 350ML": ("Shampoo", "drogerie"),
    "HARRY VITAL+FIT BROT": ("Brot", "gebaeck"),
    "HUEHNERSCHNITZEL SEM": ("Schnitzelsemmel", "belegt"),
    "IN PAPIERTASCHE": ("Papiertasche", "pfand"),
    "INNOC.IMMUNSHOT80ML": ("Innocent Shot", "shots"),
    "INNOCENTIMMUN 80ML": ("Innocent Shot", "shots"),
    "ISANA DUSCHGEL 300ML": ("Duschgel", "drogerie"),
    "KAISERSEMMEL KAESE": ("Käsesemmel", "belegt"),
    "KINDER JOY 20G": ("Kinder Joy", "suesses"),
    "KM VOLLMILCH LF 1L": ("Milch", "milch"),
    "KORNSPITZ FARMERSCHI": ("Kornspitz belegt", "belegt"),
    "LAUGENECK PIKANT": ("Laugeneck", "gebaeck"),
    "LIST.MUNDSPUEL.500ML": ("Mundspülung", "drogerie"),
    "LOVELY TOPA 4- LAG.": ("Klopapier", "haushalt"),
    "M + M'S ERDNUSS 330G": ("M&M's", "suesses"),
    "MAKI LACHS": ("Sushi", "belegt"),
    "MAN.NEAPOLIT.4-ER": ("Manner Schnitten", "suesses"),
    "MILKA TAFEL 190G": ("Milka", "suesses"),
    "MILKA TAFEL 95G": ("Milka", "suesses"),
    "NIV.SUN SPRAY FRISCH": ("Sonnenspray", "drogerie"),
    "OETKER LA MIA 380G": ("Tiefkühlpizza", "tk"),
    "OETVITSCHOKOMUESLI": ("Schokomüsli", "muesli"),
    "OLD SPICE DEO STICK": ("Deo", "drogerie"),
    "ORAL B ZC 75ML": ("Zahncreme", "drogerie"),
    "ORAL-B IO BUERSTEN": ("Zahnbürstenköpfe", "drogerie"),
    "PALM.DUSCHGEL 250ML": ("Duschgel", "drogerie"),
    "PFAND": ("Pfand", "pfand"),
    "PFAND EINWEG": ("Pfand", "pfand"),
    "PHILLIPS BLADE 3PACK": ("Rasierklingen", "drogerie"),
    "PORTION GEMUESE": ("Gemüse", "gemuese"),
    "RAGU BOLOGN.": ("Ragù", "sugo"),
    "REDBULL 0.25": ("Red Bull", "getraenke"),
    "RUBIN SPANNLEINTUCH": ("Spannleintuch", "anschaffung"),
    "S-BU. NUSSNOUGAT CR.": ("Nussnougatcreme", "suesses"),
    "S-BUDGET ALMAUFSCHN.": ("Käseaufschnitt", "kaese"),
    "S-BUDGET FRISCHKAESE": ("Frischkäse", "kaese_frisch"),
    "S-BUDGET MOZZA-RELLA": ("Mozzarella", "kaese_frisch"),
    "S-BUDGET MOZZARELLA": ("Mozzarella", "kaese_frisch"),
    "SAATENBAGUETTE PUTEN": ("Baguette belegt", "belegt"),
    "SBUDGET ALLZWECKTUCH": ("Allzwecktücher", "haushalt"),
    "SBUDGET BREZENSEMMEL": ("Gebäck", "gebaeck"),
    "SCHOLL WARZENENTFERN": ("Scholl", "anschaffung"),
    "SCHW.CORDON BLEU": ("Cordon bleu", "fleisch"),
    "SCHWEINSCHNITZELSESM": ("Schnitzelsemmel", "belegt"),
    "SEMMEL TANN": ("Semmeln", "gebaeck"),
    "SHAREBIONUSSSCHOKRIE": ("Schokoriegel", "suesses"),
    "SIMPEX FL.TOPF 16CM": ("Kochgeschirr", "anschaffung"),
    "SIMPEX PASTATELLER": ("Kochgeschirr", "anschaffung"),
    "SIMPEX PFANNE 28CM": ("Kochgeschirr", "anschaffung"),
    "SMOOTHIE 0,3L": ("Smoothie", "shots"),
    "SMOOTHIE 300ML": ("Smoothie", "shots"),
    "SPAR BIO-MILCH 1L": ("Milch", "milch"),
    "SPAR ENJOY SHOT 60ML": ("Enjoy Shot", "shots"),
    "SPAR RIEGEL 150G": ("Schokoriegel", "suesses"),
    "TA.FASCH.LAIBCHEN": ("Laibchen", "fleisch"),
    "TOPPITS BACKPAP FRIT": ("Backpapier", "haushalt"),
    "TRUE FRUITS 250ML": ("True Fruits Smoothie", "shots"),
    "VOES. MILD 1L MW FL.": ("Vöslauer", "getraenke"),
    "VOES.OHNE 1L MW FL.": ("Vöslauer", "getraenke"),
    "VOESLAUER OHNE 1L": ("Vöslauer", "getraenke"),
    "WAGNER PICCOLINIS": ("Piccolinis", "tk"),
    "WILK.HYDRO5": ("Rasierer", "drogerie"),
}


def seed(conn) -> None:
    with conn:
        conn.executemany(
            "INSERT OR IGNORE INTO categories (key, label, storage, shelf_days, use_days)"
            " VALUES (?, ?, ?, ?, ?)",
            [(k, *v) for k, v in CATEGORIES.items()],
        )
        conn.executemany(
            "INSERT OR IGNORE INTO products (name, category) VALUES (?, ?)",
            set(ALIASES.values()),
        )
        conn.executemany(
            "INSERT OR IGNORE INTO aliases (text, product_id)"
            " SELECT ?, id FROM products WHERE name = ?",
            [(text, name) for text, (name, _) in ALIASES.items()],
        )
