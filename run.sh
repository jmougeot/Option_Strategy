#!/bin/bash

# ============================================================================
# Script de Lancement Rapide - Options Strategy Analyzer
# ============================================================================
# Lance l'application Streamlit dans l'environnement virtuel
# Usage: ./run.sh
# ============================================================================

cd "$(dirname "$0")"

echo ""
echo " Lancement de l'application..."
echo ""

# Vérifier si l'environnement virtuel existe
if [ ! -d "venv" ]; then
    echo "❌ Environnement virtuel non trouvé!"
    echo "💡 Exécutez d'abord: ./install.sh"
    exit 1
fi

# Activer l'environnement virtuel
source venv/bin/activate

# Ajouter src/ au PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"


streamlit run src/myproject/app.py
