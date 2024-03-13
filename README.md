# pyaux
[logo](screenshots/pyaux-logo.png)

A Python-coded tool that analyses and rates a user’s Spotify playlist (the input is the public Spotify URL). The input of the user's spotify playlist undergoes a process for this calculation of the rating. Using OAuth2, the Spotify API is authenticated using client credentials obtained from environment variables.

### Fetching playlist tracks
Fetch detailed information about tracks in a Spotify playlist using the provided URL. Returns a list of dictionaries, each containing track information.

### The ranking system
The playlist rating is calculated for each track based on the artist diversity, genre diversity, popularity, and playlist length.
- Better playlists usually has one song per artist. Rating will be reduced if artists repeat so many times.
- Better playlists usually focus on one or few main genres in the playlist. A playlist with too many genres loses the focus of what that playlist is supposed to emulate and can bring down the score.
- Better playlists usually have a mix between popular and non popular songs in order to help listeners discover new music
- Better playlists have a length is 50 tracks at least.

### Recommendations
The program also gives extra recommendations of songs based on the user's playlist preferences to help improve the score of their playlist.

### Console output examples:
???