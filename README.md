# 🎯 Guide d'Installation depuis GitHub - Pour Débutants Absolus

> 💡 **Installation Rapide** :
> - **Windows** : Double-cliquez sur `install.bat` puis `run.bat`
> - **Mac/Linux** : Exécutez `./install.sh` puis `./run.sh` dans le Terminal

---

## 📥 Étape 1: Télécharger le Projet

### Option A: Télécharger le ZIP (le plus simple)
1. Allez sur: https://github.com/jmougeot/Option_Strategy
2. Cliquez sur le bouton vert **"Code"**
3. Cliquez sur **"Download ZIP"**
4. Le fichier `Option_Strategy-main.zip` se télécharge
5. **Double-cliquez** sur le fichier ZIP pour le décompresser
6. Un dossier `Option_Strategy-main` apparaît
7. **Glissez ce dossier** sur votre Bureau (Desktop)

### Option B: Utiliser Git (si vous connaissez)
```bash
cd ~/Desktop
git clone https://github.com/jmougeot/Option_Strategy.git
```

---

## � Étape 2: Installation Automatique

### 💻 Sur Windows (Le Plus Simple)

**Installation en 1 Double-Clic :**
1. Allez dans le dossier `Option_Strategy-main`
2. **Double-cliquez** sur `install.bat`
3. Une fenêtre noire s'ouvre et installe tout automatiquement (1-2 minutes)
4. ✅ Installation terminée !

**Lancement en 1 Double-Clic :**
1. **Double-cliquez** sur `run.bat`
2. Votre navigateur s'ouvre automatiquement avec l'application !

> 💡 **Prérequis Windows** : Python 3 doit être installé
> - Téléchargez : https://www.python.org/downloads/windows/
> - ⚠️ **IMPORTANT** : Cochez "Add Python to PATH" lors de l'installation !
> 
> 📘 **Guide détaillé Windows** : [GUIDE_WINDOWS.md](GUIDE_WINDOWS.md)

---

### 🍎 Sur Mac/Linux

**Installation en 1 Commande :**

1. Ouvrez le **Terminal** (`Cmd + Espace`, tapez "Terminal")
2. Naviguez vers le dossier :
```bash
cd ~/Desktop/Option_Strategy-main
```

3. Lancez l'installation :
```bash
./install.sh
```

> ⏱️ L'installation prend 1-2 minutes. Vous verrez:
> - ✅ Python détecté
> - ✅ Environnement virtuel créé
> - ✅ Dépendances installées
> - ✅ Base de données générée

4. Si erreur "Permission denied" :
```bash
chmod +x install.sh run.sh check.sh
./install.sh
```

**Lancement :**
```bash
./run.sh
```

> 🌐 Votre navigateur s'ouvre automatiquement à http://localhost:8501

---

## 🎮 Étape 3: Utiliser l'Application

### Interface Web - Aucune Programmation !

#### Dans la barre latérale gauche (sidebar):

1. **📂 Source de Données**
   - Laissez sur "JSON Local" (Bloomberg API viendra plus tard)

2. **💹 Paramètres de Marché**
   - **Prix Cible**: Le prix actuel de l'actif (ex: `100`)
   - **Jours jusqu'à l'Expiration**: L'horizon temporel (ex: `30`)

3. **🎯 Stratégies à Comparer**
   - Cochez les stratégies que vous voulez analyser
   - Par défaut: Iron Condor, Iron Butterfly, Short Strangle, Short Straddle

4. **⚖️ Pondération du Score** (optionnel)
   - Cliquez sur "Personnaliser les poids" pour ajuster
   - Par défaut: les poids sont équilibrés

5. **🚀 Cliquez sur le gros bouton bleu "COMPARER"**

#### Résultats affichés:

**📊 Onglet "Vue d'Ensemble":**
- Tableau comparatif de toutes les stratégies
- Graphique de comparaison des scores
- Meilleure stratégie mise en évidence

**📈 Onglet "Diagramme P&L":**
- Graphique interactif des profits/pertes
- Points de breakeven marqués
- Ligne de prix cible

**🔍 Onglet "Analyse Détaillée":**
- Analyse complète de la stratégie gagnante
- Métriques financières détaillées
- Recommandations personnalisées
- Simulation à différents prix

**📋 Onglet "Données Brutes":**
- Toutes les données au format JSON
- Pour analyse approfondie

---

## ❓ Questions Fréquentes

### "Je ne trouve pas le Terminal"
➡️ Suivez la section **Étape 2** ci-dessus en détail

### "J'ai téléchargé mais je ne vois pas install.sh"
➡️ Vérifiez que vous avez bien **décompressé** le fichier ZIP
➡️ Sur Mac: Double-cliquez sur `Option_Strategy-main.zip`

### "L'installation échoue avec 'command not found'"
➡️ Python 3 n'est pas installé. Installez-le:
- **Mac**: `brew install python3` ou téléchargez sur python.org
- **Windows**: Téléchargez sur python.org (⚠️ Cochez "Add Python to PATH" !)
- **Linux**: `sudo apt install python3`

### "Sur Windows: Python n'est pas reconnu"
➡️ Python n'est pas installé ou pas dans le PATH
➡️ Réinstallez Python depuis https://www.python.org/downloads/windows/
➡️ ⚠️ **COCHEZ "Add Python to PATH"** lors de l'installation !

### "Sur Windows: L'installation échoue"
➡️ Vérifiez que vous avez les droits d'administrateur
➡️ Désactivez temporairement l'antivirus si nécessaire
➡️ Utilisez PowerShell au lieu de l'invite de commande

### "Rien ne se passe quand je double-clique sur run.sh"
➡️ Utilisez le Terminal à la place (Étape 4 ci-dessus)

### "L'application ne s'ouvre pas dans le navigateur"
➡️ Ouvrez manuellement: http://localhost:8501
➡️ Si ça ne marche toujours pas, vérifiez que Streamlit est bien lancé dans le Terminal

### "Comment fermer l'application ?"
➡️ Fermez l'onglet du navigateur
➡️ Dans le Terminal, appuyez sur `Ctrl + C` (ou `Cmd + C` sur Mac)

### "Je veux mettre à jour le projet depuis GitHub"
➡️ Téléchargez à nouveau le ZIP et écrasez l'ancien dossier
➡️ Ou utilisez Git: `git pull origin main`

---

## 🔄 Mise à Jour du Projet

Si une nouvelle version est disponible sur GitHub:

### Méthode Simple (ZIP):
1. Téléchargez le nouveau ZIP
2. Décompressez-le
3. Remplacez l'ancien dossier
4. Relancez `./install.sh` (pour mettre à jour les dépendances si nécessaire)

### Méthode Git (Avancée):
```bash
cd ~/Desktop/Option_Strategy-main
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

---

## 📚 Structure du Projet Téléchargé

```
Option_Strategy-main/
├── 📄 README.md                    ← Documentation complète
├── 📄 GUIDE_NON_TECH.md            ← Ce guide
├── 📄 INSTALLATION_RAPIDE.md       ← Installation en une ligne
├── 📄 QUICK_REFERENCE.txt          ← Référence rapide
├── 📄 PROJECT_SUMMARY.txt          ← Résumé du projet
│
├── 🐍 app.py                       ← Interface web (NE PAS MODIFIER)
├── 🐍 strategies.py                ← Stratégies d'options
├── 🐍 strategy_comparison.py       ← Moteur de comparaison
├── 🐍 generate_full_database.py    ← Générateur de données
├── 🐍 bloomberg_connector.py       ← Connecteur Bloomberg (futur)
│
├── 🔧 install.sh / install.bat     ← Installation automatique ⭐
├── 🔧 run.sh / run.bat             ← Lancement rapide ⭐
├── 🔧 check.sh                     ← Vérification (Mac/Linux)
├── 🔧 update.sh                    ← Mise à jour depuis GitHub
│
├── 📋 requirements.txt             ← Dépendances Python
├── 🗄️ calls_export.json           ← Données d'options (généré)
└── 📁 venv/                        ← Environnement virtuel (créé lors de l'install)
```

---

## 🎯 Commandes Essentielles

### 💻 Windows
```batch
REM Installation (double-clic sur install.bat)
install.bat

REM Lancement (double-clic sur run.bat)
run.bat

REM Générer nouvelles données
python generate_full_database.py

REM Tester en ligne de commande
python test_comparison.py
```

### 🍎 Mac/Linux
```bash
# Installation
./install.sh

# Lancement
./run.sh

# Vérification
./check.sh

# Mise à jour depuis GitHub
./update.sh

# Générer nouvelles données
python3 generate_full_database.py

# Tester en ligne de commande
python3 test_comparison.py
```

---

## 🆘 Besoin d'Aide ?

1. **Vérifiez l'installation**: `./check.sh`
2. **Consultez la documentation**: 
   - `README.md` - Documentation technique
   - `QUICK_REFERENCE.txt` - Référence rapide
   - `PROJECT_SUMMARY.txt` - Vue d'ensemble
3. **Réinstallez**: `./install.sh`
4. **Logs**: Regardez les messages dans le Terminal

---

## 🎉 Vous êtes prêt !

1. ✅ Projet téléchargé
2. ✅ Terminal ouvert
3. ✅ Installation lancée
4. ✅ Application fonctionnelle

**Lancez maintenant**: `./run.sh` et commencez à analyser vos stratégies d'options ! 🚀

---

**Guide créé pour**: Utilisateurs sans expérience Terminal/Git  
**Version**: 1.0.0  
**Date**: Octobre 2025  
**Projet**: https://github.com/jmougeot/Option_Strategy
