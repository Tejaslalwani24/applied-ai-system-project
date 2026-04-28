"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from .recommender import load_songs, recommend_songs


def print_recommendations(recommendations, user_prefs: dict, profile_name: str) -> None:
    """Prints a formatted recommendation list to the terminal."""
    width = 72
    print()
    print("=" * width)
    print(f"  MUSIC RECOMMENDER — {profile_name.upper()}")
    print(f"  Genre: {user_prefs.get('genre')}  |  "
          f"Mood: {user_prefs.get('mood')}  |  "
          f"Energy: {user_prefs.get('target_energy')}  |  "
          f"Valence: {user_prefs.get('target_valence')}  |  "
          f"Tempo: {user_prefs.get('target_tempo')} BPM")
    print("=" * width)

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        bar_filled = int((score / 6.5) * 20)  # max is now 6.5 (genre 1.0 + mood 1.0 + energy 3.0 + valence 1.0 + tempo 0.5)
        bar = "#" * bar_filled + "-" * (20 - bar_filled)
        print(f"\n  #{rank}  {song['title']}  —  {song['artist']}")
        print(f"       Score: {score:.2f} / 6.00  [{bar}]")
        for reason in explanation.split(" | "):
            print(f"         • {reason}")

    print()
    print("=" * width)
    print()


def main() -> None:
    songs = load_songs("data/songs.csv")

    # Profile A: pop/happy listener (default verification profile)
    user_prefs_pop = {
        "genre": "pop",
        "mood": "happy",
        "target_energy": 0.82,
        "target_valence": 0.84,
        "target_tempo": 120,
    }

    # Profile B: high-intensity rock listener
    user_prefs_rock = {
        "genre": "rock",
        "mood": "intense",
        "target_energy": 0.90,
        "target_valence": 0.45,
        "target_tempo": 150,
    }

    # Profile C: chill study/lofi listener
    user_prefs_lofi = {
        "genre": "lofi",
        "mood": "chill",
        "target_energy": 0.38,
        "target_valence": 0.58,
        "target_tempo": 75,
    }

    # Profile D (adversarial): conflicting high-energy + sad mood
    # Edge case: energy 0.95 is "intense" but mood is "sad" — tests whether
    # genre/mood mismatch suppresses high proximity scores.
    user_prefs_conflict = {
        "genre": "pop",
        "mood": "sad",
        "target_energy": 0.95,
        "target_valence": 0.15,
        "target_tempo": 160,
    }

    # Profile E (adversarial): genre that likely has zero catalog matches
    # Edge case: no song in the catalog uses genre "country" — verifies the
    # ranker degrades gracefully and still returns k results on proximity alone.
    user_prefs_nomatch = {
        "genre": "country",
        "mood": "happy",
        "target_energy": 0.60,
        "target_valence": 0.70,
        "target_tempo": 100,
    }

    profiles = [
        (user_prefs_pop,      "Pop / Happy"),
        (user_prefs_rock,     "High-Energy Rock"),
        (user_prefs_lofi,     "Chill Lofi"),
        (user_prefs_conflict, "Adversarial — High-Energy + Sad"),
        (user_prefs_nomatch,  "Adversarial — No Genre Match (Country)"),
    ]

    for user_prefs, profile_name in profiles:
        recommendations = recommend_songs(user_prefs, songs, k=5)
        print_recommendations(recommendations, user_prefs, profile_name)


if __name__ == "__main__":
    main()
