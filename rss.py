#!/usr/bin/env python3
# By LimeCat

# http://localhost:5000/rss/<PASSKEY>/last-torrents?category=1&limit=10
# http://localhost:5000/rss/<PASSKEY>/last-torrents?subcategory=6&limit=10
# http://localhost:5000/rss/<PASSKEY>/search?name=watchmen&subcategory=9&limit=10
#!/usr/bin/env python3

from lxml import etree as et
from flask import Flask, request, abort, Response
import requests
import yaml
import humanize
import email.utils
import time

try:
    with open('config.yml', 'r') as ymlfile:
        cfgTitle = yaml.load(ymlfile, Loader=yaml.FullLoader)
        titleDict = cfgTitle.get('title', {})
except FileNotFoundError:
    print("Attention: config.yml non trouvé.")
    titleDict = {}

app = Flask(__name__)

def get_sharewood_data(url, params):
    """Récupère les données API avec un timeout pour éviter de bloquer le worker."""
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de l'appel Sharewood: {e}")
        return []

@app.route('/')
def how_to():
    return (
        '<strong>Exemples :</strong><br>'
        'http://localhost:14000/rss/VOTRE_PASSKEY/last-torrents?category=1&limit=10<br>'
        'http://localhost:14000/rss/VOTRE_PASSKEY/last-torrents?subcategory=6&limit=10<br>'
        'http://localhost:14000/rss/VOTRE_PASSKEY/search?name=watchmen&subcategory=9&limit=10'
    )

@app.route('/rss/<string:passkey>/<string:apiAction>', methods=['GET'])
def return_rss_file(passkey, apiAction):
    
    # Validation basique de la passkey
    if not passkey or len(passkey) != 32:
        return abort(404, description="Passkey invalide ou manquante")

    # Récupération des arguments
    category = request.args.get("category", type=int)
    subcategory = request.args.get("subcategory", type=int)
    limit = request.args.get("limit", 50, type=int)
    name = request.args.get("name", type=str)

    api_params = {}
    current_cat_id = '0' # Titre par défaut

    # Logique des catégories
    if category and 1 <= category <= 7:
        api_params['category'] = category
        current_cat_id = str(category)
    
    if subcategory and 8 < subcategory <= 36:
        api_params['subcategory'] = subcategory
        current_cat_id = str(subcategory)

    # Limite de sécurité
    api_params['limit'] = min(limit, 50)
    
    if name:
        api_params['name'] = name

    # Construction de l'URL cible
    base_url = f"https://www.sharewood.tv/api/{passkey}"
    if apiAction == 'last-torrents':
        url = f"{base_url}/last-torrents"
    elif apiAction == "search" and name:
        url = f"{base_url}/search"
    else:
        return abort(404, description="Action inconnue")

    # Appel API
    torrents = get_sharewood_data(url, api_params)

    # --- Génération du XML RSS ---
    rss = et.Element("rss", version="2.0")
    channel = et.SubElement(rss, "channel")
    
    # Titre du flux
    title_node = et.SubElement(channel, "title")
    if name:
        title_node.text = f"ShareWood Search : {name}"
    else:
        cat_name = titleDict.get(current_cat_id, "Inconnu")
        title_node.text = f"ShareWood RSS : {cat_name}"

    et.SubElement(channel, "description").text = "Flux RSS Sharewood"
    et.SubElement(channel, "link").text = "https://sharewood.tv"
    
    # Date au format standard RFC 822 (Important pour les clients torrent)
    et.SubElement(channel, "lastBuildDate").text = email.utils.formatdate(usegmt=True)
    et.SubElement(channel, "ttl").text = "60"

    for torrent in torrents:
        item = et.SubElement(channel, "item")
        
        # Données sécurisées
        t_id = torrent.get('id')
        t_name = torrent.get('name', 'Sans titre')
        t_slug = torrent.get('slug', 'slug')
        t_size = torrent.get('size', 0)
        t_created = torrent.get('created_at', '')
        
        et.SubElement(item, "title").text = str(t_name)
        
        # Formatage de la taille
        human_size = t_size if isinstance(t_size, str) else humanize.naturalsize(t_size, binary=True)
        
        # Liens
        page_link = f"https://sharewood.tv/torrents/{t_slug}.{t_id}"
        et.SubElement(item, "link").text = page_link
        et.SubElement(item, "guid", isPermaLink="true").text = page_link

        # Description HTML
        desc_html = (
            f"<strong><a href='{page_link}'>{t_name}</a></strong><br/>"
            f"Taille: {human_size}<br/>"
            f"Seeders: {torrent.get('seeders', 0)} | Leechers: {torrent.get('leechers', 0)}<br/>"
            f"Ajouté le: {t_created}"
        )
        description_node = et.SubElement(item, "description")
        description_node.text = et.CDATA(desc_html)

        # Lien de téléchargement (Enclosure)
        dl_url = f"https://www.sharewood.tv/api/{passkey}/{t_id}/download"
        et.SubElement(item, "enclosure", url=dl_url, type="application/x-bittorrent")

    xml_str = et.tostring(rss, pretty_print=True, encoding='utf-8', xml_declaration=True)
    
    return Response(xml_str, mimetype='application/rss+xml')

if __name__ == '__main__':
    app.run(debug=True, port=14000)