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

# Remove any orphaned thesis volumes
docker volume ls --format '{{.Name}}' | grep "^${PROJECT_NAME}_" | xargs -r docker volume rm 2>/dev/null || true

# Remove thesis networks
docker network ls --format '{{.Name}}' | grep "^${PROJECT_NAME}_" | xargs -r docker network rm 2>/dev/null || true

# Remove generated images
docker images --format '{{.Repository}}:{{.Tag}}\t{{.ID}}' | grep -E '(thesis-backend|thesis-frontend)' | awk '{print $2}' | xargs -r docker rmi -f 2>/dev/null || true

# Clean up generated directory
if [ -d "generated" ]; then
  rm -rf generated
fi

echo "✓ Cleanup complete"
