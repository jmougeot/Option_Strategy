"""
Onglet Help - Explication détaillée des critères de scoring, filtres et paramètres
"""

import streamlit as st


def display_help_tab():
    """Affiche l'onglet d'aide avec les explications complètes."""
    
    st.header("📚 Guide Complet de l'Application")
    
    st.markdown("""
    Ce guide explique tous les paramètres, filtres et critères de scoring utilisés dans l'application.
    Utilisez le menu ci-dessous pour naviguer vers la section souhaitée.
    """)
    
    # =========================================================================
    # SOMMAIRE
    # =========================================================================
    
    st.markdown("""
    **Sommaire:**
    1. [Scénarios de Marché](#scenarios-de-marche)
    2. [Paramètres de Recherche](#parametres-de-recherche)
    3. [Filtres de Stratégies](#filtres-de-strategies)
    4. [Critères de Scoring](#criteres-de-scoring)
    5. [Critères Avancés (Greeks)](#criteres-avances)
    6. [Système de Scoring](#systeme-de-scoring)
    """)
    
    st.markdown("---")
    
    # =========================================================================
    # SCÉNARIOS DE MARCHÉ
    # =========================================================================
    
    st.subheader("🎯 Scénarios de Marché", anchor="scenarios-de-marche")
    
    st.markdown("""
    Les scénarios définissent vos anticipations sur le prix du sous-jacent à l'expiration.
    Ils sont modélisés par une **mixture gaussienne** (mélange de distributions normales).
    """)
    
    with st.expander("📊 Target Price (Prix Cible)", expanded=True):
        st.markdown("""
        **Définition:** Le prix auquel vous pensez que le sous-jacent terminera pour ce scénario.
        
        **Exemple:** 
        - Target = 98.50 signifie que vous anticipez un prix de 98.50 à l'expiration
        
        **Usage:**
        - C'est le centre de la distribution gaussienne pour ce scénario
        - Plusieurs scénarios permettent de modéliser différentes possibilités (hausse, baisse, range)
        """)
    
    with st.expander("📈 Uncertainty (Incertitude / σ)"):
        st.markdown("""
        **Définition:** L'écart-type de la distribution gaussienne autour du prix cible.
        
        **Formule:** La probabilité que le prix soit entre $\\mu - \\sigma$ et $\\mu + \\sigma$ est ~68%
        
        **Interprétation:**
        - **σ petit (0.05)** : Vous êtes très confiant dans votre prédiction
        - **σ grand (0.20)** : Forte incertitude, le prix peut beaucoup varier
        
        **Mode Asymétrique:**
        - **σ left** : Incertitude à la baisse (downside)
        - **σ right** : Incertitude à la hausse (upside)
        - Permet de modéliser un biais (ex: plus de risque à la baisse qu'à la hausse)
        """)
    
    with st.expander("⚖️ Probability (Probabilité / Poids)"):
        st.markdown("""
        **Définition:** Le poids relatif de ce scénario par rapport aux autres.
        
        **Normalisation:** Les poids sont automatiquement normalisés pour que leur somme = 100%
        
        **Exemple avec 2 scénarios:**
        - Scénario 1: Target=98.0, Weight=60
        - Scénario 2: Target=99.0, Weight=40
        - → 60% de chances pour le scénario 1, 40% pour le scénario 2
        
        **Astuce:** Utilisez les probabilités pour refléter votre conviction dans chaque scénario.
        """)
    
    with st.expander("🔀 Mixture Gaussienne - Comment ça marche"):
        st.markdown("""
        **Formule de la densité:**
        $$f(x) = \\sum_{i=1}^{n} w_i \\cdot \\mathcal{N}(x | \\mu_i, \\sigma_i)$$
        
        Où:
        - $w_i$ = Poids normalisé du scénario i
        - $\\mu_i$ = Prix cible du scénario i
        - $\\sigma_i$ = Incertitude du scénario i
        - $\\mathcal{N}$ = Distribution normale
        
        **Avantages:**
        - Modélise des distributions **multimodales** (plusieurs pics possibles)
        - Capture les **fat tails** (queues épaisses) naturellement
        - Permet des distributions **asymétriques**
        
        **Visualisation:** Le diagramme P&L montre la courbe de probabilité en arrière-plan.
        """)
    
    st.markdown("---")
    
    # =========================================================================
    # PARAMÈTRES DE RECHERCHE
    # =========================================================================
    
    st.subheader("⚙️ Paramètres de Recherche", anchor="parametres-de-recherche")
    
    with st.expander("🏷️ Underlying (Sous-jacent)"):
        st.markdown("""
        **Définition:** Le code Bloomberg du sous-jacent.
        
        **Exemples courants:**
        - **ER** = EURIBOR 3 mois
        - **ED** = Eurodollar
        - **TY** = US Treasury 10Y
        
        **Format complet:** Underlying + Month + Year (ex: ERH6 = EURIBOR Mars 2026)
        """)
    
    with st.expander("📅 Years & Months (Années & Mois)"):
        st.markdown("""
        **Years (Années):**
        - Format: 1 chiffre (6 = 2026, 7 = 2027)
        - Multiples: séparer par virgule (6, 7)
        
        **Months (Mois d'expiration):**
        - **H** = Mars (March)
        - **M** = Juin (June)
        - **U** = Septembre (September)
        - **Z** = Décembre (December)
        
        **Exemple:** Months=H, Years=6 → Options expirant en Mars 2026
        """)
    
    with st.expander("💰 Price Range (Min/Max/Step)"):
        st.markdown("""
        **Min Price / Max Price:**
        - Définit la plage de strikes à considérer
        - Les options avec strike en dehors de cette plage sont ignorées
        
        **Price Step:**
        - L'incrément entre les strikes (tick size)
        - Ex: 0.0625 pour EURIBOR (1/16ème de point)
        
        **Impact:** Une plage plus large = plus d'options = plus de combinaisons possibles = temps de calcul plus long
        """)
    
    with st.expander("🦵 Max Legs (Nombre de Jambes)"):
        st.markdown("""
        **Définition:** Le nombre maximum d'options dans une stratégie.
        
        **Exemples par nombre de legs:**
        - **1 leg** : Simple call ou put
        - **2 legs** : Spreads (bull call, bear put), straddles, strangles
        - **3 legs** : Butterflies, ladders
        - **4 legs** : Condors, iron butterflies
        - **5+ legs** : Stratégies complexes personnalisées
        
        **Performance:** Plus de legs = exponentiellement plus de combinaisons
        - 2 legs : ~N² combinaisons
        - 4 legs : ~N⁴ combinaisons
        """)
    
    with st.expander("🔄 Roll Months (Mois de Roll)"):
        st.markdown("""
        **Définition:** Les échéances vers lesquelles calculer le roll.
        
        **Format:** M + Y (ex: Z5, H6)
        - Z5 = Décembre 2025
        - H6 = Mars 2026
        
        **Multiples:** Séparer par virgule (Z5, H6, M6)
        
        **Usage:** 
        - Compare le prix de la stratégie actuelle vs la même stratégie sur une échéance future
        - Utile pour évaluer le coût de maintien d'une position
        """)
    
    with st.expander("📝 Raw Code Mode"):
        st.markdown("""
        **Définition:** Mode avancé pour spécifier directement les codes Bloomberg.
        
        **Format:** Codes séparés par virgule
        - Ex: RXWF26C2, RXWF26P2
        
        **Usage:** 
        - Pour accéder à des options non-standard
        - Pour des sous-jacents avec des conventions de nommage spéciales
        """)
    
    st.markdown("---")
    
    # =========================================================================
    # FILTRES
    # =========================================================================
    
    st.subheader("🔍 Filtres de Stratégies", anchor="filtres-de-strategies")
    
    st.markdown("""
    Les filtres éliminent les stratégies qui ne correspondent pas à vos critères **avant** le scoring.
    Ils réduisent l'espace de recherche et accélèrent le calcul.
    """)
    
    with st.expander("📉 Max Loss Left / Right (Perte Max Gauche / Droite)", expanded=True):
        st.markdown("""
        **Définition:** La perte maximale autorisée dans chaque direction.
        
        **Max Loss Left:** Perte max si le prix baisse (en-dessous de Limit Left)
        **Max Loss Right:** Perte max si le prix monte (au-dessus de Limit Right)
        
        **Exemple:**
        - Max Loss Left = 0.10, Limit Left = 98.50
        - → La stratégie ne peut pas perdre plus de 0.10 si le prix est < 98.50
        
        **Checkbox "Unlimited Loss":**
        - Désactive ce filtre (permet les pertes illimitées)
        - ⚠️ Attention aux stratégies vendeuses nues !
        """)
    
    with st.expander("🎯 Limit Left / Right"):
        st.markdown("""
        **Définition:** Les seuils où les filtres Max Loss s'appliquent.
        
        **Limit Left:** Prix en-dessous duquel Max Loss Left s'applique
        **Limit Right:** Prix au-dessus duquel Max Loss Right s'applique
        
        **Logique:**
        - Si prix < Limit Left → vérifier que perte ≤ Max Loss Left
        - Si prix > Limit Right → vérifier que perte ≤ Max Loss Right
        
        **Astuce:** Alignez ces limites avec vos scénarios extrêmes.
        """)
    
    with st.expander("💵 Max Premium (Prime Maximum)"):
        st.markdown("""
        **Définition:** Le coût maximum (en valeur absolue) pour mettre en place la stratégie.
        
        **Interprétation:**
        - Filtre les stratégies trop chères
        - S'applique en valeur absolue (couvre débit et crédit)
        
        **Exemple:** Max Premium = 0.05 → rejette les stratégies qui coûtent > 0.05
        """)
    
    with st.expander("💰 Min Price for Short (Prix Min pour Vente)"):
        st.markdown("""
        **Définition:** Le prix minimum qu'une option doit valoir pour pouvoir être vendue.
        
        **Usage:**
        - Évite de vendre des options sans valeur (illiquides)
        - Filtre les options deep OTM avec prime négligeable
        
        **Exemple:** Min = 0.005 → on ne vend pas d'options valant moins de 0.005
        """)
    
    with st.expander("📊 PUT: Short-Long / CALL: Short-Long (Exposition Nette)"):
        st.markdown("""
        **Définition:** La différence entre options vendues et achetées par type.
        
        **PUT: Short-Long:**
        - = 0 : Autant de puts vendus qu'achetés (position fermée à gauche)
        - > 0 : Plus de puts vendus qu'achetés (exposition baissière)
        - < 0 : Plus de puts achetés que vendus (protection baissière)
        
        **CALL: Short-Long:**
        - = 0 : Autant de calls vendus qu'achetés (position fermée à droite)
        - > 0 : Plus de calls vendus qu'achetés (exposition haussière)
        - < 0 : Plus de calls achetés que vendus (protection haussière)
        
        **Exemple:** 
        - PUT=0, CALL=0 → Stratégies parfaitement fermées (condors, butterflies)
        - PUT=1, CALL=0 → On peut vendre 1 put de plus qu'on en achète
        """)
    
    with st.expander("Δ Delta Min / Max"):
        st.markdown("""
        **Définition:** Contraintes sur le delta total de la stratégie.
        
        **Plage typique:** -1.0 à +1.0 (ou -100% à +100%)
        
        **Exemples:**
        - Delta Min = -0.10, Delta Max = +0.10 → Stratégies quasi-neutres
        - Delta Min = 0.20, Delta Max = 0.50 → Biais haussier modéré
        
        **Usage:** Contrôle le biais directionnel de la stratégie.
        """)
    
    with st.expander("📋 Select Strategy Type (Types de Stratégies)"):
        st.markdown("""
        **Définition:** Filtre pour inclure uniquement certains types de stratégies prédéfinis.
        
        **Types disponibles:**
        - **Put Condor** : 4 puts formant un condor
        - **Call Condor** : 4 calls formant un condor
        - **Put Ladder** : 3 puts (ex: 1 long, 2 shorts)
        - **Call Ladder** : 3 calls (ex: 1 long, 2 shorts)
        - **Put Fly** : 3 puts formant un butterfly
        - **Call Fly** : 3 calls formant un butterfly
        
        **Note:** Ce filtre utilise la reconnaissance de pattern sur la structure de la stratégie.
        """)
    
    st.markdown("---")
    
    # =========================================================================
    # CRITÈRES PRINCIPAUX
    # =========================================================================
    
    st.subheader("🎯 Critères de Scoring", anchor="criteres-de-scoring")
    
    # Expected Gain (Average P&L)
    with st.expander("📈 Expected Gain at Expiry (PM - Profit Moyen)", expanded=True):
        st.markdown("""
        **Définition:** Le profit moyen attendu de la stratégie à l'expiration, pondéré par la distribution 
        de probabilité des prix du sous-jacent (mixture gaussienne).
        
        **Formule:**
        $$PM = \\int_{-\\infty}^{+\\infty} P\\&L(S) \\cdot f(S) \\, dS$$
        
        Où:
        - $P\\&L(S)$ = Profit/Perte si le sous-jacent termine à $S$
        - $f(S)$ = Densité de probabilité (mixture gaussienne définie par vos scénarios)
        
        **Interprétation:**
        - **PM > 0** : La stratégie est profitable en moyenne selon vos anticipations
        - **PM < 0** : La stratégie perd de l'argent en moyenne
        - **Plus élevé = Meilleur**
        
        **Exemple:** Si PM = 0.50, cela signifie que pour 1€ de nominal, vous gagnez en moyenne 0.50€.
        """)
    
    # Leverage of Expected Gain
    with st.expander("⚡ Leverage of Expected Gain (Levier du PM)"):
        st.markdown("""
        **Définition:** Le ratio entre le profit moyen attendu et la prime nette payée/reçue.
        Mesure l'efficacité du capital investi.
        
        **Formule:**
        $$Levier = \\frac{PM}{|Premium|}$$
        
        **Interprétation:**
        - **Levier = 2** : Vous gagnez 2€ pour chaque 1€ de prime payée
        - **Levier élevé** : Grande efficacité du capital
        - **Plus élevé = Meilleur**
        
        **Attention:** Un levier très élevé peut indiquer une stratégie risquée avec une faible probabilité de succès.
        """)
    
    # Roll Quarterly
    with st.expander("🔄 Roll into Next Quarter (Roll Q-1)"):
        st.markdown("""
        **Définition:** La différence de prix entre l'option actuelle et la même option 
        sur l'échéance du trimestre suivant (Q+1).
        
        **Formule:**
        $$Roll = Prix_{Q+1} - Prix_{actuel}$$
        
        **Interprétation:**
        - **Roll > 0** : L'option est plus chère sur l'échéance suivante (contango)
        - **Roll < 0** : L'option est moins chère sur l'échéance suivante (backwardation)
        - Pour une position **longue**, un roll positif est favorable (la valeur temps augmente)
        - **Plus élevé = Meilleur** (pour positions longues)
        
        **Usage:** Utile pour évaluer le coût de maintien d'une position dans le temps.
        """)
    
    # Tail Risk Penalty (Max Loss)
    with st.expander("⚠️ Tail Risk Penalty (Risque de Queue)"):
        st.markdown("""
        **Définition:** Mesure le risque de pertes extrêmes dans les queues de distribution.
        Pénalise les stratégies qui perdent beaucoup dans les scénarios improbables mais possibles.
        
        **Formule:**
        $$Tail\\ Penalty = \\int max(-P\\&L(S), 0)^2 \\cdot f(S) \\, dS$$
        
        **Interprétation:**
        - **Tail Penalty = 0** : Pas de risque de perte dans les extrêmes
        - **Tail Penalty élevé** : Pertes importantes possibles dans les scénarios extrêmes
        - **Plus faible = Meilleur**
        
        **Exemple:** Une vente de put non couverte aura un Tail Penalty très élevé car les pertes 
        peuvent être illimitées si le marché s'effondre.
        """)
    
    # Average Intra-Life P&L
    with st.expander("📊 Avg Intra-Life P&L (P&L Moyen Intra-Vie)"):
        st.markdown("""
        **Définition:** Le profit/perte moyen de la stratégie à des dates intermédiaires 
        avant l'expiration, calculé via le modèle de Bachelier.
        
        **Calcul:**
        1. On divise la période en 5 dates: 20%, 40%, 60%, 80%, 100% de la durée
        2. Pour chaque date, on calcule le prix de l'option avec Bachelier
        3. On moyenne les P&L sur toutes ces dates
        
        **Interprétation:**
        - **Avg Intra-Life > 0** : La stratégie est profitable même avant expiration
        - **Avg Intra-Life < 0** : La stratégie peut perdre de l'argent si on sort avant expiration
        - **Plus élevé = Meilleur**
        
        **Usage:** Important si vous prévoyez de potentiellement fermer la position avant l'échéance.
        """)
    
    # Premium
    with st.expander("💰 Premium (Prime Nette)"):
        st.markdown("""
        **Définition:** La prime nette payée ou reçue pour mettre en place la stratégie.
        
        **Formule:**
        $$Premium = \\sum_{i} sign_i \\times premium_i$$
        
        Où:
        - $sign_i$ = +1 pour achat, -1 pour vente
        - $premium_i$ = Prix de l'option i
        
        **Interprétation:**
        - **Premium > 0** : Vous payez pour mettre en place la stratégie (débit)
        - **Premium < 0** : Vous recevez de l'argent (crédit)
        - **Plus proche de 0 = Meilleur** (si poids activé)
        
        **Stratégies:**
        - Stratégies à **coût nul** : Iron condors, butterflies équilibrés
        - Stratégies **crédit** : Vente d'options, credit spreads
        - Stratégies **débit** : Achat d'options, debit spreads
        """)
    
    st.markdown("---")
    
    # =========================================================================
    # SYSTÈME DE SCORING
    # =========================================================================
    
    st.subheader("⚙️ Comment fonctionne le Scoring", anchor="systeme-de-scoring")
    
    st.markdown("""
    ### Moyenne Géométrique Pondérée
    
    Le score final de chaque stratégie est calculé via une **moyenne géométrique pondérée** des scores normalisés:
    
    $$Score = \\exp\\left(\\sum_{i} w_i \\cdot \\log(\\epsilon + s_i)\\right)$$
    
    Où:
    - $w_i$ = Poids du critère i (normalisé pour que $\\sum w_i = 1$)
    - $s_i$ = Score normalisé du critère i (entre 0 et 1)
    - $\\epsilon$ = 10⁻⁶ (pour éviter log(0))
    
    ### Avantages de cette approche:
    1. **Équilibre**: Un score très faible sur un critère important pénalise fortement le score global
    2. **Flexibilité**: Les poids permettent de personnaliser l'importance de chaque critère
    3. **Normalisation**: Tous les critères sont sur la même échelle [0, 1]
    
    ### Normalisation des critères:
    - **MAX**: Divise par le maximum → utilisé pour les critères où plus proche de 0 = meilleur
    - **MIN_MAX**: $(x - min) / (max - min)$ → utilisé pour les critères avec une plage de valeurs
    """)
    
    st.markdown("---")
    
    # =========================================================================
    # CONSEILS D'UTILISATION
    # =========================================================================
    
    st.subheader("💡 Conseils d'Utilisation")
    
    st.markdown("""
    ### Profils de stratégies suggérés:
    
    | Profil | Critères à privilégier |
    |--------|----------------------|
    | **Conservateur** | Max Loss faible, Tail Penalty faible, PM positif |
    | **Agressif** | Leverage élevé, PM élevé (accepte plus de risque) |
    | **Neutre** | Delta Neutral, Gamma Low, Vega Low |
    | **Carry Trade** | Roll élevé, Theta positif |
    | **Court terme** | Avg Intra-Life P&L élevé |
    
    ### Bonnes pratiques:
    1. **Commencez simple**: Activez 2-3 critères maximum au début
    2. **PM est essentiel**: Gardez toujours un poids sur Expected Gain
    3. **Équilibrez risque/rendement**: Combinez PM avec Max Loss ou Tail Penalty
    4. **Vérifiez visuellement**: Utilisez le diagramme P&L pour valider les stratégies
    """)
