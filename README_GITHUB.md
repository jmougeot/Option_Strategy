# 📊 Options Strategy Analyzer

<div align="center">

[![GitHub](https://img.shields.io/badge/GitHub-jmougeot%2FOption__Strategy-blue?logo=github)](https://github.com/jmougeot/Option_Strategy)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.0.0-orange)](CHANGELOG.md)

**Outil professionnel d'analyse et de comparaison de stratégies d'options**

[Démarrage Rapide](#-démarrage-rapide) •
[Fonctionnalités](#-fonctionnalités) •
[Documentation](#-documentation) •
[Contribution](#-contribution)

</div>

---

## 🎯 Présentation

Options Strategy Analyzer est un outil web interactif permettant de **comparer automatiquement** les stratégies d'options short volatility. L'application calcule automatiquement les métriques clés, génère des diagrammes P&L, et recommande la meilleure stratégie selon vos critères.

### ✨ Points Forts

- ✅ **Interface Web Intuitive** - Aucune programmation requise
- ✅ **Installation en 1 Clic** - Script automatisé
- ✅ **100% Local** - Aucun serveur externe
- ✅ **8 Stratégies Pré-configurées** - Prêtes à l'emploi
- ✅ **Scoring Automatique** - Ranking intelligent
- ✅ **Graphiques Interactifs** - Visualisations Plotly
- ✅ **Prêt Bloomberg API** - Connecteur intégré

---

## 📥 Démarrage Rapide

### Pour Débutants (Première Fois)

👉 **Consultez le guide complet**: [GUIDE_INSTALLATION_GITHUB.md](GUIDE_INSTALLATION_GITHUB.md)

**Résumé ultra-rapide:**
```bash
# 1. Télécharger le projet (bouton vert "Code" > "Download ZIP")
# 2. Décompresser le ZIP
# 3. Ouvrir le Terminal et taper:
cd ~/Desktop/Option_Strategy-main
./install.sh
./run.sh
```

### Pour Développeurs

```bash
# Cloner le repository
git clone https://github.com/jmougeot/Option_Strategy.git
cd Option_Strategy

# Installer
./install.sh

# Lancer
./run.sh
```

🌐 L'application s'ouvre automatiquement à **http://localhost:8501**

---

## 🎮 Fonctionnalités

### Interface Web (Streamlit)

<details>
<summary><b>📊 Comparaison de Stratégies</b></summary>

- Sélection intuitive des paramètres (prix, expiration)
- Choix de 8 stratégies d'options
- Scoring multicritère personnalisable
- Classement automatique

</details>

<details>
<summary><b>📈 Visualisations Interactives</b></summary>

- Diagrammes P&L à l'expiration
- Points de breakeven marqués
- Zones profitables visualisées
- Comparaison côte-à-côte

</details>

<details>
<summary><b>🎯 Analyse Détaillée</b></summary>

- Métriques financières complètes
- Calcul des Greeks (Delta, Gamma, Theta, Vega, Rho)
- Ratios risque/rendement
- Simulations multi-prix
- Recommandations personnalisées

</details>

### Stratégies Disponibles

| Stratégie | Type | Risque | Jambes |
|-----------|------|--------|--------|
| **Iron Condor** | Neutre | Défini | 4 |
| **Iron Butterfly** | Neutre | Défini | 4 |
| **Short Straddle** | Neutre | Illimité | 2 |
| **Short Strangle** | Neutre | Illimité | 2 |
| **Short Put** | Haussier | Illimité | 1 |
| **Short Call** | Baissier | Illimité | 1 |
| **Bull Put Spread** | Haussier | Défini | 2 |
| **Bear Call Spread** | Baissier | Défini | 2 |

---

## 📚 Documentation

### Guides d'Installation

- 📘 **[README.md](README.md)** - Documentation technique complète
- 🎓 **[GUIDE_INSTALLATION_GITHUB.md](GUIDE_INSTALLATION_GITHUB.md)** - Pour débutants absolus
- 🚀 **[INSTALLATION_RAPIDE.md](INSTALLATION_RAPIDE.md)** - Installation en une ligne
- 📋 **[QUICK_REFERENCE.txt](QUICK_REFERENCE.txt)** - Référence rapide visuelle

### Autres Documents

- 📝 **[CHANGELOG.md](CHANGELOG.md)** - Historique des versions
- 🤝 **[CONTRIBUTING.md](CONTRIBUTING.md)** - Guide de contribution
- 📄 **[LICENSE](LICENSE)** - Licence MIT
- 📊 **[PROJECT_SUMMARY.txt](PROJECT_SUMMARY.txt)** - Vue d'ensemble

---

## 🛠️ Technologies

- **Python 3.8+** - Langage principal
- **Streamlit** - Interface web
- **Plotly** - Visualisations interactives
- **Pandas** - Manipulation de données
- **Dataclasses** - Modélisation orientée objet
- **Black-Scholes** - Calcul des Greeks

---

## 📦 Structure du Projet

```
Option_Strategy/
├── 📄 Documentation
│   ├── README.md
│   ├── GUIDE_INSTALLATION_GITHUB.md
│   ├── CHANGELOG.md
│   └── CONTRIBUTING.md
│
├── 🐍 Code Python
│   ├── app.py                      # Interface Streamlit
│   ├── strategies.py               # Définitions des stratégies
│   ├── strategy_comparison.py      # Moteur de comparaison
│   ├── generate_full_database.py   # Générateur de données
│   └── bloomberg_connector.py      # Connecteur Bloomberg
│
├── 🔧 Scripts Utilitaires
│   ├── install.sh                  # Installation automatique
│   ├── run.sh                      # Lancement rapide
│   ├── check.sh                    # Vérification système
│   └── update.sh                   # Mise à jour depuis GitHub
│
└── 🗄️ Données
    ├── calls_export.json           # Base de données d'options
    └── requirements.txt            # Dépendances Python
```

---

## 🚀 Utilisation

### 1. Lancer l'Application

```bash
./run.sh
```

### 2. Dans l'Interface Web

1. **Définir les Paramètres** (barre latérale gauche)
   - Prix cible (ex: $100)
   - Jours jusqu'à expiration (ex: 30)
   - Stratégies à comparer

2. **Cliquer sur "🚀 COMPARER"**

3. **Analyser les Résultats**
   - Tableau comparatif
   - Diagramme P&L
   - Analyse détaillée de la meilleure stratégie

### 3. Tests en Ligne de Commande

```bash
python3 test_comparison.py
```

### 4. Générer Nouvelles Données

```bash
python3 generate_full_database.py
```

---

## 🔄 Mise à Jour

```bash
./update.sh
```

Ou manuellement:
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Consultez [CONTRIBUTING.md](CONTRIBUTING.md) pour:

- 🐛 Signaler des bugs
- 💡 Proposer des fonctionnalités
- 🔀 Soumettre des Pull Requests
- 📚 Améliorer la documentation

---

## 🗺️ Roadmap

### v1.1.0 (À venir)
- [ ] **Bloomberg Terminal API** - Données en temps réel
- [ ] **Backtesting** - Analyse historique
- [ ] **Alertes** - Notifications automatiques
- [ ] **Export Excel/PDF** - Rapports générés

### v1.2.0 (Futur)
- [ ] Machine Learning - Prédictions intelligentes
- [ ] API REST - Intégration externe
- [ ] Mode Dark - Thème sombre
- [ ] Multi-langues - Support EN/FR

Voir [CHANGELOG.md](CHANGELOG.md) pour plus de détails.

---

## 📄 Licence

Ce projet est sous licence MIT. Voir [LICENSE](LICENSE) pour plus de détails.

---

## 🙏 Remerciements

- **Streamlit** - Framework web incroyable
- **Plotly** - Visualisations professionnelles
- **Communauté Python** - Écosystème riche

---

## 📞 Support

- 📧 **Email**: [Votre email]
- 🐛 **Issues**: [GitHub Issues](https://github.com/jmougeot/Option_Strategy/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/jmougeot/Option_Strategy/discussions)

---

<div align="center">

**⭐ Si ce projet vous aide, n'hésitez pas à lui donner une étoile !**

Made with ❤️ by [Jacques Mougeot](https://github.com/jmougeot) | BGC Trading

</div>
