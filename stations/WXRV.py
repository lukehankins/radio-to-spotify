import requests
# from bs4 import BeautifulSoup
from pprint import pprint
import sys
import json


def scrape(debug=False):
    RECENT_URL = "https://theriverboston.com/discover/just-played/"
    URL = "https://api.tunegenie.com/v2/brand/nowplaying/?apiid=m2g_bar&b=wxrv&count=100"

    response = requests.get(URL)
    response_json = json.loads(response.text)

    tracks = [
        {"track_name": p["song"], "artist_name": p["artist"]}
        for p in response_json
    ]

    if debug:
        pprint(tracks)

    return tracks
