import requests
# from bs4 import BeautifulSoup
from pprint import pprint
import sys
import json


def scrape(debug=False):
    RECENT_URL = "https://www.kexp.org/playlist/"
    URL = "https://api.kexp.org/v2/plays/?limit=40&ordering=-airdate&offset=0"

    response = requests.get(URL)
    response_json = json.loads(response.text)

    tracks = [
        {"track_name": p["song"], "album_name": p["album"], "artist_name": p["artist"]}
        for p in response_json["results"]
        if "song" in p
    ]
    if debug:
        pprint(tracks)

    return tracks
