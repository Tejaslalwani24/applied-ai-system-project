# Reflection: Profile Comparisons

---

## Pop / Happy vs. High-Energy Rock

These two profiles both want high energy, but they pull the rankings in completely different directions once genre and mood enter the picture.

The pop/happy listener gets *Sunrise City* at #1 with nearly a perfect score — it matches genre, mood, energy, valence, and tempo all at once. The rock/intense listener gets *Storm Runner* at #1 for the same reason. Both results feel exactly right.

What is interesting is what happens at #2. For the pop listener, *Gym Hero* shows up even though it is labeled "intense" not "happy." For the rock listener, *Gym Hero* also shows up at #2 even though it is a pop song, not rock — it earns that slot purely because "intense" is a mood match and its energy (0.93) is very close to the rock target (0.90). The same song finds a way into the top 3 for both profiles by exploiting different parts of the scoring system. This tells you that *Gym Hero* is a generalist song that fits many high-energy profiles, not because it is the best match for any of them, but because it scores solidly on almost every axis.

---

## Chill Lofi vs. Adversarial — High-Energy + Sad

These two profiles are almost complete opposites, and the contrast in results shows exactly how the scoring responds to extreme inputs.

The lofi listener gets a clean, logical top 3: two lofi/chill songs that are almost perfect matches, followed by a third lofi song that only misses on mood ("focused" instead of "chill"). The recommendations feel calm and coherent — a person studying or relaxing would be happy with any of these.

The adversarial profile asks for something that does not really exist in the catalog: pop music that is high-energy but also sad and emotionally dark (valence 0.15). The system cannot satisfy all of those at once. What it returns instead is the highest-scoring pop songs by energy, which happen to be cheerful gym tracks. *Gym Hero* at #1 for a sad listener is the clearest example of the scoring logic being "tricked" — not because the math is broken, but because genre loyalty (2.0 points) outweighs the emotional mismatch (only 1.0 point for mood, and partial valence penalty). In plain terms: the system knows you want pop, so it gives you pop, and then pretends the sadness part does not matter as much.

---

## High-Energy Rock vs. Adversarial — High-Energy + Sad

Both profiles want high energy and fast tempo, but one has a coherent genre+mood (rock/intense) and the other has a contradictory mood (pop/sad).

The rock profile gets five songs where energy proximity is doing real work — *Storm Runner* is a near-perfect fit and the fallbacks are genuinely high-energy alternatives across different genres. The order makes sense.

The adversarial profile gets a mess at positions 3–5 — *Sunrise City* (a happy pop anthem), *Bone Cold* (an angry metal track), and *Storm Runner* (a rock song the user never asked for). Each song is winning on a different sub-score: *Sunrise City* on genre, *Bone Cold* on energy+valence proximity, *Storm Runner* on energy+tempo. The system has no way to reconcile the conflicting inputs, so different songs win for different reasons. A human music curator looking at this list would immediately notice that none of these songs actually belong together — you would never put a gym pop anthem, an angry metal track, and a driving rock song on the same "sad" playlist.

---

## Chill Lofi vs. Adversarial — No Genre Match (Country)

Both profiles want relaxed, mid-valence listening, but one has strong catalog support (lofi has 3 songs) and the other has almost none (country has 1 song).

The lofi profile produces the most consistent recommendations in the entire test — three lofi songs in the top 3, all scoring above 4.9. The catalog depth gives the system real choices, and the results feel like a coherent playlist.

The country profile has to improvise after *Rust & Rain* at #1. The system falls back to happy-mood songs with similar energy and valence — indie pop, regular pop, r&b — which are not country at all, but happen to fit numerically. This is graceful degradation: the recommender does not crash or return garbage, it just quietly switches from "give you your genre" to "give you the closest vibe." A real listener might actually appreciate some of these fallbacks, but they would also notice immediately that none of them sound like country music.

---

## Original Weights vs. Experimental Weights (Weight Shift)

The weight shift experiment — halving the genre bonus from 2.0 to 1.0 and doubling the energy weight from 1.5 to 3.0 — made one thing better and one thing worse.

Better: the adversarial sad profile now surfaces *Bone Cold* at #2. A dark, angry metal song with very low valence (0.18) is actually a more emotionally appropriate recommendation for someone asking for sad/dark music than *Sunrise City* is, even though it is a different genre. When energy matters more, songs that genuinely match the "feel" of the request can overcome genre mismatch.

Worse: the country profile's only country song (*Rust & Rain*) barely beats an indie pop song for the #1 spot — 4.87 vs 4.81. The margin is so thin that a small catalog change could flip the order. Genre preference is something listeners feel strongly about, and a system that makes it nearly ignorable will frustrate users who care about it.

The original weights are more predictable and genre-loyal. The experimental weights are more emotionally sensitive but less genre-faithful. Neither is strictly correct — the right balance depends on what kind of listener you are designing for.
