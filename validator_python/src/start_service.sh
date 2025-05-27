#!/bin/bash
cd /app
export PYTHONPATH=/app
echo "Iniciando serviço..."
python -m src.domain.service
echo "Serviço finalizado." 