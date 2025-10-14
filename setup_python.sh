#!/bin/bash

# ============================================================================
# Script d'installation automatique de Python 3
# ============================================================================
# Ce script vérifie si Python 3 est installé et l'installe automatiquement
# si nécessaire sur Mac et Linux.
# ============================================================================

set -e  # Arrêter en cas d'erreur

echo "=========================================="
echo "  Vérification de Python 3"
echo "=========================================="
echo ""

# Fonction pour vérifier la version de Python
check_python_version() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
            echo "✅ Python $PYTHON_VERSION est déjà installé"
            return 0
        else
            echo "⚠️  Python $PYTHON_VERSION trouvé, mais version 3.8+ requise"
            return 1
        fi
    else
        echo "❌ Python 3 n'est pas installé"
        return 1
    fi
}

# Fonction pour installer Python sur macOS
install_python_mac() {
    echo ""
    echo "Installation de Python 3 sur macOS..."
    echo ""
    
    # Vérifier si Homebrew est installé
    if ! command -v brew &> /dev/null; then
        echo "📦 Installation de Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Configurer Homebrew dans le PATH
        if [[ $(uname -m) == 'arm64' ]]; then
            # Apple Silicon
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        else
            # Intel
            echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/usr/local/bin/brew shellenv)"
        fi
    fi
    
    echo "📦 Installation de Python 3 via Homebrew..."
    brew install python3
    
    echo "✅ Python 3 installé avec succès!"
}

# Fonction pour installer Python sur Linux
install_python_linux() {
    echo ""
    echo "Installation de Python 3 sur Linux..."
    echo ""
    
    # Détecter la distribution
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    else
        echo "❌ Distribution Linux non reconnue"
        exit 1
    fi
    
    case $OS in
        ubuntu|debian|linuxmint|pop)
            echo "📦 Installation via apt..."
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv python3-dev
            ;;
        fedora|rhel|centos)
            echo "📦 Installation via dnf/yum..."
            if command -v dnf &> /dev/null; then
                sudo dnf install -y python3 python3-pip python3-devel
            else
                sudo yum install -y python3 python3-pip python3-devel
            fi
            ;;
        arch|manjaro)
            echo "📦 Installation via pacman..."
            sudo pacman -S --noconfirm python python-pip
            ;;
        opensuse*)
            echo "📦 Installation via zypper..."
            sudo zypper install -y python3 python3-pip python3-devel
            ;;
        *)
            echo "❌ Distribution Linux non supportée: $OS"
            echo "Veuillez installer Python 3.8+ manuellement depuis python.org"
            exit 1
            ;;
    esac
    
    echo "✅ Python 3 installé avec succès!"
}

# Fonction principale
main() {
    # Vérifier si Python est déjà installé avec la bonne version
    if check_python_version; then
        echo ""
        echo "✅ Aucune installation nécessaire"
        exit 0
    fi
    
    # Détecter le système d'exploitation
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        install_python_mac
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        install_python_linux
    else
        echo "❌ Système d'exploitation non supporté: $OSTYPE"
        echo ""
        echo "Veuillez installer Python 3.8+ manuellement:"
        echo "  • macOS: https://www.python.org/downloads/macos/"
        echo "  • Linux: https://www.python.org/downloads/source/"
        exit 1
    fi
    
    # Vérifier que l'installation a réussi
    echo ""
    echo "Vérification de l'installation..."
    if check_python_version; then
        echo ""
        echo "=========================================="
        echo "  ✅ Installation terminée avec succès!"
        echo "=========================================="
        echo ""
        echo "Vous pouvez maintenant lancer l'installation du projet:"
        echo "  ./install.sh"
        echo ""
    else
        echo ""
        echo "❌ L'installation a échoué"
        echo "Veuillez installer Python manuellement depuis python.org"
        exit 1
    fi
}

# Lancer le script
main
