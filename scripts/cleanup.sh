#!/bin/bash
set -e

echo "🧹 Stopping and removing backend/frontend containers..."
docker ps -a --format '{{.Names}}' | grep -E 'backend|frontend' | xargs -r docker rm -f

echo "🗑️  Removing backend/frontend images..."
docker images --format '{{.Repository}}:{{.Tag}}' | grep -E 'backend|frontend' | xargs -r docker rmi -f

echo "📁 Deleting generated/ folder..."
rm -rf /mnt/c/Users/FotisKatsaras/Desktop/Personal/AUTh/DIPLOMATIKI/functionality-dsl/generated

# Remove dummy DB container and image
echo "🧱 Removing dummy container/image..."
docker ps -a --format '{{.Names}}' | grep 'dummy' | xargs -r docker rm -f
docker images --format '{{.Repository}}:{{.Tag}}' | grep 'dummy' | xargs -r docker rmi -f

# Remove network if exists and unused
NETWORK_NAME="thesis_fdsl_net"
if docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
  echo "🌐 Removing Docker network: $NETWORK_NAME..."
  docker network rm "$NETWORK_NAME" || echo "⚠️  Network still in use, skipping removal."
else
  echo "ℹ️  Network $NETWORK_NAME not found, skipping."
fi

echo "✅ Cleanup complete."
