#!/bin/bash

# Database Schema Export Script
# Usage: ./export_schema.sh [username] [password] [database_name] [host] [port]

DB_USER=${1:-root}
DB_PASS=${2:-password}
DB_NAME=${3:-evaluation_platform}
DB_HOST=${4:-localhost}
DB_PORT=${5:-3306}

echo "Exporting database schema from ${DB_NAME}..."
echo "User: ${DB_USER}"
echo "Host: ${DB_HOST}:${DB_PORT}"

# Export schema only (no data)
mysqldump -u "${DB_USER}" -p"${DB_PASS}" -h "${DB_HOST}" -P "${DB_PORT}" \
    --no-data \
    --skip-triggers \
    --skip-lock-tables \
    --single-transaction \
    --routines \
    --events \
    "${DB_NAME}" > schema.sql

if [ $? -eq 0 ]; then
    echo "Schema exported successfully to schema.sql"
    echo "File size: $(du -h schema.sql | cut -f1)"
else
    echo "Export failed. Please check your database connection settings."
    exit 1
fi

