#!/bin/bash

# ============================================================================
# Script Git Helper - Options Strategy Analyzer
# ============================================================================
# Facilite les commandes Git courantes
# Usage: ./git_helper.sh [commit|push|pull|status]
# ============================================================================

REMOTE="origin"
BRANCH="main"

case "$1" in
    commit)
        echo "📝 Commit des changements..."
        git add .
        if [ -z "$2" ]; then
            MESSAGE="Update: $(date '+%Y-%m-%d %H:%M')"
        else
            MESSAGE="$2"
        fi
        git commit -m "$MESSAGE"
        echo "✅ Commit effectué: $MESSAGE"
        ;;
    
    push)
        echo "⬆️  Push vers GitHub..."
        git push -u $REMOTE $BRANCH
        echo "✅ Push effectué!"
        ;;
    
    pull)
        echo "⬇️  Pull depuis GitHub..."
        git pull $REMOTE $BRANCH
        echo "✅ Pull effectué!"
        ;;
    
    status)
        echo "📊 Status Git:"
        git status
        ;;
    
    setup)
        echo "🔧 Configuration Git initiale..."
        git init
        git remote add $REMOTE https://github.com/jmougeot/Option_Strategy.git
        git add .
        git commit -m "Initial commit: Options Strategy Analyzer v1.0"
        git branch -M $BRANCH
        git push -u $REMOTE $BRANCH
        echo "✅ Repository configuré et poussé!"
        ;;
    
    *)
        echo "Usage: ./git_helper.sh [commit|push|pull|status|setup]"
        echo ""
        echo "Commandes:"
        echo "  commit [message]  - Commit tous les changements"
        echo "  push              - Push vers GitHub"
        echo "  pull              - Pull depuis GitHub"
        echo "  status            - Afficher le status"
        echo "  setup             - Configuration initiale complète"
        echo ""
        echo "Exemples:"
        echo "  ./git_helper.sh commit 'Ajout nouvelle fonctionnalité'"
        echo "  ./git_helper.sh push"
        ;;
esac
