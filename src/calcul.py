"""Lancement d'un calcul OpenMC et lecture de k avec son incertitude."""
import tempfile
import time
from pathlib import Path

import openmc


def _resultat_existant(modele, dossier):
    """Statepoint déjà calculé pour exactement ce modèle, ou None.

    Le fichier model.xml contient toutes les entrées du calcul (matériaux,
    géométrie, réglages, graine, tallies) : s'il est identique octet pour octet à
    celui du calcul précédent, le résultat serait identique lui aussi.
    """
    ancien_xml = dossier / "model.xml"
    statepoint = dossier / f"statepoint.{modele.settings.batches}.h5"
    if not (ancien_xml.exists() and statepoint.exists()):
        return None
    with tempfile.TemporaryDirectory() as tmp:
        nouveau_xml = Path(tmp) / "model.xml"
        modele.export_to_model_xml(nouveau_xml)
        if nouveau_xml.read_bytes() != ancien_xml.read_bytes():
            return None
    # Le statepoint doit être postérieur au model.xml (calcul allé à son terme)
    if statepoint.stat().st_mtime < ancien_xml.stat().st_mtime:
        return None
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
    with openmc.StatePoint(statepoint) as sp:
        k = sp.keff
    return {
        "k": k.nominal_value,
        "sigma": k.std_dev,
        "statepoint": statepoint,
        "duree": time.time() - t0,
        "reutilise": reutilise,
    }


def reactivite_pcm(k, sigma):
    """Réactivité ρ = (k − 1)/k en pcm, et son incertitude (dρ/dk = 1/k²)."""
    return (k - 1) / k * 1e5, sigma / k**2 * 1e5
