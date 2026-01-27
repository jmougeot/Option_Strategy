# =============================================================================
# Dockerfile pour Options Strategy Analyzer
# =============================================================================
# Build: docker build -t option-strategy .
# Run:   docker run -p 8501:8501 option-strategy
# =============================================================================

FROM python:3.11-slim-bookworm

# Métadonnées
LABEL maintainer="Option Strategy Team"
LABEL version="1.0.0"
LABEL description="Options Strategy Analyzer with Bloomberg API support"

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Installer les dépendances système pour la compilation C++
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    cmake \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root
RUN useradd --create-home --shell /bin/bash appuser

# Répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances d'abord (pour le cache Docker)
COPY requirements.txt .

# Installer les dépendances Python standard
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Installer Bloomberg API (blpapi) depuis le repo officiel
# Note: blpapi nécessite un terminal Bloomberg pour fonctionner
RUN pip install --index-url=https://blpapi.bloomberg.com/repository/releases/python/simple/ blpapi || \
    echo "Warning: blpapi installation failed - Bloomberg features will be disabled"

# Installer pybind11 pour la compilation C++
RUN pip install pybind11

# Copier le code source
COPY src/ ./src/
COPY assets/ ./assets/
COPY settings.json .
COPY pyproject.toml .

# Compiler le module C++ pour les performances
WORKDIR /app/src/myproject/strategy/cpp
RUN pip install . || echo "Warning: C++ module compilation failed - using pure Python fallback"

# Retour au répertoire principal
WORKDIR /app

# Créer le répertoire pour Streamlit config
RUN mkdir -p /app/.streamlit

# Configuration Streamlit pour production
RUN echo '[server]\n\
headless = true\n\
port = 8501\n\
address = "0.0.0.0"\n\
enableCORS = false\n\
enableXsrfProtection = true\n\
\n\
[browser]\n\
gatherUsageStats = false\n\
' > /app/.streamlit/config.toml

# Changer les permissions
RUN chown -R appuser:appuser /app

# Utiliser l'utilisateur non-root
USER appuser

# Exposer le port Streamlit
EXPOSE 8501

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Point d'entrée
ENTRYPOINT ["streamlit", "run", "src/myproject/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
