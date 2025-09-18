#!/bin/bash
set -e

echo "Stopping and removing backend/frontend containers..."
docker ps -a --format '{{.Names}}' | grep -E 'backend|frontend' | xargs -r docker rm -f

echo "Removing backend/frontend images..."
docker images --format '{{.Repository}}:{{.Tag}}' | grep -E 'backend|frontend' | xargs -r docker rmi -f

echo "Deleting generated/ folder..."
rm -rf ../generated

echo "✅ Cleanup complete."
