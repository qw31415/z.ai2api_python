#!/bin/bash

# Render deployment startup script
echo "Starting Z.AI API Server on Render..."

# Set default port if not provided
export PORT=${PORT:-8080}
export LISTEN_PORT=$PORT

# Enable debug logging for deployment
export DEBUG_LOGGING=true

# Enable render deployment mode
export RENDER_DEPLOYMENT=true

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1