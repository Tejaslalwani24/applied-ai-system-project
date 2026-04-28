"""
AI-powered music recommender using a RAG + agentic workflow pipeline.

Pipeline (one recommend() call):
  1. Extract    — Claude parses free-text query into structured preferences
  2. Retrieve   — rule-based scorer ranks every catalog song (RAG retrieval)
  3. Evaluate   — confidence check; re-retrieves with broader prefs when low
  4. Generate   — Claude selects final k songs and writes rich explanations

Prompt caching is applied to the static system prompts so repeated calls
within a session do not re-encode the same context.
"""
import json
import logging
from typing import Any, Dict, List, Tuple

import anthropic

from .recommender import load_songs, recommend_songs, score_song

logger = logging.getLogger(__name__)

_AVAILABLE_GENRES = [
    "pop", "rock", "lofi", "jazz", "ambient", "synthwave",
    "indie pop", "r&b", "hip-hop", "classical", "edm",
    "country", "metal", "soul", "folk",
]
_AVAILABLE_MOODS = [
    "happy", "chill", "intense", "sad", "focused", "relaxed",
    "moody", "romantic", "energetic", "euphoric", "peaceful",
    "melancholic", "angry", "nostalgic",
]

_PREF_EXTRACT_SYSTEM = (
    "You are a music preference parser. "
    "Extract structured preferences from user queries and return only valid JSON. "
    "Never add explanation text outside the JSON object."
)

_RECOMMEND_SYSTEM = (
    "You are GrooveMatch, an expert music recommendation AI. "
    "You help users discover songs from a curated catalog. "
    "You ONLY recommend songs that appear in the provided candidate list — "
    "never invent or suggest songs outside of it. "
    "Explanations should be warm, specific, and 2-3 sentences."
)

# Maximum possible score from score_song() with current experimental weights
_MAX_SCORE = 6.5


class AIRecommender:
    """Agentic RAG recommender backed by Claude and a local song catalog."""

    def __init__(self, catalog_path: str) -> None:
        self.client = anthropic.Anthropic()
        self.songs = load_songs(catalog_path)
        self._valid_ids = {s["id"] for s in self.songs}
        logger.info("AIRecommender ready — %d songs in catalog", len(self.songs))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def recommend(self, user_query: str, k: int = 5) -> Dict[str, Any]:
        """
        Run the full agentic RAG pipeline and return a result dict:
          {
            "recommendations": [{"song_id", "title", "artist", "explanation"}, ...],
            "summary": str,
            "extracted_preferences": dict,
            "confidence": float,
          }
        """
        logger.info("Pipeline start | query=%r k=%d", user_query, k)

        # Step 1 — preference extraction (Claude call)
        prefs = self._extract_preferences(user_query)

        # Step 2 — RAG retrieval: score every catalog song, keep top 10 as candidates
        candidates = recommend_songs(prefs, self.songs, k=min(10, len(self.songs)))
        top_score = candidates[0][1] if candidates else 0.0
        logger.info("Retrieval done | candidates=%d top_score=%.2f", len(candidates), top_score)

        # Step 3 — agentic confidence check
        confidence = min(top_score / _MAX_SCORE, 1.0)
        if confidence < 0.30:
            logger.warning("Low confidence %.2f — retrying with numeric-only preferences", confidence)
            broad = {k2: v for k2, v in prefs.items()
                     if k2 in ("target_energy", "target_valence", "target_tempo")}
            candidates = recommend_songs(broad, self.songs, k=min(10, len(self.songs)))
            logger.info("Broadened retrieval | candidates=%d", len(candidates))

        # Step 4 — AI generation (Claude call)
        result = self._generate(user_query, candidates, prefs, k)

        # Guardrail: strip any recommendations that reference unknown song IDs
        valid_recs = [r for r in result.get("recommendations", [])
                      if r.get("song_id") in self._valid_ids]
        if len(valid_recs) < len(result.get("recommendations", [])):
            dropped = len(result.get("recommendations", [])) - len(valid_recs)
            logger.warning("Anti-hallucination guard removed %d unknown song(s)", dropped)
        result["recommendations"] = valid_recs

        result["extracted_preferences"] = prefs
        result["confidence"] = round(confidence, 3)
        logger.info("Pipeline done | recs=%d confidence=%.3f",
                    len(result["recommendations"]), confidence)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_preferences(self, user_query: str) -> Dict:
        """Step 1: Use Claude to turn a free-text query into structured prefs."""
        logger.debug("Extracting preferences | query=%r", user_query)
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            system=[
                {
                    "type": "text",
                    "text": _PREF_EXTRACT_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Extract music preferences and return ONLY a valid JSON object.\n\n"
                        f"Available genres: {', '.join(_AVAILABLE_GENRES)}\n"
                        f"Available moods:  {', '.join(_AVAILABLE_MOODS)}\n\n"
                        "Required JSON fields:\n"
                        '  "genre"          — one of the genres listed above\n'
                        '  "mood"           — one of the moods listed above\n'
                        '  "target_energy"  — float 0.0–1.0 (0=calm, 1=intense)\n'
                        '  "target_valence" — float 0.0–1.0 (0=dark/sad, 1=bright/happy)\n'
                        '  "target_tempo"   — int BPM, typically 60–180\n\n'
                        f"User query: {user_query}"
                    ),
                }
            ],
        )
        raw = _strip_fences(response.content[0].text)
        prefs = json.loads(raw)
        logger.debug("Extracted prefs: %s", prefs)
        return prefs

    def _generate(
        self,
        user_query: str,
        candidates: List[Tuple],
        prefs: Dict,
        k: int,
    ) -> Dict:
        """Step 4: Ask Claude to select and explain the best k songs."""
        logger.debug("Generating from %d candidates", len(candidates))

        candidate_lines = [
            f"  [{song['id']}] {song['title']} by {song['artist']} "
            f"(rule score: {score:.2f}) | {explanation}"
            for song, score, explanation in candidates
        ]
        candidate_text = "\n".join(candidate_lines)

        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": _RECOMMEND_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": (
                        f'User request: "{user_query}"\n'
                        f"Extracted preferences: {json.dumps(prefs)}\n\n"
                        f"Candidate songs (pre-ranked by rule-based scoring):\n"
                        f"{candidate_text}\n\n"
                        f"Select the best {k} songs from the list above.\n"
                        "Return ONLY this JSON (no extra text):\n"
                        "{\n"
                        '  "recommendations": [\n'
                        "    {\n"
                        '      "song_id": <int>,\n'
                        '      "title": "<string>",\n'
                        '      "artist": "<string>",\n'
                        '      "explanation": "<2-3 sentences>"\n'
                        "    }\n"
                        "  ],\n"
                        '  "summary": "<1-2 sentences about the set>"\n'
                        "}"
                    ),
                }
            ],
        )
        raw = _strip_fences(response.content[0].text)
        result = json.loads(raw)
        logger.debug("Generated %d recommendations", len(result.get("recommendations", [])))
        return result


def _strip_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) from a string."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[1:end])
    return text.strip()
