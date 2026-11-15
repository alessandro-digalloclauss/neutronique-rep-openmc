"""Modèles OpenMC complets, construits à partir de quelques paramètres physiques.

Une fonction de ce module renvoie un ``openmc.Model`` prêt à être lancé : c'est la
« fonction qui construit le modèle » qu'utilisent les balayages paramétriques et les
recherches de criticité (notebooks 02).
"""
import openmc

from src.geometry import HAUTEUR, cellule_crayon
from src.materials import (
    P_PRIMAIRE,
    T_COMBUSTIBLE,
    T_GAINE,
    T_MODERATEUR,
    combustible_uo2,
    eau_boree,
    helium_jeu,
    zircaloy4,
)


def reglages_criticite(particules=20_000, generations=200, inactives=50, graine=1):
    """Réglages d'un calcul de criticité pour la cellule crayon (voir notebook 01)."""
    reglages = openmc.Settings()
    reglages.particles = particules
    reglages.batches = generations
    reglages.inactive = inactives
    reglages.seed = graine
    reglages.temperature = {"method": "interpolation"}
    # Source initiale uniforme dans la pastille, restreinte aux matériaux fissiles
    reglages.source = openmc.IndependentSource(
        space=openmc.stats.Box((-0.41, -0.41, -HAUTEUR / 2), (0.41, 0.41, HAUTEUR / 2)),
        constraints={"fissionable": True},
    )
    reglages.output = {"tallies": False}   # pas de fichier texte tallies.out
    return reglages


def modele_cellule_crayon(
    enrichissement=4.0,
    bore_ppm=1000.0,
    t_moderateur=T_MODERATEUR,
    t_combustible=T_COMBUSTIBLE,
    pression=P_PRIMAIRE,
    **kwargs_reglages,
):
    """Cellule crayon REP complète (matériaux + géométrie + réglages).

    Les arguments supplémentaires (particules, generations, inactives, graine) sont
    transmis à :func:`reglages_criticite`.

    Renvoie (modele, cellules) : cellules est le dict nom -> openmc.Cell, utile pour
    les tallies ou pour modifier un matériau en place (recherche de criticité).
    """
    combustible = combustible_uo2(enrichissement=enrichissement, temperature=t_combustible)
    helium = helium_jeu(temperature=T_GAINE)
    gaine = zircaloy4(temperature=T_GAINE)
    eau = eau_boree(bore_ppm=bore_ppm, temperature=t_moderateur, pression=pression)

    geometrie, cellules = cellule_crayon(combustible, helium, gaine, eau)
    modele = openmc.Model(
        geometry=geometrie,
        materials=openmc.Materials([combustible, helium, gaine, eau]),
        settings=reglages_criticite(**kwargs_reglages),
    )
    return modele, cellules
