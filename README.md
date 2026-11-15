# Neutronique d'un cœur REP avec OpenMC

Étude neutronique progressive d'un réacteur à eau pressurisée (REP), du crayon combustible
isolé jusqu'à l'assemblage 17×17 et à son évolution sous irradiation, réalisée avec le code
Monte-Carlo [OpenMC](https://docs.openmc.org/).

> Projet personnel d'apprentissage — étudiant ingénieur, spécialisation nucléaire.

## Objectif

Construire, étape par étape, des modèles neutroniques de complexité croissante et interpréter
physiquement les résultats :

1. **Cellule crayon** (*pin cell*) : facteur de multiplication infini k∞ et spectre neutronique.
2. **Études paramétriques** : sensibilité de k∞ à l'enrichissement, à la concentration en bore
   et à la température du modérateur (coefficient de température).
3. **Assemblage REP 17×17** : tubes guides, carte de puissance crayon par crayon.
4. **Épuisement** : évolution de k∞ avec le burn-up et production de plutonium.

## Méthode

- **Code** : OpenMC 0.16 — transport des neutrons par méthode Monte-Carlo en énergie continue.
- **Données nucléaires** : bibliothèque ENDF/B-VIII.0 au format HDF5, fournie par l'équipe OpenMC.
- **Calcul de criticité** : itérations sur les sources de fission (cycles inactifs pour converger
  la source, cycles actifs pour accumuler les statistiques) ; chaque résultat est donné avec
  son incertitude statistique (1σ).
- **Organisation** : un notebook par étude dans `notebooks/`, fonctions communes dans `src/`.

## Résultats

| Étude | Notebook | Résultat principal |
|---|---|---|
| Cellule crayon UO₂ 4 % | [`01_pin_cell.ipynb`](notebooks/01_pin_cell.ipynb) | k∞ = 1,2647 ± 0,0006 (1σ), à 1000 ppm de bore et 580 K |
| Enrichissement et bore | [`02a_enrichissement_bore.ipynb`](notebooks/02a_enrichissement_bore.ipynb) | Bore critique (réseau infini, UO₂ 4 %) : 5032 ± 9 ppm par ajustement, 5029 ppm par recherche GRsecant ; efficacité du bore ≈ −5,4 pcm/ppm |
| Coefficient du modérateur | [`02b_coefficient_moderateur.ipynb`](notebooks/02b_coefficient_moderateur.ipynb) | α_mod = −36 pcm/K sans bore, s'annule à 2195 ± 50 ppm de bore ; effet dû à la densité de l'eau |
| Coefficient Doppler | [`02c_doppler.ipynb`](notebooks/02c_doppler.ipynb) | α_D = −2,0 pcm/K à 900 K, loi approchée en √T ; captures résonnantes de l'U-238 +19 % entre 294 et 2500 K |
| Assemblage 17×17 | [`03_assemblage_17x17.ipynb`](notebooks/03_assemblage_17x17.ipynb) | k∞ = 1,2739 ± 0,0002 ; F_xy = 1,061 ; convergence de la source : 3 générations (assemblage) contre ≈ 55 (rangée de 9 assemblages) |
| Épuisement | [`04_epuisement.ipynb`](notebooks/04_epuisement.ipynb) | Jusqu'à 50 GWj/t : empoisonnement Xe + Sm ≈ 3 300 pcm, puis ≈ −680 pcm par GWj/t ; U-235 de 4 % à 0,76 % ; 14,3 kg/t de plutonium, qui assure les deux tiers des fissions en fin d'irradiation |

### Assemblage 17×17 : géométrie et carte de puissance

<p align="center">
  <img src="results/03_assemblage_17x17/rendu_3d.png" width="45%" alt="Rendu 3D de l'assemblage 17×17">
</p>

![Carte de puissance crayon par crayon](results/03_assemblage_17x17/carte_puissance.png)

Les crayons voisins des 24 tubes guides (« trous d'eau ») sont les plus puissants ; F_xy = 1,061, avec une incertitude
d'environ 0,3 % par crayon.

### Épuisement : le plutonium prend le relais de l'uranium 235

![Part des fissions par nucléide en fonction du taux de combustion](results/04_epuisement/fissions.png)

Au fil de l'irradiation, l'U-235 s'épuise et le Pu-239 formé par capture sur l'U-238 fissionne à son tour : à
50 GWj/t, les deux tiers des fissions viennent du plutonium. Le notebook montre aussi qu'un calcul des taux de
réaction par flux multigroupe, sans autoprotection, surestime de 30 % la production de plutonium.

### Spectre neutronique d'une cellule crayon

![Spectre du flux en énergie dans le combustible et le modérateur](results/01_pin_cell/spectre_flux.png)

Flux par unité de léthargie : bosse thermique (~0,1 eV), plateau de ralentissement en 1/E creusé par les
résonances de capture de l'U-238 (6,67, 20,9, 36,7 eV…), plus marquées dans le combustible (autoprotection),
et pic des neutrons de fission vers 1–2 MeV.

## Structure du dépôt

```text
.
├── notebooks/                  # études, numérotées dans l'ordre de lecture
│   ├── 01_pin_cell.ipynb
│   ├── 02a_enrichissement_bore.ipynb
│   ├── 02b_coefficient_moderateur.ipynb
│   ├── 02c_doppler.ipynb
│   ├── 03_assemblage_17x17.ipynb
│   └── 04_epuisement.ipynb
├── results/                    # figures (PNG) et tableaux (CSV), un dossier par notebook
│   ├── 01_pin_cell/
│   ├── 02a_enrichissement_bore/
│   ├── …
│   ├── 03_assemblage_17x17/
│   └── 04_epuisement/
├── src/                        # code Python commun aux notebooks
│   ├── materiaux.py            #   matériaux (UO₂, Zircaloy-4, eau borée…)
│   ├── geometrie.py            #   cellule crayon
│   ├── assemblage.py           #   assemblage 17×17 et rangée d'assemblages
│   ├── modeles.py              #   modèles OpenMC complets, paramétrés
│   ├── calcul.py               #   lancement des calculs, avec cache des résultats
│   └── style.py                #   style commun des figures
├── docs/plan.md                # plan détaillé des études
├── environment.yml             # environnement conda reproductible
└── LICENSE                     # licence MIT
```

Les calculs OpenMC écrivent leurs fichiers (XML, HDF5) dans `runs/`, un dossier non versionné, avec la même
organisation par notebook.

## Reproduire les calculs

### 1. Environnement

```bash
conda env create --platform osx-64 -f environment.yml   # macOS Apple Silicon (via Rosetta 2)
conda env create -f environment.yml                     # Linux / macOS Intel
conda activate openmc-env
```

OpenMC n'est pas distribué pour `osx-arm64` sur conda-forge : sur Mac Apple Silicon, on installe
la version Intel, exécutée de manière transparente par Rosetta 2.

### 2. Données nucléaires

Télécharger la bibliothèque **ENDF/B-VIII.0** (≈ 3,4 Go compressés, 13 Go décompressés) depuis
[openmc.org/data](https://openmc.org/data/), l'extraire hors du dépôt, puis indiquer son index à OpenMC :

```bash
mkdir -p ~/nuclear_data && cd ~/nuclear_data
tar -xJf endfb-viii.0-hdf5.tar.xz
export OPENMC_CROSS_SECTIONS=~/nuclear_data/endfb-viii.0-hdf5/cross_sections.xml
```

(ajouter la ligne `export` à `~/.zshrc` ou `~/.bash_profile` pour la rendre permanente).

Pour le notebook 04 (épuisement), télécharger aussi la **chaîne d'évolution simplifiée REP**
(*Simplified Chain*, « Thermal spectrum », ≈ 1 Mo) depuis la même page, et l'enregistrer sous
`~/nuclear_data/chaines/chain_casl_pwr.xml`.

### 3. Exécution

Ouvrir les notebooks dans VS Code ou Jupyter avec le noyau `openmc-env` et les exécuter dans l'ordre.
Les fichiers XML et HDF5 produits par OpenMC ne sont pas versionnés : la première exécution les génère dans
`runs/` (environ 15 min pour les notebooks 01 à 03, 35 min pour le 04), les suivantes réutilisent les calculs dont les entrées n'ont pas changé.

## Références

- P. K. Romano et al., *OpenMC: A state-of-the-art Monte Carlo code for research and development*,
  Annals of Nuclear Energy 82 (2015) 90–97.
- D. A. Brown et al., *ENDF/B-VIII.0: The 8th Major Release of the Nuclear Reaction Data Library*,
  Nuclear Data Sheets 148 (2018) 1–142.
- Documentation OpenMC : <https://docs.openmc.org/>
- Exemples officiels OpenMC : <https://github.com/openmc-dev/openmc/wiki/Example-Jupyter-Notebooks>
- Plan détaillé des études à venir : [`docs/plan.md`](docs/plan.md)

## Licence

Code et notebooks distribués sous licence [MIT](LICENSE) : libre réutilisation, à condition de citer la source.
Les données nucléaires ENDF/B-VIII.0 ne font pas partie du dépôt et restent soumises à leurs propres conditions.
