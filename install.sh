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
    echo "❌ Python 3 n'est pas installé."
    echo ""
    echo "Voulez-vous l'installer automatiquement ? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo ""
        echo "Lancement de l'installation automatique de Python..."
        ./setup_python.sh
        if [ $? -ne 0 ]; then
            echo "❌ L'installation de Python a échoué"
            exit 1
        fi
    else
        echo ""
        echo "Installation annulée."
        echo "Veuillez installer Python 3.8+ manuellement depuis python.org"
        exit 1
    fi
fi

# Vérifier la version de Python
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo "⚠️  Python $PYTHON_VERSION trouvé, mais version 3.8+ requise"
    echo ""
    echo "Voulez-vous installer une version plus récente ? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        ./setup_python.sh
        if [ $? -ne 0 ]; then
            echo "❌ L'installation de Python a échoué"
            exit 1
        fi
    else
        echo "Installation annulée."
        exit 1
    fi
fi

echo "✅ Python $PYTHON_VERSION détecté"
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
pip install -r requirements.txt --quiet
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
streamlit run src/app.py
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
echo "   → Option 2: source venv/bin/activate && streamlit run src/app.py"
echo ""
echo "   L'application s'ouvrira automatiquement dans votre navigateur"
echo "   URL: http://localhost:8501"
echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo ""
