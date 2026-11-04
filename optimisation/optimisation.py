import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE = BASE_DIR / "database" / "database.db"

CONSEILS = {
    "Climatiseur": "Vérifier la température de consigne, l'entretien du climatiseur et réduire son fonctionnement lorsque la salle est inoccupée.",
    "Éclairage": "Éteindre les éclairages inutilisés et privilégier uniquement les zones nécessaires.",
    "Ordinateurs": "Éteindre les postes inutilisés et activer les modes d'économie d'énergie.",
    "Ventilateurs": "Vérifier les ventilateurs actifs et arrêter ceux qui ne sont pas nécessaires.",
    "Vidéoprojecteur": "Éteindre le vidéoprojecteur après utilisation et vérifier qu'il ne reste pas allumé inutilement.",
    "Imprimante": "Éteindre l'imprimante lorsqu'elle n'est pas utilisée et vérifier son mode veille.",
    "Équipements de laboratoire": "Vérifier les appareils actifs et arrêter uniquement ceux qui peuvent l'être sans perturber les activités."
}

def generer_optimisations():
    connexion = sqlite3.connect(DATABASE, timeout=20)
    try:
        connexion.execute("PRAGMA foreign_keys = ON")
        curseur = connexion.cursor()

        # Chaque alerte non encore liée reçoit exactement une optimisation.
        curseur.execute("""
            SELECT
                a.id,
                a.salle_id,
                a.equipement_id,
                a.type,
                a.message,
                a.niveau,
                a.date_heure,
                e.nom,
                s.nom
            FROM alertes a
            JOIN salles s ON s.id = a.salle_id
            LEFT JOIN equipements e ON e.id = a.equipement_id
            LEFT JOIN optimisations o ON o.alerte_id = a.id
            WHERE o.id IS NULL
            ORDER BY a.id ASC
        """)
        alertes = curseur.fetchall()

        creees = 0
        for (
            alerte_id, salle_id, equipement_id, type_alerte,
            message_alerte, niveau, date_alerte, nom_equipement, nom_salle
        ) in alertes:

            nom = nom_equipement or "équipement"
            conseil = CONSEILS.get(
                nom,
                "Vérifier l'équipement concerné et adapter son fonctionnement aux besoins réels."
            )

            titre = f"Optimisation — {nom}"
            description = (
                f"Cette recommandation est liée à l'alerte #{alerte_id} "
                f"détectée dans {nom_salle}. {message_alerte} "
                f"Action recommandée : {conseil}"
            )

            # Estimation indicative, exprimée en pourcentage potentiel.
            # Ce n'est pas une économie mesurée après intervention.
            gain_estime = 20.0 if niveau == "TRÈS ÉLEVÉ" else 10.0

            curseur.execute("""
                INSERT OR IGNORE INTO optimisations
                    (salle_id, equipement_id, alerte_id, titre, description,
                     gain_estime, date_heure, statut)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'EN ATTENTE')
            """, (
                salle_id,
                equipement_id,
                alerte_id,
                titre,
                description,
                gain_estime,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

            if curseur.rowcount == 1:
                creees += 1
                print(
                    f"[OPTIMISATION] Créée pour l'alerte #{alerte_id} "
                    f"— {nom_salle} / {nom}.",
                    flush=True
                )

        connexion.commit()
        print(
            f"[OPTIMISATION] {len(alertes)} alerte(s) sans recommandation examinée(s) ; "
            f"{creees} optimisation(s) créée(s).",
            flush=True
        )
    except Exception:
        connexion.rollback()
        raise
    finally:
        connexion.close()

if __name__ == "__main__":
    generer_optimisations()
