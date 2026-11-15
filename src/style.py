"""Style graphique commun à tous les notebooks.

Objectif : des figures lisibles en petit format (téléphone, post LinkedIn), homogènes
d'un notebook à l'autre. À appeler une fois en début de notebook : ``appliquer_style()``.
"""
import matplotlib as mpl

# Palette sobre et contrastée, utilisée de façon cohérente dans tout le projet
COULEURS = {
    "rouge": "#c0392b",
    "bleu": "#2471a3",
    "vert": "#229954",
    "orange": "#e67e22",
    "gris": "#7f8c8d",
    "violet": "#7d3c98",
}


def appliquer_style():
    mpl.rcParams.update({
        # Texte : grand, pour rester lisible une fois l'image réduite
        "font.size": 13,
        "axes.titlesize": 15,
        "axes.titleweight": "bold",
        "axes.labelsize": 14,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "legend.fontsize": 12,
        "legend.title_fontsize": 12,
        "figure.titlesize": 17,
        "figure.titleweight": "bold",
        # Tracés
        "lines.linewidth": 2.0,
        "lines.markersize": 7,
        "errorbar.capsize": 4,
        "axes.prop_cycle": mpl.cycler(color=list(COULEURS.values())),
        # Axes épurés
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 1.1,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linewidth": 0.8,
        "legend.frameon": True,
        "legend.framealpha": 0.9,
        # Export : fond blanc, haute définition, marges serrées
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.15,
        "figure.dpi": 100,
    })
