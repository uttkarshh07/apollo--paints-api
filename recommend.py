"""
Feature 2: "Recommend shades from a text description"

Two tiers, cheapest-first:

TIER 1 — Keyword/mood lexicon (instant, free, no API call)
  Catches direct family names ("blue", "green"), room types, and common
  moods ("calming", "energetic", "cosy") by mapping them to hue/lightness
  targets, then reuses the same nearest_shades() engine from color_utils.

TIER 2 — LLM fallback (for anything the lexicon can't parse)
  For open-ended queries like "something that feels like a rainy Tokyo
  evening," ask Claude to translate the vibe into a target hex + family,
  then run it through the same deterministic matching engine. The LLM
  never invents shade names/codes itself — it only picks a color
  direction, and the real catalogue lookup does the rest. This avoids
  hallucinated shade codes, which is the main risk of letting an LLM
  answer directly from "knowledge" of a catalogue it hasn't memorized.
"""

import os
import re
from color_utils import nearest_shades, hsl_to_hex, load_shades

FAMILY_WORDS = {
    "red": "Reds", "pink": "Reds", "rose": "Reds", "maroon": "Reds", "crimson": "Reds",
    "orange": "Oranges", "peach": "Oranges", "coral": "Oranges", "terracotta": "Oranges",
    "yellow": "Yellows", "gold": "Yellows", "mustard": "Yellows", "amber": "Yellows",
    "green": "Greens", "sage": "Greens", "olive": "Greens", "emerald": "Greens", "mint": "Greens",
    "blue": "Blues", "navy": "Blues", "teal": "Blues", "turquoise": "Blues", "sky": "Blues",
    "purple": "Violets", "violet": "Violets", "lavender": "Violets", "mauve": "Violets", "plum": "Violets",
    "brown": "Earth Tones", "tan": "Earth Tones", "beige": "Earth Tones", "taupe": "Earth Tones",
    "grey": "Classic Neutrals", "gray": "Classic Neutrals", "neutral": "Classic Neutrals",
    "black": "Dark Accents", "charcoal": "Dark Accents", "dark": "Dark Accents",
    "white": "Whispering Whites", "cream": "Whispering Whites", "ivory": "Whispering Whites",
}

# mood -> (lightness bias, saturation bias). Values are deltas applied to
# whatever base hue we land on, roughly -50..+50
MOOD_WORDS = {
    "calm": (+15, -20), "calming": (+15, -20), "soothing": (+15, -20), "peaceful": (+15, -20),
    "cosy": (-5, +5), "cozy": (-5, +5), "warm": (-5, +10),
    "energetic": (0, +25), "vibrant": (0, +30), "bold": (-10, +25), "bright": (+10, +20),
    "elegant": (-5, -15), "sophisticated": (-10, -20), "luxurious": (-15, +5),
    "airy": (+20, -15), "fresh": (+10, +5), "light": (+25, -10), "minimal": (+20, -25),
    "moody": (-20, +5), "dramatic": (-20, +15),
}

ROOM_DEFAULT_FAMILY = {
    "nursery": "Yellows", "kids room": "Yellows", "kitchen": "Yellows",
    "bedroom": "Blues", "bathroom": "Blues",
    "living room": "Earth Tones", "dining room": "Reds",
    "office": "Classic Neutrals", "study": "Classic Neutrals",
}


def _keyword_match(query, n=6):
    q = query.lower()

    family = None
    for word, fam in FAMILY_WORDS.items():
        if re.search(r"\b" + re.escape(word) + r"\b", q):
            family = fam
            break
    if not family:
        for room, fam in ROOM_DEFAULT_FAMILY.items():
            if room in q:
                family = fam
                break

    l_delta, s_delta = 0, 0
    for word, (ld, sd) in MOOD_WORDS.items():
        if word in q:
            l_delta += ld
            s_delta += sd

    if not family:
        return None  # tier 1 can't confidently handle this

    shades = [s for s in load_shades() if s["f"] == family]
    if not shades:
        return None

    # pick a representative mid-tone hue from the family as our anchor,
    # then bias it by the detected mood, then find nearest real matches
    anchor = shades[len(shades) // 2]
    from color_utils import hex_to_hsl
    h, s, l = hex_to_hsl(anchor["h"])
    biased_hex = hsl_to_hex(h, max(10, min(90, s + s_delta)), max(10, min(90, l + l_delta)))

    return nearest_shades(biased_hex, n=n, family=family)


def _llm_match(query, n=6):
    """
    Tier 2 fallback using Claude. Only used if ANTHROPIC_API_KEY is set
    and the keyword tier returned nothing. The LLM's ONLY job is to name
    a target hex + family — it never sees or invents shade codes.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""A customer described a paint color mood/vibe: "{query}"

Respond with ONLY a JSON object, no other text:
{{"hex": "#RRGGBB", "family": "one of Reds/Oranges/Yellows/Greens/Blues/Violets/Earth Tones/Classic Neutrals/Dark Accents/Whispering Whites"}}

Pick the hex and family that best captures the described mood/vibe for an interior wall paint."""

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    import json
    try:
        text = resp.content[0].text.strip()
        text = re.sub(r"^```json|```$", "", text, flags=re.MULTILINE).strip()
        parsed = json.loads(text)
        return nearest_shades(parsed["hex"], n=n, family=parsed.get("family"))
    except Exception:
        return None


def recommend(query, n=6):
    result = _keyword_match(query, n=n)
    if result:
        return {"method": "keyword_lexicon", "matches": result}

    result = _llm_match(query, n=n)
    if result:
        return {"method": "llm_assisted", "matches": result}

    return {"method": "none", "matches": [], "note": "Could not interpret the query. Try mentioning a colour name or mood."}
