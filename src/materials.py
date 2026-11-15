"""Matériaux d'un crayon combustible de REP.

Chaque fonction renvoie un ``openmc.Material`` paramétré, pour pouvoir faire varier
enrichissement, bore ou température dans les études paramétriques (notebook 02).

Unités OpenMC : densités en g/cm³, températures en K.
"""
import openmc
import openmc.model

# Conditions nominales d'un REP en fonctionnement (valeurs typiques)
T_COMBUSTIBLE = 900.0   # K  — température moyenne effective de la pastille UO2
T_GAINE = 600.0         # K  — gaine en Zircaloy
T_MODERATEUR = 580.0    # K  — eau du circuit primaire (~307 °C)
P_PRIMAIRE = 15.5       # MPa — pression du circuit primaire (155 bar)


def combustible_uo2(enrichissement=4.0, densite=10.4, temperature=T_COMBUSTIBLE):
    """Dioxyde d'uranium UO2.

    enrichissement : % massique d'U-235 dans l'uranium.
    densite : 10.4 g/cm³ ≈ 95 % de la densité théorique (10.97 g/cm³),
              la porosité résiduelle venant du frittage des pastilles.
    """
    uo2 = openmc.Material(name=f"UO2 {enrichissement:g} %")
    # add_element("U", enrichment=...) répartit automatiquement U-234/235/236/238
    uo2.add_element("U", 1.0, enrichment=enrichissement)
    uo2.add_element("O", 2.0)
    uo2.set_density("g/cm3", densite)
    uo2.temperature = temperature
    uo2.depletable = True   # utile pour l'épuisement (notebook 04)
    return uo2


def helium_jeu(temperature=T_GAINE):
    """Hélium remplissant le jeu pastille-gaine (pressurisation à la fabrication)."""
    he = openmc.Material(name="Hélium")
    he.add_element("He", 1.0)
    he.set_density("g/cm3", 0.0015)
    he.temperature = temperature
    return he


def zircaloy4(temperature=T_GAINE):
    """Zircaloy-4 : alliage de zirconium, quasi transparent aux neutrons.

    Composition massique nominale, au centre des plages de la norme ASTM B350 :
    Sn 1.45 %, Fe 0.21 %, Cr 0.10 %, O 0.125 %, reste Zr.
    """
    zr4 = openmc.Material(name="Zircaloy-4")
    zr4.add_element("Sn", 0.0145, "wo")
    zr4.add_element("Fe", 0.0021, "wo")
    zr4.add_element("Cr", 0.0010, "wo")
    zr4.add_element("O", 0.00125, "wo")
    zr4.add_element("Zr", 1 - 0.0145 - 0.0021 - 0.0010 - 0.00125, "wo")
    zr4.set_density("g/cm3", 6.56)
    zr4.temperature = temperature
    return zr4


def eau_boree(bore_ppm=1000.0, temperature=T_MODERATEUR, pression=P_PRIMAIRE, densite=None):
    """Eau légère borée du circuit primaire.

    bore_ppm : concentration massique en bore naturel (ppm = mg de B par kg d'eau).
    La densité est calculée à partir de (T, P) via les tables IAPWS de l'eau :
    ≈ 0.71 g/cm³ à 580 K et 15.5 MPa, contre 1.0 g/cm³ à 20 °C.
    La loi de diffusion thermique S(α,β) de l'hydrogène lié dans H2O est ajoutée
    automatiquement : sans elle, les neutrons thermiques verraient des atomes
    d'hydrogène libres, ce qui fausse le spectre thermique.
    densite : si elle est donnée (g/cm³), elle remplace la densité calculée à partir
    de (T, P). Sert à séparer l'effet de la densité de celui de la température
    (notebook 02b) : la température reste alors celle des sections efficaces.
    """
    eau = openmc.model.borated_water(
        bore_ppm, temperature=temperature, pressure=pression, density=densite,
        name=f"Eau borée {bore_ppm:g} ppm",
    )
    eau.temperature = temperature
    return eau
