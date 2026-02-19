FROM python:3.13-slim

WORKDIR /app

ENV TZ=Europe/Paris
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Utilisateur non-root pour la sécurité conteneur
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser /app
USER appuser

EXPOSE 14000

HEALTHCHECK --interval=30s --timeout=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:14000/health', timeout=3)" || exit 1

ENTRYPOINT ["gunicorn"]
CMD ["rss:app", \
     "-b", "0.0.0.0:14000", \
     "--worker-class=gthread", \
     "--workers=2", \
     "--threads=8", \
     "--timeout=45", \
     "--keep-alive=5", \
     "--max-requests=1000", \
     "--max-requests-jitter=100"]
