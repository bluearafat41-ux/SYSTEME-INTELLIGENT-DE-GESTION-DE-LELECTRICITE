"""
MODULE D'OPTIMISATION INTELLIGENTE DE L'ÉNERGIE

Utilisation :
    python optimisation optimisation.py

Le module analyse les consommations des 7 derniers jours
et génère automatiquement des recommandations d'optimisation.

Types d'anomalies détectées :
    1. Surconsommation
    2. Fonctionnement répété hors horaires
    3. Surconsommation + fonctionnement hors horaires
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE = BASE_DIR / "database" / "database.db"


# ============================================================
# PUISSANCE NORMALE DES ÉQUIPEMENTS
# ============================================================

PUISSANCES_NORMALES = {
    "Ordinateurs": 0.15,
    "Climatiseur": 1.50,
    "Ventilateurs": 0.08,
    "Éclairage": 0.20,
    "Vidéoprojecteur": 0.30,
    "Imprimante": 0.50,
    "Équipements de laboratoire": 1.00
}


# ============================================================
# HORAIRES NORMAUX
# ============================================================

HEURE_DEBUT_MATIN = 7 * 60 + 30
HEURE_FIN_MATIN = 12 * 60 + 30

HEURE_DEBUT_APRES_MIDI = 14 * 60 + 30
HEURE_FIN_APRES_MIDI = 18 * 60 + 30


# ============================================================
# SEUILS DE SURCONSOMMATION
# ============================================================

SEUIL_FAIBLE = 10
SEUIL_MOYEN = 30
SEUIL_ELEVE = 50


# ============================================================
# SEUIL HORS HORAIRES
# ============================================================

# Au moins 20 % des mesures hors horaires doivent montrer
# une consommation réelle pour considérer le comportement
# comme significatif.

SEUIL_HORS_HORAIRE = 0.20

# Une puissance inférieure à cette valeur est considérée
# comme pratiquement nulle.

SEUIL_PUISSANCE_ACTIVE = 0.01


# ============================================================
# MESSAGES HORS HORAIRES
# ============================================================

MSG_HORS_HORAIRE = {

    "Climatiseur":
        "Fonctionnement de la climatisation détecté régulièrement "
        "hors des horaires normaux. Il est recommandé d'éteindre "
        "ou de réduire la climatisation lorsque la salle est inoccupée.",

    "Éclairage":
        "Éclairage détecté régulièrement hors des horaires normaux. "
        "Il est recommandé d'éteindre les éclairages inutilisés "
        "lorsque la salle est inoccupée.",

    "Ventilateurs":
        "Ventilation détectée régulièrement hors des horaires normaux. "
        "Il est recommandé d'arrêter les ventilateurs lorsqu'ils "
        "ne sont pas nécessaires.",

    "Vidéoprojecteur":
        "Vidéoprojecteur détecté régulièrement hors des horaires normaux. "
        "Il est recommandé d'éteindre l'appareil après utilisation.",

    "Ordinateurs":
        "Ordinateurs détectés régulièrement hors des horaires normaux. "
        "Il est recommandé d'éteindre les postes inutilisés et "
        "d'activer les modes d'économie d'énergie.",

    "Imprimante":
        "Imprimante détectée régulièrement hors des horaires normaux. "
        "Il est recommandé de l'éteindre lorsqu'elle n'est pas utilisée.",

    "Équipements de laboratoire":
        "Équipements de laboratoire détectés régulièrement hors des "
        "horaires normaux. Il est recommandé de vérifier les équipements "
        "qui peuvent être arrêtés sans perturber les activités."
}


# ============================================================
# MESSAGES SURCONSOMMATION ÉLEVÉE
# ============================================================

MSG_ELEVE = {

    "Climatiseur":
        "Consommation de climatisation très élevée. Vérifier la "
        "température de consigne, l'entretien du climatiseur et "
        "limiter son fonctionnement lorsque la salle est inoccupée.",

    "Éclairage":
        "Consommation d'éclairage très élevée. Vérifier les éclairages "
        "restés actifs inutilement et privilégier uniquement les "
        "zones nécessaires.",

    "Ordinateurs":
        "Consommation informatique très élevée. Éteindre les postes "
        "inutilisés et activer les modes d'économie d'énergie.",

    "Ventilateurs":
        "Consommation de ventilation très élevée. Vérifier les "
        "ventilateurs actifs et arrêter ceux qui ne sont pas nécessaires.",

    "Vidéoprojecteur":
        "Consommation du vidéoprojecteur très élevée. Vérifier son "
        "utilisation et l'éteindre après les présentations.",

    "Imprimante":
        "Consommation de l'imprimante très élevée. Vérifier son "
        "fonctionnement et éviter de la laisser active inutilement.",

    "Équipements de laboratoire":
        "Consommation des équipements de laboratoire très élevée. "
        "Vérifier les appareils actifs et arrêter ceux qui ne "
        "sont pas nécessaires."
}


# ============================================================
# DÉTERMINER SI UNE SALLE EST OUVERTE
# ============================================================

def salle_ouverte(date_heure):
    """
    Vérifie si une mesure se trouve dans les horaires normaux.
    """

    minutes = date_heure.hour * 60 + date_heure.minute

    matin = (
        HEURE_DEBUT_MATIN
        <= minutes
        < HEURE_FIN_MATIN
    )

    apres_midi = (
        HEURE_DEBUT_APRES_MIDI
        <= minutes
        < HEURE_FIN_APRES_MIDI
    )

    return matin or apres_midi


# ============================================================
# CONVERTIR UNE DATE SQLITE
# ============================================================

def convertir_date(date_heure):
    """
    Convertit une date SQLite en objet datetime.

    Plusieurs formats sont acceptés afin de rendre
    le module plus robuste.
    """

    if isinstance(date_heure, datetime):
        return date_heure

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M"
    ]

    for format_date in formats:

        try:
            return datetime.strptime(
                str(date_heure),
                format_date
            )

        except ValueError:
            continue

    return None


# ============================================================
# CALCULER L'ÉCART
# ============================================================

def calculer_ecart(puissance_moyenne, puissance_normale):
    """
    Calcule la différence en pourcentage entre la puissance
    mesurée et la puissance normale.
    """

    if puissance_normale <= 0:
        return 0

    ecart = (
        (puissance_moyenne - puissance_normale)
        / puissance_normale
    ) * 100

    # Une valeur négative n'est pas une surconsommation.

    if ecart < 0:
        return 0

    return ecart


# ============================================================
# DÉTERMINER LA PRIORITÉ
# ============================================================

def determiner_priorite(ecart, hors_horaire):
    """
    Détermine la priorité globale de l'optimisation.

    La surconsommation reste le critère principal.
    Le fonctionnement hors horaires peut augmenter
    la priorité lorsqu'il est réellement significatif.
    """

    if ecart >= SEUIL_ELEVE:
        return "ÉLEVÉE"

    if ecart >= SEUIL_MOYEN:
        return "MOYENNE"

    if ecart >= SEUIL_FAIBLE:
        return "FAIBLE"

    if hors_horaire:
        return "FAIBLE"

    return "NORMALE"


# ============================================================
# GÉNÉRER LA RECOMMANDATION
# ============================================================

def generer_recommandation(
    nom_equipement,
    ecart,
    hors_horaire
):
    """
    Génère automatiquement une recommandation adaptée
    au problème détecté.
    """

    # --------------------------------------------------------
    # CAS 1 : SURCONSOMMATION + HORS HORAIRES
    # --------------------------------------------------------

    if (
        hors_horaire
        and ecart >= SEUIL_MOYEN
    ):

        return (
            f"Le {nom_equipement} présente une surconsommation "
            f"et fonctionne régulièrement hors des horaires normaux. "
            f"Il est recommandé de réduire son fonctionnement "
            f"lorsque la salle est inoccupée et de vérifier son utilisation."
        )

    # --------------------------------------------------------
    # CAS 2 : HORS HORAIRES
    # --------------------------------------------------------

    if (
        hors_horaire
        and nom_equipement in MSG_HORS_HORAIRE
    ):

        return MSG_HORS_HORAIRE[nom_equipement]

    # --------------------------------------------------------
    # CAS 3 : SURCONSOMMATION ÉLEVÉE
    # --------------------------------------------------------

    if (
        ecart >= SEUIL_ELEVE
        and nom_equipement in MSG_ELEVE
    ):

        return MSG_ELEVE[nom_equipement]

    # --------------------------------------------------------
    # CAS 4 : SURCONSOMMATION MOYENNE
    # --------------------------------------------------------

    if ecart >= SEUIL_MOYEN:

        return (
            f"La consommation de {nom_equipement} est supérieure "
            f"d'environ {ecart:.1f}% à la puissance normale. "
            f"Une vérification de son utilisation et de son état "
            f"est recommandée."
        )

    # --------------------------------------------------------
    # CAS 5 : SURCONSOMMATION FAIBLE
    # --------------------------------------------------------

    return (
        f"La consommation de {nom_equipement} est légèrement "
        f"supérieure à la normale ({ecart:.1f}%). "
        f"Il est recommandé de surveiller son évolution."
    )


# ============================================================
# CALCULER LE GAIN ESTIMÉ
# ============================================================

def calculer_gain(ecart, hors_horaire):
    """
    Estime le gain potentiel après optimisation.

    Le gain reste volontairement limité afin d'éviter
    des estimations irréalistes.
    """

    if ecart >= SEUIL_ELEVE:

        gain = ecart * 0.30

    elif ecart >= SEUIL_MOYEN:

        gain = ecart * 0.25

    elif ecart >= SEUIL_FAIBLE:

        gain = ecart * 0.20

    elif hors_horaire:

        gain = 5

    else:

        gain = 0

    return min(gain, 30)


# ============================================================
# VÉRIFIER SI UNE OPTIMISATION EXISTE DÉJÀ
# ============================================================

def optimisation_existe(
    connexion,
    salle_id,
    equipement_id,
    titre
):
    """
    Évite de créer plusieurs fois la même recommandation
    lorsqu'elle est encore en attente.
    """

    curseur = connexion.cursor()

    curseur.execute("""
        SELECT id
        FROM optimisations
        WHERE salle_id = ?
        AND equipement_id = ?
        AND titre = ?
        AND statut = 'EN ATTENTE'
        LIMIT 1
    """, (
        salle_id,
        equipement_id,
        titre
    ))

    return curseur.fetchone() is not None


# ============================================================
# ANALYSE PRINCIPALE
# ============================================================

def analyser_optimisation():

    connexion = sqlite3.connect(DATABASE)
    curseur = connexion.cursor()

    try:

        # ====================================================
        # VÉRIFIER LES DONNÉES
        # ====================================================

        curseur.execute("""
            SELECT COUNT(*)
            FROM consommations
        """)

        nombre_total = curseur.fetchone()[0]

        if nombre_total == 0:

            print()
            print("=" * 70)
            print("AUCUNE DONNÉE DE CONSOMMATION")
            print("=" * 70)
            print()
            print("Lance d'abord le simulateur.")
            print()

            return

        # ====================================================
        # PÉRIODE D'ANALYSE
        # ====================================================

        maintenant = datetime.now()

        date_limite = maintenant - timedelta(days=7)

        curseur.execute("""
            SELECT
                e.id,
                e.salle_id,
                e.nom,
                s.nom,
                c.date_heure,
                c.puissance,
                c.energie
            FROM consommations c

            JOIN equipements e
                ON c.equipement_id = e.id

            JOIN salles s
                ON e.salle_id = s.id

            WHERE c.date_heure >= ?

            ORDER BY c.date_heure ASC
        """, (
            date_limite.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        ))

        donnees = curseur.fetchall()

        if not donnees:

            print()
            print("=" * 70)
            print("AUCUNE DONNÉE RÉCENTE")
            print("=" * 70)
            print()
            print("Lance le simulateur pour générer des données.")
            print()

            return

        # ====================================================
        # REGROUPEMENT PAR ÉQUIPEMENT
        # ====================================================

        groupes = {}

        for ligne in donnees:

            (
                equipement_id,
                salle_id,
                nom_equipement,
                salle,
                date_heure,
                puissance,
                energie
            ) = ligne

            if equipement_id not in groupes:

                groupes[equipement_id] = {

                    "equipement_id": equipement_id,

                    "salle_id": salle_id,

                    "nom": nom_equipement,

                    "salle": salle,

                    "mesures": []
                }

            groupes[equipement_id]["mesures"].append({

                "date_heure": date_heure,

                "puissance": puissance,

                "energie": energie
            })

        # ====================================================
        # AFFICHAGE DU TITRE
        # ====================================================

        print()
        print("=" * 75)
        print("       ANALYSE INTELLIGENTE DES OPTIMISATIONS")
        print("=" * 75)
        print()

        print(
            f"Période analysée : "
            f"{date_limite.strftime('%Y-%m-%d %H:%M:%S')}"
            f" → "
            f"{maintenant.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        print(
            f"Données analysées : {len(donnees)}"
        )

        print(
            f"Équipements analysés : {len(groupes)}"
        )

        print()

        nombre_recommandations = 0

        # ====================================================
        # ANALYSE DE CHAQUE ÉQUIPEMENT
        # ====================================================

        for equipement_id, infos in groupes.items():

            nom = infos["nom"]

            salle = infos["salle"]

            salle_id = infos["salle_id"]

            mesures = infos["mesures"]

            print("-" * 75)

            # =================================================
            # NOMBRE MINIMUM DE MESURES
            # =================================================

            if len(mesures) < 5:

                print(
                    f"Salle              : {salle}"
                )

                print(
                    f"Équipement         : {nom}"
                )

                print(
                    f"Nombre de mesures  : {len(mesures)}"
                )

                print(
                    "Résultat            : données insuffisantes"
                )

                continue

            # =================================================
            # PUISSANCE NORMALE
            # =================================================

            puissance_normale = PUISSANCES_NORMALES.get(
                nom
            )

            if puissance_normale is None:

                print(
                    f"Salle              : {salle}"
                )

                print(
                    f"Équipement         : {nom}"
                )

                print(
                    "Résultat            : puissance normale inconnue"
                )

                continue

            # =================================================
            # PUISSANCE MOYENNE
            # =================================================

            puissances = [

                float(mesure["puissance"])

                for mesure in mesures

                if mesure["puissance"] is not None
            ]

            if not puissances:

                print(
                    "Résultat            : aucune puissance valide"
                )

                continue

            puissance_moyenne = (
                sum(puissances)
                / len(puissances)
            )

            # =================================================
            # SURCONSOMMATION
            # =================================================

            ecart = calculer_ecart(
                puissance_moyenne,
                puissance_normale
            )

            # =================================================
            # ANALYSE HORS HORAIRES
            # =================================================

            nombre_hors_horaire = 0

            nombre_mesures_actives_hors_horaire = 0

            for mesure in mesures:

                date_mesure = convertir_date(
                    mesure["date_heure"]
                )

                if date_mesure is None:
                    continue

                if not salle_ouverte(date_mesure):

                    nombre_hors_horaire += 1

                    puissance_mesure = float(
                        mesure["puissance"]
                    )

                    # Une petite valeur proche de zéro
                    # n'est pas considérée comme du fonctionnement.

                    if (
                        puissance_mesure
                        > SEUIL_PUISSANCE_ACTIVE
                    ):

                        nombre_mesures_actives_hors_horaire += 1

            # =================================================
            # POURCENTAGE HORS HORAIRES
            # =================================================

            if len(mesures) > 0:

                pourcentage_hors_horaire = (
                    nombre_mesures_actives_hors_horaire
                    / len(mesures)
                )

            else:

                pourcentage_hors_horaire = 0

            # =================================================
            # COMPORTEMENT HORS HORAIRES SIGNIFICATIF
            # =================================================

            hors_horaire = (
                pourcentage_hors_horaire
                >= SEUIL_HORS_HORAIRE
            )

            # =================================================
            # PRIORITÉ
            # =================================================

            priorite = determiner_priorite(
                ecart,
                hors_horaire
            )

            # =================================================
            # AFFICHAGE DES RÉSULTATS
            # =================================================

            print(
                f"Salle              : {salle}"
            )

            print(
                f"Équipement         : {nom}"
            )

            print(
                f"Nombre de mesures  : {len(mesures)}"
            )

            print(
                f"Puissance moyenne  : "
                f"{puissance_moyenne:.3f} kW"
            )

            print(
                f"Puissance normale  : "
                f"{puissance_normale:.3f} kW"
            )

            print(
                f"Surconsommation    : "
                f"{ecart:.1f}%"
            )

            print(
                f"Mesures actives hors horaires : "
                f"{nombre_mesures_actives_hors_horaire}"
            )

            print(
                f"Hors horaires      : "
                f"{pourcentage_hors_horaire * 100:.1f}%"
            )

            print(
                f"Priorité           : {priorite}"
            )

            # =================================================
            # CONSOMMATION NORMALE
            # =================================================

            if priorite == "NORMALE":

                print(
                    "Résultat            : "
                    "consommation normale"
                )

                continue

            # =================================================
            # CRÉER LE TITRE
            # =================================================

            if (
                hors_horaire
                and ecart >= SEUIL_MOYEN
            ):

                titre = (
                    f"Optimiser fonctionnement - {nom}"
                )

            elif hors_horaire:

                titre = (
                    f"Réduire fonctionnement hors horaires - {nom}"
                )

            elif ecart >= SEUIL_ELEVE:

                titre = (
                    f"Réduire fortement la consommation - {nom}"
                )

            elif ecart >= SEUIL_MOYEN:

                titre = (
                    f"Réduire la consommation - {nom}"
                )

            else:

                titre = (
                    f"Surveiller la consommation - {nom}"
                )

            # =================================================
            # DESCRIPTION
            # =================================================

            description_base = generer_recommandation(
                nom,
                ecart,
                hors_horaire
            )

            description = (
                f"{description_base} "
                f"Analyse basée sur {len(mesures)} mesures "
                f"des 7 derniers jours. "
                f"Surconsommation moyenne : {ecart:.1f} %. "
                f"Fonctionnement actif hors horaires : "
                f"{pourcentage_hors_horaire * 100:.1f} %."
            )

            # =================================================
            # GAIN ESTIMÉ
            # =================================================

            gain_estime = calculer_gain(
                ecart,
                hors_horaire
            )

            # =================================================
            # VÉRIFIER LES DOUBLONS
            # =================================================

            if optimisation_existe(
                connexion,
                salle_id,
                equipement_id,
                titre
            ):

                print(
                    "Résultat            : "
                    "recommandation déjà enregistrée"
                )

                continue

            # =================================================
            # ENREGISTRER
            # =================================================

            curseur.execute("""
                INSERT INTO optimisations
                (
                    salle_id,
                    equipement_id,
                    titre,
                    description,
                    gain_estime,
                    date_heure,
                    statut
                )

                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (

                salle_id,

                equipement_id,

                titre,

                description,

                gain_estime,

                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

                "EN ATTENTE"
            ))

            connexion.commit()

            nombre_recommandations += 1

            print(
                f"Optimisation créée : "
                f"{titre}"
            )

            print(
                f"Gain estimé        : "
                f"{gain_estime:.1f}%"
            )

        # ====================================================
        # RÉSUMÉ
        # ====================================================

        print()
        print("=" * 75)
        print("                         RÉSUMÉ")
        print("=" * 75)

        print()

        print(
            f"Nombre de nouvelles recommandations : "
            f"{nombre_recommandations}"
        )

        print()

        if nombre_recommandations == 0:

            print(
                "Aucune nouvelle optimisation nécessaire."
            )

            print(
                "La consommation actuelle est globalement normale "
                "ou les recommandations existent déjà."
            )

        else:

            print(
                "Les recommandations ont été enregistrées "
                "dans la base de données."
            )

        print()

        print("Analyse terminée.")

        print()

    finally:

        connexion.close()


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

if __name__ == "__main__":
    analyser_optimisation()

