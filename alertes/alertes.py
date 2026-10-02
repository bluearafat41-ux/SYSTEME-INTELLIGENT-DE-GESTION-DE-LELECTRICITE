
import sqlite3
from datetime import datetime


# ============================================================
# PUISSANCE NORMALE DES ÉQUIPEMENTS
# ============================================================

puissances_normales = {
    "Ordinateurs": 0.15,
    "Climatiseur": 1.50,
    "Ventilateurs": 0.08,
    "Éclairage": 0.20,
    "Vidéoprojecteur": 0.30,
    "Imprimante": 0.50,
    "Équipements de laboratoire": 1.00
}


# ============================================================
# CONNEXION À LA BASE DE DONNÉES
# ============================================================

connexion = sqlite3.connect("database/database.db")
curseur = connexion.cursor()


# ============================================================
# RÉCUPÉRATION DES MESURES
# ============================================================

curseur.execute("""
    SELECT
        consommations.id,
        consommations.date_heure,
        consommations.puissance,
        equipements.id,
        equipements.nom,
        salles.id,
        salles.nom
    FROM consommations
    JOIN equipements
        ON consommations.equipement_id = equipements.id
    JOIN salles
        ON equipements.salle_id = salles.id
    ORDER BY consommations.date_heure DESC
""")

mesures = curseur.fetchall()


# ============================================================
# TRAITEMENT DES MESURES
# ============================================================

nombre_alertes = 0

for (
    consommation_id,
    date_heure,
    puissance,
    equipement_id,
    equipement,
    salle_id,
    salle
) in mesures:

    # Récupération de la puissance normale
    puissance_normale = puissances_normales.get(equipement)

    # Si l'équipement n'est pas défini, on passe au suivant
    if puissance_normale is None:
        continue

    # Calcul du seuil d'anomalie
    seuil = puissance_normale * 1.20

    # Vérification de l'anomalie
    if puissance > seuil:

        # Vérifier si cette alerte existe déjà
        curseur.execute("""
            SELECT id
            FROM alertes
            WHERE salle_id = ?
            AND equipement_id = ?
            AND date_heure = ?
        """, (
            salle_id,
            equipement_id,
            date_heure
        ))

        alerte_existante = curseur.fetchone()

        # Création de l'alerte uniquement si elle n'existe pas
        if alerte_existante is None:

            message = (
                f"Consommation anormale détectée pour "
                f"{equipement} dans {salle}. "
                f"Puissance mesurée : {puissance:.2f} kW. "
                f"Seuil : {seuil:.2f} kW."
            )

            curseur.execute("""
                INSERT INTO alertes
                (
                    salle_id,
                    equipement_id,
                    type,
                    message,
                    niveau,
                    date_heure,
                    statut
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                salle_id,
                equipement_id,
                "SURCONSOMMATION",
                message,
                "ÉLEVÉ",
                date_heure,
                "ACTIVE"
            ))

            nombre_alertes += 1


# ============================================================
# ENREGISTREMENT
# ============================================================

connexion.commit()


# ============================================================
# AFFICHAGE
# ============================================================

print()
print("====================================================")
print("              SYSTÈME D'ALERTES")
print("====================================================")
print()

print("Date du traitement :", datetime.now())
print()

print("Mesures analysées :", len(mesures))
print("Nouvelles alertes :", nombre_alertes)
print()


# ============================================================
# AFFICHAGE DES ALERTES ACTIVES
# ============================================================

curseur.execute("""
    SELECT
        alertes.date_heure,
        salles.nom,
        equipements.nom,
        alertes.type,
        alertes.message,
        alertes.niveau,
        alertes.statut
    FROM alertes
    JOIN salles
        ON alertes.salle_id = salles.id
    LEFT JOIN equipements
        ON alertes.equipement_id = equipements.id
    WHERE alertes.statut = 'ACTIVE'
    ORDER BY alertes.date_heure DESC
""")

alertes_actives = curseur.fetchall()


print("----------------------------------------------------")
print("ALERTES ACTIVES")
print("----------------------------------------------------")

if alertes_actives:

    for (
        date_heure,
        salle,
        equipement,
        type_alerte,
        message,
        niveau,
        statut
    ) in alertes_actives:

        print()
        print(
            f"[{niveau}] "
            f"{date_heure} | "
            f"{salle} | "
            f"{equipement}"
        )

        print("Type :", type_alerte)
        print("Message :", message)
        print("Statut :", statut)

else:

    print("Aucune alerte active.")


print()
print("====================================================")
print("           FIN DU SYSTÈME D'ALERTES")
print("====================================================")


# ============================================================
# FERMETURE
# ============================================================

connexion.close()

