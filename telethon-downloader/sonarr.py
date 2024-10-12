from multiprocessing.connection import Client
import select
from arrapi import SonarrAPI

# Set Host URL and API-Key
host_url = 'http://10.10.0.11:8990'
# You can find your API key in Settings > General.
api_key = 'b8d49d87f42447ad9f9eddc8454745b9'
# Instantiate SonarrAPI Object
sonarr = SonarrAPI(host_url, api_key)

class Serie(object):
    def __init__(self, id, path, names, image):
        self.id = id
        self.path = path
        self.names = names
        self.image = image

async def sonarr_search(command, client, usuarios):
    # Search series downloaded
    await tg_send_message("Searching '" + command + "'", client, usuarios)
    search = sonarr.search_series(term=command)
    filtered = list(filter(lambda x: x.id != None , search))
    return filtered;

async def sonarr_get_serie(id):
    # Get serie
    series = sonarr.get_series(series_id=id)
    folder = series.path.replace(series.rootFolderPath,"")
    alternativeTitles = [i.get("title") for i in series._data.get("alternateTitles")]
    image = next(filter(lambda x: "poster" in x.remoteUrl, series.images), None);
    return Serie(id, folder, alternativeTitles, image.remoteUrl);

async def tg_send_message(msg, client, usuarios):
    await client.send_message(usuarios[0], msg)
    return True

async def sonarr_put_serie_tag_uploaded(id):
    series = sonarr.get_series(series_id=id)
    series.edit(tags=["uploaded"])
    return True