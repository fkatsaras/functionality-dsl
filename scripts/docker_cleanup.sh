#!/bin/bash
set -e

PROJECT_NAME="thesis"

echo "Cleaning up previous generated app..."

# Stop and remove all thesis containers and volumes
if [ -d "generated" ]; then
  cd generated
  docker compose -p "$PROJECT_NAME" down -v 2>/dev/null || true
  cd ..
fi

# Remove any orphaned thesis_* volumes
docker volume ls --format '{{.Name}}' | grep "^${PROJECT_NAME}_" | xargs -r docker volume rm 2>/dev/null || true

# Remove generated_* volumes (pgadmin data, db data, etc. from named generated projects)
docker volume ls --format '{{.Name}}' | grep "^generated" | xargs -r docker volume rm 2>/dev/null || true

# Remove anonymous volumes (hash-only names, 64 hex chars)
docker volume ls --format '{{.Name}}' | grep -E '^[a-f0-9]{64}$' | xargs -r docker volume rm 2>/dev/null || true

# Remove thesis networks
docker network ls --format '{{.Name}}' | grep "^${PROJECT_NAME}_" | xargs -r docker network rm 2>/dev/null || true

# Remove all thesis-* images (generated app images)
docker images --format '{{.Repository}}:{{.Tag}}\t{{.ID}}' | grep "^thesis-" | awk '{print $2}' | xargs -r docker rmi -f 2>/dev/null || true

# Clean up generated directory
if [ -d "generated" ]; then
  rm -rf generated
fi

echo "✓ Cleanup complete"
