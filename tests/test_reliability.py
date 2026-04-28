"""
Reliability tests for the GrooveMatch recommendation system.

Covers:
  1. Catalog integrity        — all 18 songs present with correct field types
  2. Scoring determinism      — identical inputs always produce identical scores
  3. Score bounds             — no score exceeds the documented maximum (6.5)
  4. Recommendation count     — recommend_songs always returns exactly min(k, n) results
  5. Sort order               — results are sorted descending by score
  6. Graceful degradation     — unknown genre still returns k results
  7. Anti-hallucination gate  — response validator catches fabricated song IDs
  8. Schema validation        — validator catches missing required fields
"""
import pytest
from pathlib import Path

from src.recommender import load_songs, score_song, recommend_songs

DATA_PATH = Path(__file__).parent.parent / "data" / "songs.csv"
REQUIRED_FIELDS = {
    "id", "title", "artist", "genre", "mood",
    "energy", "tempo_bpm", "valence", "danceability", "acousticness",
}
MAX_SCORE = 6.5  # genre 1.0 + mood 1.0 + energy 3.0 + valence 1.0 + tempo 0.5


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def catalog():
    return load_songs(str(DATA_PATH))


@pytest.fixture
def sample_prefs():
    return {
        "genre": "pop",
        "mood": "happy",
        "target_energy": 0.8,
        "target_valence": 0.8,
        "target_tempo": 120,
    }


# ---------------------------------------------------------------------------
# 1. Catalog integrity
# ---------------------------------------------------------------------------

def test_catalog_loads_all_songs(catalog):
    assert len(catalog) == 18, f"Expected 18 songs, got {len(catalog)}"


def test_all_songs_have_required_fields(catalog):
    for song in catalog:
        missing = REQUIRED_FIELDS - set(song.keys())
        assert not missing, f"Song id={song.get('id')} missing fields: {missing}"


def test_numeric_fields_have_correct_types(catalog):
    for song in catalog:
        assert isinstance(song["id"], int), f"Song {song['id']}.id is not int"
        for field in ("energy", "tempo_bpm", "valence", "danceability", "acousticness"):
            assert isinstance(song[field], float), \
                f"Song {song['id']}.{field} is not float"


def test_energy_and_valence_in_unit_range(catalog):
    for song in catalog:
        assert 0.0 <= song["energy"] <= 1.0, \
            f"Song {song['id']}: energy {song['energy']} out of [0, 1]"
        assert 0.0 <= song["valence"] <= 1.0, \
            f"Song {song['id']}: valence {song['valence']} out of [0, 1]"


# ---------------------------------------------------------------------------
# 2. Scoring determinism
# ---------------------------------------------------------------------------

def test_score_song_is_deterministic(catalog, sample_prefs):
    for song in catalog:
        score1, reasons1 = score_song(sample_prefs, song)
        score2, reasons2 = score_song(sample_prefs, song)
        assert score1 == score2, \
            f"Score changed between runs for song id={song['id']}"
        assert reasons1 == reasons2, \
            f"Reasons changed between runs for song id={song['id']}"


# ---------------------------------------------------------------------------
# 3. Score bounds
# ---------------------------------------------------------------------------

def test_score_never_exceeds_maximum(catalog, sample_prefs):
    for song in catalog:
        score, _ = score_song(sample_prefs, song)
        assert score <= MAX_SCORE + 1e-9, \
            f"Song id={song['id']} scored {score} > max {MAX_SCORE}"


def test_score_is_non_negative(catalog, sample_prefs):
    for song in catalog:
        score, _ = score_song(sample_prefs, song)
        assert score >= 0.0, \
            f"Song id={song['id']} has negative score {score}"


# ---------------------------------------------------------------------------
# 4. Recommendation count
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("k", [1, 3, 5, 10, 18])
def test_recommend_returns_exactly_k_results(catalog, sample_prefs, k):
    results = recommend_songs(sample_prefs, catalog, k=k)
    assert len(results) == min(k, len(catalog)), \
        f"k={k}: expected {min(k, len(catalog))} results, got {len(results)}"


# ---------------------------------------------------------------------------
# 5. Sort order
# ---------------------------------------------------------------------------

def test_results_are_sorted_descending(catalog, sample_prefs):
    results = recommend_songs(sample_prefs, catalog, k=10)
    scores = [r[1] for r in results]
    assert scores == sorted(scores, reverse=True), \
        "Results are not sorted by score descending"


def test_top_result_has_highest_score(catalog, sample_prefs):
    results = recommend_songs(sample_prefs, catalog, k=18)
    all_scores = [r[1] for r in results]
    assert results[0][1] == max(all_scores), \
        "First result does not have the highest score"


# ---------------------------------------------------------------------------
# 6. Graceful degradation
# ---------------------------------------------------------------------------

def test_unknown_genre_still_returns_results(catalog):
    prefs = {"genre": "zydeco", "mood": "ecstatic", "target_energy": 0.5}
    results = recommend_songs(prefs, catalog, k=5)
    assert len(results) == 5, \
        "Should return 5 results even when genre has no catalog match"


def test_missing_optional_prefs_does_not_crash(catalog):
    # Only genre provided — numeric fields omitted
    results = recommend_songs({"genre": "lofi"}, catalog, k=3)
    assert len(results) == 3


# ---------------------------------------------------------------------------
# 7 & 8. Anti-hallucination gate and schema validation (no API key needed)
# ---------------------------------------------------------------------------

def _validate_ai_response(response: dict, valid_ids: set) -> list:
    """Return a list of violation strings; empty list means the response is valid."""
    violations = []
    if "recommendations" not in response:
        violations.append("missing 'recommendations' key")
        return violations
    if "summary" not in response:
        violations.append("missing 'summary' key")
    for i, rec in enumerate(response["recommendations"]):
        for field in ("song_id", "title", "artist", "explanation"):
            if field not in rec:
                violations.append(f"recommendations[{i}] missing field '{field}'")
        sid = rec.get("song_id")
        if sid not in valid_ids:
            violations.append(
                f"recommendations[{i}] references unknown song_id={sid}"
            )
    return violations


def test_validator_catches_hallucinated_song_id(catalog):
    valid_ids = {s["id"] for s in catalog}
    fake = {
        "recommendations": [
            {"song_id": 9999, "title": "Ghost Track", "artist": "Nobody",
             "explanation": "Does not exist."}
        ],
        "summary": "A hallucinated recommendation.",
    }
    violations = _validate_ai_response(fake, valid_ids)
    assert any("unknown song_id" in v for v in violations), \
        "Validator should flag unknown song_id=9999"


def test_validator_accepts_valid_response(catalog):
    valid_ids = {s["id"] for s in catalog}
    good = {
        "recommendations": [
            {"song_id": 1, "title": "Sunrise City", "artist": "Neon Echo",
             "explanation": "Great energy match."},
            {"song_id": 2, "title": "Midnight Coding", "artist": "LoRoom",
             "explanation": "Chill and focused."},
        ],
        "summary": "Two solid picks.",
    }
    violations = _validate_ai_response(good, valid_ids)
    assert violations == [], f"Unexpected violations: {violations}"


def test_validator_catches_missing_summary(catalog):
    valid_ids = {s["id"] for s in catalog}
    response = {
        "recommendations": [
            {"song_id": 1, "title": "X", "artist": "Y", "explanation": "Z"}
        ]
        # deliberately omitting "summary"
    }
    violations = _validate_ai_response(response, valid_ids)
    assert any("summary" in v for v in violations)


def test_validator_catches_missing_recommendation_fields(catalog):
    valid_ids = {s["id"] for s in catalog}
    response = {
        "recommendations": [
            {"song_id": 1, "title": "Only title"}  # missing artist + explanation
        ],
        "summary": "test",
    }
    violations = _validate_ai_response(response, valid_ids)
    assert len(violations) >= 2, \
        f"Expected >=2 violations for missing fields, got: {violations}"
