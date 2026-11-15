"""Lancement d'un calcul OpenMC et lecture de k avec son incertitude."""
import time
from pathlib import Path

import openmc


def calculer_k(modele, dossier):
    """Lance ``modele`` dans ``dossier`` et renvoie un dict de résultats.

    Clés : k (moyenne combinée), sigma (1σ), statepoint (chemin du fichier HDF5),
    duree (s). Chaque calcul a son propre dossier pour que les fichiers XML et HDF5
    d'un point de balayage n'écrasent pas ceux d'un autre.
    """
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    statepoint = modele.run(cwd=dossier, output=False)
    with openmc.StatePoint(statepoint) as sp:
        k = sp.keff
    return {
        "k": k.nominal_value,
        "sigma": k.std_dev,
        "statepoint": statepoint,
        "duree": time.time() - t0,
    }


def reactivite_pcm(k, sigma):
    """Réactivité ρ = (k − 1)/k en pcm, et son incertitude (dρ/dk = 1/k²)."""
    return (k - 1) / k * 1e5, sigma / k**2 * 1e5
