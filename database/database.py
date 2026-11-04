import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"

PUISSANCES = {
    "Ordinateurs": 0.15,
    "Climatiseur": 1.50,
    "Ventilateurs": 0.08,
    "Éclairage": 0.20,
    "Vidéoprojecteur": 0.30,
    "Imprimante": 0.50,
    "Équipements de laboratoire": 1.00,
}

SALLES = [
    ("Salle informatique", "Salle contenant les ordinateurs et équipements informatiques", "Bâtiment principal", 1),
    ("Salle de cours", "Salle destinée aux enseignements", "Bâtiment principal", 1),
    ("Laboratoire", "Salle destinée aux travaux pratiques et équipements de laboratoire", "Bâtiment principal", 1),
    ("Bureau administratif", "Bureau destiné aux activités administratives", "Bâtiment administratif", 1),
    ("Salle de réunion", "Salle destinée aux réunions et présentations", "Bâtiment administratif", 1),
]

EQUIPEMENTS = [
    ("Salle informatique", "Ordinateurs", "Informatique"),
    ("Salle informatique", "Climatiseur", "Climatisation"),
    ("Salle informatique", "Ventilateurs", "Ventilation"),
    ("Salle informatique", "Éclairage", "Éclairage"),
    ("Salle informatique", "Vidéoprojecteur", "Multimédia"),
    ("Salle de cours", "Climatiseur", "Climatisation"),
    ("Salle de cours", "Ventilateurs", "Ventilation"),
    ("Salle de cours", "Éclairage", "Éclairage"),
    ("Salle de cours", "Vidéoprojecteur", "Multimédia"),
    ("Laboratoire", "Ordinateurs", "Informatique"),
    ("Laboratoire", "Climatiseur", "Climatisation"),
    ("Laboratoire", "Ventilateurs", "Ventilation"),
    ("Laboratoire", "Éclairage", "Éclairage"),
    ("Laboratoire", "Équipements de laboratoire", "Laboratoire"),
    ("Bureau administratif", "Ordinateurs", "Informatique"),
    ("Bureau administratif", "Climatiseur", "Climatisation"),
    ("Bureau administratif", "Ventilateurs", "Ventilation"),
    ("Bureau administratif", "Éclairage", "Éclairage"),
    ("Bureau administratif", "Imprimante", "Bureautique"),
    ("Salle de réunion", "Climatiseur", "Climatisation"),
    ("Salle de réunion", "Ventilateurs", "Ventilation"),
    ("Salle de réunion", "Éclairage", "Éclairage"),
    ("Salle de réunion", "Vidéoprojecteur", "Multimédia"),
]

def colonne_existe(cur, table, colonne):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == colonne for row in cur.fetchall())

def initialiser():
    connexion = sqlite3.connect(DB_PATH)
    try:
        connexion.execute("PRAGMA foreign_keys = ON")
        cur = connexion.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS salles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            description TEXT,
            localisation TEXT,
            etage INTEGER NOT NULL DEFAULT 1
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS equipements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salle_id INTEGER NOT NULL,
            nom TEXT NOT NULL,
            type TEXT,
            etat TEXT NOT NULL DEFAULT 'ACTIF',
            FOREIGN KEY (salle_id) REFERENCES salles(id) ON DELETE CASCADE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS consommations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipement_id INTEGER NOT NULL,
            date_heure DATETIME NOT NULL,
            puissance REAL NOT NULL,
            energie REAL NOT NULL,
            FOREIGN KEY (equipement_id) REFERENCES equipements(id) ON DELETE CASCADE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS alertes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salle_id INTEGER NOT NULL,
            equipement_id INTEGER,
            type TEXT NOT NULL,
            message TEXT NOT NULL,
            niveau TEXT NOT NULL,
            date_heure DATETIME NOT NULL,
            statut TEXT NOT NULL DEFAULT 'ACTIVE',
            FOREIGN KEY (salle_id) REFERENCES salles(id) ON DELETE CASCADE,
            FOREIGN KEY (equipement_id) REFERENCES equipements(id) ON DELETE SET NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS optimisations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salle_id INTEGER NOT NULL,
            equipement_id INTEGER,
            alerte_id INTEGER UNIQUE,
            titre TEXT NOT NULL,
            description TEXT NOT NULL,
            gain_estime REAL,
            date_heure DATETIME NOT NULL,
            statut TEXT NOT NULL DEFAULT 'EN ATTENTE',
            FOREIGN KEY (salle_id) REFERENCES salles(id) ON DELETE CASCADE,
            FOREIGN KEY (equipement_id) REFERENCES equipements(id) ON DELETE SET NULL,
            FOREIGN KEY (alerte_id) REFERENCES alertes(id) ON DELETE SET NULL
        )
        """)

        # Migration non destructive pour les bases déjà créées.
        if not colonne_existe(cur, "salles", "etage"):
            cur.execute("ALTER TABLE salles ADD COLUMN etage INTEGER NOT NULL DEFAULT 1")

        if not colonne_existe(cur, "optimisations", "alerte_id"):
            cur.execute("ALTER TABLE optimisations ADD COLUMN alerte_id INTEGER REFERENCES alertes(id) ON DELETE SET NULL")

        # Une alerte ne peut être liée qu'à une seule optimisation.
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_optimisations_alerte_unique
            ON optimisations(alerte_id)
            WHERE alerte_id IS NOT NULL
        """)

        # Index utiles pour accélérer les lectures régulières.
        cur.execute("CREATE INDEX IF NOT EXISTS idx_consommations_date ON consommations(date_heure)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_consommations_equipement_date ON consommations(equipement_id, date_heure)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alertes_equipement_statut ON alertes(equipement_id, statut)")

        # Insérer les salles sans supposer que leurs identifiants sont 1, 2, 3...
        for nom, description, localisation, etage in SALLES:
            cur.execute("""
                INSERT OR IGNORE INTO salles (nom, description, localisation, etage)
                VALUES (?, ?, ?, ?)
            """, (nom, description, localisation, etage))

        cur.execute("SELECT id, nom FROM salles")
        ids_salles = {nom: identifiant for identifiant, nom in cur.fetchall()}

        for nom_salle, nom_equipement, type_equipement in EQUIPEMENTS:
            salle_id = ids_salles[nom_salle]
            cur.execute("""
                SELECT id FROM equipements
                WHERE salle_id = ? AND nom = ?
            """, (salle_id, nom_equipement))
            if cur.fetchone() is None:
                cur.execute("""
                    INSERT INTO equipements (salle_id, nom, type, etat)
                    VALUES (?, ?, ?, 'ACTIF')
                """, (salle_id, nom_equipement, type_equipement))

        connexion.commit()
        print("Base vérifiée et mise à niveau sans supprimer les données.")
        print(f"Base utilisée : {DB_PATH}")
        print("Tables : salles, equipements, consommations, alertes, optimisations.")
        print("Lien alerte → optimisation : activé (alerte_id UNIQUE).")
    except sqlite3.Error as erreur:
        connexion.rollback()
        print(f"Erreur SQLite : {erreur}")
        raise
    finally:
        connexion.close()

if __name__ == "__main__":
    initialiser()
