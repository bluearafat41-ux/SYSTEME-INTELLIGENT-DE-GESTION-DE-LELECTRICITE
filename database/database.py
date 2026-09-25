import sqlite3

# Connexion à la base de données
connexion = sqlite3.connect("database/database.db")

# Activation des clés étrangères
connexion.execute("PRAGMA foreign_keys = ON")

curseur = connexion.cursor()


# ============================================================
# 1. TABLE DES SALLES
# ============================================================

curseur.execute("""
CREATE TABLE IF NOT EXISTS salles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    description TEXT,
    localisation TEXT
)
""")


# ============================================================
# 2. TABLE DES ÉQUIPEMENTS
# ============================================================

curseur.execute("""
CREATE TABLE IF NOT EXISTS equipements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    salle_id INTEGER NOT NULL,
    nom TEXT NOT NULL,
    type TEXT,
    etat TEXT NOT NULL DEFAULT 'ACTIF',
    
    FOREIGN KEY (salle_id)
        REFERENCES salles(id)
        ON DELETE CASCADE
)
""")


# ============================================================
# 3. TABLE DES CONSOMMATIONS
# ============================================================

curseur.execute("""
CREATE TABLE IF NOT EXISTS consommations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipement_id INTEGER NOT NULL,
    date_heure DATETIME NOT NULL,
    puissance REAL NOT NULL,
    energie REAL NOT NULL,

    FOREIGN KEY (equipement_id)
        REFERENCES equipements(id)
        ON DELETE CASCADE
)
""")


# ============================================================
# 4. TABLE DES ALERTES
# ============================================================

curseur.execute("""
CREATE TABLE IF NOT EXISTS alertes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    salle_id INTEGER NOT NULL,
    equipement_id INTEGER,
    type TEXT NOT NULL,
    message TEXT NOT NULL,
    niveau TEXT NOT NULL,
    date_heure DATETIME NOT NULL,
    statut TEXT NOT NULL DEFAULT 'ACTIVE',

    FOREIGN KEY (salle_id)
        REFERENCES salles(id)
        ON DELETE CASCADE,

    FOREIGN KEY (equipement_id)
        REFERENCES equipements(id)
        ON DELETE SET NULL
)
""")


# ============================================================
# 5. TABLE DES OPTIMISATIONS
# ============================================================

curseur.execute("""
CREATE TABLE IF NOT EXISTS optimisations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    salle_id INTEGER NOT NULL,
    equipement_id INTEGER,
    titre TEXT NOT NULL,
    description TEXT NOT NULL,
    gain_estime REAL,
    date_heure DATETIME NOT NULL,
    statut TEXT NOT NULL DEFAULT 'EN ATTENTE',

    FOREIGN KEY (salle_id)
        REFERENCES salles(id)
        ON DELETE CASCADE,

    FOREIGN KEY (equipement_id)
        REFERENCES equipements(id)
        ON DELETE SET NULL
)
""")


# ============================================================
# 6. AJOUT DES 5 SALLES
# ============================================================

salles = [
    (
        "Salle informatique",
        "Salle contenant les ordinateurs et équipements informatiques",
        "Bâtiment principal"
    ),
    (
        "Salle de cours",
        "Salle destinée aux enseignements",
        "Bâtiment principal"
    ),
    (
        "Laboratoire",
        "Salle destinée aux travaux pratiques et équipements de laboratoire",
        "Bâtiment principal"
    ),
    (
        "Bureau administratif",
        "Bureau destiné aux activités administratives",
        "Bâtiment administratif"
    ),
    (
        "Salle de réunion",
        "Salle destinée aux réunions et présentations",
        "Bâtiment administratif"
    )
]

curseur.executemany("""
INSERT OR IGNORE INTO salles
(nom, description, localisation)
VALUES (?, ?, ?)
""", salles)


# ============================================================
# 7. AJOUT DES ÉQUIPEMENTS
# ============================================================

equipements = [
    # Salle informatique
    (1, "Ordinateurs", "Informatique", "ACTIF"),
    (1, "Climatiseur", "Climatisation", "ACTIF"),
    (1, "Ventilateurs", "Ventilation", "ACTIF"),
    (1, "Éclairage", "Éclairage", "ACTIF"),
    (1, "Vidéoprojecteur", "Multimédia", "ACTIF"),

    # Salle de cours
    (2, "Climatiseur", "Climatisation", "ACTIF"),
    (2, "Ventilateurs", "Ventilation", "ACTIF"),
    (2, "Éclairage", "Éclairage", "ACTIF"),
    (2, "Vidéoprojecteur", "Multimédia", "ACTIF"),

    # Laboratoire
    (3, "Ordinateurs", "Informatique", "ACTIF"),
    (3, "Climatiseur", "Climatisation", "ACTIF"),
    (3, "Ventilateurs", "Ventilation", "ACTIF"),
    (3, "Éclairage", "Éclairage", "ACTIF"),
    (3, "Équipements de laboratoire", "Laboratoire", "ACTIF"),

    # Bureau administratif
    (4, "Ordinateurs", "Informatique", "ACTIF"),
    (4, "Climatiseur", "Climatisation", "ACTIF"),
    (4, "Ventilateurs", "Ventilation", "ACTIF"),
    (4, "Éclairage", "Éclairage", "ACTIF"),
    (4, "Imprimante", "Bureautique", "ACTIF"),

    # Salle de réunion
    (5, "Climatiseur", "Climatisation", "ACTIF"),
    (5, "Ventilateurs", "Ventilation", "ACTIF"),
    (5, "Éclairage", "Éclairage", "ACTIF"),
    (5, "Vidéoprojecteur", "Multimédia", "ACTIF")
]

curseur.executemany("""
INSERT INTO equipements
(salle_id, nom, type, etat)
VALUES (?, ?, ?, ?)
""", equipements)


# ============================================================
# 8. ENREGISTREMENT DES MODIFICATIONS
# ============================================================

connexion.commit()

print("Base de données créée avec succès !")
print("Tables et données initiales enregistrées.")

connexion.close()