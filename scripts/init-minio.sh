#!/bin/bash
# MinIO initialization script for development
# This script helps create default buckets in MinIO

set -e

MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:9000}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin}"
MINIO_ALIAS="odin-minio"

echo "Initializing MinIO at ${MINIO_ENDPOINT}..."

# Check if MinIO is running
if ! curl -s "http://${MINIO_ENDPOINT}/minio/health/live" > /dev/null 2>&1; then
    echo "Error: MinIO is not accessible at ${MINIO_ENDPOINT}"
    echo "Make sure MinIO container is running: docker-compose up -d minio"
    exit 1
fi

# Install mc (MinIO Client) if not available
if ! command -v mc &> /dev/null; then
    echo "MinIO Client (mc) is not installed."
    echo "Install it from: https://min.io/docs/minio/linux/reference/minio-mc.html"
    echo "Or use the web console at: http://localhost/minio/"
    exit 1
fi

# Configure MinIO alias
mc alias set "${MINIO_ALIAS}" "http://${MINIO_ENDPOINT}" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}"

# Create default buckets
BUCKETS=("odin-data" "odin-backups" "odin-temp")

for bucket in "${BUCKETS[@]}"; do
    if mc ls "${MINIO_ALIAS}/${bucket}" > /dev/null 2>&1; then
        echo "Bucket '${bucket}' already exists, skipping..."
    else
        echo "Creating bucket '${bucket}'..."
        mc mb "${MINIO_ALIAS}/${bucket}"
        echo "Bucket '${bucket}' created successfully."
    fi
done

echo ""
echo "MinIO initialization complete!"
echo "Access MinIO Console at: http://localhost/minio/"
echo "Access MinIO API at: http://localhost/minio/api/"

