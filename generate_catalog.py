"""Generate catalog.json from the repo folder structure.

Run this after adding/removing files, then commit + push.

Usage:
    python generate_catalog.py
"""

import json
import os
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).parent
CATEGORIES = {
    "manga": {
        "name": "Truyện Tranh",
        "icon": "📚",
        "extensions": {".cbz", ".cbr", ".pdf"},
    },
    "novels": {
        "name": "Truyện Chữ",
        "icon": "📖",
        "extensions": {".epub", ".mobi", ".azw3", ".pdf", ".azw"},
    },
    "audiobooks": {
        "name": "Sách Nói",
        "icon": "🎧",
        "extensions": {".mp3", ".m4a", ".m4b", ".ogg", ".flac"},
    },
}


def scan_category(category_dir: Path, extensions: set) -> list[dict]:
    """Scan a category directory for files, supporting nested folders (series)."""
    items = []

    if not category_dir.exists():
        return items

    for root, dirs, files in os.walk(category_dir):
        root_path = Path(root)
        rel_root = root_path.relative_to(category_dir)

        # Series name = subfolder name, or empty for root-level files
        series = str(rel_root) if str(rel_root) != "." else ""

        for fname in sorted(files):
            fpath = root_path / fname
            ext = fpath.suffix.lower()

            if ext not in extensions:
                continue

            rel_path = fpath.relative_to(REPO_ROOT)
            size_bytes = fpath.stat().st_size

            item = {
                "filename": fname,
                "path": str(rel_path).replace("\\", "/"),
                "size": size_bytes,
                "size_mb": round(size_bytes / (1024 * 1024), 1),
                "series": series.replace("\\", "/") if series else None,
            }
            items.append(item)

    return items


def generate():
    catalog = {
        "version": 1,
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "repo": "thienlogin/retroreader-online",
        "categories": {},
    }

    total = 0
    for cat_id, cat_info in CATEGORIES.items():
        cat_dir = REPO_ROOT / cat_id
        items = scan_category(cat_dir, cat_info["extensions"])
        total += len(items)

        catalog["categories"][cat_id] = {
            "name": cat_info["name"],
            "icon": cat_info["icon"],
            "count": len(items),
            "items": items,
        }

    # Write catalog.json
    out = REPO_ROOT / "catalog.json"
    out.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated catalog.json: {total} items across {len(CATEGORIES)} categories")


if __name__ == "__main__":
    generate()
