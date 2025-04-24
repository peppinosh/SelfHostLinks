#!/bin/bash

echo "🚀 Starting SelfHostLinks deployment..."

# 1. Verifica se il file .env esiste
if [ ! -f .env ]; then
  echo "❌ .env file is missing. Please create it from .env.example."
  exit 1
fi

# 2. Trova il comando Docker Compose corretto
if command -v docker compose &> /dev/null; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
  COMPOSE_CMD="docker-compose"
else
  echo "❌ Neither 'docker compose' nor 'docker-compose' is available."
  echo "👉 Make sure Docker and Docker Compose are installed and on your PATH."
  exit 1
fi

# 3. Avvia il container
$COMPOSE_CMD up --build -d

# 4. Messaggio finale
if [ $? -eq 0 ]; then
  echo "✅ SelfHostLinks is now running on http://localhost (or your server IP)"
else
  echo "❌ Something went wrong during deployment."
fi
