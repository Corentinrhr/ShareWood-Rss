# ShareWood Rss Fetch

Sharewood API to RSS for torrents clients auto-dl

## Install

### Docker :

```bash
docker run -d --name=sharewood -p 14000:14000 corentinrhr/sharewood-rss

```

### Docker-compose :

```yml
---
services:
  sharewood:
    container_name: sharewood
    image: corentinrhr/sharewood-rss
    restart: unless-stopped
    ports:
      - '14000:14000'

```

## Usage :

Replace `https://www.sharewood.tv/api` by `http://YOUR_IP:14000/rss`.

Example:
`http://localhost:14000/rss/YOUR_PASSKEY/last-torrents?category=1`