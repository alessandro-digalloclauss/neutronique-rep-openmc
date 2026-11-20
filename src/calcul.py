"""Fonctions pour lancer les calculs OpenMC du projet.

Au début, je relançais tous les calculs à chaque exécution d'un notebook, même quand je
ne modifiais qu'une figure ou un texte, et certains prennent plusieurs minutes. J'ai donc
écrit ces fonctions pour qu'un calcul déjà fait avec exactement les mêmes entrées soit
simplement relu au lieu d'être relancé (une sorte de « cache »).
"""
import contextlib
import hashlib
import io
import json
import os
import sys
import shutil
import tempfile
import threading
import time
from pathlib import Path

import openmc
from openmc.model import SearchResult

TEMOIN = "entrees_calcul.xml"   # copie des entrées, que j'écris seulement quand le calcul est allé au bout


def _exporter_entrees(modele):
    """Renvoie le contenu du fichier model.xml que ce modèle produirait (sans lancer de calcul)."""
    with tempfile.TemporaryDirectory() as tmp:
        chemin = Path(tmp) / "model.xml"
        modele.export_to_model_xml(chemin)
        return chemin.read_bytes()


def _resultat_existant(modele, dossier):
    """Cherche dans `dossier` un résultat déjà calculé pour ce modèle ; renvoie None sinon.

    L'idée : model.xml contient toutes les entrées du calcul (matériaux, géométrie,
    réglages, graine, tallies). S'il est exactement le même que celui d'un calcul déjà
    terminé, refaire le calcul donnerait exactement le même résultat.
    """
    statepoint = dossier / f"statepoint.{modele.settings.batches}.h5"
    if not statepoint.exists():
        return None
    temoin = dossier / TEMOIN
    if temoin.exists():
        # Cas normal : le témoin n'existe que si le calcul précédent est allé jusqu'au bout
        return statepoint if _exporter_entrees(modele) == temoin.read_bytes() else None
    # Anciens dossiers, créés avant que j'ajoute le témoin : on compare directement model.xml
    ancien_xml = dossier / "model.xml"
    if not ancien_xml.exists() or _exporter_entrees(modele) != ancien_xml.read_bytes():
        return None
    if statepoint.stat().st_mtime < ancien_xml.stat().st_mtime:
        return None   # statepoint plus ancien que model.xml : le dernier calcul a été interrompu
    return statepoint


def calculer_k(modele, dossier, reutiliser=True):
    """Lance le calcul de `modele` dans `dossier` et renvoie k avec son incertitude.

    Renvoie un dictionnaire avec : k, sigma (incertitude à 1σ), statepoint (chemin du
    fichier de résultats), duree (en secondes) et reutilise (True si le résultat a été relu).

    Chaque calcul a son propre dossier, pour que les fichiers d'un point d'un balayage
    n'écrasent pas ceux d'un autre.

    Si le même calcul a déjà été fait dans ce dossier, je relis son résultat au lieu de
    relancer OpenMC. Mettre reutiliser=False pour forcer le calcul, par exemple si on
    change de bibliothèque de données nucléaires (ça ne se voit pas dans model.xml).
    """
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    statepoint = _resultat_existant(modele, dossier) if reutiliser else None
    reutilise = statepoint is not None
    if not reutilise:
        statepoint = modele.run(cwd=dossier, output=False)
        shutil.copyfile(dossier / "model.xml", dossier / TEMOIN)   # le calcul est fini : j'écris le témoin
    with openmc.StatePoint(statepoint) as sp:
        k = sp.keff
    return {
        "k": k.nominal_value,
        "sigma": k.std_dev,
        "statepoint": statepoint,
        "duree": time.time() - t0,
        "reutilise": reutilise,
    }


def recherche_keff(modele, fonction, x0, x1, dossier, reutiliser=True, **kwargs_recherche):
    """Recherche de criticité (`modele.keff_search`), en gardant le résultat pour les fois suivantes.

    Une recherche enchaîne une dizaine de calculs (environ 4 minutes). Pour savoir si elle a
    déjà été faite, je calcule une « empreinte » (un résumé, avec la fonction de hachage
    sha256) de tout ce qui peut changer le résultat : le modèle de départ, le code de la
    fonction qui modifie le modèle, les points de départ et les réglages. Si l'empreinte est
    la même que celle enregistrée dans historique_recherche.json, je relis cet historique.
    Renvoie un `openmc.model.SearchResult`, comme keff_search.
    """
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    code = fonction.__code__
    empreinte = hashlib.sha256(
        _exporter_entrees(modele)
        + code.co_code
        + repr(code.co_consts).encode()
        + repr((x0, x1, sorted(kwargs_recherche.items()))).encode()
    ).hexdigest()

    fichier = dossier / "historique_recherche.json"
    if reutiliser and fichier.exists():
        donnees = json.loads(fichier.read_text())
        if donnees.get("empreinte") == empreinte:
            return SearchResult(**donnees["resultat"])

    resultat = modele.keff_search(fonction, x0, x1, run_kwargs={"cwd": dossier, "output": False},
                                  **kwargs_recherche)
    champs = ("root", "parameters", "means", "stdevs", "batches", "converged", "flag")
    sauvegarde = {c: getattr(resultat, c) for c in champs}
    sauvegarde = {c: (list(map(float, v)) if c in ("parameters", "means", "stdevs")
                      else list(map(int, v)) if c == "batches" else v) for c, v in sauvegarde.items()}
    sauvegarde["root"] = float(sauvegarde["root"])
    sauvegarde["converged"] = bool(sauvegarde["converged"])
    sauvegarde["flag"] = str(sauvegarde["flag"])
    fichier.write_text(json.dumps({"empreinte": empreinte, "resultat": sauvegarde}, indent=1))
    return resultat


def _canonique(valeur):
    """Transforme un réglage (dictionnaire, liste, tableau numpy, nombre…) en texte, toujours écrit pareil.

    Sert à calculer l'empreinte des calculs d'épuisement : il faut qu'un même réglage donne
    toujours exactement le même texte (par exemple, les clés d'un dictionnaire triées).
    """
    if isinstance(valeur, dict):
        return "{" + ",".join(f"{k!r}:{_canonique(v)}" for k, v in sorted(valeur.items())) + "}"
    if hasattr(valeur, "__len__") and not isinstance(valeur, str):
        return "[" + ",".join(_canonique(v) for v in valeur) + "]"
    if isinstance(valeur, float) or hasattr(valeur, "dtype"):
        return repr(float(valeur))
    return repr(valeur)


@contextlib.contextmanager
def _sans_sortie_console():
    """Rend le calcul silencieux le temps d'un bloc `with`.

    Pendant un épuisement, le solveur OpenMC écrit des centaines de lignes à l'écran, et la
    première fois, tout ce texte s'est retrouvé dans le notebook (plusieurs centaines de ko).
    Comme le solveur est du code compilé, il n'écrit pas via `print` : il faut rediriger
    directement la sortie du processus (descripteur de fichier n° 1) vers /dev/null.
    """
    sys.stdout.flush()
    sauvegarde, nul = os.dup(1), os.open(os.devnull, os.O_WRONLY)
    os.dup2(nul, 1)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            yield
    finally:
        os.dup2(sauvegarde, 1)
        os.close(nul)
        os.close(sauvegarde)


def _suivre_progression(dossier, n_transports, arret, periode=5.0):
    """Écrit l'avancement d'un épuisement dans dossier/progression.log.

    Un épuisement dure plus d'une demi-heure et le notebook n'affiche rien avant la fin. Cette
    fonction tourne en parallèle du calcul (dans un « thread ») : toutes les 5 secondes, elle
    compte les fichiers openmc_simulation_nX.h5 (un par transport terminé) et écrit une ligne
    avec le temps restant estimé. Pour suivre le calcul depuis un terminal :
    tail -f runs/.../progression.log
    """
    journal = dossier / "progression.log"
    t0 = time.time()
    with open(journal, "w") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] début : {n_transports} transports à faire\n")
    faits = 0
    while True:
        termine = arret.wait(periode)
        n = len(list(dossier.glob("openmc_simulation_n*.h5")))
        if n != faits or termine:
            faits = n
            ecoule = time.time() - t0
            reste = ecoule / faits * (n_transports - faits) if faits else float("nan")
            ligne = (f"[{time.strftime('%H:%M:%S')}] transport {faits}/{n_transports} terminé — "
                     f"écoulé {ecoule / 60:.1f} min — reste ≈ {reste / 60:.0f} min")
            if termine:
                ligne = f"[{time.strftime('%H:%M:%S')}] fin du calcul ({faits}/{n_transports} transports, {ecoule / 60:.1f} min)"
            with open(journal, "a") as f:
                f.write(ligne + "\n")
        if termine:
            return


def epuiser(modele, chaine, pas, dossier, integrateur="predictor", options_operateur=None,
            reutiliser=True, **kwargs_integrateur):
    """Lance un calcul d'épuisement (transport + évolution du combustible).

    Paramètres :
    - modele : le modèle OpenMC ; son combustible doit avoir depletable = True et un volume ;
    - chaine : le fichier XML de la chaîne d'évolution ;
    - pas : la durée de chaque pas (l'unité est donnée par timestep_units) ;
    - integrateur : "predictor" (le plus simple) ou "cecm" (plus précis, mais 2 transports par pas) ;
    - options_operateur : options de openmc.deplete.CoupledOperator, par exemple le mode de
      calcul des taux de réaction (voir le notebook 04) ;
    - kwargs_integrateur : power_density, timestep_units…

    Comme le calcul prend environ 35 minutes, j'utilise la même idée que pour recherche_keff :
    une empreinte de tout ce qui compte (modèle, contenu de la chaîne, réglages). Si elle n'a pas
    changé depuis le dernier calcul terminé, je renvoie directement le fichier de résultats.
    Renvoie un dictionnaire : resultats (chemin de depletion_results.h5), duree, reutilise.
    """
    import openmc.deplete

    dossier = Path(dossier).resolve()
    dossier.mkdir(parents=True, exist_ok=True)
    chaine = Path(chaine)
    options_operateur = options_operateur or {}
    empreinte = hashlib.sha256(
        _exporter_entrees(modele)
        + hashlib.sha256(chaine.read_bytes()).digest()
        + _canonique([list(pas), integrateur, options_operateur, kwargs_integrateur]).encode()
    ).hexdigest()

    fichier_resultats = dossier / "depletion_results.h5"
    temoin = dossier / "empreinte_epuisement.txt"
    t0 = time.time()
    if (reutiliser and fichier_resultats.exists() and temoin.exists()
            and temoin.read_text().strip() == empreinte):
        return {"resultats": fichier_resultats, "duree": time.time() - t0, "reutilise": True}

    temoin.unlink(missing_ok=True)
    for ancien in dossier.glob("openmc_simulation_n*.h5"):   # fichiers d'un ancien calcul : sinon le suivi compte faux
        ancien.unlink()
    classes = {"predictor": openmc.deplete.PredictorIntegrator, "cecm": openmc.deplete.CECMIntegrator}
    n_transports = len(pas) * (2 if integrateur == "cecm" else 1) + 1
    arret = threading.Event()
    suivi = threading.Thread(target=_suivre_progression, args=(dossier, n_transports, arret), daemon=True)
    repertoire_initial = Path.cwd()
    os.chdir(dossier)   # OpenMC écrit ses fichiers dans le dossier courant : on se place dans le bon
    suivi.start()
    try:
        # Sans ça, tout le journal du solveur finit dans le notebook (voir _sans_sortie_console)
        with _sans_sortie_console():
            operateur = openmc.deplete.CoupledOperator(modele, chaine, **options_operateur)
            classes[integrateur](operateur, pas, **kwargs_integrateur).integrate(output=False)
    finally:
        arret.set()
        suivi.join()
        os.chdir(repertoire_initial)
    temoin.write_text(empreinte)   # le calcul est fini : j'enregistre son empreinte
    return {"resultats": fichier_resultats, "duree": time.time() - t0, "reutilise": False}


def reactivite_pcm(k, sigma):
    """Convertit k en réactivité ρ = (k − 1)/k, en pcm, avec son incertitude.

    Pour l'incertitude, on dérive : dρ/dk = 1/k², donc σ_ρ = σ_k / k².
    """
    return (k - 1) / k * 1e5, sigma / k**2 * 1e5
