import csv
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top-k songs from the catalog for the given user profile."""
        prefs = {"genre": user.favorite_genre, "mood": user.favorite_mood,
                 "target_energy": user.target_energy}
        song_dicts = [_song_to_dict(s) for s in self.songs]
        results = recommend_songs(prefs, song_dicts, k=k)
        id_to_song = {s.id: s for s in self.songs}
        return [id_to_song[r[0]["id"]] for r in results]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a human-readable string explaining why a song was recommended."""
        prefs = {"genre": user.favorite_genre, "mood": user.favorite_mood,
                 "target_energy": user.target_energy}
        _, reasons = score_song(prefs, _song_to_dict(song))
        return " | ".join(reasons) if reasons else "no strong matches"

def _song_to_dict(song: "Song") -> Dict:
    return {
        "id": song.id, "title": song.title, "artist": song.artist,
        "genre": song.genre, "mood": song.mood, "energy": song.energy,
        "tempo_bpm": song.tempo_bpm, "valence": song.valence,
        "danceability": song.danceability, "acousticness": song.acousticness,
    }


def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py

    Numeric fields (id, energy, tempo_bpm, valence, danceability, acousticness)
    are cast to their proper types so arithmetic works downstream.
    """
    int_fields   = {"id"}
    float_fields = {"energy", "tempo_bpm", "valence", "danceability", "acousticness"}

    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for field in int_fields:
                row[field] = int(row[field])
            for field in float_fields:
                row[field] = float(row[field])
            songs.append(row)

    logger.info("Loaded %d songs from %s", len(songs), csv_path)
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.
    Required by recommend_songs() and src/main.py

    Algorithm Recipe (max 6.0 points):
      +2.0        genre match      — exact string comparison
      +1.0        mood match       — exact string comparison
      +0.0–1.5    energy proximity — 1.5 * (1 - |song.energy - target_energy|)
      +0.0–1.0    valence proximity— 1.0 * (1 - |song.valence - target_valence|)
      +0.0–0.5    tempo proximity  — 0.5 * (1 - |normalized tempo diff|)
                  tempo is normalized over [60, 180] BPM before comparison

    Returns:
        score   — float in range [0.0, 6.0]
        reasons — list of strings explaining each point contribution
    """
    score = 0.0
    reasons = []

    # --- Genre: +1.0 for exact match (EXPERIMENT: halved from 2.0) ---
    if song.get("genre") == user_prefs.get("genre"):
        score += 1.0
        reasons.append(f"genre match '{song['genre']}' (+1.0)")
    else:
        reasons.append(f"genre mismatch: '{song.get('genre')}' vs '{user_prefs.get('genre')}' (+0.0)")

    # --- Mood: +1.0 for exact match ---
    if song.get("mood") == user_prefs.get("mood"):
        score += 1.0
        reasons.append(f"mood match '{song['mood']}' (+1.0)")
    else:
        reasons.append(f"mood mismatch: '{song.get('mood')}' vs '{user_prefs.get('mood')}' (+0.0)")

    # --- Energy proximity: up to +3.0 (EXPERIMENT: doubled from 1.5) ---
    if "target_energy" in user_prefs:
        energy_sim = 1.0 - abs(float(song["energy"]) - float(user_prefs["target_energy"]))
        energy_points = round(3.0 * energy_sim, 2)
        score += energy_points
        reasons.append(f"energy {song['energy']} vs target {user_prefs['target_energy']} (+{energy_points}/3.00)")

    # --- Valence proximity: up to +1.0 ---
    if "target_valence" in user_prefs:
        valence_sim = 1.0 - abs(float(song["valence"]) - float(user_prefs["target_valence"]))
        valence_points = round(1.0 * valence_sim, 2)
        score += valence_points
        reasons.append(f"valence {song['valence']} vs target {user_prefs['target_valence']} (+{valence_points}/1.00)")

    # --- Tempo proximity: up to +0.5 ---
    if "target_tempo" in user_prefs:
        BPM_MIN, BPM_MAX = 60, 180
        song_norm = (float(song["tempo_bpm"]) - BPM_MIN) / (BPM_MAX - BPM_MIN)
        user_norm = (float(user_prefs["target_tempo"]) - BPM_MIN) / (BPM_MAX - BPM_MIN)
        tempo_sim = 1.0 - abs(song_norm - user_norm)
        tempo_points = round(0.5 * tempo_sim, 2)
        score += tempo_points
        reasons.append(f"tempo {song['tempo_bpm']} BPM vs target {user_prefs['target_tempo']} BPM (+{tempo_points}/0.50)")

    return round(score, 2), reasons


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py

    Pipeline:
      1. LOOP   — iterate over every song in the catalog
      2. SCORE  — call score_song() to judge each song against user_prefs
      3. RANK   — sort all (song, score, explanation) tuples by score descending
      4. SLICE  — return only the top-k results

    Uses .sort() (in-place) rather than sorted() because `scored` is a local
    list built in this function — no external caller holds a reference to it,
    so mutating it is safe and avoids allocating a second list in memory.
    """
    # Step 1 & 2: loop + score
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = " | ".join(reasons) if reasons else "no strong matches"
        scored.append((song, score, explanation))

    # Step 3: rank — sort in-place by score (index 1 of each tuple), highest first
    scored.sort(key=lambda x: x[1], reverse=True)

    # Step 4: slice — return only the top-k
    return scored[:k]
