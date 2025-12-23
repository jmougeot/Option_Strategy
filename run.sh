#!/bin/bash
# Script de lancement rapide
cd "$(dirname "$0")"
source venv/bin/activate
streamlit run src/app.py
