import requests
# from bs4 import BeautifulSoup
from pprint import pprint
import sys
import json


def scrape(debug=False):
    RECENT_URL = "https://coast931.com/recently-played/"
    URL = "https://d1b3cgpj1fupp9.cloudfront.net/prt/nowplaying/2/40/6316/nowplaying.js?widget=recentlyplayed"

    response = requests.get(URL)
    response_json = json.loads(response.text[28:-1])

    tracks = [
        {"track_name": p["title"], "artist_name": p["artist"]}
        for p in response_json["performances"]
    ]
    return tracks
