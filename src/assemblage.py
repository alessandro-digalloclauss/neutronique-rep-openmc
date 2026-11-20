"""Géométrie d'un assemblage REP 17×17 (type Westinghouse), pour le notebook 03.

264 crayons combustibles, 24 tubes guides (où coulissent les crayons des grappes de
commande) et 1 tube d'instrumentation au centre, sur un réseau de pas 1,26 cm.
"""
import openmc

from src.geometrie import HAUTEUR, PAS, R_GAINE_EXT, R_GAINE_INT, R_PASTILLE

N = 17                        # crayons par côté
PAS_ASSEMBLAGE = 21.50        # cm : pas entre assemblages (lame d'eau incluse)
R_TUBE_INT = 0.561            # cm : rayon intérieur des tubes guides
R_TUBE_EXT = 0.602            # cm : rayon extérieur des tubes guides

# Positions (ligne, colonne) des tubes guides, ligne 0 = rangée du haut.
# Le réseau est symétrique au huitième.
TUBES_GUIDES = [
    (2, 5), (2, 8), (2, 11),
    (3, 3), (3, 13),
    (5, 2), (5, 5), (5, 8), (5, 11), (5, 14),
    (8, 2), (8, 5), (8, 11), (8, 14),
    (11, 2), (11, 5), (11, 8), (11, 11), (11, 14),
    (13, 3), (13, 13),
    (14, 5), (14, 8), (14, 11),
]
TUBE_INSTRUMENTATION = (8, 8)


def carte_assemblage():
    """Matrice 17×17 de chaînes : 'C' combustible, 'G' tube guide, 'I' instrumentation."""
    carte = [["C"] * N for _ in range(N)]
    for i, j in TUBES_GUIDES:
        carte[i][j] = "G"
    i, j = TUBE_INSTRUMENTATION
    carte[i][j] = "I"
    return carte


def reseau_17x17(combustible, helium, gaine, moderateur):
    """Construit le réseau 17×17 d'un assemblage, sans les bords.

    Je le sépare de assemblage_17x17 pour pouvoir le réutiliser dans la rangée
    d'assemblages (rangee_assemblages).
    Renvoie (reseau, cellules) : cellules["combustible"] est la cellule combustible
    du crayon, répétée 264 fois dans le réseau.
    """
    # --- Univers « crayon combustible » (identique à la cellule crayon du notebook 01)
    s_pastille = openmc.ZCylinder(r=R_PASTILLE)
    s_gaine_int = openmc.ZCylinder(r=R_GAINE_INT)
    s_gaine_ext = openmc.ZCylinder(r=R_GAINE_EXT)
    cellules = {
        "combustible": openmc.Cell(name="combustible", fill=combustible, region=-s_pastille),
        "jeu": openmc.Cell(name="jeu He", fill=helium, region=+s_pastille & -s_gaine_int),
        "gaine": openmc.Cell(name="gaine", fill=gaine, region=+s_gaine_int & -s_gaine_ext),
        "moderateur": openmc.Cell(name="modérateur", fill=moderateur, region=+s_gaine_ext),
    }
    u_crayon = openmc.Universe(name="crayon combustible", cells=list(cellules.values()))

    # --- Univers « tube guide » : tube de Zircaloy rempli d'eau (grappe extraite)
    s_tube_int = openmc.ZCylinder(r=R_TUBE_INT)
    s_tube_ext = openmc.ZCylinder(r=R_TUBE_EXT)
    cellules["eau_tube"] = openmc.Cell(name="eau du tube", fill=moderateur, region=-s_tube_int)
    cellules["tube"] = openmc.Cell(name="tube guide", fill=gaine, region=+s_tube_int & -s_tube_ext)
    cellules["eau_autour_tube"] = openmc.Cell(name="eau autour du tube", fill=moderateur, region=+s_tube_ext)
    u_tube = openmc.Universe(
        name="tube guide",
        cells=[cellules["eau_tube"], cellules["tube"], cellules["eau_autour_tube"]],
    )

    # --- Réseau 17×17 (le tube d'instrumentation a ici les mêmes dimensions qu'un tube guide)
    univers = {"C": u_crayon, "G": u_tube, "I": u_tube}
    reseau = openmc.RectLattice(name="réseau 17x17")
    reseau.pitch = (PAS, PAS)
    reseau.lower_left = (-N * PAS / 2, -N * PAS / 2)
    reseau.universes = [[univers[x] for x in ligne] for ligne in carte_assemblage()]
    reseau.outer = openmc.Universe(cells=[openmc.Cell(fill=moderateur)])   # lame d'eau autour du réseau
    return reseau, cellules


def assemblage_17x17(combustible, helium, gaine, moderateur, hauteur=HAUTEUR):
    """Un assemblage avec des bords réfléchissants sur les 6 faces.

    Comme pour la cellule crayon, ça revient à un réseau infini d'assemblages identiques.
    Renvoie (geometrie, cellules).
    """
    reseau, cellules = reseau_17x17(combustible, helium, gaine, moderateur)
    boite = openmc.model.RectangularPrism(PAS_ASSEMBLAGE, PAS_ASSEMBLAGE, boundary_type="reflective")
    bas = openmc.ZPlane(z0=-hauteur / 2, boundary_type="reflective")
    haut = openmc.ZPlane(z0=+hauteur / 2, boundary_type="reflective")
    cellules["assemblage"] = openmc.Cell(name="assemblage", fill=reseau, region=-boite & +bas & -haut)
    return openmc.Geometry([cellules["assemblage"]]), cellules


def rangee_assemblages(combustible, helium, gaine, moderateur, n_assemblages=9, hauteur=HAUTEUR):
    """Rangée de n assemblages selon x, avec des fuites (vide) aux deux bouts.

    Réfléchissante en y et en z : c'est une « bande » de cœur. Je l'utilise dans le
    notebook 03 pour avoir un système beaucoup plus grand que le parcours d'un neutron,
    où la source de fission met du temps à converger.
    Renvoie (geometrie, cellules, longueur).
    """
    reseau, cellules = reseau_17x17(combustible, helium, gaine, moderateur)
    u_assemblage = openmc.Universe(name="assemblage", cells=[openmc.Cell(fill=reseau)])
    longueur = n_assemblages * PAS_ASSEMBLAGE
    rangee = openmc.RectLattice(name=f"rangée de {n_assemblages} assemblages")
    rangee.pitch = (PAS_ASSEMBLAGE, PAS_ASSEMBLAGE)
    rangee.lower_left = (-longueur / 2, -PAS_ASSEMBLAGE / 2)
    rangee.universes = [[u_assemblage] * n_assemblages]
    region = (
        +openmc.XPlane(-longueur / 2, boundary_type="vacuum")
        & -openmc.XPlane(longueur / 2, boundary_type="vacuum")
        & +openmc.YPlane(-PAS_ASSEMBLAGE / 2, boundary_type="reflective")
        & -openmc.YPlane(PAS_ASSEMBLAGE / 2, boundary_type="reflective")
        & +openmc.ZPlane(-hauteur / 2, boundary_type="reflective")
        & -openmc.ZPlane(hauteur / 2, boundary_type="reflective")
    )
    cellules["rangee"] = openmc.Cell(name="rangée", fill=rangee, region=region)
    return openmc.Geometry([cellules["rangee"]]), cellules, longueur
