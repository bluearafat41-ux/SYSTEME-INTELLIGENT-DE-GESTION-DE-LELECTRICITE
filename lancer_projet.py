import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SIMULATEUR = BASE_DIR / "simulator" / "simulator.py"
APP = BASE_DIR / "app.py"
ALERTES = BASE_DIR / "alertes" / "alertes.py"
OPTIMISATION = BASE_DIR / "optimisation" / "optimisation.py"

INTERVALLE_MESURE = 120
INTERVALLE_TRAITEMENT = 600  # 10 minutes

def afficher(message):
    print(f"[SYSTEME] {message}", flush=True)

def trouver_analyse():
    candidats = [
        BASE_DIR / "analyse.py",
        BASE_DIR / "analyse" / "analyse.py",
        BASE_DIR / "analysis" / "analyse.py",
    ]
    for fichier in candidats:
        if fichier.is_file():
            return fichier

    ignores = {".git", ".venv", "venv", "__pycache__", "site-packages", "node_modules"}
    for fichier in BASE_DIR.rglob("analyse.py"):
        if not any(part in ignores for part in fichier.parts) and fichier.is_file():
            return fichier
    return None

def demarrer_processus(nom, fichier):
    if not fichier.is_file():
        afficher(f"{nom} introuvable : {fichier}")
        return None
    processus = subprocess.Popen(
        [sys.executable, str(fichier)],
        cwd=str(BASE_DIR)
    )
    afficher(f"{nom} démarré (PID {processus.pid}).")
    return processus

def executer_module(nom, fichier):
    if fichier is None or not fichier.is_file():
        afficher(f"{nom} introuvable — étape ignorée.")
        return False
    afficher(f"Début : {nom}")
    resultat = subprocess.run(
        [sys.executable, str(fichier)],
        cwd=str(BASE_DIR)
    )
    if resultat.returncode == 0:
        afficher(f"Terminé : {nom}")
        return True
    afficher(f"ERREUR : {nom} (code {resultat.returncode}).")
    return False

def arreter_processus(processus):
    for nom, proc in processus.items():
        if proc is None or proc.poll() is not None:
            continue
        afficher(f"Arrêt de {nom}...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

def cycle_traitement(analyse):
    afficher("Cycle de traitement de 10 minutes.")
    # L'ordre est important : analyse, alertes, puis optimisation liée aux alertes.
    if analyse is not None:
        executer_module("Analyse générale", analyse)
    executer_module("Détection des alertes", ALERTES)
    executer_module("Génération des optimisations", OPTIMISATION)
    afficher("Cycle de traitement terminé.")

def main():
    afficher("Démarrage du système de gestion énergétique.")
    processus = {}
    analyse = trouver_analyse()

    try:
        processus["simulateur"] = demarrer_processus("Simulateur", SIMULATEUR)
        time.sleep(1)
        processus["application Flask"] = demarrer_processus("Application Flask", APP)

        afficher("Mesures prévues toutes les 2 minutes.")
        afficher("Premier traitement prévu dans 10 minutes (pas de traitement prématuré).")

        prochaine_execution = time.monotonic() + INTERVALLE_TRAITEMENT

        while True:
            attente = prochaine_execution - time.monotonic()
            if attente > 0:
                time.sleep(attente)

            cycle_traitement(analyse)

            # Cadence régulière, sans dérive due à la durée des traitements.
            prochaine_execution += INTERVALLE_TRAITEMENT
            maintenant = time.monotonic()
            while prochaine_execution <= maintenant:
                prochaine_execution += INTERVALLE_TRAITEMENT

    except KeyboardInterrupt:
        afficher("Arrêt demandé par l'utilisateur.")
    finally:
        arreter_processus(processus)
        afficher("Tous les processus ont été arrêtés.")

if __name__ == "__main__":
    main()
