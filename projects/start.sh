#!/bin/bash
# B2B Customer Growth System - Quick Start Script

set -e

echo "=== B2B Customer Growth System ==="
echo ""

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Error: Docker Compose is not installed."
    exit 1
fi

# Setup environment file
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "IMPORTANT: Edit .env file and add your API keys before starting!"
    echo "  - SERPAPI_KEY: Get from https://serpapi.com"
    echo ""
    read -p "Press Enter after editing .env to continue (or Ctrl+C to abort)..."
fi

# Start services
echo ""
echo "Starting services..."
docker compose up -d db redis
echo "Waiting for database..."
sleep 5

docker compose up -d backend
echo "Waiting for backend..."
sleep 3

docker compose up -d frontend
echo ""
echo "=== Services Started ==="
echo ""
echo "Frontend:  http://localhost:3000"
echo "Backend:   http://localhost:8000"
echo "API Docs:  http://localhost:8000/docs"
echo "Database:  localhost:5432"
echo "Redis:     localhost:6379"
echo ""
echo "To start background worker:"
echo "  docker compose --profile worker up -d worker"
echo ""
echo "To stop all services:"
echo "  docker compose down"
echo ""
echo "To view logs:"
echo "  docker compose logs -f"
