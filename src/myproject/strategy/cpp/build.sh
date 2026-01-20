#!/bin/bash
# Script de compilation du module C++

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"

echo "🔨 Compilation du module C++ strategy_metrics_cpp..."

# Créer le répertoire build
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configurer avec CMake
cmake .. -DCMAKE_BUILD_TYPE=Release

# Compiler
cmake --build . --config Release -j$(sysctl -n hw.ncpu 2>/dev/null || nproc)

# Copier le .so dans le répertoire parent
cp strategy_metrics_cpp*.so ../.. 2>/dev/null || \
cp strategy_metrics_cpp*.dylib ../.. 2>/dev/null || \
cp strategy_metrics_cpp*.pyd ../.. 2>/dev/null || true

echo "✅ Compilation terminée!"
echo "📦 Module installé dans: $(dirname "$SCRIPT_DIR")"
