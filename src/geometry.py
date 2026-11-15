"""Géométrie d'une cellule crayon (pin cell) de REP 17×17.

Dimensions de type Westinghouse 17×17 (cm).
"""
import math

import openmc

R_PASTILLE = 0.4096      # rayon de la pastille UO2
R_GAINE_INT = 0.4180     # rayon intérieur de la gaine (jeu He de 84 µm)
R_GAINE_EXT = 0.4750     # rayon extérieur de la gaine (épaisseur 0.57 mm)
PAS = 1.26               # pas du réseau : distance entre axes de deux crayons
HAUTEUR = 10.0           # hauteur de la tranche modélisée (arbitraire, voir ci-dessous)


def cellule_crayon(combustible, helium, gaine, moderateur, pas=PAS, hauteur=HAUTEUR):
    """Construit la cellule crayon : un crayon entouré de son eau, tous bords réfléchissants.

    Les 4 faces latérales renvoient chaque neutron sortant comme dans un miroir :
    c'est équivalent à un réseau infini de crayons identiques (pas de fuites),
    donc le facteur de multiplication calculé est k-infini.
    Les faces haute et basse sont aussi réfléchissantes : le crayon est donc infini
    selon z, et la hauteur choisie n'a aucune influence sur le résultat. Elle sert
    seulement à avoir des volumes finis (normalisation du flux).

    Renvoie (geometrie, cellules) où cellules est un dict nom -> openmc.Cell.
    """
    # Surfaces : trois cylindres coaxiaux d'axe z
    s_pastille = openmc.ZCylinder(r=R_PASTILLE, name="pastille")
    s_gaine_int = openmc.ZCylinder(r=R_GAINE_INT, name="gaine intérieure")
    s_gaine_ext = openmc.ZCylinder(r=R_GAINE_EXT, name="gaine extérieure")
    # Carré de côté `pas`, centré en (0, 0), à bords réfléchissants
    boite = openmc.model.RectangularPrism(pas, pas, boundary_type="reflective")
    bas = openmc.ZPlane(z0=-hauteur / 2, boundary_type="reflective")
    haut = openmc.ZPlane(z0=+hauteur / 2, boundary_type="reflective")
    tranche = +bas & -haut

    # Cellules = régions de l'espace (combinaisons booléennes de demi-espaces) + matériau
    #   -s : intérieur de la surface s ; +s : extérieur ; & : intersection
    cellules = {
        "combustible": openmc.Cell(name="combustible", fill=combustible,
                                   region=-s_pastille & tranche),
        "jeu": openmc.Cell(name="jeu He", fill=helium,
                           region=+s_pastille & -s_gaine_int & tranche),
        "gaine": openmc.Cell(name="gaine", fill=gaine,
                             region=+s_gaine_int & -s_gaine_ext & tranche),
        "moderateur": openmc.Cell(name="modérateur", fill=moderateur,
                                  region=+s_gaine_ext & -boite & tranche),
    }
    # Volumes exacts (cm³), utiles pour convertir les tallies en flux moyen
    aire = {
        "combustible": math.pi * R_PASTILLE**2,
        "jeu": math.pi * (R_GAINE_INT**2 - R_PASTILLE**2),
        "gaine": math.pi * (R_GAINE_EXT**2 - R_GAINE_INT**2),
        "moderateur": pas**2 - math.pi * R_GAINE_EXT**2,
    }
    for nom, cellule in cellules.items():
        cellule.volume = aire[nom] * hauteur
        if cellule.fill is not None:
            cellule.fill.volume = cellule.volume   # requis pour l'épuisement (notebook 04)
    geometrie = openmc.Geometry(list(cellules.values()))
    return geometrie, cellules
