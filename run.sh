#!/bin/bash
# Script de lancement rapide
cd "$(dirname "$0")"
source venv/bin/activate
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
streamlit run src/myproject/app.py
