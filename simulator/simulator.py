import sqlite3
import random
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE = BASE_DIR / "database" / "database.db"
INTERVALLE_SECONDES = 120  # une mesure toutes les 2 minutes
DUREE_MESURE_MINUTES = INTERVALLE_SECONDES / 60

PUISSANCES = {
    "Ordinateurs": 0.15,
    "Climatiseur": 1.50,
    "Ventilateurs": 0.08,
    "Éclairage": 0.20,
    "Vidéoprojecteur": 0.30,
    "Imprimante": 0.50,
    "Équipements de laboratoire": 1.00
}

anomalie_equipement_id = None
anomalie_mesures_restantes = 0

def salle_active(maintenant):
    heure = maintenant.hour + maintenant.minute / 60
    return 7.5 <= heure < 12.5 or 14.5 <= heure < 18.5

def enregistrer_mesure():
    global anomalie_equipement_id, anomalie_mesures_restantes

    connexion = sqlite3.connect(DATABASE, timeout=20)
    try:
        curseur = connexion.cursor()
        curseur.execute("""
            SELECT id, salle_id, nom
            FROM equipements
            WHERE etat = 'ACTIF'
        """)
        equipements = curseur.fetchall()

        if not equipements:
            print("[SIMULATEUR] Aucun équipement actif.", flush=True)
            return

        maintenant = datetime.now()
        actif = salle_active(maintenant)

        if actif and anomalie_mesures_restantes <= 0 and random.random() < 0.05:
            equipement_anormal = random.choice(equipements)
            anomalie_equipement_id = equipement_anormal[0]
            anomalie_mesures_restantes = random.randint(3, 6)
            print(
                f"[SIMULATEUR] Scénario d'anomalie simulée sur "
                f"{equipement_anormal[2]} (équipement {anomalie_equipement_id}).",
                flush=True
            )

        for equipement_id, salle_id, nom in equipements:
            puissance_normale = PUISSANCES.get(nom, 0.10)

            if actif:
                if equipement_id == anomalie_equipement_id and anomalie_mesures_restantes > 0:
                    puissance = puissance_normale * random.uniform(1.5, 2.0)
                else:
                    puissance = puissance_normale * random.uniform(0.90, 1.10)
            else:
                puissance = puissance_normale * random.uniform(0.00, 0.05)

            # kW × heures = kWh ; une mesure couvre ici 2 minutes.
            energie = puissance * (DUREE_MESURE_MINUTES / 60)

            curseur.execute("""
                INSERT INTO consommations
                    (equipement_id, date_heure, puissance, energie)
                VALUES (?, ?, ?, ?)
            """, (
                equipement_id,
                maintenant.strftime("%Y-%m-%d %H:%M:%S"),
                puissance,
                energie
            ))

        if anomalie_mesures_restantes > 0:
            anomalie_mesures_restantes -= 1
            if anomalie_mesures_restantes == 0:
                anomalie_equipement_id = None

        connexion.commit()
        print(
            f"[SIMULATEUR] {maintenant:%d/%m/%Y %H:%M:%S} — "
            f"{len(equipements)} équipements mesurés.",
            flush=True
        )
    finally:
        connexion.close()

def main():
    print("[SIMULATEUR] Démarré — fréquence : 2 minutes.", flush=True)
    while True:
        try:
            enregistrer_mesure()
            time.sleep(INTERVALLE_SECONDES)
        except sqlite3.Error as erreur:
            print(f"[SIMULATEUR] Erreur SQLite : {erreur}", flush=True)
            time.sleep(10)
        except Exception as erreur:
            print(f"[SIMULATEUR] Erreur inattendue : {erreur}", flush=True)
            time.sleep(10)

if __name__ == "__main__":
    main()
