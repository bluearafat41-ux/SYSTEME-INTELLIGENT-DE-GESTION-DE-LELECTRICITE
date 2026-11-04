import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE = BASE_DIR / "database" / "database.db"
FENETRE_ANALYSE_MINUTES = 10
SEUIL_ANOMALIE = 1.20

PUISSANCES_NORMALES = {
    "Ordinateurs": 0.15,
    "Climatiseur": 1.50,
    "Ventilateurs": 0.08,
    "Éclairage": 0.20,
    "Vidéoprojecteur": 0.30,
    "Imprimante": 0.50,
    "Équipements de laboratoire": 1.00
}

def analyser_alertes():
    connexion = sqlite3.connect(DATABASE, timeout=20)
    try:
        curseur = connexion.cursor()
        maintenant = datetime.now()
        debut = maintenant - timedelta(minutes=FENETRE_ANALYSE_MINUTES)

        curseur.execute("""
            SELECT
                c.equipement_id,
                e.salle_id,
                e.nom,
                s.nom,
                c.date_heure,
                c.puissance
            FROM consommations c
            JOIN equipements e ON e.id = c.equipement_id
            JOIN salles s ON s.id = e.salle_id
            WHERE c.date_heure >= ?
            ORDER BY c.date_heure ASC
        """, (debut.strftime("%Y-%m-%d %H:%M:%S"),))
        mesures = curseur.fetchall()

        # On conserve seulement la mesure anormale la plus élevée
        # de chaque équipement pendant cette fenêtre.
        anomalies = {}
        for equipement_id, salle_id, nom, salle, date_heure, puissance in mesures:
            normale = PUISSANCES_NORMALES.get(nom)
            if normale is None or puissance is None:
                continue
            seuil = normale * SEUIL_ANOMALIE
            if float(puissance) > seuil:
                ancienne = anomalies.get(equipement_id)
                if ancienne is None or float(puissance) > float(ancienne[5]):
                    anomalies[equipement_id] = (
                        equipement_id, salle_id, nom, salle, date_heure, puissance, seuil
                    )

        nouvelles = 0
        for equipement_id, salle_id, nom, salle, date_heure, puissance, seuil in anomalies.values():
            # Une seule alerte ACTIVE par équipement et par type :
            # les cycles suivants ne recréent pas le même événement en boucle.
            curseur.execute("""
                SELECT id FROM alertes
                WHERE equipement_id = ?
                  AND type = 'SURCONSOMMATION'
                  AND UPPER(statut) = 'ACTIVE'
                LIMIT 1
            """, (equipement_id,))
            if curseur.fetchone():
                continue

            niveau = "TRÈS ÉLEVÉ" if float(puissance) >= seuil * 1.5 else "ÉLEVÉ"
            message = (
                f"Surconsommation détectée dans {salle} : {nom}. "
                f"Puissance mesurée : {float(puissance):.3f} kW ; "
                f"seuil de détection : {seuil:.3f} kW."
            )

            curseur.execute("""
                INSERT INTO alertes
                    (salle_id, equipement_id, type, message, niveau, date_heure, statut)
                VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
            """, (
                salle_id,
                equipement_id,
                "SURCONSOMMATION",
                message,
                niveau,
                date_heure
            ))
            nouvelles += 1
            print(f"[ALERTE] Nouvelle alerte #{curseur.lastrowid} — {nom} / {salle}", flush=True)

        connexion.commit()
        print(
            f"[ALERTES] {len(mesures)} mesures examinées sur {FENETRE_ANALYSE_MINUTES} min ; "
            f"{len(anomalies)} équipement(s) anormal(aux) ; {nouvelles} nouvelle(s) alerte(s).",
            flush=True
        )
    except Exception:
        connexion.rollback()
        raise
    finally:
        connexion.close()

if __name__ == "__main__":
    analyser_alertes()
