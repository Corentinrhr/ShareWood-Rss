FROM python:3.13-slim

WORKDIR /app

ENV TZ=Europe/Paris

# Installation des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copie du reste des fichiers
COPY . .

# Port d'écoute de l'application
EXPOSE 14000

# Utilisation de gthread pour la stabilité avec requests
ENTRYPOINT [ "gunicorn" ]
CMD [ "rss:app", "-b", "0.0.0.0:14000", "--worker-class=gthread", "--workers=2", "--threads=4", "--timeout=60" ]