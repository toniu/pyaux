import spotipy, os, random, re, math
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
from collections import Counter

load_dotenv()

def validate_spotify_playlist_url(url):
    """
    Validate the Spotify playlist URL format.
    Returns True if the URL is valid, False otherwise.
    """
    # Regular expression pattern to match a Spotify playlist URL
    SPOTIFY_PLAYLIST_REGEX = r'^https://open\.spotify\.com/playlist/[a-zA-Z0-9_-]+\?si=[a-zA-Z0-9_-]+$'
    """
    Validate the Spotify playlist URL format.
    Returns True if the URL is valid, False otherwise.
    """
    return bool(re.match(SPOTIFY_PLAYLIST_REGEX, url))

def authenticate_spotify():
    """
    Authenticate with the Spotify API using client credentials obtained from environment variables.
    Returns a Spotify client object.
    """
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
    sp = authenticate_spotify()
    playlist_id = playlist_url.split('?')[0].split('/')[-1]  # Split using '?' and extract first part
    playlist = sp.playlist(playlist_id)
    print('\n------------ Playlist Name:', playlist['name'])
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
            'album': track['album']['name'],
            # add list of genres found in particular track to be used for calculating genre cohension
        })

    return track_info

def get_artist_genres(artist_name, sp):
    results = sp.search(q='artist:' + artist_name, type='artist')
    if results['artists']['items']:
        return results['artists']['items'][0]['genres']
    else:
        return []

def display_playlist_tracks(track_info):
    """
    Display information for each track.
    """
    print(f"\n({len(track_info)} tracks) ")
    for i, track in enumerate(track_info, 1):
        print(f"{i}. '{track['name']}' - {', '.join(track['artists'])} ({track['album']})")

def generate_recommendations(track_info, sp, num_recommendations=10, num_artists_sample=10):
    """
    Generate recommendations for additional tracks to enhance the playlist.
    Returns a list of recommended track dictionaries.
    """
    print('Generating recommendations...')
    recommendations = []

    # Collect unique artists from existing tracks
    existing_artists = {artist for track in track_info for artist in track['artists']}

    # Collect genres from existing tracks
    existing_genres = set()
    for track in track_info:
        for artist in track['artists']:
            existing_genres.update(get_artist_genres(artist, sp))

    # Track albums already included in recommendations
    included_albums = set()

    # Iterate over existing artists and find recommendations
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
            if item['name'] in {t['name'] for t in track_info}:
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
    recommendations.sort(key=lambda x: (0.7 * x['popularity'] + 0.3 * x['genre_similarity'] - 0.2 * len(set(x['artists']).intersection(existing_artists)) - 0.1 * len(included_albums)), reverse=True)

    return recommendations[:num_recommendations]

def calculate_playlist_ratings(track_info, genre_mapping):
    """
    Calculate ratings for the entire playlist based on artist diversity, popularity, genre cohesion, and playlist length.
    Returns the overall rating for the playlist.
    """
    # Weights for each rating
    ARTIST_WEIGHT = 0.3
    POPULARITY_WEIGHT = 0.2
    GENRE_WEIGHT = 0.25
    LENGTH_WEIGHT = 0.25

    # Artist diversity rating
    unique_artists = set(artist for track in track_info for artist in track['artists'])
    artist_diversity_rating = min(len(unique_artists) / len(track_info), 1.0)  # Normalize to range between 0 and 1

    # Genre cohesion rating
    genre_cohesion_rating = min(calculate_genre_diversity(track_info, sp, genre_mapping), 1.0)

    # Popularity rating - better playlists have a good mixture of popular and unpopular tracks
    popularity_ratings = [track['popularity'] for track in track_info]
    popularity_rating = min(sum(popularity_ratings) / len(popularity_ratings) / 100, 1.0)  # Normalize to range between 0 and 1

    # Playlist length rating
    playlist_length_rating = min(len(track_info) / 50, 1.0)  # Cap at 1.0 if playlist length exceeds 50 tracks

    # Calculate overall rating
    overall_rating = ((ARTIST_WEIGHT * artist_diversity_rating) + \
                     (POPULARITY_WEIGHT * popularity_rating) + \
                     (GENRE_WEIGHT * genre_cohesion_rating) + \
                     (LENGTH_WEIGHT * playlist_length_rating))

    return {
        'artist_diversity_rating': artist_diversity_rating * 100,
        'popularity_rating': popularity_rating * 100,
        'genre_cohesion_rating': genre_cohesion_rating * 100,
        'playlist_length_rating': playlist_length_rating * 100,
        'overall_rating': overall_rating * 100
    }

def calculate_genre_diversity(track_info, sp, genre_mapping):
    """
    Calculate the diversity rating for parent genres in the playlist.
    Returns a diversity score between 0.0 and 1.0.
    """
    print('Calculating genre diversity...')
    
    all_parent_genres = []
    total_tracks = len(track_info)
    
    # Iterate through each track in the playlist
    for track in track_info:
        for artist in track['artists']:
            artist_genres = get_artist_genres(artist, sp)
            parent_genres = []
            # Check if each artist genre or its keywords match any parent genre
            for genre in artist_genres:
                for parent_genre, keywords in genre_mapping.items():
                    if any(keyword in genre for keyword in keywords):
                        parent_genres.append(parent_genre)
                        break
            if not parent_genres:  # If no match found, assign to Miscellaneous
                parent_genres.append('Miscellaneous')
            all_parent_genres.extend(parent_genres)
    
    # Calculate the frequency of each parent genre
    parent_genre_counts = Counter(all_parent_genres)
    
    # Calculate the entropy
    entropy = 0.0
    for count in parent_genre_counts.values():
        probability = count / total_tracks
        entropy -= probability * math.log(probability, 2)
    
    # Normalize entropy to a score between 0.0 and 1.0
    max_entropy = math.log(len(parent_genre_counts), 2)
    
    # Handle cases where max_entropy is 0
    diversity_score = 1.0 if max_entropy == 0 else 1.0 - (entropy / max_entropy)
    
    return diversity_score

def display_most_popular_genres(track_info, genre_mapping, num_genres=3):
    """
    Display the most popular parent genres of the playlist.
    """
    all_genres = []
    for track in track_info:
        for artist in track['artists']:
            artist_genres = get_artist_genres(artist, sp)
            parent_genres = []
            for genre in artist_genres:
                for parent_genre, keywords in genre_mapping.items():
                    if any(keyword in genre for keyword in keywords):
                        parent_genres.append(parent_genre)
                        break
            if not parent_genres:
                parent_genres.append('Miscellaneous/World')
            all_genres.extend(parent_genres)
    
    genre_counts = Counter(all_genres)
    total_tracks = len(all_genres)
    most_common_genres = genre_counts.most_common(num_genres)
    
    print("\nPopular Genres:")
    for genre, count in most_common_genres:
        percentage = (count / total_tracks) * 100
        print(f"{genre}: {percentage:.2f}%")

# Main
if __name__ == "__main__":
    # Parent genres and their particular key-words
    genre_mapping = {
        'Rap/Hip-Hop': ['rap', 'hip hop', 'trap', 'drill', 'hip-hop'],
        'R&B/Soul': ['r&b', 'soul', 'alternative r&b', 'neo soul'],
        'Pop': ['pop', 'party'],
        'Dance/Electronic': ['dance', 'electronic', 'techno', 'dubstep', 'drum and bass', 'garage', 'house', 'amapiano'],
        'Metal/Rock': ['metal','rock', 'punk', 'metalcore'],
        'Jazz/Blues': ['jazz', 'blues'],
        'Country/Folk': ['country', 'folk', 'worship'],
        'Afrobeats': ['afrobeats', 'reggaeton', 'afroswing', 'afrobeat'],
        'Latin': ['latin', 'reggaeton', 'samba'],
        'Carribbean': ['reggae', 'dancehall','soca'],
        'Gospel': ['christian', 'gospel', 'worship'],
        'Indie/Alternative': ['alternative', 'indie', 'worship'],
        'Instrumental/Classical': ['classical','instrumental', 'percussion', 'lo-fi'],
        'Spoken Word': ['spoken word','spoken', 'word', 'poetry', 'freestyle'],
        'Miscellaneous/World': []  # For genres not identified in other categories
    }

    playlist_url = input("Enter the Spotify playlist URL: ")

    # Validate the input URL
    while not validate_spotify_playlist_url(playlist_url):
        print("Invalid Spotify playlist URL. Please enter a valid URL.")
        playlist_url = input("Enter the Spotify playlist URL: ")

    print('Authenticating Spotify API...')
    sp = authenticate_spotify()
    print('Fetching playlist information...')
    track_info = fetch_playlist_tracks(playlist_url)

    print('Calculating playlist ratings...')
    overall_playlist_rating = calculate_playlist_ratings(track_info, genre_mapping)
    print()

    display_playlist_tracks(track_info)
    display_most_popular_genres(track_info, genre_mapping)
    print()
    print('\n------------ Overall Playlist Ratings:')
    for key, value in overall_playlist_rating.items():
        print(f"{key.replace('_', ' ').title()}: {value:.2f}")

    recommendations = generate_recommendations(track_info, sp)
    print("\n------------ Recommended tracks:")
    for i, track in enumerate(recommendations, 1):
        print(f"{i}. '{track['name']}' - {', '.join(track['artists'])} ({track['album']})")
