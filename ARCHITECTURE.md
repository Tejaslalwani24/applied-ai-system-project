# GrooveMatch — Design & Architecture

## Overview

GrooveMatch is an AI-powered music recommender that combines a rule-based retrieval engine with a Claude-backed agentic pipeline. Users describe what they want in plain English; the system extracts structured preferences, retrieves catalog candidates, self-evaluates confidence, and generates personalized recommendations with explanations.

---

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER (Streamlit UI)                          │
│          "something chill and acoustic for studying"                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ free-text query
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  PREFERENCE EXTRACTOR  (Claude API — claude-sonnet-4-6)              │
│  Turns natural language into structured JSON:                        │
│  { genre, mood, target_energy, target_valence, target_tempo }        │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ structured prefs
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  RETRIEVER  (rule-based scorer in recommender.py)                    │
│  Scores all 18 catalog songs against the structured prefs            │
│  Returns top-10 ranked candidates with per-feature explanations      │
└───────────────┬──────────────────────────────────────────────────────┘
                │ scored candidates
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  CONFIDENCE EVALUATOR  (agentic self-check)                          │
│  confidence = top_score / 6.5                                        │
│  ┌─────────────────────┐      ┌──────────────────────────────────┐   │
│  │  confidence ≥ 0.30  │      │  confidence < 0.30               │   │
│  │  proceed as-is      │      │  drop genre/mood, re-retrieve     │   │
│  └──────────┬──────────┘      └──────────────────────────────────┘   │
└─────────────┼────────────────────────────────────────────────────────┘
              │ candidates (possibly re-retrieved)
              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  RECOMMENDATION GENERATOR  (Claude API — claude-sonnet-4-6)          │
│  Receives: user query + extracted prefs + retrieved candidates       │
│  Selects best k songs; writes conversational explanations            │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ raw JSON response
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  ANTI-HALLUCINATION GUARD  (guardrail in ai_recommender.py)          │
│  Strips any song_id not present in the 18-song catalog               │
│  Logs a warning if any entries are dropped                           │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ validated recommendations
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  OUTPUT  (Streamlit UI)                                              │
│  • Recommendation cards with titles, artists, AI explanations        │
│  • Summary banner from Claude                                        │
│  • Expander: extracted prefs, confidence score                       │
└──────────────────────────────────────────────────────────────────────┘


WHERE TESTING / HUMANS ARE INVOLVED
─────────────────────────────────────────────────────────────────────
 Automated  │ tests/test_reliability.py (22 tests, no API key needed)
            │   • Catalog integrity — all 18 songs, correct field types
            │   • Scoring determinism — same input → same output
            │   • Score bounds — nothing exceeds 6.5 max
            │   • Completeness — always returns k results
            │   • Anti-hallucination validator logic
            │   • Schema validation (required fields present)
            │
 Automated  │ tests/test_recommender.py (OOP unit tests)
            │   • Recommender.recommend() sorts by score correctly
            │   • explain_recommendation() returns non-empty string
            │
 Human      │ Streamlit "How GrooveMatch thinks" expander
            │   • Shows extracted preferences so user can verify
            │     Claude understood their query correctly
            │   • Shows retrieval confidence (%) for transparency
            │
 Logging    │ groovematch.log — every pipeline step recorded:
            │   preference extraction, retrieval count, confidence,
            │   re-retrieval triggers, hallucination guard drops
```

---

## Components

### Preference Extractor
**File:** `src/ai_recommender.py` — `AIRecommender._extract_preferences()`

Accepts a free-text user query and calls Claude to produce a structured JSON object. Uses a cached system prompt so repeated calls within a session do not re-encode the same context. Output feeds directly into the retriever.

### Retriever
**File:** `src/recommender.py` — `recommend_songs()` + `score_song()`

Pure Python, no API calls. Scores every song in the catalog against the structured preferences using a weighted formula (max 6.5 points):

| Feature | Weight | Method |
|---|---|---|
| Genre match | 1.0 | Exact string comparison |
| Mood match | 1.0 | Exact string comparison |
| Energy proximity | 3.0 | `1 - abs(song - target)` |
| Valence proximity | 1.0 | `1 - abs(song - target)` |
| Tempo proximity | 0.5 | Normalized over 60–180 BPM |

Returns the top 10 candidates with per-feature explanations for Claude to reason over.

### Confidence Evaluator
**File:** `src/ai_recommender.py` — `AIRecommender.recommend()`

Divides the top candidate's rule-based score by the maximum possible score (6.5). If confidence falls below 0.30, the agent strips genre and mood constraints and re-runs retrieval using only the numeric features (energy, valence, tempo). This prevents the system from returning poor results when the user's genre has few catalog matches.

### Recommendation Generator
**File:** `src/ai_recommender.py` — `AIRecommender._generate()`

Receives the user's original query, extracted preferences, and retrieved candidates in a single prompt. Claude selects the best k songs from the candidate list only and writes a 2–3 sentence explanation for each pick plus an overall summary. The model is explicitly instructed never to recommend songs outside the provided list.

### Anti-Hallucination Guard
**File:** `src/ai_recommender.py` — `AIRecommender.recommend()`

After Claude returns its JSON response, every `song_id` is checked against the set of valid catalog IDs. Any recommendation referencing an unknown ID is removed and a warning is written to the log. This runs on every call regardless of confidence.

### Reliability Test Suite
**File:** `tests/test_reliability.py`

Twenty automated tests that run without an API key. Covers catalog integrity, scoring determinism, score bounds, result count, sort order, graceful degradation on unknown genres, and the anti-hallucination validator. Acts as a regression gate to confirm the rule-based layer behaves correctly before any AI call is made.

---

## File Structure

```
applied-ai-system-project/
├── app.py                      # Streamlit web UI
├── src/
│   ├── ai_recommender.py       # RAG + agentic pipeline (Claude)
│   ├── recommender.py          # Rule-based scorer and OOP interface
│   └── logger.py               # Centralized logging setup
├── tests/
│   ├── test_recommender.py     # OOP unit tests
│   └── test_reliability.py     # Reliability + anti-hallucination tests
├── data/
│   └── songs.csv               # 18-song catalog
├── .env.example                # API key template
├── requirements.txt
└── ARCHITECTURE.md             # This file
```

---

## Data Flow Summary

A free-text query becomes structured preferences (Claude), which drive rule-based retrieval over the local catalog. A confidence check decides whether to broaden the search. Claude then generates explanations grounded in the retrieved context. A guardrail strips any invented songs before results reach the user.
