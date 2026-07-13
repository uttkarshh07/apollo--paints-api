# Apollo Paints — AI Colour Intelligence API

An AI-powered colour matching backend for [Apollo Paints & Hardware](https://apollopaints.netlify.app), an authorized Berger Paints dealer. Customers can describe a mood, upload a photo, or ask for a matching colour palette — and get back real, purchasable shades from a 1,575-entry Berger catalogue.

**Live API:** `https://apollo-paints-api.onrender.com`
**Live site (with chat widget):** `https://apollopaints.netlify.app`

---

## What it does

### 🎨 Photo → matching shade
Upload any image — a fabric swatch, an inspiration photo, a wall you like elsewhere — and the API detects its dominant colours and matches each one to the closest real shade in the catalogue.

### 💬 Text → recommended shades
Describe what you want in plain language — *"calming blue for a bedroom"*, *"warm orange for a kitchen"* — and get back real matching shades. Falls back to an LLM-assisted interpretation for open-ended descriptions the keyword matcher can't parse.

### 🎯 Colour harmony / palettes
Ask *"what goes with [shade code]"* or *"complementary colours for a warm terracotta"* to get a full palette: complementary, analogous, triadic, split-complementary, and tonal variations — built from real colour-wheel theory and snapped to actual catalogue shades.

---

## How it works (no ML training required)

This project deliberately uses **deterministic colour science** instead of a trained ML model, because colour matching against a fixed catalogue is a nearest-neighbour search problem, not a learning problem:

| Feature | Technique |
|---|---|
| Photo colour matching | k-means clustering (scikit-learn) to find dominant colours, then nearest-neighbour lookup |
| Perceptual colour distance | RGB → **LAB colour space** conversion + CIE76 distance (approximates human colour perception far better than raw RGB) |
| Colour harmony | HSL colour-wheel math (complementary/analogous/triadic/split-complementary), snapped to real catalogue entries |
| Text understanding | Keyword/mood lexicon first; Claude (Anthropic API) as a fallback for open-ended queries — the LLM only ever picks a *colour direction*, never a shade code, so it can't hallucinate a product that doesn't exist |

---

## Tech stack

- **Backend:** Python, FastAPI, Uvicorn
- **Colour science:** NumPy, scikit-learn (k-means), custom LAB/HSL conversion
- **Image handling:** Pillow
- **LLM fallback:** Anthropic API (Claude)
- **Data source:** scraped from Berger Paints' public colour catalogue (`requests` + `BeautifulSoup`)
- **Deployment:** Render (backend), Netlify (static frontend)
- **Frontend:** vanilla HTML/CSS/JS chat widget, no framework

---

## Data pipeline

Berger's catalogue has no public API, so the shade dataset was built by:
1. Inspecting the live site's HTML structure to locate shade name/code/colour markup
2. Confirming each colour-family page (Reds, Blues, Greens, etc.) is server-rendered — meaning a plain HTTP scraper works, no headless browser needed
3. Scraping all 10 category pages with `requests` + `BeautifulSoup`, extracting name, code, and hex value for each shade
4. Output: `data/shades.json` — 1,575 shades, indexed into LAB colour space once at app startup for fast matching

---

## API reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/shades?family=&q=` | Browse/search the catalogue |
| `GET` | `/api/shades/{code}` | Look up a single shade by code |
| `POST` | `/api/match-photo` | Upload an image, get matching shades |
| `POST` | `/api/match-color` | Match a given hex to nearest shades |
| `GET` | `/api/recommend?q=` | Text description → recommended shades |
| `GET` | `/api/harmony/{code}` | Colour palette built from a shade code |
| `GET` | `/api/harmony?hex=` | Colour palette built from any hex |

Interactive API docs available at `/docs` (FastAPI auto-generated Swagger UI).

---

## Running locally

```bash
git clone https://github.com/uttkarshh07/apollo--paints-api.git
cd apollo--paints-api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000/docs` to test every endpoint interactively.

Optional — enable the LLM fallback for open-ended text queries:
```bash
export ANTHROPIC_API_KEY=your_key_here
```

---

## Project structure

```
main.py          — FastAPI app, all routes
color_utils.py   — LAB conversion, nearest-shade matching engine
image_match.py   — photo → dominant colour extraction (k-means)
harmony.py       — colour-wheel math for palette generation
recommend.py     — text-to-shade matching (keyword + LLM fallback)
data/shades.json — the Berger shade catalogue (1,575 entries)
```

---

## Notes

- Shade data is a snapshot from bergerpaints.com's public colour catalogue. Apollo Paints is an authorized Berger dealer, so shade names/codes match what's actually sold in-store.
- Free-tier hosting (Render) spins down after inactivity — first request after idle time may take 30–50s to respond.
