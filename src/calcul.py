"""Lancement d'un calcul OpenMC et lecture de k avec son incertitude.

Les fonctions de ce module réutilisent les résultats déjà calculés quand les entrées
sont strictement identiques (cache), pour ne jamais relancer un calcul inutilement.
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

TEMOIN = "entrees_calcul.xml"   # copie des entrées, écrite seulement quand le calcul est terminé


def _exporter_entrees(modele):
    """Contenu du model.xml que produirait ce modèle (octets)."""
    with tempfile.TemporaryDirectory() as tmp:
        chemin = Path(tmp) / "model.xml"
        modele.export_to_model_xml(chemin)
        return chemin.read_bytes()


def _resultat_existant(modele, dossier):
    """Statepoint déjà calculé pour exactement ce modèle, ou None.

    Le fichier model.xml contient toutes les entrées du calcul (matériaux,
    géométrie, réglages, graine, tallies) : s'il est identique octet pour octet à
    celui d'un calcul terminé, le résultat serait identique lui aussi.
    """
    statepoint = dossier / f"statepoint.{modele.settings.batches}.h5"
    if not statepoint.exists():
        return None
    temoin = dossier / TEMOIN
    if temoin.exists():
        # Règle principale : le témoin n'est écrit qu'à la fin d'un calcul complet
        return statepoint if _exporter_entrees(modele) == temoin.read_bytes() else None
    # Dossiers antérieurs au témoin : model.xml identique et statepoint plus récent que lui
    ancien_xml = dossier / "model.xml"
    if not ancien_xml.exists() or _exporter_entrees(modele) != ancien_xml.read_bytes():
        return None
    if statepoint.stat().st_mtime < ancien_xml.stat().st_mtime:
        return None   # calcul interrompu
    return statepoint


def calculer_k(modele, dossier, reutiliser=True):
    """Lance ``modele`` dans ``dossier`` et renvoie un dict de résultats.

    Clés : k (moyenne combinée), sigma (1σ), statepoint (chemin du fichier HDF5),
    duree (s), reutilise (bool). Chaque calcul a son propre dossier pour que les
    fichiers XML et HDF5 d'un point de balayage n'écrasent pas ceux d'un autre.

    reutiliser : si le dossier contient déjà le résultat d'un calcul aux entrées
    strictement identiques, on le relit au lieu de relancer OpenMC. Mettre False
    pour forcer le calcul (par exemple après un changement de bibliothèque de
    données nucléaires, qui n'apparaît pas dans model.xml).
    """
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    statepoint = _resultat_existant(modele, dossier) if reutiliser else None
    reutilise = statepoint is not None
    if not reutilise:
        statepoint = modele.run(cwd=dossier, output=False)
        shutil.copyfile(dossier / "model.xml", dossier / TEMOIN)   # calcul terminé : on écrit le témoin
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
    """``modele.keff_search`` avec mise en cache de tout l'historique de la recherche.

    L'empreinte combine les entrées du modèle initial, le code de la fonction qui
    modifie le modèle, les points de départ et les réglages de la recherche. Si elle
    est identique à celle d'une recherche terminée, on relit l'historique (fichier
    JSON) au lieu de relancer. Renvoie un ``openmc.model.SearchResult``.
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
    """Représentation texte stable d'un réglage (dict, liste, tableau numpy, nombre…)."""
    if isinstance(valeur, dict):
        return "{" + ",".join(f"{k!r}:{_canonique(v)}" for k, v in sorted(valeur.items())) + "}"
    if hasattr(valeur, "__len__") and not isinstance(valeur, str):
        return "[" + ",".join(_canonique(v) for v in valeur) + "]"
    if isinstance(valeur, float) or hasattr(valeur, "dtype"):
        return repr(float(valeur))
    return repr(valeur)


@contextlib.contextmanager
def _sans_sortie_console():
    """Redirige la sortie standard (Python et code compilé) vers /dev/null le temps d'un bloc."""
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
    """Écrit l'avancement d'un épuisement dans ``dossier/progression.log`` (une ligne par transport terminé).

    Chaque transport produit un fichier openmc_simulation_nX.h5 : on les compte. Pour suivre en direct
    depuis un terminal : ``tail -f runs/.../progression.log``.
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
    """Calcul d'épuisement (transport + évolution) avec mise en cache.

    modele : ``openmc.Model`` dont le combustible a ``depletable = True`` et un volume.
    chaine : chemin du fichier XML de la chaîne d'évolution.
    pas : durées des pas (unité donnée par ``timestep_units`` dans kwargs_integrateur).
    integrateur : "predictor" (Euler explicite) ou "cecm" (prédicteur-correcteur, 2 transports par pas).
    options_operateur : arguments de ``openmc.deplete.CoupledOperator`` (mode de calcul des taux…).
    kwargs_integrateur : power, power_density, timestep_units…

    L'empreinte combine les entrées du modèle, le contenu de la chaîne et tous les réglages ;
    si elle est identique à celle d'un calcul terminé, on renvoie le fichier de résultats existant.
    Renvoie un dict : resultats (chemin de depletion_results.h5), duree (s), reutilise (bool).
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
    for ancien in dossier.glob("openmc_simulation_n*.h5"):   # restes d'un calcul précédent
        ancien.unlink()
    classes = {"predictor": openmc.deplete.PredictorIntegrator, "cecm": openmc.deplete.CECMIntegrator}
    n_transports = len(pas) * (2 if integrateur == "cecm" else 1) + 1
    arret = threading.Event()
    suivi = threading.Thread(target=_suivre_progression, args=(dossier, n_transports, arret), daemon=True)
    repertoire_initial = Path.cwd()
    os.chdir(dossier)   # l'opérateur écrit ses fichiers dans le répertoire courant
    suivi.start()
    try:
        # Le solveur OpenMC, chargé en mémoire, écrit directement sur la sortie standard du processus :
        # on la redirige vers /dev/null (sinon tout son journal finit dans le notebook).
        with _sans_sortie_console():
            operateur = openmc.deplete.CoupledOperator(modele, chaine, **options_operateur)
            classes[integrateur](operateur, pas, **kwargs_integrateur).integrate(output=False)
    finally:
        arret.set()
        suivi.join()
        os.chdir(repertoire_initial)
    temoin.write_text(empreinte)   # calcul terminé : on écrit le témoin
    return {"resultats": fichier_resultats, "duree": time.time() - t0, "reutilise": False}


def reactivite_pcm(k, sigma):
    """Réactivité ρ = (k − 1)/k en pcm, et son incertitude (dρ/dk = 1/k²)."""
    return (k - 1) / k * 1e5, sigma / k**2 * 1e5
