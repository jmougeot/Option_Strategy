#!/bin/bash

# ============================================================================
# Script de Mise à Jour - Options Strategy Analyzer
# ============================================================================
# Met à jour le projet depuis GitHub
# Usage: ./update.sh
# ============================================================================

set -e

echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo "  🔄 MISE À JOUR DU PROJET"
echo "════════════════════════════════════════════════════════════════════════"
echo ""

# Vérifier si Git est installé
if ! command -v git &> /dev/null; then
    echo "❌ Git n'est pas installé"
    echo "💡 Téléchargez la nouvelle version manuellement depuis GitHub"
    echo "   https://github.com/jmougeot/Option_Strategy"
    exit 1
fi

# Vérifier si c'est un repository Git
if [ ! -d ".git" ]; then
    echo "⚠️  Ce dossier n'est pas un repository Git"
    echo ""
    echo "Options:"
    echo "1. Télécharger manuellement depuis GitHub:"
    echo "   https://github.com/jmougeot/Option_Strategy"
    echo ""
    echo "2. Initialiser Git et configurer le remote:"
    echo "   git init"
    echo "   git remote add origin https://github.com/jmougeot/Option_Strategy.git"
    echo "   git fetch origin"
    echo "   git checkout main"
    exit 1
fi

# Sauvegarder les modifications locales
echo "💾 Sauvegarde des modifications locales..."
git stash push -m "Auto-stash before update $(date)"

# Récupérer les dernières modifications
echo "📥 Téléchargement des mises à jour..."
git fetch origin

# Vérifier la branche actuelle
CURRENT_BRANCH=$(git branch --show-current)
echo "📍 Branche actuelle: $CURRENT_BRANCH"

# Mettre à jour
echo "⬆️  Mise à jour en cours..."
if git pull origin "$CURRENT_BRANCH"; then
    echo "✅ Mise à jour réussie!"
else
    echo "❌ Erreur lors de la mise à jour"
    echo "💡 Consultez les logs ci-dessus pour plus de détails"
    exit 1
fi

# Restaurer les modifications locales si nécessaire
if git stash list | grep -q "Auto-stash before update"; then
    echo ""
    echo "💡 Modifications locales sauvegardées détectées"
    echo "   Pour les restaurer: git stash pop"
fi

# Mettre à jour les dépendances Python
echo ""
echo "📦 Mise à jour des dépendances Python..."
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install --upgrade -r requirements.txt --quiet
    echo "✅ Dépendances mises à jour"
else
    echo "⚠️  Environnement virtuel non trouvé"
    echo "💡 Exécutez: ./install.sh"
fi

# Vérifier les nouveaux fichiers
echo ""
echo "📄 Nouveaux fichiers ou modifications:"
git diff --name-status HEAD@{1} HEAD | head -10

echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo "  ✅ MISE À JOUR TERMINÉE!"
echo "════════════════════════════════════════════════════════════════════════"
echo ""
echo "💡 Prochaines étapes:"
echo "   • Vérifiez que tout fonctionne: ./check.sh"
echo "   • Lancez l'application: ./run.sh"
echo "   • Consultez le CHANGELOG pour les nouveautés"
echo ""
echo "📚 Changelog: https://github.com/jmougeot/Option_Strategy/releases"
echo ""
