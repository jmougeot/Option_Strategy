# 📊 Options Strategy Analyzer

Outil d'analyse et de comparaison de stratégies d'options pour traders professionnels.

## 🚀 Installation Ultra-Rapide

### Option 1: Installation automatique (Recommandé)
```bash
./install.sh
```

### Option 2: Installation manuelle
```bash
# 1. Créer l'environnement virtuel
python3 -m venv venv

# 2. Activer l'environnement
source venv/bin/activate

# 3. Installer les dépendances
pip install streamlit plotly pandas

# 4. Générer la base de données
python3 generate_full_database.py
```

## ▶️ Lancement de l'Application

### Option 1: Script rapide (Recommandé)
```bash
./run.sh
```

### Option 2: Commande manuelle
```bash
source venv/bin/activate
streamlit run app.py
```

L'application s'ouvrira automatiquement dans votre navigateur à l'adresse:
**http://localhost:8501**

## 📦 Structure du Projet

```
BGC/Stratégies/
├── app.py                      # Interface utilisateur Streamlit
├── strategies.py               # Définitions des stratégies d'options
├── strategy_comparison.py      # Système de comparaison
├── data.py                     # Gestion de la base de données
├── generate_full_database.py   # Génération des données de test
├── test_comparison.py          # Tests en ligne de commande
├── bloomberg_connector.py      # Connecteur Bloomberg API (futur)
├── install.sh                  # Script d'installation automatique
├── run.sh                      # Script de lancement rapide
├── requirements.txt            # Dépendances Python
└── calls_export.json          # Base de données d'options
```

## 🎯 Fonctionnalités

### Interface Web (Streamlit)
- ✅ **Sélection intuitive** des paramètres (prix cible, expiration)
- ✅ **Comparaison de 8 stratégies** d'options short volatility
- ✅ **Diagrammes P&L interactifs** à l'expiration
- ✅ **Scoring et ranking** automatique des stratégies
- ✅ **Analyse détaillée** avec breakevens, zones profitables, ratios R/R
- ✅ **Simulation multi-prix** pour tester différents scénarios

### Stratégies Disponibles
1. **Iron Condor** - Stratégie à 4 jambes avec risque défini
2. **Iron Butterfly** - Stratégie centrée avec risque défini
3. **Short Strangle** - Vente call + put OTM (risque illimité)
4. **Short Straddle** - Vente call + put ATM (risque illimité)
5. **Short Put** - Vente put simple
6. **Short Call** - Vente call simple
7. **Bull Put Spread** - Spread haussier avec risque défini
8. **Bear Call Spread** - Spread baissier avec risque défini

## 🎮 Utilisation

### 1. Dans l'interface web (sidebar):
- Ajustez le **prix cible** (ex: $100)
- Choisissez l'**horizon temporel** (ex: 30 jours)
- **Sélectionnez les stratégies** à comparer
- (Optionnel) Personnalisez les **poids du scoring**
- Cliquez sur **"🚀 COMPARER"**

### 2. Résultats affichés:
- **Tableau comparatif** avec toutes les métriques
- **Diagramme P&L** interactif
- **Analyse détaillée** de la stratégie gagnante
- **Simulation** à différents prix spot
- **Recommandations** personnalisées

## 🔧 Configuration Avancée

### Pondération du Scoring
Vous pouvez personnaliser les poids dans l'interface:
- **Max Profit** (par défaut: 30%)
- **Risque/Rendement** (par défaut: 30%)
- **Zone Profitable** (par défaut: 20%)
- **Performance Cible** (par défaut: 20%)

### Génération de Nouvelles Données
Pour créer une nouvelle base de données avec vos propres paramètres:
```bash
python3 generate_full_database.py
```

Éditez le fichier pour modifier:
- Prix spot du sous-jacent
- Range de strikes
- Dates d'expiration
- Volatilité implicite

## 🔌 Bloomberg API (À venir)

Le connecteur Bloomberg est préparé dans `bloomberg_connector.py`.
Pour l'activer:
1. Installez le Bloomberg Terminal
2. Installez le package: `pip install blpapi`
3. Décommentez la ligne dans `requirements.txt`
4. Dans l'interface, sélectionnez "Bloomberg API" au lieu de "JSON Local"

## 📝 Tests en Ligne de Commande

Pour tester sans interface graphique:
```bash
python3 test_comparison.py
```

Affiche une analyse complète en mode texte avec:
- Tableau de comparaison
- Stratégie gagnante détaillée
- Top 3 des stratégies
- Simulation P&L
- Recommandations

## 🐛 Dépannage

### Problème: "ModuleNotFoundError"
```bash
# Réinstallez les dépendances
source venv/bin/activate
pip install -r requirements.txt
```

### Problème: "FileNotFoundError: calls_export.json"
```bash
# Régénérez la base de données
python3 generate_full_database.py
```

### Problème: "L'environnement virtuel n'existe pas"
```bash
# Relancez l'installation
./install.sh
```

## 📊 Format des Données

### Structure JSON (calls_export.json)
```json
{
  "options": [
    {
      "symbol": "SPY",
      "option_type": "call",
      "strike": 100.0,
      "expiration": "2025-11-13",
      "days_to_expiry": 30,
      "premium": 2.27,
      "bid": 2.25,
      "ask": 2.29,
      "volume": 1360,
      "delta": 0.542,
      "gamma": 0.073,
      "theta": -0.061,
      "vega": 0.099,
      "rho": 0.042,
      "iv": 0.18
    }
  ]
}
```

## 🎓 Documentation Complète

Pour plus de détails:
- **QUICK_START.md** - Guide de démarrage rapide
- **STRATEGY_COMPARISON_README.md** - Détails du système de comparaison

## 📄 Licence

Projet propriétaire - BGC Trading

## 🤝 Support

Pour toute question ou problème:
1. Vérifiez la section **Dépannage** ci-dessus
2. Consultez les logs dans le terminal
3. Vérifiez que Python 3.8+ est installé

---

**Version**: 1.0.0  
**Dernière mise à jour**: Octobre 2025  
**Auteur**: BGC Trading Team
