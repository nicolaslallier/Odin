#!/bin/bash
# MinIO initialization script for development
# This script helps create default buckets in MinIO

set -e

MINIO_CONTAINER="odin-minio"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin}"
MINIO_ALIAS="odin"

echo "Initializing MinIO..."

# Check if MinIO container is running
if ! docker ps | grep -q "${MINIO_CONTAINER}"; then
    echo "Error: MinIO container is not running"
    echo "Make sure MinIO container is running: docker-compose up -d minio"
    exit 1
fi

echo "✓ MinIO container is running"

# Configure MinIO alias using docker exec
echo "Configuring MinIO alias..."
docker exec "${MINIO_CONTAINER}" mc alias set "${MINIO_ALIAS}" "http://localhost:9000" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" > /dev/null 2>&1 || true

# Create default buckets
BUCKETS=("odin-data" "odin-backups" "odin-temp" "confluence-backups" "confluence-markdown")

for bucket in "${BUCKETS[@]}"; do
    if docker exec "${MINIO_CONTAINER}" mc ls "${MINIO_ALIAS}/${bucket}" > /dev/null 2>&1; then
        echo "  Bucket '${bucket}' already exists"
    else
        echo "  Creating bucket '${bucket}'..."
        docker exec "${MINIO_CONTAINER}" mc mb "${MINIO_ALIAS}/${bucket}"
        echo "  ✓ Bucket '${bucket}' created"
    fi
done

echo ""
echo "✓ MinIO initialization complete!"
echo "  Access MinIO Console at: http://localhost/minio/"
echo "  Username: ${MINIO_ROOT_USER}"
echo "  Password: ${MINIO_ROOT_PASSWORD}"
echo ""

