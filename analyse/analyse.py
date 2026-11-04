
import sqlite3
from datetime import datetime


# ============================================================
# PUISSANCE NORMALE DE CHAQUE TYPE D'ÉQUIPEMENT
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
# 1. CONSOMMATION TOTALE DU BÂTIMENT
# ============================================================

curseur.execute("""
    SELECT SUM(energie)
    FROM consommations
""")

resultat = curseur.fetchone()

consommation_totale = resultat[0] if resultat[0] is not None else 0


# ============================================================
# 2. CONSOMMATION PAR SALLE
# ============================================================

curseur.execute("""
    SELECT
        salles.nom,
        SUM(consommations.energie)
    FROM salles
    JOIN equipements
        ON salles.id = equipements.salle_id
    JOIN consommations
        ON equipements.id = consommations.equipement_id
    GROUP BY salles.id
    ORDER BY SUM(consommations.energie) DESC
""")

consommation_salles = curseur.fetchall()


# ============================================================
# 3. CONSOMMATION PAR ÉQUIPEMENT
# ============================================================

curseur.execute("""
    SELECT
        equipements.nom,
        salles.nom,
        SUM(consommations.energie)
    FROM equipements
    JOIN salles
        ON equipements.salle_id = salles.id
    JOIN consommations
        ON equipements.id = consommations.equipement_id
    GROUP BY equipements.id
    ORDER BY SUM(consommations.energie) DESC
""")

consommation_equipements = curseur.fetchall()


# ============================================================
# 4. PUISSANCE MOYENNE ET MAXIMALE
# ============================================================

curseur.execute("""
    SELECT
        AVG(puissance),
        MAX(puissance)
    FROM consommations
""")

puissance_moyenne, puissance_maximale = curseur.fetchone()

if puissance_moyenne is None:
    puissance_moyenne = 0

if puissance_maximale is None:
    puissance_maximale = 0


# ============================================================
# 5. CONSOMMATION PAR HEURE
# ============================================================

curseur.execute("""
    SELECT
        strftime('%H', date_heure) AS heure,
        SUM(energie)
    FROM consommations
    GROUP BY heure
    ORDER BY heure
""")

consommation_par_heure = curseur.fetchall()


# ============================================================
# 6. DÉTECTION DES ANOMALIES
# ============================================================

# On récupère toutes les mesures enregistrées.

curseur.execute("""
    SELECT
        consommations.date_heure,
        salles.nom,
        equipements.nom,
        consommations.puissance,
        consommations.energie
    FROM consommations
    JOIN equipements
        ON consommations.equipement_id = equipements.id
    JOIN salles
        ON equipements.salle_id = salles.id
    ORDER BY consommations.puissance DESC
""")

mesures = curseur.fetchall()

anomalies = []


# Une mesure est considérée comme anormale
# si elle dépasse de 2 0 % la puissance normale
# de son propre équipement.

for date_heure, salle, equipement, puissance, energie in mesures:

    puissance_normale = puissances_normales.get(equipement)

    if puissance_normale is None:
        continue

    seuil_anomalie = puissance_normale * 1.20

    if puissance > seuil_anomalie:

        anomalies.append(
            (
                date_heure,
                salle,
                equipement,
                puissance,
                energie,
                puissance_normale,
                seuil_anomalie
            )
        )


# ============================================================
# 7. ÉQUIPEMENTS À FORTE CONSOMMATION
# ============================================================

curseur.execute("""
    SELECT AVG(total_energie)
    FROM (
        SELECT
            equipement_id,
            SUM(energie) AS total_energie
        FROM consommations
        GROUP BY equipement_id
    )
""")

resultat = curseur.fetchone()

moyenne_equipement = resultat[0]

if moyenne_equipement is None:
    moyenne_equipement = 0


# Un équipement est considéré comme fortement consommateur
# lorsque sa consommation totale dépasse de 20 %
# la consommation moyenne des équipements.

seuil_forte_consommation = moyenne_equipement * 1.20


curseur.execute("""
    SELECT
        equipements.nom,
        salles.nom,
        SUM(consommations.energie)
    FROM equipements
    JOIN salles
        ON equipements.salle_id = salles.id
    JOIN consommations
        ON equipements.id = consommations.equipement_id
    GROUP BY equipements.id
    HAVING SUM(consommations.energie) > ?
    ORDER BY SUM(consommations.energie) DESC
""", (seuil_forte_consommation,))

equipements_forts_consommateurs = curseur.fetchall()


# ============================================================
# 8. AFFICHAGE DES RÉSULTATS
# ============================================================

print()
print("====================================================")
print("          ANALYSE INTELLIGENTE DE L'ÉNERGIE")
print("====================================================")
print()

print("Date de l'analyse :", datetime.now())
print()


# ============================================================
# CONSOMMATION TOTALE
# ============================================================

print("----------------------------------------------------")
print("1. CONSOMMATION TOTALE")
print("----------------------------------------------------")

print(
    f"Consommation totale : "
    f"{consommation_totale:.4f} kWh"
)

print()


# ============================================================
# PUISSANCE
# ============================================================

print("----------------------------------------------------")
print("2. PUISSANCE")
print("----------------------------------------------------")

print(
    f"Puissance moyenne : "
    f"{puissance_moyenne:.4f} kW"
)

print(
    f"Puissance maximale : "
    f"{puissance_maximale:.4f} kW"
)

print()


# ============================================================
# CONSOMMATION PAR SALLE
# ============================================================

print("----------------------------------------------------")
print("3. CONSOMMATION PAR SALLE")
print("----------------------------------------------------")

if consommation_salles:

    for salle, consommation in consommation_salles:

        print(
            f"{salle} : "
            f"{consommation:.4f} kWh"
        )

else:

    print("Aucune donnée disponible.")

print()


# ============================================================
# CONSOMMATION PAR ÉQUIPEMENT
# ============================================================

print("----------------------------------------------------")
print("4. CONSOMMATION PAR ÉQUIPEMENT")
print("----------------------------------------------------")

if consommation_equipements:

    for equipement, salle, consommation in consommation_equipements:

        print(
            f"{equipement} | "
            f"{salle} | "
            f"{consommation:.4f} kWh"
        )

else:

    print("Aucune donnée disponible.")

print()


# ============================================================
# CONSOMMATION PAR HEURE
# ============================================================

print("----------------------------------------------------")
print("5. CONSOMMATION PAR HEURE")
print("----------------------------------------------------")

if consommation_par_heure:

    for heure, consommation in consommation_par_heure:

        print(
            f"{heure}:00 - "
            f"{consommation:.4f} kWh"
        )

else:

    print("Aucune donnée disponible.")

print()


# ============================================================
# ANOMALIES
# ============================================================

print("----------------------------------------------------")
print("6. DÉTECTION DES ANOMALIES")
print("----------------------------------------------------")

print(
    "Méthode : comparaison avec la puissance normale "
    "de chaque équipement."
)

print("Marge d'anomalie : 20 %")
print()

if anomalies:

    print(
        f"{len(anomalies)} anomalie(s) détectée(s) :"
    )

    print()

    for (
        date_heure,
        salle,
        equipement,
        puissance,
        energie,
        puissance_normale,
        seuil_anomalie
    ) in anomalies:

        print(
            f"[ANOMALIE] {date_heure} | "
            f"{salle} | "
            f"{equipement} | "
            f"Puissance : {puissance:.4f} kW | "
            f"Normale : {puissance_normale:.2f} kW | "
            f"Seuil : {seuil_anomalie:.2f} kW | "
            f"Énergie : {energie:.4f} kWh"
        )

else:

    print("Aucune anomalie détectée.")

print()


# ============================================================
# FORTE CONSOMMATION
# ============================================================

print("----------------------------------------------------")
print("7. ÉQUIPEMENTS À FORTE CONSOMMATION")
print("----------------------------------------------------")

print(
    f"Consommation moyenne par équipement : "
    f"{moyenne_equipement:.4f} kWh"
)

print(
    f"Seuil de forte consommation : "
    f"{seuil_forte_consommation:.4f} kWh"
)

print()

if equipements_forts_consommateurs:

    for equipement, salle, consommation in equipements_forts_consommateurs:

        print(
            f"[FORTE CONSOMMATION] "
            f"{equipement} | "
            f"{salle} | "
            f"{consommation:.4f} kWh"
        )

else:

    print("Aucun équipement à forte consommation.")

print()


# ============================================================
# FIN DE L'ANALYSE
# ============================================================

print("====================================================")
print("              FIN DE L'ANALYSE")
print("====================================================")


# ============================================================
# FERMETURE DE LA CONNEXION
# ============================================================

connexion.close()

