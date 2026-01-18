#!/bin/bash
set -e

echo "* Stopping and removing backend/frontend containers..."
docker ps -a --format '{{.Names}}' | grep -E 'backend|frontend' | xargs -r docker rm -f

echo "* Removing backend/frontend images..."
docker images --format '{{.Repository}}:{{.Tag}}' | grep -E 'backend|frontend' | xargs -r docker rmi -f

# Remove dummy DB container and image
echo "* Removing dummy container/image..."
docker ps -a --format '{{.Names}}' | grep 'dummy' | xargs -r docker rm -f
docker images --format '{{.Repository}}:{{.Tag}}' | grep 'dummy' | xargs -r docker rmi -f

# Remove database containers (postgres, db, etc.)
echo "* Removing database containers..."
docker ps -a --format '{{.Names}}' | grep -E '\-db$' | xargs -r docker rm -f

# Remove postgres volumes
echo "* Removing postgres volumes..."
docker volume ls --format '{{.Name}}' | grep -E 'postgres_data' | xargs -r docker volume rm -f

# Remove network if exists
NETWORK_NAME="thesis_fdsl_net"
if docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
  echo "* Removing Docker network: $NETWORK_NAME..."
  docker network rm "$NETWORK_NAME" || echo "!  Network still in use, skipping removal."
else
  echo "! Network $NETWORK_NAME not found, skipping."
fi

# Also try to remove fdsl_net (used by generated docker-compose)
if docker network inspect "fdsl_net" >/dev/null 2>&1; then
  echo "* Removing Docker network: fdsl_net..."
  docker network rm "fdsl_net" || echo "!  Network still in use, skipping removal."
fi

# Clean up any generated project networks (pattern: *_fdsl_net)
echo "* Removing any project fdsl networks..."
docker network ls --format '{{.Name}}' | grep -E '_fdsl_net$' | xargs -r docker network rm 2>/dev/null || true

echo "[OK] Cleanup complete."
