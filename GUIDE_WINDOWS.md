# 🪟 Guide d'Installation Windows - Options Strategy Analyzer

## ⚡ Installation Ultra-Rapide (Recommandé)

### Étape 1 : Télécharger depuis GitHub
1. Allez sur : https://github.com/jmougeot/Option_Strategy
2. Cliquez sur le bouton **"<> Code"** (en haut à droite)
3. Cliquez sur **"Download ZIP"**
4. Le fichier se télécharge dans votre dossier **Téléchargements**

### Étape 2 : Décompresser
1. Ouvrez votre dossier **Téléchargements**
2. Faites un **clic droit** sur `Option_Strategy-main.zip`
3. Choisissez **"Extraire tout..."**
4. Cliquez sur **"Extraire"**
5. Un dossier `Option_Strategy-main` apparaît

### Étape 3 : Déplacer sur le Bureau (optionnel)
1. **Glissez-déposez** le dossier `Option_Strategy-main` sur votre **Bureau**

### Étape 4 : Installer Python (si pas encore fait)
1. Allez sur : https://www.python.org/downloads/windows/
2. Téléchargez la dernière version (Python 3.12+)
3. **Lancez l'installateur**
4. ⚠️ **TRÈS IMPORTANT** : Cochez **"Add Python to PATH"** en bas !
5. Cliquez sur **"Install Now"**

### Étape 5 : Installer l'Application
1. Ouvrez le dossier `Option_Strategy-main`
2. **Double-cliquez** sur `install.bat`
3. Une fenêtre noire s'ouvre et installe tout automatiquement (1-2 minutes)
4. Attendez le message "INSTALLATION TERMINEE AVEC SUCCES !"
5. Appuyez sur une touche pour fermer

### Étape 6 : Lancer l'Application
1. **Double-cliquez** sur `run.bat`
2. Votre navigateur s'ouvre automatiquement avec l'application ! 🎉

---

## 🛠️ Installation Manuelle (Si les scripts ne fonctionnent pas)

### Option A : Avec PowerShell (Recommandé)

1. **Ouvrir PowerShell dans le dossier :**
   - Ouvrez le dossier `Option_Strategy-main`
   - Maintenez `Shift` et faites un **clic droit** dans le dossier
   - Choisissez **"Ouvrir la fenêtre PowerShell ici"** ou **"Ouvrir dans Windows Terminal"**

2. **Créer l'environnement virtuel :**
```powershell
python -m venv venv
```

3. **Activer l'environnement :**
```powershell
.\venv\Scripts\Activate.ps1
```

> ⚠️ **Si erreur "Execution Policy"** :
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Puis relancez l'activation

4. **Installer les dépendances :**
```powershell
pip install streamlit plotly pandas
```

5. **Générer la base de données :**
```powershell
python generate_full_database.py
```

6. **Lancer l'application :**
```powershell
streamlit run app.py
```

### Option B : Avec l'Invite de Commandes

1. **Ouvrir l'Invite de Commandes :**
   - Ouvrez le dossier `Option_Strategy-main`
   - Cliquez dans la **barre d'adresse** en haut
   - Tapez `cmd` et appuyez sur `Entrée`

2. **Créer l'environnement virtuel :**
```batch
python -m venv venv
```

3. **Activer l'environnement :**
```batch
venv\Scripts\activate.bat
```

4. **Installer les dépendances :**
```batch
pip install streamlit plotly pandas
```

5. **Générer la base de données :**
```batch
python generate_full_database.py
```

6. **Lancer l'application :**
```batch
streamlit run app.py
```

---

## 🎮 Utilisation de l'Application

### Lancement Quotidien

**Méthode 1 - Le Plus Simple :**
1. **Double-cliquez** sur `run.bat`
2. L'application s'ouvre dans votre navigateur

**Méthode 2 - Via PowerShell :**
```powershell
.\venv\Scripts\Activate.ps1
streamlit run app.py
```

**Méthode 3 - Via Invite de Commandes :**
```batch
venv\Scripts\activate.bat
streamlit run app.py
```

### Fermer l'Application

1. Fermez l'onglet du navigateur
2. Dans la fenêtre noire (PowerShell/CMD), appuyez sur `Ctrl + C`
3. Fermez la fenêtre

---

## ❓ Problèmes Courants

### "Python n'est pas reconnu"
**Cause** : Python pas installé ou pas dans le PATH

**Solution** :
1. Réinstallez Python : https://www.python.org/downloads/windows/
2. ⚠️ **Cochez "Add Python to PATH"** !
3. Redémarrez votre ordinateur
4. Testez dans PowerShell : `python --version`

### "pip n'est pas reconnu"
**Solution** :
```powershell
python -m ensurepip --upgrade
python -m pip install --upgrade pip
```

### "streamlit n'est pas reconnu"
**Cause** : Environnement virtuel pas activé

**Solution** :
```powershell
.\venv\Scripts\Activate.ps1
pip install streamlit plotly pandas
```

### "Execution Policy" dans PowerShell
**Cause** : PowerShell bloque l'exécution de scripts

**Solution** :
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### L'application ne s'ouvre pas dans le navigateur
**Solution** :
1. Ouvrez manuellement : http://localhost:8501
2. Si ça ne fonctionne toujours pas, vérifiez que Streamlit est lancé dans la console

### "ModuleNotFoundError"
**Cause** : Dépendances pas installées

**Solution** :
```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Antivirus bloque l'installation
**Solution** :
1. Désactivez temporairement l'antivirus
2. Lancez `install.bat`
3. Réactivez l'antivirus

### Double-clic sur .bat ne fait rien
**Solution** :
1. Clic droit sur `install.bat` ou `run.bat`
2. Choisissez **"Exécuter en tant qu'administrateur"**

---

## 🔄 Mise à Jour

### Méthode Simple
1. Téléchargez la nouvelle version ZIP depuis GitHub
2. Décompressez-la
3. Remplacez l'ancien dossier
4. Double-cliquez sur `install.bat` pour mettre à jour les dépendances

### Méthode Git (Avancée)
```powershell
git pull origin main
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt --upgrade
```

---

## 🎯 Commandes Utiles

```powershell
# Vérifier la version de Python
python --version

# Vérifier que pip fonctionne
pip --version

# Lister les packages installés
pip list

# Activer l'environnement virtuel
.\venv\Scripts\Activate.ps1

# Désactiver l'environnement virtuel
deactivate

# Générer de nouvelles données
python generate_full_database.py

# Lancer les tests
python test_comparison.py

# Nettoyer le cache Python
python -m pip cache purge
```

---

## 📁 Structure des Fichiers Windows

```
Option_Strategy-main/
├── install.bat          ← Double-clic pour installer ⭐
├── run.bat              ← Double-clic pour lancer ⭐
├── app.py               ← Application principale
├── requirements.txt     ← Liste des dépendances
├── venv/                ← Environnement virtuel (créé automatiquement)
│   └── Scripts/
│       ├── activate.bat
│       ├── Activate.ps1
│       └── python.exe
└── ...
```

---

## 🆘 Support

### Si rien ne fonctionne :

1. **Vérifiez Python** :
   ```powershell
   python --version
   ```
   Doit afficher : `Python 3.x.x`

2. **Vérifiez le PATH** :
   - Ouvrez **"Variables d'environnement"** dans Windows
   - Vérifiez que Python est dans le PATH

3. **Réinstallez tout** :
   - Supprimez le dossier `venv`
   - Double-cliquez sur `install.bat`

4. **Consultez les logs** :
   - Les messages d'erreur apparaissent dans la fenêtre noire
   - Prenez une capture d'écran si besoin

---

## 🎉 Vous êtes prêt !

1. ✅ Python installé
2. ✅ Application installée (`install.bat`)
3. ✅ Application lancée (`run.bat`)
4. ✅ Navigateur ouvert automatiquement

**Bon trading ! 📊**

---

**Version**: 1.0.0  
**Dernière mise à jour**: Octobre 2025  
**Projet**: https://github.com/jmougeot/Option_Strategy
