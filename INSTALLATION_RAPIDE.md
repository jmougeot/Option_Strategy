# 🎯 Installation en Une Commande

## Pour Utilisateurs Non-Techniques

### Installation + Lancement:
```bash
cd ~/Desktop/BGC/Stratégies && ./install.sh && ./run.sh
```

**C'est tout !** En une seule ligne, le projet s'installe et se lance. ✨

---

## Pour Développeurs

### Installation rapide:
```bash
python3 -m venv venv && source venv/bin/activate && pip install streamlit plotly pandas && python3 generate_full_database.py
```

### Lancement:
```bash
source venv/bin/activate && streamlit run app.py
```

---

## Guides Disponibles

- **README.md** - Documentation technique complète
- **GUIDE_NON_TECH.md** - Guide étape par étape pour non-techniciens
- **QUICK_START.md** - Démarrage rapide pour développeurs

---

## Architecture du Projet

```
Local → Python → Streamlit → Navigateur Web
              ↓
         SQLite/JSON (données)
              ↓
         Bloomberg API (futur)
```

**100% Local** - Aucun serveur externe nécessaire ✅

---

## Commandes Essentielles

| Action | Commande |
|--------|----------|
| Installer | `./install.sh` |
| Lancer | `./run.sh` |
| Tester | `python3 test_comparison.py` |
| Générer données | `python3 generate_full_database.py` |
| Ouvrir l'app | http://localhost:8501 |

---

**Made with ❤️ for BGC Trading**
