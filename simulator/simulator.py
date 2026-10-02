import sqlite3
import random
import time
from datetime import datetime

# Puissance moyenne de chaque type d'équipement en kW
puissances = {
    "Ordinateurs": 0.15,
    "Climatiseur": 1.50,
    "Ventilateurs": 0.08,
    "Éclairage": 0.20,
    "Vidéoprojecteur": 0.30,
    "Imprimante": 0.50,
    "Équipements de laboratoire": 1.00
}

while True:

    # Connexion à la base de données
    connexion = sqlite3.connect("database/database.db")
    curseur = connexion.cursor()

    # Récupérer tous les équipements
    curseur.execute("""
        SELECT id, salle_id, nom
        FROM equipements
    """)

    equipements = curseur.fetchall()

    # Heure actuelle
    maintenant = datetime.now()
    heure = maintenant.hour + maintenant.minute / 60

    # Vérifier si les salles sont ouvertes
    salle_active = (
        7.5 <= heure < 12.5
        or
        14.5 <= heure < 19.833
    )

    print("====================================")
    print("   NOUVELLE MESURE")
    print("====================================")
    print("Date :", maintenant)
    print("Salles actives :", salle_active)
    print()

    # Générer une mesure pour chaque équipement
    for equipement_id, salle_id, nom in equipements:

        puissance_normale = puissances.get(nom, 0.10)

        if salle_active:
            # Petite variation aléatoire autour de la puissance normale
            puissance = puissance_normale * random.uniform(0.90, 1.10)
        else:
            # Consommation très faible lorsque la salle est fermée
            puissance = puissance_normale * random.uniform(0.00, 0.05)

        # Énergie consommée pendant 5 minutes
        energie = puissance * (5 / 60)

        # Enregistrer la mesure dans la base
        curseur.execute("""
            INSERT INTO consommations
            (equipement_id, date_heure, puissance, energie)
            VALUES (?, ?, ?, ?)
        """, (
            equipement_id,
            maintenant,
            puissance,
            energie
        ))

        print(
            f"{nom} | "
            f"Puissance : {puissance:.3f} kW | "
            f"Énergie : {energie:.4f} kWh"
        )

    connexion.commit()
    connexion.close()

    print()
    print("Mesures enregistrées avec succès !")
    print("Prochaine mesure dans 5 minutes...")
    print()

    # Attendre 5 minutes
    time.sleep(300)