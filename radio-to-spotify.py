from importlib import import_module
import spotipy.util as util
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy import Spotify
import sys
import tomllib
from pprint import pprint
from fuzzywuzzy import fuzz, process
import os
import argparse

def list_known_stations():
    """List files in the stations directory"""
    known_stations = [
        f.split(".")[0]
        for f in os.listdir("stations")
        if f.endswith(".py") and f != "__init__.py"
    ]
    return known_stations

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Scrape a radio station and add tracks to a Spotify playlist"
    )
    parser.add_argument(
        "call_letters", nargs="*", help="Call letters of the radio station(s) to scrape.  Use 'all' to scrape all known stations."
    )
    parser.add_argument("--debug", help="Print debug output", action="store_true")
    parser.add_argument("--list_stations", help="List known stations", action="store_true")
    parser.add_argument(
        "--create_playlist",
        help="Create the playlist if it does not exist (default: False)",
        action="store_true",
    )
    parser.add_argument(
        "--playlist_prefix",
        help="Prefix of playlist name to update/create (default: 'radio ')",
        type=str,
        required=False,
        default="radio ",
    )
    args = parser.parse_args()

    # If "all" is specified, use all known stations
    if args.call_letters == ["all"]:
        args.call_letters = known_stations

    # If no call letters are specified, list known stations and exit
    if not args.call_letters:
        print("ERROR: call_letters required.")
        print("Known stations: ")
    if args.list_stations or not args.call_letters:
        for station in known_stations:
            print(f"    {station}")
        sys.exit()

    return args

def get_spotify_credentials():
    """Get Spotify credentials"""

    # Get Spotify credentials
    env = os.environ
    client_id = env["SPOTIFY_CLIENT_ID"]
    client_secret = env["SPOTIFY_CLIENT_SECRET"]
    username = env["SPOTIFY_USERNAME"]
    redirect_uri = "http://localhost:4242/"

    # Log in to Spotify
    scope = "user-library-read user-library-modify playlist-modify-private"
    token = util.prompt_for_user_token(
        username,
        scope,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )

    if token:
        sp = Spotify(auth=token)
    else:
        print(f"Can't get authentication token for {username}")
        sys.exit()

    return (sp, username)

def get_tracks_for_station(call_letters):
    """Scrape a radio station and look up tracks on Spotify"""
   # Scrape the station
    try:
        station = import_module("stations." + call_letters)
    except ModuleNotFoundError:
        print(f"ERROR: error loading station module for {call_letters}")
        sys.exit()
    tracks = station.scrape(debug=args.debug)

    # Look up scraped tracks
    # TODO: include album name in search
    radio_track_list = []
    for track in tracks:
        track_name = track["track_name"]
        artist_name = track["artist_name"]

        results = sp.search(q=f"{track_name} {artist_name} ", limit=5, type="track")
        matched = False
        for result in results["tracks"]["items"]:
            if args.debug:
                print(
                    f"matching for '{track_name}' by {artist_name} against '{result['name']}' by {result['artists'][0]['name']}"
                )
            if (
                fuzz.partial_ratio(
                    artist_name.lower(), result["artists"][0]["name"].lower()
                )
                > 90
                and fuzz.partial_ratio(track_name.lower(), result["name"].lower()) > 90
            ):
                matched = True
                radio_track_list.append(result["id"])
                print(
                    f"matched id: {result['id']}, artist: {result['artists'][0]['name']}, track: '{result['name']}' "
                )
                break
            else:
                if args.debug:
                    print(
                        f"no    {track_name} -> {result['name']} = {fuzz.partial_ratio(track_name.lower(), result['name'].lower())}"
                    )
                    print(
                        f"no    {artist_name} -> {result['artists'][0]['name']} = {fuzz.partial_ratio(artist_name.lower(), result['artists'][0]['name'].lower())}"
                    )

        if not matched:
            print(f"no match for {track_name} by {artist_name}.  Skipping.")
            if args.debug:
                found = [
                    r["name"] + " by " + r["artists"][0]["name"]
                    for r in results["tracks"]["items"]
                ]
                print(f"search results: {found}")
    
    return radio_track_list

def get_playlist(sp, username, playlist_name):
    """Look up a playlist by name"""
    # Look up playlist
    playlists = []
    results = sp.current_user_playlists()
    playlists.extend(results["items"])
    while results["next"]:
        results = sp.next(results)
        playlists.extend(results["items"])

    playlist = [p for p in playlists if p["name"] == playlist_name]
    if len(playlist) > 1:
        print(f"ERROR: unable to find a unitary playlist for {call_letters}.  Found:")
        print(playlist)

    if args.create_playlist and not playlist:
        print(f"creating playlist {playlist_name}")
        result = sp.user_playlist_create(username, playlist_name, public=False)
        if "id" in result:
            playlist = [result]
        else:
            print(f"ERROR: unable to create playlist {playlist_name}")
            pprint(result)

    if playlist:
        playlist_id = playlist[0]["id"]
    else:
        playlist_id = None
        print(f"ERROR: playlist for {call_letters} not found")

    return playlist_id

known_stations = list_known_stations()
args = parse_arguments()
(sp, username) = get_spotify_credentials()

for call_letters in args.call_letters:
    if call_letters not in known_stations:
        print(f"WARNING: station {call_letters} not found, so skipping it.")
        continue

    print(f"Processing station {call_letters}")

    playlist_name = args.playlist_prefix + call_letters

    radio_track_list = get_tracks_for_station(call_letters)

    playlist_id = get_playlist(sp, username, playlist_name)
    if not playlist_id:
        continue

    # Get playlist tracks
    playlist_tracks = []
    result = sp.playlist_items(playlist_id)
    playlist_tracks.extend(result["items"])
    while result["next"]:
        result = sp.next(result)
        playlist_tracks.extend(result["items"])

    # Update playlist
    playlist_track_list = [t["track"]["id"] for t in playlist_tracks]
    tracks_to_add = [t for t in radio_track_list if t not in playlist_track_list]
    if tracks_to_add:
        print(f"adding {len(tracks_to_add)} tracks to playlist '{playlist_name}'")
        response = sp.playlist_add_items(playlist_id, tracks_to_add)
        # TODO: check response
    else:
        print(f"no new tracks to add to playlist '{playlist_name}'")
