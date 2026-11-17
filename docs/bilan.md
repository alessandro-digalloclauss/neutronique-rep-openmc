# Bilan du projet et perspectives

Ce document était au départ le plan des notebooks 02 à 04. Il fait maintenant le point : ce qui a été réalisé,
les écarts avec le plan initial, les limites des modèles, et les études qui restent à faire.

---

## Synthèse

| Notebook | Question | Résultat principal | Contrôles |
|---|---|---|---|
| 01 Cellule crayon | Que vaut k∞ d'un crayon REP, et à quoi ressemble son spectre ? | k∞ = 1,26468 ± 0,00055 (UO₂ 4 %, 1000 ppm, 580 K) | 3 estimateurs de k cohérents ; bilan production / absorption à 1σ ; chevauchements de géométrie |
| 02a Enrichissement et bore | Comment k∞ dépend-il de l'enrichissement et du bore ? | k∞ = 0,887 à l'uranium naturel ; bore critique 5032 ± 9 ppm (ajustement) et 5029 ppm (`keff_search`) | deux méthodes indépendantes pour le bore critique ; χ² réduit des ajustements |
| 02b Coefficient du modérateur | Pourquoi un REP est-il stable ? | α_mod = −36,1 ± 0,8 pcm/K sans bore, nul vers 2195 ± 50 ppm, positif au-delà | décomposition densité / température ; facteur de Birge |
| 02c Coefficient Doppler | Que fait la température du combustible ? | α_D = −2,01 ± 0,04 pcm/K à 900 K, loi en √T | captures résonnantes de l'U-238 : +19 % entre 294 et 2500 K |
| 03 Assemblage 17×17 | Comment la puissance se répartit-elle entre les crayons ? | k∞ = 1,27391 ± 0,00022 ; F_xy = 1,061 | symétrie au huitième ; corrélation puissance / flux thermique 0,998 ; entropie de Shannon ; méthode des blocs |
| 04 Épuisement | Comment évolue le combustible, et combien de plutonium produit-il ? | k∞ de 1,266 à 0,857 à 50 GWj/t ; 14,3 kg/t de plutonium | trois modes de calcul des taux de réaction comparés ; transports de contrôle |

---

## Ce qui a été réalisé, notebook par notebook

### 01 — Cellule crayon

- Modèle : pastille UO₂ 4 % (900 K), jeu d'hélium, gaine Zircaloy-4 (600 K), eau borée à 1000 ppm (580 K, 15,5 MPa,
  densité IAPWS), bords réfléchissants : réseau infini de crayons.
- k∞ par trois estimateurs (collision, absorption, longueur de trace) et leur combinaison ; contrôle par bilan
  neutronique, qui demande d'inclure les réactions (n,2n) et (n,3n) (≈ 160 pcm).
- Spectre par unité de léthargie dans le combustible et le modérateur : bosse thermique, ralentissement en 1/E,
  résonances de l'U-238 et autoprotection ; facteur de désavantage thermique 1,145.
- Convergence : entropie de Shannon stable dès la première génération ; autocorrélation entre générations ≈ −0,2.

### 02 — Études paramétriques (trois notebooks)

Le plan prévoyait six parties (2a à 2f). Les parties enrichissement et bore critique ont été regroupées dans le
notebook **02a** ; le coefficient du modérateur est devenu **02b**, le Doppler **02c**. Les deux options (2e, 2f) n'ont
pas été faites (voir *Perspectives*).

- **02a** : balayage de l'enrichissement de 0,711 à 5 % (k∞ = 1 vers 1 % d'enrichissement, à 0 ppm), balayage du bore
  de 0 à 6000 ppm, efficacité différentielle du bore −5,4 pcm/ppm à 1000 ppm. Bore critique du réseau infini par
  ajustement pondéré et par `Model.keff_search` (méthode GRsecant, Price et Roskoff 2023). Ce bore critique, très
  supérieur à celui d'un cœur réel, est interprété comme tel : un réseau infini n'a pas de fuites.
- **02b** : α_mod de 0 à 4000 ppm. Il change de signe vers 2195 ± 50 ppm : à forte concentration, la dilatation de
  l'eau retire du bore, et le coefficient devient positif. C'est la raison de la limite de concentration en bore en
  début de cycle. Décomposition à 1000 ppm : la densité porte l'essentiel de l'effet (−19,5 pcm/K), la température
  seule à densité fixe (loi S(α,β)) très peu (−1,2 pcm/K).
- **02c** : α_D en fonction de la température aux températures tabulées des données (294 à 2500 K), ajustement en
  a + b√T ; zoom sur le creux de flux à la résonance de 6,67 eV, qui s'élargit avec la température.

### 03 — Assemblage 17×17

- Géométrie de type Westinghouse (264 crayons, 24 tubes guides, 1 tube d'instrumentation) construite avec un
  `RectLattice`, sans chevauchement ; coupe avec le maillage des tallies (`SlicePlot`, `meshlines`) et rendu 3D
  (`SolidRayTracePlot`).
- k∞ supérieur de 923 ± 59 pcm à celui de la cellule crayon : l'eau des tubes guides sur-modère un réseau
  sous-modéré.
- Carte de puissance crayon par crayon (20 millions d'histoires, ≈ 0,3 % d'incertitude par crayon), F_xy = 1,061 ;
  crayons voisins des tubes guides les plus puissants.
- Test statistique par symétrie : les écarts entre crayons symétriques suivent une loi normale d'écart-type 1,09.
- Convergence de la source : 3 générations pour l'assemblage, ≈ 55 pour une rangée de 9 assemblages avec fuites ;
  la méthode des blocs suggère une sous-estimation de ≈ 40 % de l'incertitude naïve dans le grand système.

Écart au plan : la statistique a été fixée à 50 000 neutrons × 400 générations actives (au lieu de
100 000 × 300), suffisante pour 0,3 % par crayon. L'assemblage n'a pas été comparé au problème 2 du
benchmark VERA (assemblage 2D) ; seule la cellule crayon l'a été (voir plus bas).

### 04 — Épuisement

- Cellule crayon irradiée à 40 W/g (193 W/cm) jusqu'à 50 GWj/t : 29 pas, schéma prédicteur, chaîne d'évolution
  simplifiée REP (228 nucléides, benchmark VERA/CASL), téléchargée depuis openmc.org (hors dépôt).
- Empoisonnement Xe-135 (≈ 2 jours) et Sm-149 (≈ 50 jours) : ≈ 3 300 pcm ; puis ≈ −680 pcm par GWj/t.
- U-235 de 4 % à 0,76 % ; 14,3 kg/t de plutonium, dont 68 % fissile ; deux tiers des fissions dues au plutonium en
  fin d'irradiation (transports de contrôle sur les compositions exportées).
- Taux de réaction : le mode `flux` pur (flux multigroupe, 361 groupes) surestime de ≈ 30 % les captures de l'U-238,
  faute d'autoprotection dans les groupes. Le mode retenu comptabilise directement les captures et fissions des
  actinides ; il est validé à 0,2 % près contre le mode exact.

Écarts au plan : le contrôle de **convergence en pas de temps** et le **modèle de réactivité linéaire** n'ont pas
été faits (voir *Perspectives*).

### Validation sur le benchmark VERA (sans notebook dédié)

Le modèle de cellule crayon a été comparé au **problème 1 du benchmark VERA** (*VERA Core Physics Benchmark
Progression Problems*, CASL-U-2012-0131-004, rév. 4), avec les densités atomiques exactes de la spécification :
cas 1A (isotherme à 565 K) et 1B à 1D (combustible à 600, 900 et 1200 K). La référence est un calcul KENO-VI en
énergie continue avec ENDF/B-VII.0 (≈ 6 pcm).

- Écarts OpenMC − référence : −48, −99, −12 et +3 pcm (± ≈ 21 pcm), soit **moins de 100 pcm** dans les quatre cas,
  malgré des bibliothèques de données différentes. Résultat cité dans les notebooks 01 et 02c.
- Le cas 1B (combustible à 600 K) se distingue et abaisse de 12 % le coefficient Doppler entre 600 et 900 K ;
  l'écart n'est pas expliqué.
- Le traitement exact de la diffusion dans les résonances de l'U-238 (méthode RVS) n'explique pas cet écart (la
  référence ne l'utilise pas), mais il montre un effet réel : −220 à −280 pcm sur k et +30 % sur le coefficient
  Doppler entre 600 et 900 K.

---

## Méthodes communes

- **Code partagé** dans `src/` : matériaux, géométries (crayon, assemblage, rangée), modèles paramétrés, lancement
  des calculs, style des figures.
- **Cache des calculs** (`src/calcul.py`) : un calcul n'est relancé que si ses entrées changent (comparaison du
  `model.xml`, ou empreinte des réglages pour `keff_search` et l'épuisement). Réexécuter tous les notebooks depuis le
  cache prend moins d'une minute.
- **Reproductibilité** : graine fixe ; dans `keff_search` sur plusieurs cœurs, paramètre arrondi à 0,1 ppm (sinon
  les écarts d'arrondi entre threads rendent la recherche non reproductible).
- **Incertitudes** : chaque k avec son σ, chaque coefficient avec son incertitude propagée ; ajustements pondérés,
  χ² réduit et facteur de Birge quand la dispersion dépasse les incertitudes.
- **Contrôle de la géométrie** avant tout calcul : `slice_data(show_overlaps=True)` et `assert` sur l'absence de
  pixel sans cellule ou en chevauchement.
- **Figures** : style commun (`src/style.py`), lisibles en petit format.

---

## Limites communes des modèles

- **Pas de fuites** : cellule crayon et assemblage ont des bords réfléchissants (k∞, pas k_eff). Les bores critiques
  et taux de combustion obtenus ne sont pas ceux d'un cœur réel.
- **Conditions uniformes** : une seule température de combustible et de modérateur, sans couplage thermohydraulique.
- **Bore constant** pendant l'épuisement (en réacteur, il est dilué au cours du cycle).
- **Une seule bibliothèque de données** (ENDF/B-VIII.0) : l'incertitude due aux données nucléaires n'est pas évaluée.
- **Validation limitée** au problème 1 de VERA (cellule crayon), avec une bibliothèque différente de celle de la
  référence.
- **Diffusion dans les résonances** : tous les calculs utilisent le traitement par défaut d'OpenMC. Le test sur le
  benchmark VERA montre que le traitement exact (RVS) renforce le coefficient Doppler de ≈ 30 % entre 600 et 900 K : le Doppler du
  notebook 02c (−2,0 pcm/K) est donc probablement sous-estimé en valeur absolue.

---

## Perspectives

Par ordre d'intérêt :

1. **Suite de la validation VERA** : comprendre l'écart du cas 1B (autres graines, bibliothèque ENDF/B-VII.x plus
   proche de la référence), puis traiter le problème 2 (assemblage 2D), proche du notebook 03.
2. **Formule des quatre facteurs** (prévue en 2e) : calculer ε, p, f, η à partir de tallies, vérifier que leur
   produit redonne k∞, et montrer quel facteur porte chaque effet du notebook 02 (enrichissement : η et f ; bore : f ;
   température du combustible : p).
3. **Convergence en pas de temps** de l'épuisement : refaire le calcul avec des pas deux fois plus petits, ou avec le
   schéma prédicteur-correcteur `CECMIntegrator`, et comparer k∞ et les masses (≈ 35 min de calcul).
4. **Modèle de réactivité linéaire** : à partir de k∞(burn-up), estimer le taux de combustion de décharge d'une
   gestion en 3 ou 4 lots, avec une estimation des fuites.
5. **Grappe de commande** insérée dans les tubes guides de l'assemblage (AIC ou B₄C) : efficacité en pcm et
   déformation de la carte de puissance ; **crayons au gadolinium** : creux de puissance local.
6. **UO₂ ou uranium métal** (prévue en 2f) : effet de la densité d'uranium et du rapport de modération.
7. **Sensibilité aux données nucléaires** : refaire le notebook 01 avec JEFF-3.3 ; les écarts entre bibliothèques
   (quelques centaines de pcm) dépassent souvent l'incertitude statistique.
8. **Combustible MOX**, avec le vecteur de plutonium du notebook 04 ; **réseau hexagonal de type VVER** (exemple
   officiel *Hexagonal Lattices*) ; **épuisement de l'assemblage**, nettement plus coûteux.

---

## Ressources

- Documentation OpenMC : <https://docs.openmc.org/>
- Exemples officiels : <https://github.com/openmc-dev/openmc/wiki/Example-Jupyter-Notebooks>, en particulier
  *Pincell*, *Criticality Search*, *Source Convergence*, *Pincell Depletion*.
- Benchmark VERA (CASL) : conditions et résultats de référence pour la cellule crayon et l'assemblage.
