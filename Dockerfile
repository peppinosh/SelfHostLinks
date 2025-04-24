# Usa una base Python leggera
FROM python:3.11-slim

# Imposta la directory di lavoro
WORKDIR /app

# Copia solo requirements prima (migliora cache Docker)
COPY requirements.txt .

# Installa dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Copia il resto dei file dell'app
COPY . .

# Esponi la porta 5000 (Flask default)
EXPOSE 5000

# Imposta variabili ambiente base (override in docker-compose)
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_ENV=production

# Comando per avviare Flask direttamente
CMD ["flask", "run"]
