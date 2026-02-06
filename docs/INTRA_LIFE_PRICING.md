# Pricing Intra-Vie des Options avec Tilt Terminal

## Introduction

Ce document décrit la méthodologie mathématique utilisée pour évaluer les options à des dates intermédiaires (avant expiration) en intégrant une **vue macro** sur la distribution future du sous-jacent.

L'approche classique de pricing risk-neutre utilise la distribution implicite des prix de marché. Notre méthode permet d'incorporer une vue alternative (mixture de gaussiennes) tout en restant cohérent avec l'absence d'arbitrage.

---

## 1. Problématique

### 1.1 Contexte

À la date $t = 0$, nous avons :
- **Prix actuel de l'option** : $V_0$ (prix de marché, premium)
- **Densité risque-neutre du marché** : $q_T(x)$ — distribution implicite du sous-jacent $F_T$ à expiration
- **Vue macro** : $p_T(x)$ — notre mixture de gaussiennes représentant notre anticipation

### 1.2 Objectif

Calculer le **prix de l'option à une date intermédiaire** $0 < t < T$ sous notre vue macro, noté $V_t^{\text{view}}$.

---

## 2. Formulation Mathématique

### 2.1 Mesure de Pricing Tilté

On définit une nouvelle mesure de probabilité $\mathbb{P}^{\text{view}}$ à partir de la mesure risque-neutre $\mathbb{Q}$ via le **dérivé de Radon-Nikodym terminal** :

$$
L_T = \frac{d\mathbb{P}^{\text{view}}}{d\mathbb{Q}} \bigg|_{\mathcal{F}_T} = \frac{p_T(F_T)}{q_T(F_T)}
$$

Où :
- $p_T(x)$ : densité de notre vue (mixture de gaussiennes)
- $q_T(x)$ : densité risque-neutre du marché

### 2.2 Prix à Date Intermédiaire

Le prix de l'option à la date $t$ sous notre vue est :

$$
\boxed{V_t^{\text{view}} = \frac{\mathbb{E}^{\mathbb{Q}}\left[ D(t,T) \cdot g(F_T) \cdot L_T \,|\, \mathcal{F}_t \right]}{\mathbb{E}^{\mathbb{Q}}\left[ L_T \,|\, \mathcal{F}_t \right]}}
$$

Où :
- $D(t,T) = e^{-r(T-t)}$ : facteur d'actualisation
- $g(F_T)$ : payoff de l'option à expiration
  - **Call** : $g(x) = \max(x - K, 0)$
  - **Put** : $g(x) = \max(K - x, 0)$
- $\mathcal{F}_t$ : information disponible à la date $t$

### 2.3 Simplification Numérique

Pour l'implémentation, on utilise l'approximation suivante (conditionnement trivial) :

$$
V_t^{\text{view}} \approx \frac{\int p_T(x) \cdot D(t,T) \cdot g(x) \, dx}{\int p_T(x) \, dx}
$$

Ce qui se simplifie en (puisque $\int p_T = 1$) :

$$
V_t^{\text{view}} = D(t,T) \cdot \mathbb{E}^{p_T}[g(F_T)]
$$

---

## 3. Construction de la Densité Marché

### 3.1 Approximation Log-Normale

La densité risque-neutre $q_T(x)$ est approximée par une distribution log-normale :

$$
q_T(x) = \frac{1}{x \cdot \sigma \cdot \sqrt{2\pi}} \exp\left( -\frac{1}{2} \left( \frac{\ln(x/F_0)}{\sigma} \right)^2 \right)
$$

Où :
- $F_0$ : prix forward (≈ prix spot du sous-jacent)
- $\sigma$ : volatilité implicite de l'option

### 3.2 Méthode Breeden-Litzenberger (Implémentée)

Pour une approche plus précise, on extrait $q_T$ directement des prix d'options via la formule de Breeden-Litzenberger :

$$
q_T(K) = e^{rT} \frac{\partial^2 C}{\partial K^2}(K)
$$

Où $C(K)$ est le prix du call de strike $K$.

#### Implémentation

```python
def breeden_litzenberger_density(
    strikes: np.ndarray,      # Strikes triés
    call_prices: np.ndarray,  # Prix des calls correspondants
    price_grid: np.ndarray,   # Grille d'interpolation
    risk_free_rate: float,    # Taux sans risque
    time_to_expiry: float     # Temps jusqu'à expiration
) -> np.ndarray:
    """
    1. Interpolation cubique C(K) via CubicSpline
    2. Dérivée seconde ∂²C/∂K² 
    3. q_T(K) = e^{rT} × ∂²C/∂K²
    4. Normalisation pour ∫q_T = 1
    """
```

#### Conditions d'utilisation

- **Minimum 4 strikes** de calls avec des prix > 0
- Les options doivent avoir la **même expiration**
- Si les conditions ne sont pas remplies, fallback sur l'approximation log-normale

---

## 4. Vue Macro : Mixture de Gaussiennes

### 4.1 Définition

Notre vue est modélisée par une mixture de $n$ gaussiennes (potentiellement asymétriques) :

$$
p_T(x) = \sum_{i=1}^{n} w_i \cdot \phi_i(x)
$$

Où :
- $w_i$ : poids de la composante $i$ ($\sum w_i = 1$)
- $\phi_i(x)$ : densité gaussienne (ou gaussienne asymétrique)

### 4.2 Gaussienne Asymétrique

Pour une gaussienne asymétrique de paramètres $(\mu, \sigma_L, \sigma_R)$ :

$$
\phi(x) = \begin{cases}
\frac{2}{\sigma_L + \sigma_R} \cdot \frac{1}{\sqrt{2\pi}} \exp\left( -\frac{(x-\mu)^2}{2\sigma_L^2} \right) & \text{si } x < \mu \\
\frac{2}{\sigma_L + \sigma_R} \cdot \frac{1}{\sqrt{2\pi}} \exp\left( -\frac{(x-\mu)^2}{2\sigma_R^2} \right) & \text{si } x \geq \mu
\end{cases}
$$

---

## 5. Calcul des Poids du Tilt

### 5.1 Formule

Les poids du tilt terminal sont calculés point par point :

$$
L_T(x) = \frac{p_T(x)}{q_T(x)}
$$

### 5.2 Protection Numérique

Pour éviter les divisions par zéro :

```python
L_T = view_density / (market_density + 1e-10)
```

### 5.3 Interprétation

- $L_T(x) > 1$ : notre vue surpondère les prix $x$ par rapport au marché
- $L_T(x) < 1$ : notre vue sous-pondère les prix $x$
- $L_T(x) = 1$ : accord entre notre vue et le marché

---

## 6. Dates Intermédiaires

### 6.1 Choix des Dates

On calcule le prix à $N = 5$ dates intermédiaires correspondant aux fractions :

$$
\frac{t}{T} \in \{0.2, 0.4, 0.6, 0.8, 1.0\}
$$

### 6.2 Temps Restant

Pour chaque date intermédiaire :
$$
\tau = T - t = (1 - t/T) \cdot T
$$

### 6.3 Discount Factor

$$
D(t,T) = e^{-r \cdot \tau}
$$

---

## 7. Calcul du P&L Intra-Vie

### 7.1 Définition

À chaque date intermédiaire $t$, le P&L moyen est :

$$
\text{P\&L}_t = V_t^{\text{view}} - V_0
$$

Où $V_0$ est le premium initial payé (pour une position long).

### 7.2 Moyenne des P&L Intra-Vie

Le score `avg_intra_life_pnl` est la moyenne des P&L sur toutes les dates :

$$
\text{Avg Intra P\&L} = \frac{1}{N} \sum_{i=1}^{N} \text{P\&L}_{t_i}
$$

---

## 8. Implémentation

### 8.1 Fichiers Concernés

| Fichier | Rôle |
|---------|------|
| `option_class.py` | Calcul Python des prix intra-vie pour chaque option |
| `strategy_metrics.cpp` | Agrégation C++ des prix pour les stratégies |
| `strategy_scoring.cpp` | Scoring basé sur `avg_intra_life_pnl` |

### 8.2 Méthodes Python

```python
class Option:
    def _build_market_density(sigma_market):
        """Construit q_T(x) - densité log-normale"""
        
    def _calculate_tilt_weights():
        """Calcule L_T = p_T / q_T"""
        
    def _calculate_intra_life_prices(n_dates, risk_free_rate):
        """Calcule V_t^view pour chaque date"""
        
    def calculate_all_intra_life(sigma_market, n_dates, risk_free_rate):
        """Orchestre le calcul complet"""
```

### 8.3 Calcul C++ pour Stratégies

Pour une stratégie multi-jambes, le prix intra-vie total est :

$$
V_t^{\text{strategy}} = \sum_{i=1}^{\text{legs}} \text{sign}_i \cdot V_t^{(i)}
$$

Où $\text{sign}_i = +1$ (long) ou $-1$ (short).

---

## 9. Exemple Numérique

### Paramètres
- Sous-jacent : $F_0 = 98$
- Strike : $K = 100$
- Premium : $V_0 = 2.5$
- Volatilité implicite : $\sigma = 20\%$
- Vue : Gaussienne centrée sur 102 avec $\sigma = 3$

### Résultats (Call)

| Date (t/T) | $V_t^{\text{view}}$ | P&L |
|------------|---------------------|-----|
| 0.2 | 3.12 | +0.62 |
| 0.4 | 3.45 | +0.95 |
| 0.6 | 3.89 | +1.39 |
| 0.8 | 4.21 | +1.71 |
| 1.0 | 4.50 | +2.00 |

**Avg Intra P&L** = (0.62 + 0.95 + 1.39 + 1.71 + 2.00) / 5 = **+1.33**

---

## 10. Avantages et Limites

### 10.1 Avantages

✅ Intègre les vues macro dans le pricing  
✅ Cohérent avec l'absence d'arbitrage (changement de mesure)  
✅ Permet d'évaluer la performance espérée avant expiration  
✅ Score comparable entre stratégies différentes  

### 10.2 Limites

⚠️ Approximation de la densité marché (log-normale vs réelle)  
⚠️ Conditionnement trivial (pas de modèle de diffusion intermédiaire)  
⚠️ Ne tient pas compte du smile de volatilité dynamique  

---

## 11. Références

1. **Breeden, D. & Litzenberger, R.** (1978). "Prices of State-Contingent Claims Implicit in Option Prices"
2. **Föllmer, H. & Schweizer, M.** (1991). "Hedging of Contingent Claims under Incomplete Information"
3. **Brigo, D. & Mercurio, F.** (2006). *Interest Rate Models - Theory and Practice*

---

## Annexe : Formule Résumée

Pour une option de payoff $g(x)$ :

$$
\boxed{
V_t^{\text{view}} = e^{-r(T-t)} \cdot \frac{\int p_T(x) \cdot g(x) \, dx}{\int p_T(x) \, dx}
}
$$

**P&L à la date $t$** :
$$
\text{P\&L}_t = V_t^{\text{view}} - \text{Premium initial}
$$

**Score final** :
$$
\text{avg\_intra\_life\_pnl} = \frac{1}{N} \sum_{i=1}^{N} \text{P\&L}_{t_i}
$$
