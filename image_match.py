"""
Feature 1: "Match a photo to a paint shade"

User uploads a photo (a fabric swatch, a Pinterest inspo pic, a photo of
a wall they like). We extract the dominant colors via k-means clustering
on the pixels, then match each cluster to the nearest catalogue shade.

pip install pillow numpy scikit-learn
"""

from io import BytesIO
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

from color_utils import rgb_to_hex, nearest_shades


def extract_dominant_colors(image_bytes, n_colors=5, resize_to=150):
    """
    Returns a list of dominant hex colors, sorted by how much of the
    image they cover (most dominant first).
    """
    img = Image.open(BytesIO(image_bytes)).convert("RGB")

    # Downscale for speed — color clustering doesn't need full resolution
    img.thumbnail((resize_to, resize_to))
    pixels = np.array(img).reshape(-1, 3)

    # Drop near-white / near-black pixels if they're just background/shadow
    # noise (optional — comment out if you want raw dominant colors)
    mask = ~(
        (pixels.sum(axis=1) > 740) |  # near-white
        (pixels.sum(axis=1) < 15)     # near-black
    )
    filtered = pixels[mask] if mask.sum() > n_colors * 10 else pixels

    k = min(n_colors, len(np.unique(filtered.reshape(-1, 3), axis=0)))
    kmeans = KMeans(n_clusters=k, n_init=4, random_state=42)
    labels = kmeans.fit_predict(filtered)

    counts = np.bincount(labels)
    order = np.argsort(-counts)  # most common cluster first

    dominant = []
    total = counts.sum()
    for idx in order:
        rgb = kmeans.cluster_centers_[idx]
        dominant.append({
            "hex": rgb_to_hex(tuple(rgb)),
            "coverage_pct": round(100 * counts[idx] / total, 1),
        })
    return dominant


def match_photo_to_shades(image_bytes, n_colors=5, matches_per_color=3):
    """
    Full pipeline: photo -> dominant colors -> nearest catalogue shades
    for each one. This is what the API endpoint calls.
    """
    dominant = extract_dominant_colors(image_bytes, n_colors=n_colors)
    results = []
    for color in dominant:
        matches = nearest_shades(color["hex"], n=matches_per_color)
        results.append({
            "detected_hex": color["hex"],
            "coverage_pct": color["coverage_pct"],
            "closest_shades": matches,
        })
    return results
