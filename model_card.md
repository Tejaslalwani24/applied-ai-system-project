# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**GrooveMatch 1.0**

A rule-based music recommender that scores every song in a small catalog against what a listener says they want, then returns the top 5.

---

## 2. Goal / Task

GrooveMatch tries to answer one question: given what a listener tells you about their taste right now — their preferred genre, mood, energy level, emotional brightness, and tempo — which songs in the catalog are the closest match?

It does not learn from listening history. It does not know what you played last week. It only looks at the preferences you hand it and finds the best-scoring songs for those preferences at that moment.

---

## 3. How the Model Works

Every song in the catalog gets a score between 0 and 6. The score is built from five checks:

- **Genre** — Does the song's genre exactly match what the listener asked for? If yes, +2 points. If not, +0. This is the biggest single check.
- **Mood** — Does the song's mood label exactly match? If yes, +1 point. If not, +0.
- **Energy** — How close is the song's energy to what the listener wants? A perfect match gives +1.5 points. The further apart they are, the fewer points.
- **Emotional brightness (valence)** — How close is the song's positivity level to the listener's target? Up to +1 point.
- **Tempo** — How close is the song's BPM to the listener's target? Up to +0.5 points.

Once every song has a score, they are sorted from highest to lowest and the top 5 are returned. The system also prints out exactly why each song scored the way it did, so you can see the math.

---

## 4. Data

The catalog contains **18 songs** stored in a CSV file (`data/songs.csv`). Each song has 10 attributes: a title, an artist, a genre, a mood label, and six numbers (energy, tempo, valence, danceability, acousticness, and an ID).

**Genres represented:** pop, lofi, rock, ambient, jazz, synthwave, indie pop, r&b, folk, hip-hop, classical, edm, country, metal, soul — 15 distinct genres across 18 songs.

**Moods represented:** happy, chill, intense, relaxed, focused, moody, romantic, melancholic, energetic, peaceful, euphoric, nostalgic, angry, sad — 14 distinct moods.

**Key limits of the data:**
- Lofi is the only genre with more than 2 songs (it has 3). Every other genre has exactly 1 or 2.
- Sad, melancholic, and peaceful moods each appear only once. If you ask for those moods in any genre other than soul or folk, there is no true match in the catalog.
- The catalog was built for a classroom exercise. It does not represent the full range of music taste — no Latin, no K-pop, no country subgenres, no classical subcategories, and no explicit rap or hardcore.
- Energy values cluster between 0.35 and 0.97. The very quiet end of the spectrum (below 0.3) has almost nothing.

---

## 5. Strengths

The system works best when the listener's preferences are well-represented in the catalog.

- **Lofi / chill listeners** get the most useful results because 3 lofi songs exist and all 3 score well for that profile. The top 3 feel like a real cohesive playlist.
- **Rock and pop listeners** each get one near-perfect #1 match (*Storm Runner* and *Sunrise City*) that scores above 5.9 out of 6.0. Those results feel exactly right.
- **The scoring explanation is transparent.** Every result shows exactly why it ranked where it did — how many points came from genre, how many from energy, where points were lost. This makes the system easy to audit and debug, which is a real advantage over black-box models.
- **Graceful degradation** — when a genre has no catalog match, the system does not crash or return an error. It quietly falls back to proximity scoring and still returns 5 songs. A country listener with no country songs available still gets musically reasonable fallbacks.

---

## 6. Limitations and Bias

The most significant weakness discovered during stress testing is a **genre-weight filter bubble** caused by two compounding problems: the genre bonus is the single largest point award (2.0 out of a max 6.0), and 13 of the 18 catalog genres appear exactly once. This means that for most genre preferences — rock, metal, country, jazz, classical, and others — the system will always return the same single song at #1, no matter how poorly its energy, valence, or tempo actually match the user. A metal fan asking for slow, melancholic music still gets *Bone Cold* (energy 0.97, mood: angry) ranked first simply because it is the only metal song, and the 2.0 genre bonus cannot be overcome by any combination of proximity scores. This creates a hard filter bubble: the recommender never surfaces cross-genre songs that might actually feel better to the listener, because the genre weight is too dominant to allow them to compete. The lofi genre is the only exception — with 3 songs it can produce genuinely diverse top-3 results — which inadvertently means lofi listeners are better served by this system than users of any other genre.

---

## 7. Evaluation

Five user profiles were tested by running `python -m src.main` from the project root and observing the top-5 results for each:

- **Pop / Happy** — a listener who wants upbeat pop with high energy and high valence
- **High-Energy Rock** — a listener who wants intense rock around 150 BPM
- **Chill Lofi** — a listener who wants low-energy background music for studying
- **Adversarial: High-Energy + Sad** — a deliberately contradictory profile (pop genre, high energy, but mood: sad and very low valence) designed to see if the system gets "tricked"
- **Adversarial: No Genre Match (Country)** — a profile whose genre has almost no catalog representation, to test graceful degradation

For each profile, the check was: does the #1 result feel like something a real listener would actually want, and do the lower-ranked results make intuitive sense as fallbacks?

The biggest surprise was **Gym Hero** — a high-energy pop song labeled as "intense" — consistently appearing near the top of multiple unrelated profiles, including a profile asking for sad music. The reason is that the genre bonus (2.0 points) is so large that any pop song starts with a huge head start over songs in other genres, even when the mood and emotional tone are completely wrong. A song called "Gym Hero" does not feel like a reasonable recommendation for someone describing a sad, low-valence listening session, but the scoring logic has no way to recognize that contradiction.

A weight-shift experiment was also run — halving the genre bonus to 1.0 and doubling the energy weight to 3.0 — to see whether reducing genre dominance improved the adversarial results. It did move *Bone Cold* (a dark, angry metal track with energy 0.97 and valence 0.18) into the #2 slot for the sad/high-energy profile, which felt more intuitive. However, it also caused the Country profile's only country song to barely outscore an indie pop song — showing that reducing genre weight introduces its own trade-off.

---

## 8. Intended Use and Non-Intended Use

**Intended use:**
This system is designed for a classroom exercise. Its purpose is to demonstrate how a simple rule-based recommender works — how preferences become numbers, how numbers become rankings, and where that process breaks down. It is meant to be read, modified, and questioned, not deployed.

**Not intended for:**
- Real music apps or production use of any kind
- Users who expect personalized recommendations based on their listening history
- Any catalog larger than a few dozen songs — the logic does not scale without changes
- Making decisions about what music people "should" like based on demographics, location, or personal identity

---

## 9. Ideas for Improvement

1. **Grow the catalog and balance it.** The single biggest fix is adding more songs per genre — at least 5 per genre — so that the system has real choices to make within a genre instead of defaulting to the only song available. Right now, genre matching is almost a coin flip disguised as a recommendation.

2. **Replace binary mood matching with mood similarity groups.** "Chill" and "relaxed" feel nearly identical to a listener but score 0 for each other. A simple lookup table grouping adjacent moods (chill/relaxed/peaceful, intense/energetic/angry) would make the mood score much more useful without adding complexity.

3. **Add a diversity re-ranking step.** After scoring, the top-k results sometimes include the same artist twice or three songs that are nearly identical in every feature. A simple rule — "no two songs from the same artist in the top 5" — would make the output feel more like a real playlist and less like a search result list.

---

## 10. Personal Reflection

**Biggest learning moment**

The clearest moment came when I ran the adversarial "sad pop" profile and got *Gym Hero* — a workout anthem — as the #1 recommendation. I expected the system to fail gracefully, maybe returning something neutral. Instead it confidently returned the most energetic, pump-up song in the catalog. That was the moment I understood that the algorithm does not know what a song *feels like*. It only knows that "pop" matches "pop" and that 0.93 is close to 0.95. The word "sad" in the mood field means nothing to it beyond a string comparison. No amount of tuning the weights fully fixes that — the system fundamentally cannot understand emotional context, only measure numeric distance. That gap between what the numbers say and what a listener actually experiences is the most important thing I took away from this project.

**How AI tools helped — and when I had to double-check**

AI tools were useful for speeding up the mechanical parts: generating the initial scoring structure, formatting the output, writing docstrings, and suggesting edge-case profiles to test. Where I had to slow down and verify was any time the tool explained *why* a result made sense. The explanations were plausible and well-worded, but they were not always grounded in what the code was actually doing. For example, an early suggestion described the system as "balancing genre and mood equally" — but looking at the weights, genre was worth twice as much as mood, so that was wrong. The tool was summarizing the intent, not the math. I learned to treat AI-generated explanations as a starting point that needs to be checked against the actual numbers.

**What surprised me about simple algorithms**

What surprised me most is how convincing a purely mechanical process can feel. When you see the output formatted nicely with song titles, artist names, score bars, and bullet-point reasons, it genuinely looks like a thoughtful recommendation. The presentation creates the impression of intelligence even when the logic underneath is just five arithmetic operations. I think this is exactly how many real recommendation systems work at their core — not because they understand music, but because they are fast, consistent, and produce output that looks reasonable most of the time. The formatting does a lot of the emotional work.

**What I would try next**

If I extended this project, the first thing I would do is expand the catalog to at least 10 songs per genre. Almost every limitation I found — the filter bubble, the lock-in at #1, the poor adversarial results — traced back to the catalog being too small to give the scoring any real choices. After that, I would experiment with soft mood matching: instead of a binary yes/no, group similar moods and award partial credit for adjacent ones. That single change would probably make the system feel meaningfully smarter without requiring a completely different approach.
