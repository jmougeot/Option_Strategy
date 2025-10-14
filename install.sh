#!/bin/bash

# ============================================================================
# Script d'Installation Automatique - Options Strategy Analyzer
# ============================================================================
# Ce script installe tout ce qui est nécessaire pour lancer l'application
# Usage: ./install.sh
# ============================================================================

set -e  # Arrêter en cas d'erreur

echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo "  📊 Installation - Options Strategy Analyzer"
echo "════════════════════════════════════════════════════════════════════════"
echo ""

# Étape 1: Vérifier Python
echo "🔍 Vérification de Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "✅ $PYTHON_VERSION détecté"
echo ""

# Étape 2: Créer l'environnement virtuel
echo "📦 Création de l'environnement virtuel..."
if [ -d "venv" ]; then
    echo "⚠️  L'environnement virtuel existe déjà, utilisation de celui-ci..."
else
    python3 -m venv venv
    echo "✅ Environnement virtuel créé"
fi
echo ""

# Étape 3: Activer l'environnement virtuel
echo "🔌 Activation de l'environnement virtuel..."
source venv/bin/activate
echo "✅ Environnement activé"
echo ""

# Étape 4: Mettre à jour pip
echo "⬆️  Mise à jour de pip..."
pip install --upgrade pip --quiet
echo "✅ pip mis à jour"
echo ""

# Étape 5: Installer les dépendances
echo "📥 Installation des dépendances..."
echo "   • streamlit"
echo "   • plotly"
echo "   • pandas"
pip install streamlit plotly pandas --quiet
echo "✅ Dépendances installées"
echo ""

# Étape 6: Générer la base de données
echo "🗄️  Génération de la base de données d'options..."
if [ -f "generate_full_database.py" ]; then
    python generate_full_database.py > /dev/null
    echo "✅ Base de données générée (calls_export.json)"
else
    echo "⚠️  generate_full_database.py non trouvé, sautant cette étape"
fi
echo ""

# Étape 7: Créer le script de lancement
echo "🚀 Création du script de lancement..."
cat > run.sh << 'EOF'
#!/bin/bash
# Script de lancement rapide
cd "$(dirname "$0")"
source venv/bin/activate
streamlit run app.py
EOF
chmod +x run.sh
echo "✅ Script run.sh créé"
echo ""

# Résumé
echo "════════════════════════════════════════════════════════════════════════"
echo "  ✅ INSTALLATION TERMINÉE AVEC SUCCÈS!"
echo "════════════════════════════════════════════════════════════════════════"
echo ""
echo "📋 Prochaines étapes:"
echo ""
echo "   Pour lancer l'application:"
echo "   → Option 1: ./run.sh"
echo "   → Option 2: source venv/bin/activate && streamlit run app.py"
echo ""
echo "   L'application s'ouvrira automatiquement dans votre navigateur"
echo "   URL: http://localhost:8501"
echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo ""
