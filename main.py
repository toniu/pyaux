import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Authentication
client_id = 'YOUR_CLIENT_ID'
client_secret = 'YOUR_CLIENT_SECRET'

client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# Fetching Playlist Data
playlist_url = 'https://open.spotify.com/playlist/PLAYLIST_ID'
playlist_id = playlist_url.split('/')[-1]
playlist_info = sp.playlist(playlist_id)

# Display Playlist Information
print("Playlist Name:", playlist_info['name'])
print("Owner:", playlist_info['owner']['display_name'])
print("Total Tracks:", playlist_info['tracks']['total'])
