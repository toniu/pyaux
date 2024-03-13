import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
from dotenv import load_dotenv
import random

load_dotenv()

def authenticate_spotify():
    """
    Authenticate with the Spotify API using client credentials obtained from environment variables.
    Returns a Spotify client object.
    """
    print('Authenticating Spotify API...')
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
    return sp

def fetch_playlist_tracks(playlist_url):
    """
    Fetch detailed information about tracks in a Spotify playlist using the provided URL.
    Returns a list of dictionaries, each containing track information.
    """
    print('Fetching playlist information...')
    sp = authenticate_spotify()
    playlist_id = playlist_url.split('?')[0].split('/')[-1]  # Split using '?' and extract first part
    track_info = []

    results = sp.playlist_tracks(playlist_id)
    for item in results['items']:
        track = item['track']
        release_date = track['album']['release_date'] if 'release_date' in track['album'] else None
        release_year = int(release_date.split('-')[0]) if release_date else None
        track_info.append({
            'name': track['name'],
            'artists': [artist['name'] for artist in track['artists']],
            'popularity': track['popularity'],
            'release_year': release_year,
            # Add more attributes as needed (e.g., genres)
        })

    return track_info

def get_artist_genres(artist_name, sp):
    results = sp.search(q='artist:' + artist_name, type='artist')
    if results['artists']['items']:
        return results['artists']['items'][0]['genres']
    else:
        return []

def calculate_track_ratings(track_info):
    """
    Calculate ratings for each track based on artist diversity, popularity, and playlist length.
    Returns the track_info list with added rating information.
    """
    print('Calculating rating based on playlist information...')
    ARTIST_WEIGHT = 0.2
    GENRES_WEIGHT = 0.3
    POPULARITY_WEIGHT = 0.25
    LENGTH_WEIGHT = 0.25

    sp = authenticate_spotify()

    for track in track_info:
        artist_rating = 1 / len(set(track['artists']))

        genres_count = 0
        for artist in track['artists']:
            genres = get_artist_genres(artist, sp)
            if genres:
                genres_count += len(genres)
        if genres_count:
            genres_rating = 1 / genres_count
        else:
            genres_rating = 0

        popularity_rating = track['popularity'] / 100
        length_rating = len(track_info) / 50

        overall_rating = (ARTIST_WEIGHT * artist_rating) + (GENRES_WEIGHT * genres_rating) + \
                         (POPULARITY_WEIGHT * popularity_rating) + (LENGTH_WEIGHT * length_rating)

        track['artist_rating'] = artist_rating
        track['genres_rating'] = genres_rating
        track['popularity_rating'] = popularity_rating
        track['length_rating'] = length_rating
        track['overall_rating'] = overall_rating

    return track_info

def display_track_ratings(track_info):
    """
    Display ratings for each track.
    """
    for i, track in enumerate(track_info, 1):
        print(f"Track {i}:")
        print("Name:", track['name'])
        print("Artists:", ", ".join(track['artists']))
        print("Artist Rating:", track['artist_rating'])
        print("Genres Rating:", track['genres_rating'])
        print("Popularity Rating:", track['popularity_rating'])
        print("Length Rating:", track['length_rating'])
        print("Overall Rating:", track['overall_rating'])
        print()

def calculate_overall_rating(track_info):
    """
    Calculate the overall rating of the playlist based on the ratings of individual tracks.
    Returns the overall rating.
    """
    total_tracks = len(track_info)
    overall_rating = 0

    for track in track_info:
        overall_rating += track['overall_rating']

    overall_rating /= total_tracks
    return overall_rating

def generate_recommendations(track_info, sp, num_recommendations=10, num_artists_sample=10):
    """
    Generate recommendations for additional tracks to enhance the playlist.
    Returns a list of recommended track dictionaries.
    """
    recommendations = []

    # Collect a random sample of artists from existing tracks
    existing_artists = [track['artists'] for track in track_info]
    existing_artists = random.sample(existing_artists, min(len(existing_artists), num_artists_sample))
    existing_artists = set(artist for sublist in existing_artists for artist in sublist)  # Flatten the list

    # Collect genres from existing tracks
    existing_genres = set()
    for track in track_info:
        for artist in track['artists']:
            existing_genres.update(get_artist_genres(artist, sp))

    # Track albums already included in recommendations
    included_albums = set()

    # Find similar tracks based on shared artists or genres
    for artist in existing_artists:
        # Search for tracks by the artist
        results = sp.search(q='artist:' + artist, type='track', limit=num_recommendations)
        for item in results['tracks']['items']:
            try:
                # Check if the album and release_date keys exist
                if 'album' in item and 'release_date' in item['album']:
                    release_date = item['album']['release_date']
                    release_year = int(release_date.split('-')[0])
                    # Filter out tracks released after the latest track in the playlist
                    if release_year < max(track['release_year'] for track in track_info):
                        continue
                else:
                    # Skip if release_date is missing
                    continue
            except KeyError:
                # Skip if 'album' or 'release_date' keys are missing
                continue
            
            # Filter out tracks already in the playlist
            if item['name'] in [t['name'] for t in track_info]:
                continue

            # Filter out tracks from albums already included in recommendations
            if item['album']['name'] in included_albums:
                continue
            
            # Collect genres of the recommended track
            recommended_genres = set()
            for artist in item['artists']:
                recommended_genres.update(get_artist_genres(artist['name'], sp))

            # Calculate the similarity score based on shared genres
            genre_similarity = len(existing_genres.intersection(recommended_genres)) / len(existing_genres.union(recommended_genres))

            recommendations.append({
                'name': item['name'],
                'artists': [artist['name'] for artist in item['artists']],
                'popularity': item['popularity'],
                'album': item['album']['name'],
                'release_year': release_year,
                'genre_similarity': genre_similarity,
                # Add more attributes as needed
            })

            # Add the album to the set of included albums
            included_albums.add(item['album']['name'])

    # Sort recommendations by popularity, genre similarity, artist diversity, and album diversity
    recommendations.sort(key=lambda x: (0.7 * x['popularity'] + 0.3 * x['genre_similarity'] - 0.2 * len(set(x['artists'])) - 0.1 * len(included_albums)), reverse=True)

    return recommendations[:num_recommendations]


# Main
if __name__ == "__main__":
    playlist_url = 'https://open.spotify.com/playlist/0EWM6YBLBxCW0WIgnB0izA?si=d19d1e0f1f374593'
    track_info = fetch_playlist_tracks(playlist_url)
    track_info = calculate_track_ratings(track_info)
    overall_rating = calculate_overall_rating(track_info)

    print("Overall Playlist Rating:", overall_rating)

    sp = authenticate_spotify()
    recommendations = generate_recommendations(track_info, sp)
    print("\nRecommendations:")
    for i, track in enumerate(recommendations, 1):
        print(f"{i}. {track['name']} - {', '.join(track['artists'])} (Popularity: {track['popularity']}, Genre Similarity: {track['genre_similarity']:.2f})")