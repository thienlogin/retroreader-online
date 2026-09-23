"""Download free public domain ebooks from Project Gutenberg.

Downloads epub files + cover images for the retroreader-online repo.
"""

import os
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

REPO_ROOT = Path(r"C:\chum\trimui\retroreader-online")

# Project Gutenberg books - popular public domain titles
# Format: (gutenberg_id, title, author, category_folder)
BOOKS = [
    # === NOVELS (English Classics) ===
    (11, "Alice's Adventures in Wonderland", "Lewis Carroll", "novels/English Classics"),
    (1342, "Pride and Prejudice", "Jane Austen", "novels/English Classics"),
    (84, "Frankenstein", "Mary Shelley", "novels/English Classics"),
    (1661, "The Adventures of Sherlock Holmes", "Arthur Conan Doyle", "novels/English Classics"),
    (345, "Dracula", "Bram Stoker", "novels/English Classics"),
    (2701, "Moby Dick", "Herman Melville", "novels/English Classics"),
    (174, "The Picture of Dorian Gray", "Oscar Wilde", "novels/English Classics"),
    (1232, "The Prince", "Niccolo Machiavelli", "novels/English Classics"),

    # === NOVELS (Sci-Fi & Fantasy) ===
    (35, "The Time Machine", "H.G. Wells", "novels/Sci-Fi"),
    (36, "The War of the Worlds", "H.G. Wells", "novels/Sci-Fi"),
    (43, "The Strange Case of Dr. Jekyll and Mr. Hyde", "R.L. Stevenson", "novels/Sci-Fi"),
    (84, "Frankenstein", "Mary Shelley", "novels/Sci-Fi"),
    (215, "The Call of the Wild", "Jack London", "novels/Adventure"),

    # === NOVELS (Adventure) ===
    (120, "Treasure Island", "Robert Louis Stevenson", "novels/Adventure"),
    (1184, "The Count of Monte Cristo", "Alexandre Dumas", "novels/Adventure"),
    (2148, "The Works of Edgar Allan Poe Vol 1", "Edgar Allan Poe", "novels/Horror"),

    # === NOVELS (Philosophy & Non-Fiction) ===
    (1497, "The Republic", "Plato", "novels/Philosophy"),
    (5827, "The Problems of Philosophy", "Bertrand Russell", "novels/Philosophy"),
    (4300, "Ulysses", "James Joyce", "novels/Literary Fiction"),
]

# Remove duplicates by ID
seen_ids = set()
unique_books = []
for book in BOOKS:
    if book[0] not in seen_ids:
        seen_ids.add(book[0])
        unique_books.append(book)
BOOKS = unique_books


def download_file(url: str, dest: Path, max_retries: int = 3) -> bool:
    """Download a file with retries."""
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (RetroReader Online Library)"
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                return True
        except Exception as e:
            print(f"  Retry {attempt+1}/{max_retries}: {e}")
            time.sleep(2)
    return False


def get_gutenberg_epub_url(book_id: int) -> str:
    """Get the epub download URL for a Gutenberg book."""
    # Try multiple URL patterns
    return f"https://www.gutenberg.org/ebooks/{book_id}.epub3.images"


def get_gutenberg_cover_url(book_id: int) -> str:
    """Get cover image URL."""
    return f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.cover.medium.jpg"


def main():
    print(f"Downloading {len(BOOKS)} books from Project Gutenberg...")
    print(f"Destination: {REPO_ROOT}")
    print()

    results = []

    for book_id, title, author, folder in BOOKS:
        safe_title = "".join(c if c.isalnum() or c in " -_'" else "_" for c in title)
        safe_title = safe_title.strip()[:80]

        dest_dir = REPO_ROOT / folder
        epub_path = dest_dir / f"{safe_title}.epub"
        cover_path = dest_dir / f"{safe_title}.jpg"

        print(f"[{book_id}] {title} by {author}")

        # Download EPUB
        if epub_path.exists():
            print(f"  EPUB already exists, skipping")
        else:
            epub_url = get_gutenberg_epub_url(book_id)
            print(f"  Downloading EPUB...")
            if download_file(epub_url, epub_path):
                size_kb = epub_path.stat().st_size / 1024
                print(f"  EPUB OK ({size_kb:.0f} KB)")
            else:
                # Try alternative URL pattern
                alt_url = f"https://www.gutenberg.org/ebooks/{book_id}.epub.images"
                if download_file(alt_url, epub_path):
                    size_kb = epub_path.stat().st_size / 1024
                    print(f"  EPUB OK (alt) ({size_kb:.0f} KB)")
                else:
                    print(f"  EPUB FAILED!")
                    continue

        # Download Cover
        if cover_path.exists():
            print(f"  Cover already exists, skipping")
        else:
            cover_url = get_gutenberg_cover_url(book_id)
            print(f"  Downloading cover...")
            if download_file(cover_url, cover_path):
                size_kb = cover_path.stat().st_size / 1024
                print(f"  Cover OK ({size_kb:.0f} KB)")
            else:
                print(f"  Cover not available")

        results.append({
            "id": book_id,
            "title": title,
            "author": author,
            "folder": folder,
            "epub": str(epub_path.relative_to(REPO_ROOT)).replace("\\", "/"),
            "cover": str(cover_path.relative_to(REPO_ROOT)).replace("\\", "/") if cover_path.exists() else None,
        })

        # Be nice to Gutenberg servers
        time.sleep(1)

    print(f"\nDone! Downloaded {len(results)} books.")
    print("\nRun 'python generate_catalog.py' to update catalog.json")


if __name__ == "__main__":
    main()
