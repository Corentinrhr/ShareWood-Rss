# ShareWood RSS Fetch

Sharewood API to RSS for torrent clients auto-dl (Sonarr, Radarr, qBittorrent…)

## Install

### Docker

```bash
docker run -d \
  --name=sharewood \
  -p 14000:14000 \
  corentinrhr/sharewood-rss
```

Avec authentification :

```bash
docker run -d \
  --name=sharewood \
  -p 14000:14000 \
  -e RSS_USERNAME=monuser \
  -e RSS_PASSWORD=monmotdepasse \
  corentinrhr/sharewood-rss
```

### Docker Compose

`docker-compose.yml`
```yaml
services:
  sharewood:
    container_name: sharewood
    image: corentinrhr/sharewood-rss
    restart: unless-stopped
    ports:
      - '14000:14000'
    environment:
      # Optionnel
      - RSS_USERNAME=${RSS_USERNAME}
      - RSS_PASSWORD=${RSS_PASSWORD}
```

`.env`
```env
RSS_USERNAME=monuser
RSS_PASSWORD=monmotdepasse
```

## Authentication (optionnelle)

L'authentification HTTP Basic Auth est **désactivée par défaut**.

Pour l'activer, définir les deux variables d'environnement :

| Variable       | Description              |
|----------------|--------------------------|
| `RSS_USERNAME` | Nom d'utilisateur        |
| `RSS_PASSWORD` | Mot de passe             |

Une fois activée, les clients RSS (Sonarr, Radarr…) doivent inclure les credentials dans l'URL :

```
http://monuser:monmotdepasse@localhost:14000/rss/PASSKEY/last-torrents?category=1
```

## Usage

Remplacer `https://www.sharewood.tv/api` par `http://YOUR_IP:14000/rss`.

Exemples :

```
http://localhost:14000/rss/YOUR_PASSKEY/last-torrents
http://localhost:14000/rss/YOUR_PASSKEY/last-torrents?category=1
http://localhost:14000/rss/YOUR_PASSKEY/last-torrents?subcategory=10
http://localhost:14000/rss/YOUR_PASSKEY/search?name=watchmen&subcategory=9
```

### Paramètres disponibles

| Paramètre     | Type   | Description                          |
|---------------|--------|--------------------------------------|
| `category`    | int    | Catégorie principale (1–7)           |
| `subcategory` | int    | Sous-catégorie (9–36)                |
| `limit`       | int    | Nombre de résultats (max 100, déf 50)|
| `name`        | string | Recherche par nom                    |

## Health check

```
GET http://localhost:14000/health
→ 200 ok
```
