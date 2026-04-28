# GrooveMatch — AI Music Recommender

> An agentic RAG system that turns natural language into personalized music recommendations, built on top of a rule-based recommender originally created in Modules 1–3.

---

## Original Project (Modules 1–3)

**Music Recommender Simulation** was the foundation project built across the first three modules of this course. Its goal was to represent songs as structured data and score them against a user's taste profile using a hand-crafted, point-based algorithm. Given a user's preferred genre, mood, energy level, and tempo target, the system ranked all 18 catalog songs and returned the top 5 with a breakdown of exactly which rules contributed to each score. It was rule-based and fully transparent — no black box, no API calls, just weighted math.

---

## Title and Summary

**GrooveMatch** extends the original simulation into a real AI application. Instead of requiring users to fill in a structured form, they can now describe what they want in plain English — *"something chill and acoustic for late-night studying"* — and the system handles the rest.

Under the hood, a Claude-powered agent extracts structured preferences from the query, the original rule-based scorer retrieves the best candidate songs from the catalog (RAG), and Claude then selects and explains the final picks in a conversational tone. A confidence evaluator decides whether the initial retrieval is strong enough or whether the search should be broadened automatically. Every step is logged, every AI response is validated against the real catalog before it reaches the user, and a 22-test reliability suite verifies the system's correctness without requiring an API key.

**Why it matters:** Most people can't articulate their musical taste as a genre string and a floating-point energy score. GrooveMatch closes that gap, and the architecture — natural language in, structured retrieval, AI-generated explanation — reflects patterns used in production recommendation systems at scale.

---

## Architecture Overview

```
User (Streamlit UI)
        │  free-text query
        ▼
Preference Extractor  (Claude)
        │  structured JSON: {genre, mood, energy, valence, tempo}
        ▼
Retriever  (rule-based scorer — recommender.py)
        │  top-10 scored candidates with per-feature breakdowns
        ▼
Confidence Evaluator  (agentic self-check)
        │  confidence ≥ 0.30 → proceed   |   < 0.30 → broaden & re-retrieve
        ▼
Recommendation Generator  (Claude)
        │  raw JSON recommendations + summary
        ▼
Anti-Hallucination Guard  (guardrail)
        │  strips any song ID not in the 18-song catalog
        ▼
Output  (Streamlit UI — cards, confidence score, extracted prefs)
```

There are two Claude calls per request: one to extract preferences from the user's query, and one to select and explain the final recommendations from the retrieved candidates. The rule-based retriever in the middle is the RAG retrieval step — Claude never answers from training data alone; it always works from songs that were explicitly retrieved and passed in as context.

The full component diagram, including where automated tests and human oversight are involved, lives in [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## Setup Instructions

### Prerequisites
- Python 3.10 or later
- An Anthropic API key ([get one here](https://console.anthropic.com))

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd applied-ai-system-project
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your API key

```bash
cp .env.example .env
```

Open `.env` and replace `your_api_key_here` with your actual Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 5. Launch the web app

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

### 6. (Optional) Run the original rule-based CLI

```bash
python -m src.main
```

### 7. Run the test suite

No API key needed — all 22 tests run against the rule-based layer and the response validator.

```bash
pytest tests/ -v
```

---

## Sample Interactions

The following examples show a real user query, what GrooveMatch extracts from it, and the kind of recommendations and explanations the system produces.

---

### Example 1 — Late-night study session

**User input:**
> "something chill and acoustic for late-night studying"

**Extracted preferences:**
```json
{
  "genre": "lofi",
  "mood": "chill",
  "target_energy": 0.35,
  "target_valence": 0.58,
  "target_tempo": 75
}
```

**Recommendations:**

| # | Song | Artist | Explanation |
|---|---|---|---|
| 1 | Library Rain | Paper Lanterns | A near-perfect match — gentle energy, mid-range valence, and a slow 72 BPM tempo that keeps your mind from drifting. The high acousticness score means real instruments rather than heavy synths, exactly right for a quiet desk. |
| 2 | Midnight Coding | LoRoom | Another lofi staple with almost identical energy and valence to your target. The slightly warmer, busier feel compared to Library Rain makes it a good track to queue when you need a subtle tempo shift. |
| 3 | Spacewalk Thoughts | Orbit Bloom | Ambient rather than lofi, but the slow 60 BPM and very high acousticness earn it a spot here. Good for deep focus when you want something even quieter than the lofi picks. |

**Summary:** Three low-energy, acoustic-leaning tracks that sit comfortably in the study-session zone — start with Library Rain and let the playlist drift into Spacewalk Thoughts as the night gets later.

**Retrieval confidence:** 91%

---

### Example 2 — Morning workout

**User input:**
> "upbeat pop for a morning run, something that'll actually wake me up"

**Extracted preferences:**
```json
{
  "genre": "pop",
  "mood": "happy",
  "target_energy": 0.88,
  "target_valence": 0.82,
  "target_tempo": 130
}
```

**Recommendations:**

| # | Song | Artist | Explanation |
|---|---|---|---|
| 1 | Gym Hero | Max Pulse | Built for exactly this moment — 132 BPM, 0.93 energy, high danceability. The intense mood means it pushes rather than coasts, which is what you want at mile two. |
| 2 | Sunrise City | Neon Echo | Slightly lighter than Gym Hero at 0.82 energy, but the happy mood and 0.84 valence make it feel genuinely sunny rather than aggressive. Good for the warm-up lap. |
| 3 | Neon Carnival | Club Static | EDM rather than pure pop, but the 140 BPM and 0.96 energy are hard to beat when you hit a hill. The euphoric mood matches the bright valence target closely. |

**Summary:** Two pop tracks bracketing the tempo target plus one EDM option for when you need to push — sequenced here from warmup to sprint.

**Retrieval confidence:** 87%

---

### Example 3 — Low-confidence query triggering broadened search

**User input:**
> "something dark and heavy for when I'm frustrated"

**Extracted preferences:**
```json
{
  "genre": "metal",
  "mood": "angry",
  "target_energy": 0.95,
  "target_valence": 0.18,
  "target_tempo": 165
}
```

**System behavior:** Initial retrieval confidence was 15% (only one metal song in the catalog). The confidence evaluator automatically dropped genre/mood constraints and re-retrieved using energy, valence, and tempo only.

**Recommendations:**

| # | Song | Artist | Explanation |
|---|---|---|---|
| 1 | Bone Cold | Dread Signal | The only track in the catalog that genuinely matches the dark, high-energy request — 0.97 energy, 0.18 valence, 168 BPM, and an angry mood. This is the obvious pick. |
| 2 | Storm Runner | Voltline | Rock rather than metal, but the intense mood and 0.91 energy make it a close second. The 152 BPM keeps the momentum even if the sonic weight is a step lighter. |
| 3 | Night Drive Loop | Neon Echo | A surprising fit — synthwave with a moody tone and 0.75 energy. Lower intensity than the first two, but the 0.49 valence sits on the darker half of the scale and the 110 BPM works as a come-down track. |

**Summary:** The catalog is thin on heavy music, but these three covers the range from full-intensity metal to a darker synthwave option for when the anger cools slightly.

**Retrieval confidence:** 15% (broadened search triggered automatically)

---

## Design Decisions

### Why RAG instead of just asking Claude to recommend music?

Asking Claude to recommend songs without grounding it in a catalog would produce invented or out-of-catalog results — Claude would name real-world songs it knows from training, not the 18 songs the system is actually built around. By first retrieving candidates with the rule-based scorer and then passing only those candidates to Claude, the AI works as an explanation and selection layer over real, retrieved data. This is the core RAG pattern, and it's the same reason production search systems like Perplexity or Bing AI use retrieval before generation.

### Why keep the rule-based scorer at all?

The rule-based retriever is fast, deterministic, and explainable. It never hallucinates a song. It also provides the per-feature score breakdown that Claude uses as evidence when writing explanations — "energy 0.82 vs target 0.82 (+1.5/1.50)" is something Claude can actually reason about. Replacing it entirely with a vector similarity search would lose that transparency and add infrastructure (an embedding model, a vector database) that isn't necessary at this catalog size.

### Why two Claude calls instead of one?

Separating preference extraction from recommendation generation keeps each prompt focused and short. A single mega-prompt asking Claude to simultaneously parse a free-text query, score songs, and write explanations would be harder to debug, more expensive, and more likely to mix up the tasks. Splitting also lets me cache each system prompt independently, so repeated queries in the same session only pay the input token cost once.

### Why the 30% confidence threshold?

Below 30% confidence means the top rule-based score is under ~2 points out of 6.5 — essentially no strong matches. At that point, forcing genre and mood constraints would just return the one catalog song that matches a rare genre, regardless of how well it fits the emotional request. Dropping those constraints lets the numeric features (energy, valence, tempo) surface more genuinely similar songs across genre lines. The threshold was chosen by manually testing edge cases (metal, country, classical queries against the 18-song catalog).

### Trade-offs made

| Decision | Benefit | Cost |
|---|---|---|
| Rule-based retrieval | Deterministic, no extra infra | Binary genre/mood matching misses adjacent categories |
| Two Claude calls | Clear separation of concerns | ~2× latency vs one-shot |
| Anti-hallucination guard | Safety net against invented songs | Silently drops recommendations; could leave fewer than k results |
| 18-song catalog | Simple and controllable | Thin genre coverage; metal/classical fans get weak results |
| Experimental weights (energy 3.0) | Surfaces emotional matches better | Misaligned with original README documentation |

---

## Testing Summary

### How to run

```bash
# Full automated test suite (no API key needed)
pytest tests/ -v

# Standalone reliability report with confidence scoring
python tests/reliability_report.py
```

### Real results (run 2026-04-27)

```
Automated tests (pytest)        22 / 22 passed
Scoring determinism             18 / 18 songs stable
Average retrieval confidence    89%
Genre/mood hit in top result     5 /  5 profiles
Anti-hallucination checks        3 /  3 correct
Graceful degradation             3 /  3 edge cases handled
Score bound violations           0 / 90
```

### What the tests cover

**`tests/test_reliability.py` — 20 tests, no API key needed:**

| Category | What is checked |
|---|---|
| Catalog integrity | All 18 songs present, correct field types, energy/valence in [0, 1] |
| Scoring determinism | Same song + same prefs always returns the same score |
| Score bounds | No score exceeds 6.5 or goes below 0 across all 90 song/profile combos |
| Completeness | `recommend_songs()` returns exactly k results for k = 1, 3, 5, 10, 18 |
| Sort order | Results always ranked descending by score; #1 always has the highest score |
| Graceful degradation | Unknown genre, single field, and empty prefs all return 5 results without crashing |
| Anti-hallucination | Validator correctly blocks `song_id=9999`, blocks `song_id=0`, passes `song_id=1` |
| Schema validation | Missing `summary`, `artist`, and `explanation` fields each caught as separate violations |

**`tests/test_recommender.py` — 2 OOP unit tests:**
Both pass after the previously-stubbed `Recommender.recommend()` and `explain_recommendation()` methods were fully implemented.

### Confidence scores across 5 profiles

| Profile | Confidence | Top score | Notes |
|---|---|---|---|
| Pop / Happy | 100% | 6.49 / 6.50 | Near-perfect catalog match |
| High-Energy Rock | 99% | 6.43 / 6.50 | Near-perfect catalog match |
| Chill Lofi | 98% | 6.38 / 6.50 | 3 lofi songs in catalog |
| Adversarial: High-Energy + Sad | 72% | 4.70 / 6.50 | No song satisfies both constraints |
| Adversarial: No Genre Match | 75% | 4.87 / 6.50 | One country song; falls back to proximity |

Average confidence: **89%**. Profiles below 30% would trigger the automatic broadened-search fallback; none of the five standard profiles hit that threshold.

### What worked

The three well-supported genres (pop, rock, lofi) all returned confidence above 98%, meaning the retriever found near-perfect matches before Claude even saw the query. The anti-hallucination guard correctly handled all three test cases. The graceful degradation tests confirmed the system never crashes on partial or unusual input — an empty preferences dict still returns 5 results.

### What didn't work / limitations found

- **Binary genre matching** is the biggest weakness. A query mapped to "indie folk" by Claude gets zero genre points against "folk" or "indie pop" — the extractor must land on an exact catalog genre string or the 1.0 genre score is lost entirely.
- **Thin catalog coverage** means a metal fan always gets the same top result (`Bone Cold`) regardless of how their specific energy or valence target differs from that song's attributes.
- **The 0.30 confidence threshold** was set by hand-testing a handful of edge cases. A data-driven threshold based on the full score distribution would be more principled.

### What testing taught me

Writing the bounds and determinism tests before touching the AI layer was the most valuable decision in the project — it confirmed the retrieval foundation was solid before introducing nondeterminism from Claude. The anti-hallucination tests also forced a clear definition of "valid output" before the first API call, which led directly to the runtime guardrail that now runs on every response, not just in tests.

---

