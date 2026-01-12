#!/bin/bash

# Streamlit 시작 스크립트 (Cloud Run용)

set -e

echo "Starting Streamlit on port 8080..."

# Streamlit 실행 (포그라운드)
exec streamlit run streamlit_app.py \
    --server.port=8080 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
