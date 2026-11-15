# Plan du projet — notebooks 02 à 04

Ce document prépare la suite du projet après le notebook 01 (cellule crayon, k∞ = 1,26468 ± 0,00055).
Pour chaque étude : la question physique, la méthode OpenMC, les résultats attendus et les pièges à éviter.

Les **ordres de grandeur** indiqués servent à repérer un résultat aberrant, pas à valider le calcul :
ils dépendent des conditions exactes et doivent être recoupés avec la littérature ou un benchmark.

---

## Principes communs

- **Réutiliser `src/`** : les matériaux et la géométrie du notebook 01 sont paramétrés (enrichissement,
  bore, températures). Toute nouvelle géométrie (assemblage) va dans `src/`, pas dans les notebooks.
- **Toujours donner l'incertitude** : chaque k∞ avec son σ, chaque coefficient avec son incertitude propagée.
  Une différence entre deux calculs n'est significative que si elle dépasse nettement
  $\sqrt{\sigma_1^2 + \sigma_2^2}$.
- **Graine fixe** (`settings.seed`) pour la reproductibilité ; un dossier `runs/NN_xxx/` par calcul.
- **Contrôle de la géométrie avant tout calcul** (comme dans le notebook 01) : `model.plot(..., show_overlaps=True)`
  et un `assert` sur `model.slice_data(...)` (aucun identifiant de cellule négatif), sur plusieurs plans de
  coupe si la géométrie est 3D.
- **Tracés** : `model.plot()` pour les coupes 2D dans les notebooks (figure matplotlib, moteur C++
  `openmc.lib`). La classe `openmc.Plot` des anciens exemples est **dépréciée** en 0.16 : utiliser
  `openmc.SlicePlot` / `openmc.VoxelPlot` pour le traceur intégré.
- **Avant de publier** : *Restart + Run All*, puis vérifier que les chiffres cités dans le texte
  correspondent aux sorties.
- **Exporter** les résultats chiffrés en CSV et les figures en PNG dans `results/`, préfixés par le numéro du notebook.
- **Coût de calcul** : sur le Mac (10 cœurs, x86_64 via Rosetta), le notebook 01 traite environ 35 000 neutrons/s.
  Un point de calcul de cellule crayon (3 M d'histoires) prend environ 2 min.

---

## Notebook 02 — Études paramétriques et coefficients de réactivité

**Question** : comment k∞ réagit-il aux paramètres que l'exploitant ou le concepteur contrôlent ? Et pourquoi
un REP est-il naturellement stable ?

### 2a. Enrichissement

- Balayage : 0,711 % (uranium naturel), 1, 2, 3, 4, 5 % — environ 6 calculs.
- Figure : k∞ en fonction de l'enrichissement, et spectres superposés pour 2 ou 3 enrichissements.
- Physique attendue : croissance de k∞ avec **saturation** (le facteur η tend vers sa limite quand l'U-235
  domine l'absorption), et **durcissement du spectre** (moins de neutrons thermiques quand le combustible
  absorbe davantage).
- Point pédagogique : à l'uranium naturel, k∞ < 1 dans ce réseau à eau légère. C'est la raison pour laquelle
  les REP doivent enrichir le combustible, contrairement aux réacteurs à eau lourde ou à graphite.

### 2b. Concentration en bore et bore critique

- Balayage : 0 à 2 500 ppm, par pas de 500 ppm.
- Grandeur clé : l'**efficacité différentielle du bore**, $\partial\rho/\partial C_B$ en pcm/ppm
  (ordre de grandeur : quelques pcm/ppm, de signe négatif).
- **Recherche de bore critique** avec `openmc.search_for_keff()` : on fournit une fonction qui construit
  le modèle pour une concentration donnée, et OpenMC cherche la valeur qui donne k = 1 (exemple officiel
  *Criticality Search*).
- ⚠️ Interprétation : pour une cellule crayon, cette concentration rend critique un **réseau infini**. Elle
  surestime le bore critique d'un vrai cœur, qui a des fuites. Le dire explicitement.

### 2c. Température du modérateur : coefficient de température (MTC)

- Balayage : 540 à 600 K. Rester **sous la saturation** : 617,9 K à 15,5 MPa, au-delà l'eau bout.
- Coefficient : $\alpha_{mod} = \Delta\rho / \Delta T$ en pcm/K. Attendu **négatif** à faible bore : c'est la
  propriété de sûreté fondamentale des REP sous-modérés.
- **Décomposer l'effet** en deux calculs :
  1. variation de la **densité** seule, à température fixe : effet dominant, moins de modérateur ;
  2. variation de la **température** seule, à densité fixe : effet de la loi S(α,β) sur la thermalisation.
- **MTC en fonction de la concentration en bore** (par exemple à 0, 1 000 et 2 000 ppm) : quand l'eau se dilate,
  elle perd aussi du bore. À forte concentration, le MTC devient moins négatif et peut devenir **positif**.
  C'est pour ça que la concentration en bore est limitée en début de cycle. **C'est le résultat le plus
  intéressant du notebook pour un ingénieur REP.**
- ⚠️ Statistique : une différence de température de 20 K donne un Δk de quelques centaines de pcm seulement.
  Il faut donc des σ d'environ 20 pcm par point, soit environ 10 fois plus d'histoires que dans le notebook 01,
  ou plusieurs points avec une **régression linéaire pondérée** (meilleure méthode, et l'incertitude sur la pente
  est donnée par l'ajustement).

### 2d. Température du combustible : coefficient Doppler

- Balayage : 600 à 1 500 K (données disponibles à 600, 900, 1 200 et 2 500 K, interpolées entre elles).
- Attendu : **négatif**, de l'ordre de −2 à −4 pcm/K. L'élargissement Doppler des résonances de l'U-238
  augmente les captures.
- Figure possible : zoom sur la résonance à 6,67 eV à deux températures (flux dans le combustible).
- C'est le premier contre-effet de sûreté en cas d'excursion de puissance : il agit instantanément, avant que
  la chaleur atteigne l'eau.

### 2e. (Option) Formule des quatre facteurs

- Calculer ε, p, f, η à partir de tallies (taux de fission et d'absorption par domaine d'énergie, coupure à
  0,625 eV), puis vérifier que leur produit redonne k∞.
- Montrer quel facteur porte chaque effet : l'enrichissement agit sur η et f, le bore sur f, la température
  du combustible sur p.

### 2f. (Option) UO₂ ou uranium métal

- Même enrichissement, comparaison de k∞ et des spectres. Illustre l'effet de la densité en uranium et du
  rapport de modération. Le cas métal n'est pas réaliste en REP (voir la discussion sur la tenue du métal).

### Code à ajouter dans `src/`

- `src/runs.py` : une fonction `calcul_k(modele, dossier, ...)` qui lance un calcul et renvoie k∞, σ et le
  chemin du statepoint, pour éviter de recopier le même bloc dans chaque balayage.
- Une fonction de construction de modèle paramétrée, pour `search_for_keff`.

---

## Notebook 03 — Assemblage REP 17×17

**Question** : comment la puissance se répartit-elle d'un crayon à l'autre dans un assemblage réel ?

### Modèle

- **Assemblage de type Westinghouse 17×17** : 264 crayons combustibles, 24 **tubes guides** et 1 **tube
  d'instrumentation** central (tubes en Zircaloy remplis d'eau, rayons environ 0,561 et 0,602 cm).
- `openmc.RectLattice` de 17×17 universes (crayon, tube guide), pas de 1,26 cm, lame d'eau entre assemblages
  (pas d'assemblage d'environ 21,50 cm), bords réfléchissants : on calcule le **k∞ d'un réseau infini d'assemblages**.
- Code : `src/assembly.py`, avec la carte des positions des tubes guides.

### Résultats

- **Carte de puissance crayon par crayon** : taux de fission (score `kappa-fission` ou `fission`) par crayon,
  avec un `MeshFilter` 17×17 ou un `DistribcellFilter`. On normalise à une moyenne de 1 sur les crayons
  combustibles, et on trace une carte de chaleur avec la valeur dans chaque case.
- **Facteur de point chaud** $F_{xy}$ = puissance maximale / puissance moyenne. Pour un assemblage neuf et
  homogène, attendu à quelques % au-dessus de 1.
- **Carte des incertitudes** relatives, pour montrer que les écarts observés sont significatifs.
- Physique attendue : les crayons **voisins des tubes guides** sont plus puissants. Les tubes pleins d'eau font
  des « trous d'eau » qui sur-modèrent localement et augmentent le flux thermique.
- Exploiter le **huitième de symétrie** de l'assemblage pour vérifier la cohérence statistique (les crayons
  symétriques doivent avoir la même puissance aux incertitudes près).

### Visualisation

- **Coupe de l'assemblage** avec `model.plot()` coloré par matériau, puis contrôle des chevauchements sur
  toute la section (les 289 positions du réseau).
- **Traceur intégré `openmc.SlicePlot` avec `meshlines`** : superposer à la géométrie le maillage 17×17 des
  tallies (et celui de l'entropie de Shannon), pour vérifier que chaque maille contient bien un crayon.
- **Rendu 3D** de l'assemblage avec `openmc.SolidRayTracePlot` (vue en perspective, coupe partielle pour
  montrer les crayons), et éventuellement un `VoxelPlot` exporté en VTK pour ParaView. Visuel de choix pour
  le README et LinkedIn.
- Vérifier ces API dans la documentation de la version installée avant de coder (elles sont récentes).

### Convergence (suite du notebook 01)

- Ici, la source initiale est loin de la distribution fondamentale : suivre l'**entropie de Shannon** sur un
  maillage 17×17 et choisir le nombre de cycles inactifs **d'après la courbe**.
- Mesurer l'**autocorrélation entre générations** : elle devrait être positive cette fois, et l'incertitude
  naïve serait alors sous-estimée. Comparer avec l'exemple officiel *Source Convergence*.
- Statistique : il faut beaucoup plus d'histoires pour avoir une incertitude d'environ 1 % sur chaque crayon,
  par exemple 100 000 neutrons × 300 générations. Durée à mesurer : de l'ordre de dizaines de minutes.

### Validation (fort intérêt pour le CV)

- Reproduire un cas du **benchmark VERA** (CASL, « VERA Core Physics Benchmark Progression Problems ») :
  problème 1 (cellule crayon) et problème 2 (assemblage 2D), dont les conditions et les k de référence sont
  publiés. Comparer notre k∞ avec la référence, en pcm. Ce serait la première validation réelle du modèle.

### Options

- **Grappe de commande insérée** (absorbant AIC ou B₄C dans les tubes guides) : efficacité de la grappe en pcm
  et déformation de la carte de puissance.
- **Crayons à poison consommable** (gadolinium) : creux de puissance local.

---

## Notebook 04 — Épuisement (depletion)

**Question** : comment le combustible évolue-t-il pendant son séjour en réacteur, et combien de plutonium produit-il ?

### Méthode

- Module `openmc.deplete` : un `CoupledOperator` relie le transport (OpenMC) et l'évolution isotopique
  (équations de Bateman), et un intégrateur en temps (`PredictorIntegrator` pour commencer, `CECMIntegrator`
  pour plus de précision) avance par pas de burn-up.
- **Chaîne d'évolution** : le fichier XML « thermal spectrum » d'ENDF/B-VIII.0, téléchargé depuis
  [openmc.org/data](https://openmc.org/data/) et rangé dans `~/nuclear_data/` (hors dépôt).
- **Normalisation en puissance** : puissance linéique d'un crayon moyen de REP, environ 180 W/cm, soit environ
  40 W/g de métal lourd (à préciser en le calculant). Les volumes des matériaux sont déjà définis dans
  `src/geometry.py`.
- **Pas de temps** : des pas courts au début (quelques heures, puis quelques jours) pour capter la mise à
  l'équilibre du **xénon-135** et du **samarium-149**, puis des pas plus longs jusqu'à environ 50–60 GWj/t.
- Modèle : la cellule crayon (environ 20 à 30 pas × 1 à 2 min, faisable). L'assemblage en épuisement sera
  nettement plus coûteux, en option.
- Simplification à assumer : concentration en bore constante (ou nulle) pendant l'irradiation.

### Résultats

- **k∞ en fonction du burn-up** : chute initiale due au Xe et au Sm, puis décroissance quasi linéaire.
- **Bilan des noyaux lourds** : consommation de l'U-235, production du Pu-239, puis des Pu-240, Pu-241 et Pu-242.
- **Vecteur isotopique du plutonium** en fin d'irradiation : la part de Pu-239 diminue avec le burn-up
  (qualité du plutonium).
- **Part de puissance due au plutonium** : en fin de cycle, une fraction importante des fissions vient du
  Pu-239 formé sur place.
- (Option) **Modèle de réactivité linéaire** : à partir de k∞(burn-up), estimer le taux de combustion de
  décharge d'une gestion en 3 ou 4 lots, en tenant compte des fuites.

### Pièges

- Ne pas oublier `depletable = True` (déjà fait dans `src/materials.py`) et les volumes.
- Les résultats sont dans `depletion_results.h5` : on les lit avec `openmc.deplete.Results`.
- Vérifier la convergence en pas de temps : refaire le calcul avec des pas deux fois plus petits et comparer.

---

## Idées d'extensions (au-delà du plan initial)

- **Sensibilité aux données nucléaires** : refaire le notebook 01 avec JEFF-3.3 et comparer k∞ avec
  ENDF/B-VIII.0. Les écarts de quelques centaines de pcm entre bibliothèques montrent que l'incertitude sur
  les données dépasse souvent l'incertitude statistique.
- **Combustible MOX** (`Material.mix_materials`) : spectre plus dur, efficacité du bore réduite.
- **Réseau hexagonal de type VVER** (exemple officiel *Hexagonal Lattices*).

## Ressources

- Documentation OpenMC : <https://docs.openmc.org/>
- Exemples officiels : <https://github.com/openmc-dev/openmc/wiki/Example-Jupyter-Notebooks>, en particulier
  *Criticality Search*, *Source Convergence*, *Tally Arithmetic*, *Depletion*. Une copie locale de
  l'exemple *pincell* est dans `reference/` (non publiée).
- Benchmark VERA (CASL) : conditions et résultats de référence pour la cellule crayon et l'assemblage.
