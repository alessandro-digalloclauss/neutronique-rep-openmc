"""Lancement d'un calcul OpenMC et lecture de k avec son incertitude.

Les fonctions de ce module réutilisent les résultats déjà calculés quand les entrées
sont strictement identiques (cache), pour ne jamais relancer un calcul inutilement.
"""
import hashlib
import json
import shutil
import tempfile
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


def reactivite_pcm(k, sigma):
    """Réactivité ρ = (k − 1)/k en pcm, et son incertitude (dρ/dk = 1/k²)."""
    return (k - 1) / k * 1e5, sigma / k**2 * 1e5
