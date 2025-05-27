#!/bin/bash
cd /app
export PYTHONPATH=/app
echo "Iniciando load balancer..."
python -m src.domain.load_balancer_proxy
echo "Load balancer finalizado." 