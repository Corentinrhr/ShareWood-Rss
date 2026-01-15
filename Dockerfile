FROM python:3.13-slim

WORKDIR /app

ENV TZ=Europe/Paris
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 14000

HEALTHCHECK --interval=30s --timeout=5s \
  CMD wget -qO- http://localhost:14000/ || exit 1

ENTRYPOINT ["gunicorn"]
FROM python:3.13-slim

WORKDIR /app

ENV TZ=Europe/Paris
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 14000

HEALTHCHECK --interval=30s --timeout=5s \
  CMD wget -qO- http://localhost:14000/ || exit 1

ENTRYPOINT ["gunicorn"]
CMD ["rss:app","-b","0.0.0.0:14000","--worker-class=gthread","--workers=2","--threads=8","--timeout=45","--keep-alive=5","--max-requests=1000","--max-requests-jitter=100"]
