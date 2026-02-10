# M2O — Simulation de vues macro à partir de la densité implicite marché
## Méthode 1 : Implicit density + entropic tilt (exponential tilting)

---

## 0. Objectif

Simuler, à chaque date historique t, des vues macro plausibles sous forme de
distributions de probabilité sur le sous-jacent à maturité T, **sans fuite d’information**,
afin de backtester le moteur M2O de manière défendable.

Principe fondamental :
> La vue ne crée pas une distribution ex nihilo.
> Elle déforme la distribution déjà donnée par le marché options.

---

## 1. Entrées nécessaires à la date t

À chaque date t (backtest ou production), on suppose disponibles :

- La surface de volatilité implicite observée à t
- Les prix bid/ask des options pour la maturité T
- Le forward F_t,T
- Les contraintes utilisateur (filtres)
- Le cadre de risque (contraintes dures)

Aucune information postérieure à t ne doit être utilisée.

---

## 2. Construction de la densité implicite marché p_t(x)

### 2.1 Principe

Le marché options encode une densité **risk-neutral** implicite :
\[
p_t(x) = \mathbb{Q}(S_T = x \mid \mathcal{F}_t)
\]

Cette densité est considérée comme le **prior objectif**.

### 2.2 Méthodes acceptables (au choix selon implémentation)

- Densité Breeden–Litzenberger (seconde dérivée des calls)
- Approximation paramétrique :
  - lognormale ajustée au
