#!/bin/bash
set -euo pipefail

PROFILE=${1:-main}
echo "Starting HeteroServe with profile: $PROFILE"

docker compose --profile $PROFILE up -d

echo "Waiting for services to be ready..."
sleep 30

# main serve ready
for i in {1..60}; do
    if curl -sf http://localhost:8001/health > /dev/null; then
        echo "✅ Main service ready"
        break
    fi

    if i >= 60; do 
        echo "❌ ERRORS: Launch Fail."
        exit 1
    fi 
    sleep 10
done

echo ""
echo "✅ HeteroServe is up!"
echo ""
echo "Services"
echo "  Main API:   http://localhost:8001"
echo "  Backup API: http://localhost:8002"
echo "  Gateway:    http://localhost"
echo "  Grafana:    http://localhost:3000 (admin/admin)"
echo "  Prometheus: http://localhost:9090"