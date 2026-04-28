"""
GrooveMatch — AI Music Recommender
Streamlit web interface for the agentic RAG recommendation pipeline.

Run with:
    streamlit run app.py
"""
import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path so `src` resolves as a package.
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# Load .env if present (API key etc.)
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass  # python-dotenv not installed; rely on environment variables

import streamlit as st

from src.logger import setup_logging
from src.ai_recommender import AIRecommender

DATA_PATH = ROOT / "data" / "songs.csv"

# ------------------------------------------------------------------
# Page config
# ------------------------------------------------------------------
st.set_page_config(
    page_title="GrooveMatch — AI Music Recommender",
    page_icon="🎵",
    layout="centered",
)

# ------------------------------------------------------------------
# Cached resource: one AIRecommender per Streamlit session
# ------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_recommender() -> AIRecommender:
    setup_logging(log_file=str(ROOT / "groovematch.log"))
    return AIRecommender(str(DATA_PATH))


# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------
st.title("🎵 GrooveMatch")
st.caption(
    "Describe your vibe in plain English — GrooveMatch uses AI to extract your "
    "preferences, search the catalog, and explain every pick."
)
st.divider()

# ------------------------------------------------------------------
# Input form
# ------------------------------------------------------------------
with st.form("query_form"):
    query = st.text_area(
        "What are you in the mood for?",
        placeholder=(
            "e.g. something chill and acoustic for studying, "
            "an upbeat pop track for a morning run, "
            "moody synthwave for a late-night drive…"
        ),
        height=110,
    )
    k = st.slider("Number of recommendations", min_value=3, max_value=8, value=5)
    submitted = st.form_submit_button("Find My Music →", use_container_width=True)

# ------------------------------------------------------------------
# Results
# ------------------------------------------------------------------
if submitted and query.strip():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error(
            "ANTHROPIC_API_KEY is not set. "
            "Copy `.env.example` to `.env` and add your key, then restart the app."
        )
        st.stop()

    try:
        recommender = get_recommender()
        with st.spinner("Analysing your vibe and searching the catalog…"):
            result = recommender.recommend(query.strip(), k=k)

        # Summary banner
        if summary := result.get("summary"):
            st.info(f"**GrooveMatch says:** {summary}")

        # Recommendation cards
        st.subheader(f"Your Top {k} Picks")
        recs = result.get("recommendations", [])
        if not recs:
            st.warning("No recommendations returned — try rephrasing your query.")
        for i, rec in enumerate(recs, start=1):
            with st.container(border=True):
                col_num, col_info = st.columns([1, 11])
                col_num.markdown(f"### {i}")
                col_info.markdown(
                    f"**{rec.get('title', 'Unknown')}**  \n"
                    f"*{rec.get('artist', 'Unknown artist')}*"
                )
                st.write(rec.get("explanation", ""))

        # Explainability expander
        with st.expander("How GrooveMatch chose these tracks"):
            prefs = result.get("extracted_preferences", {})
            confidence = result.get("confidence", 0.0)

            st.write("**Preferences Claude extracted from your query:**")
            col_a, col_b = st.columns(2)
            col_a.metric("Genre", prefs.get("genre", "—"))
            col_a.metric("Mood", prefs.get("mood", "—"))
            col_b.metric("Energy", f"{prefs.get('target_energy', 0):.0%}")
            col_b.metric("Valence", f"{prefs.get('target_valence', 0):.0%}")
            st.metric("Retrieval confidence", f"{confidence:.0%}",
                      help="How well the top rule-based match fits the extracted preferences. "
                           "Below 30% the system broadens the search automatically.")

    except Exception as exc:
        st.error(f"Something went wrong: {exc}")
        st.caption("Check groovematch.log for details.")

elif submitted:
    st.warning("Please describe what you're in the mood for before submitting.")
