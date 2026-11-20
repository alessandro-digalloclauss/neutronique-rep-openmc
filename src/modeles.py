"""Construction de modèles OpenMC complets à partir de quelques paramètres.

Dans les notebooks 02, je dois construire le même modèle des dizaines de fois en ne
changeant qu'un paramètre (enrichissement, bore, température…). Chaque fonction ici
renvoie un openmc.Model complet, prêt à être lancé.
"""
import openmc

from src.geometrie import HAUTEUR, cellule_crayon
from src.materiaux import (
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
    densite_moderateur=None,
    **kwargs_reglages,
):
    """Cellule crayon REP complète (matériaux + géométrie + réglages).

    densite_moderateur : densité imposée de l'eau (g/cm³) ; par défaut, elle est
    calculée à partir de t_moderateur et de la pression.
    Les arguments supplémentaires (particules, generations, inactives, graine) sont
    transmis à :func:`reglages_criticite`.

    Renvoie (modele, cellules) : cellules est le dict nom -> openmc.Cell, utile pour
    les tallies ou pour modifier un matériau en place (recherche de criticité).
    """
    combustible = combustible_uo2(enrichissement=enrichissement, temperature=t_combustible)
    helium = helium_jeu(temperature=T_GAINE)
    gaine = zircaloy4(temperature=T_GAINE)
    eau = eau_boree(bore_ppm=bore_ppm, temperature=t_moderateur, pression=pression,
                    densite=densite_moderateur)

    geometrie, cellules = cellule_crayon(combustible, helium, gaine, eau)
    modele = openmc.Model(
        geometry=geometrie,
        materials=openmc.Materials([combustible, helium, gaine, eau]),
        settings=reglages_criticite(**kwargs_reglages),
    )
    return modele, cellules


def modele_assemblage(
    enrichissement=4.0,
    bore_ppm=1000.0,
    t_moderateur=T_MODERATEUR,
    t_combustible=T_COMBUSTIBLE,
    source_ponctuelle=None,
    **kwargs_reglages,
):
    """Assemblage REP 17×17 complet (matériaux + géométrie + réglages).

    source_ponctuelle : None pour une source initiale uniforme dans tout le
    combustible, ou un point (x, y, z) en cm pour une source ponctuelle
    (utile pour étudier la convergence de la source).
    Renvoie (modele, cellules).
    """
    from src.assemblage import N, assemblage_17x17
    from src.geometrie import PAS

    combustible = combustible_uo2(enrichissement=enrichissement, temperature=t_combustible)
    helium = helium_jeu(temperature=T_GAINE)
    gaine = zircaloy4(temperature=T_GAINE)
    eau = eau_boree(bore_ppm=bore_ppm, temperature=t_moderateur)

    geometrie, cellules = assemblage_17x17(combustible, helium, gaine, eau)
    reglages = reglages_criticite(**kwargs_reglages)
    if source_ponctuelle is None:
        demi = N * PAS / 2
        espace = openmc.stats.Box((-demi, -demi, -HAUTEUR / 2), (demi, demi, HAUTEUR / 2))
        reglages.source = openmc.IndependentSource(space=espace, constraints={"fissionable": True})
    else:
        reglages.source = openmc.IndependentSource(space=openmc.stats.Point(source_ponctuelle))
    modele = openmc.Model(
        geometry=geometrie,
        materials=openmc.Materials([combustible, helium, gaine, eau]),
        settings=reglages,
    )
    return modele, cellules


def modele_rangee(n_assemblages=9, source_ponctuelle=(0.0, 0.0, 0.0), enrichissement=4.0, bore_ppm=1000.0,
                  **kwargs_reglages):
    """Rangée de n assemblages avec fuites aux extrémités, source initiale ponctuelle.

    Renvoie (modele, longueur) ; longueur = dimension de la rangée selon x (cm).
    """
    from src.assemblage import rangee_assemblages

    combustible = combustible_uo2(enrichissement=enrichissement)
    helium, gaine = helium_jeu(), zircaloy4()
    eau = eau_boree(bore_ppm=bore_ppm)
    geometrie, _, longueur = rangee_assemblages(combustible, helium, gaine, eau, n_assemblages)
    reglages = reglages_criticite(**kwargs_reglages)
    reglages.source = openmc.IndependentSource(space=openmc.stats.Point(source_ponctuelle))
    modele = openmc.Model(geometry=geometrie, materials=openmc.Materials([combustible, helium, gaine, eau]),
                          settings=reglages)
    return modele, longueur
