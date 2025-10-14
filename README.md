# 🎯 Guide d'Installation depuis GitHub - Pour Débutants Absolus

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

## 💻 Étape 2: Ouvrir le Terminal (PREMIÈRE FOIS)

### Sur Mac:
1. Appuyez sur `Cmd + Espace` (⌘ + Espace)
2. Une petite barre de recherche apparaît en haut de l'écran
3. Tapez: `Terminal`
4. Appuyez sur `Entrée`
5. ✅ Une fenêtre avec du texte noir/blanc s'ouvre - c'est le Terminal !


### Sur Windows:
1. Ouvrez le dossier `Option_Strategy-main`
2. Dans la barre d'adresse en haut, cliquez dedans
3. Tapez `cmd` et appuyez sur `Entrée`
4. ✅ Une fenêtre noire s'ouvre - c'est le Terminal !

---

## 🚀 Étape 3: Installation Automatique

### Une fois le Terminal ouvert:

**1. Naviguez vers le dossier (si ce n'est pas déjà fait):**

```bash
cd ~/Desktop/Option_Strategy-main
```

> 💡 **Astuce**: Tapez `cd ~/Desktop/Opt` puis appuyez sur `Tab` → le nom complet se complète automatiquement !

**2. Vérifiez que vous êtes au bon endroit:**

```bash
ls
```

> Vous devez voir apparaître: `app.py`, `install.sh`, `README.md`, etc.

**3. Lancez l'installation automatique:**

```bash
./install.sh
```

> ⏱️ L'installation prend 1-2 minutes. Vous verrez:
> - ✅ Python détecté
> - ✅ Environnement virtuel créé
> - ✅ Dépendances installées
> - ✅ Base de données générée

**4. Si vous avez une erreur "Permission denied":**

```bash
chmod +x install.sh run.sh check.sh
./install.sh
```

---

## ▶️ Étape 4: Lancer l'Application

### Chaque fois que vous voulez utiliser l'application:

**Dans le Terminal:**

```bash
cd ~/Desktop/Option_Strategy-main
./run.sh
```

> 🌐 Votre navigateur s'ouvre automatiquement à http://localhost:8501

**Ou en un seul clic:**
1. Allez dans le dossier `Option_Strategy-main`
2. **Double-cliquez** sur `run.sh`
3. Choisissez **"Ouvrir avec Terminal"** ou **"Exécuter"**

---

## 🎮 Étape 5: Utiliser l'Application

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
- Mac: `brew install python3` ou téléchargez sur python.org
- Windows: Téléchargez sur python.org
- Linux: `sudo apt install python3`

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
├── 🔧 install.sh                   ← Installation automatique ⭐
├── 🔧 run.sh                       ← Lancement rapide ⭐
├── 🔧 check.sh                     ← Vérification de l'installation
├── 🔧 git_helper.sh                ← Aide pour Git
│
├── 📋 requirements.txt             ← Dépendances Python
├── 🗄️ calls_export.json           ← Données d'options (généré)
└── 📁 venv/                        ← Environnement virtuel (créé lors de l'install)
```

---

## 🎯 Commandes Essentielles à Retenir

```bash
# 1. Aller dans le dossier
cd ~/Desktop/Option_Strategy-main

# 2. Installer (une seule fois)
./install.sh

# 3. Vérifier l'installation
./check.sh

# 4. Lancer l'application
./run.sh

# 5. Générer de nouvelles données
python3 generate_full_database.py

# 6. Tester en ligne de commande
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
