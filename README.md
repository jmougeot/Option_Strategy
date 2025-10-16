# 🎯 Guide d'Installation depuis GitHub - Pour Débutants Absolus

> 💡 **Installation Rapide** :
> - **Windows** : Double-cliquez sur `install.bat` puis `run.bat`
> - **Mac/Linux** : Exécutez `./install.sh` puis `./run.sh` dans le Terminal

---

##  Étape 1: Télécharger le Projet

1. Allez sur: https://github.com/jmougeot/Option_Strategy
2. Cliquez sur le bouton vert **"Code"**
3. Cliquez sur **"Download ZIP"**
4. Le fichier `Option_Strategy-main.zip` se télécharge
5. **Double-cliquez** sur le fichier ZIP pour le décompresser
6. Un dossier `Option_Strategy-main` apparaît
7. **Glissez ce dossier** ou vous voulez

---

## � Étape 2: Installation Automatique

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

> 🌐 Votre navigateur s'ouvre automatiquement à http://localhost:8501


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
