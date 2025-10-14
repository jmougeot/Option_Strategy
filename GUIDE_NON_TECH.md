# 🎯 Guide d'Installation pour Non-Techniciens

## Ce dont vous avez besoin

1. **Un Mac** (vous l'avez déjà ✅)
2. **5 minutes** de votre temps
3. **Rien d'autre !** Tout se fait automatiquement

---

## Installation en 3 étapes

### Étape 1: Ouvrir le Terminal
1. Appuyez sur `Cmd + Espace` (barre de recherche Spotlight)
2. Tapez "Terminal"
3. Appuyez sur `Entrée`

Une fenêtre noire s'ouvre → c'est parfait ! ✅

### Étape 2: Naviguer vers le projet
Dans le Terminal, copiez-collez cette ligne et appuyez sur `Entrée`:
```bash
cd ~/Desktop/BGC/Stratégies
```

### Étape 3: Lancer l'installation
Copiez-collez cette ligne et appuyez sur `Entrée`:
```bash
./install.sh
```

**C'est tout !** ✨ L'installation se fait automatiquement (1-2 minutes).

---

## Lancer l'Application

### À chaque fois que vous voulez utiliser l'application:

**Option 1 - Le plus simple** (recommandé):
1. Double-cliquez sur le fichier `run.sh` dans le dossier
2. Choisissez "Ouvrir avec Terminal"

**Option 2 - Via le Terminal**:
```bash
cd ~/Desktop/BGC/Stratégies
./run.sh
```

➡️ **Votre navigateur s'ouvre automatiquement** avec l'application !

---

## Utiliser l'Application

### Interface intuitive - Aucune programmation requise !

#### Dans la barre latérale gauche:
1. **Prix Cible**: Le prix actuel de l'actif (ex: 100$)
2. **Jours jusqu'à l'Expiration**: Combien de temps (ex: 30 jours)
3. **Stratégies**: Cochez celles que vous voulez comparer
4. Cliquez sur le gros bouton bleu **"🚀 COMPARER"**

#### Résultats affichés:
- 📊 **Tableau comparatif**: Toutes les stratégies classées
- 📈 **Graphique P&L**: Voir les profits/pertes à l'expiration
- 🏆 **Meilleure stratégie**: Analyse détaillée automatique
- 💡 **Recommandations**: Ce que vous devriez faire

---

## Questions Fréquentes

### ❓ "J'ai un message d'erreur lors de l'installation"
➡️ Fermez le Terminal et recommencez l'Étape 2 et 3

### ❓ "L'application ne s'ouvre pas dans le navigateur"
➡️ Ouvrez manuellement: http://localhost:8501

### ❓ "Comment fermer l'application ?"
➡️ Fermez l'onglet du navigateur + appuyez sur `Ctrl + C` dans le Terminal

### ❓ "Je veux modifier les données (prix, volatilité, etc.)"
➡️ Ouvrez `generate_full_database.py` et modifiez les valeurs en haut du fichier
➡️ Puis lancez: `python3 generate_full_database.py`

### ❓ "Ça ne marche pas du tout"
➡️ Contactez votre équipe IT ou le développeur qui a créé ce projet

---

## Raccourcis Utiles

### Relancer l'application rapidement:
```bash
./run.sh
```

### Générer de nouvelles données:
```bash
python3 generate_full_database.py
```

### Tester en ligne de commande (sans interface):
```bash
python3 test_comparison.py
```

---

## Ce qui se passe "sous le capot" (pour votre culture)

1. **Python**: Le langage de programmation utilisé
2. **Streamlit**: Crée l'interface web automatiquement
3. **Environnement virtuel (venv)**: Garde tout isolé et propre
4. **Scripts automatiques**: Vous n'avez rien à coder !

---

## Vidéo de Démonstration (si disponible)

[AJOUTER LIEN VERS VIDÉO SI CRÉÉE]

---

## Support

**En cas de problème:**
1. Vérifiez que vous êtes dans le bon dossier: `pwd` doit afficher `/Users/votreNom/Desktop/BGC/Stratégies`
2. Vérifiez que les scripts sont exécutables: `ls -l *.sh` doit montrer des `x`
3. Réinstallez: `./install.sh`

**Tout fonctionne ?** Profitez de l'outil ! 🎉

---

**Version simplifiée** - Octobre 2025
