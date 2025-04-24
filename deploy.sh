#!/bin/bash

echo "🚀 Starting SelfHostLinks deployment..."

# Check for .env
if [ ! -f .env ]; then
  echo "❌ .env file is missing. Please create it from .env.example."
  exit 1
fi

# Run docker-compose
docker-compose up --build -d

echo "✅ SelfHostLinks is now running on http://localhost (or your server IP)"
