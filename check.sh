#!/bin/bash

# ============================================================================
# Script de Vérification - Options Strategy Analyzer
# ============================================================================
# Vérifie que toutes les dépendances sont installées correctement
# Usage: ./check.sh
# ============================================================================

echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo "  🔍 VÉRIFICATION DE L'INSTALLATION"
echo "════════════════════════════════════════════════════════════════════════"
echo ""

ERRORS=0

# Vérifier Python
echo "🐍 Python..."
if command -v python3 &> /dev/null; then
    VERSION=$(python3 --version)
    echo "   ✅ $VERSION"
else
    echo "   ❌ Python 3 non installé"
    ERRORS=$((ERRORS + 1))
fi

# Vérifier l'environnement virtuel
echo ""
echo "📦 Environnement virtuel..."
if [ -d "venv" ]; then
    echo "   ✅ venv/ existe"
    
    # Activer et vérifier les modules
    source venv/bin/activate
    
    echo ""
    echo "📚 Modules Python..."
    
    # Streamlit
    if python -c "import streamlit" 2>/dev/null; then
        STREAMLIT_VERSION=$(python -c "import streamlit; print(streamlit.__version__)")
        echo "   ✅ streamlit ($STREAMLIT_VERSION)"
    else
        echo "   ❌ streamlit non installé"
        ERRORS=$((ERRORS + 1))
    fi
    
    # Plotly
    if python -c "import plotly" 2>/dev/null; then
        PLOTLY_VERSION=$(python -c "import plotly; print(plotly.__version__)")
        echo "   ✅ plotly ($PLOTLY_VERSION)"
    else
        echo "   ❌ plotly non installé"
        ERRORS=$((ERRORS + 1))
    fi
    
    # Pandas
    if python -c "import pandas" 2>/dev/null; then
        PANDAS_VERSION=$(python -c "import pandas; print(pandas.__version__)")
        echo "   ✅ pandas ($PANDAS_VERSION)"
    else
        echo "   ❌ pandas non installé"
        ERRORS=$((ERRORS + 1))
    fi
    
else
    echo "   ❌ venv/ n'existe pas"
    ERRORS=$((ERRORS + 1))
fi

# Vérifier les fichiers principaux
echo ""
echo "📄 Fichiers du projet..."

FILES=(
    "app.py"
    "strategies.py"
    "strategy_comparison.py"
    "generate_full_database.py"
    "test_comparison.py"
    "install.sh"
    "run.sh"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file manquant"
        ERRORS=$((ERRORS + 1))
    fi
done

# Vérifier les données
echo ""
echo "🗄️  Données..."
if [ -f "calls_export.json" ]; then
    SIZE=$(du -h calls_export.json | cut -f1)
    echo "   ✅ calls_export.json ($SIZE)"
else
    echo "   ⚠️  calls_export.json manquant (exécutez: python3 generate_full_database.py)"
fi

# Vérifier les permissions des scripts
echo ""
echo "🔐 Permissions..."
if [ -x "install.sh" ]; then
    echo "   ✅ install.sh est exécutable"
else
    echo "   ❌ install.sh n'est pas exécutable (exécutez: chmod +x install.sh)"
    ERRORS=$((ERRORS + 1))
fi

if [ -x "run.sh" ]; then
    echo "   ✅ run.sh est exécutable"
else
    echo "   ❌ run.sh n'est pas exécutable (exécutez: chmod +x run.sh)"
    ERRORS=$((ERRORS + 1))
fi

# Résumé
echo ""
echo "════════════════════════════════════════════════════════════════════════"
if [ $ERRORS -eq 0 ]; then
    echo "  ✅ TOUT EST OK! Le projet est prêt à être utilisé."
    echo "  💡 Lancez l'application avec: ./run.sh"
else
    echo "  ❌ $ERRORS ERREUR(S) DÉTECTÉE(S)"
    echo "  💡 Exécutez: ./install.sh pour corriger les problèmes"
fi
echo "════════════════════════════════════════════════════════════════════════"
echo ""
