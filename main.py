"""
Apollo Paints — Colour Intelligence API

pip install fastapi uvicorn pillow numpy scikit-learn python-multipart anthropic

Run:  uvicorn main:app --reload --port 8000
Docs: http://localhost:8000/docs  (FastAPI auto-generates an interactive
      test UI here — open it in a browser and try every endpoint by hand)
"""

from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from color_utils import nearest_shades, load_shades
from image_match import match_photo_to_shades
from harmony import full_palette
from recommend import recommend

app = FastAPI(title="Apollo Paints Colour Intelligence API", version="1.0")

# Lock this down to your actual frontend domain(s) before going live —
# "*" is only for local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://apollopaints.netlify.app",
        "http://localhost:3000",  # for local testing only, remove later if unused
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- 0. Catalogue browsing (baseline, used by the frontend grid) ----------

@app.get("/api/shades")
def list_shades(family: str = Query(None), q: str = Query(None), limit: int = 100):
    shades = load_shades()
    if family:
        shades = [s for s in shades if s["f"].lower() == family.lower()]
    if q:
        ql = q.lower()
        shades = [s for s in shades if ql in s["n"].lower() or ql in s["c"].lower()]
    return [
        {"family": s["f"], "name": s["n"], "code": s["c"], "hex": s["h"]}
        for s in shades[:limit]
    ]


@app.get("/api/shades/{code}")
def get_shade(code: str):
    for s in load_shades():
        if s["c"].lower() == code.lower():
            return {"family": s["f"], "name": s["n"], "code": s["c"], "hex": s["h"]}
    raise HTTPException(404, "Shade code not found")


# ---------- 1. Photo -> matching shade ----------

@app.post("/api/match-photo")
async def match_photo(file: UploadFile = File(...), colors: int = 5):
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")
    image_bytes = await file.read()
    try:
        results = match_photo_to_shades(image_bytes, n_colors=colors)
    except Exception as e:
        raise HTTPException(422, f"Could not process image: {e}")
    return {"results": results}


class HexMatchRequest(BaseModel):
    hex: str
    n: int = 5
    family: str | None = None

@app.post("/api/match-color")
def match_color(req: HexMatchRequest):
    """Same matching engine, but for a hex the frontend already knows
    (e.g. from an <input type='color'> picker) instead of a photo."""
    return {"results": nearest_shades(req.hex, n=req.n, family=req.family)}


# ---------- 2. Text -> recommended shades ----------

@app.get("/api/recommend")
def recommend_shades(q: str = Query(..., min_length=2), n: int = 6):
    return recommend(q, n=n)


# ---------- 3. Colour harmony ----------

@app.get("/api/harmony/{code}")
def harmony_by_code(code: str):
    shade = get_shade(code)  # reuses lookup + 404 handling above
    return full_palette(shade["hex"])


@app.get("/api/harmony")
def harmony_by_hex(hex: str = Query(...)):
    return full_palette(hex)


@app.get("/")
def root():
    return {
        "status": "ok",
        "shade_count": len(load_shades()),
        "endpoints": [
            "GET  /api/shades?family=&q=",
            "GET  /api/shades/{code}",
            "POST /api/match-photo (multipart file upload)",
            "POST /api/match-color {hex, n, family}",
            "GET  /api/recommend?q=",
            "GET  /api/harmony/{code}",
            "GET  /api/harmony?hex=",
        ],
    }
