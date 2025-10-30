#!/usr/bin/env python3
"""
Script to parse funrecords.de catalog and match with Last.fm albums
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Set
import unicodedata


def normalize_string(s: str) -> str:
    """
    Normalize string for comparison:
    - Remove diacritics
    - Convert to lowercase
    - Remove special characters
    - Strip whitespace
    """
    # Remove diacritics
    s = ''.join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')
    # Convert to lowercase
    s = s.lower()
    # Remove special characters except alphanumeric and spaces
    s = re.sub(r'[^a-z0-9\s]', '', s)
    # Collapse multiple spaces
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def parse_funrecords_line(line: str) -> Dict[str, str] | None:
    """
    Parse a line from c308.txt
    Format: ID---Type---Artist---Album---Price
    """
    parts = line.split('---')
    if len(parts) < 5:
        return None

    try:
        return {
            'id': parts[0].strip(),
            'type': parts[1].strip(),
            'artist': parts[2].strip(),
            'album': parts[3].strip(),
            'price': parts[4].strip(),
            'artist_normalized': normalize_string(parts[2]),
            'album_normalized': normalize_string(parts[3])
        }
    except Exception as e:
        return None


def load_funrecords_catalog(filepath: str) -> List[Dict[str, str]]:
    """Load and parse the entire funrecords catalog"""
    print(f"Loading funrecords catalog from {filepath}...")

    albums = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f, 1):
            if i % 50000 == 0:
                print(f"  Processed {i} lines...")

            parsed = parse_funrecords_line(line)
            if parsed:
                albums.append(parsed)

    print(f"✓ Loaded {len(albums)} albums from funrecords.de")
    return albums


def create_search_index(albums: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    """
    Create a search index for faster lookups
    Key: normalized "artist album" string
    Value: list of matching album entries
    """
    print("Creating search index...")
    index = {}

    for album in albums:
        # Create multiple keys for flexible matching
        keys = [
            f"{album['artist_normalized']} {album['album_normalized']}",
            album['album_normalized'],  # Album only
        ]

        for key in keys:
            if key not in index:
                index[key] = []
            index[key].append(album)

    print(f"✓ Created search index with {len(index)} entries")
    return index


def save_catalog_json(albums: List[Dict[str, str]], output_path: str):
    """Save parsed catalog as JSON for future use"""
    print(f"Saving catalog to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(albums, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved catalog")


if __name__ == "__main__":
    # Parse funrecords catalog
    catalog_file = "/Users/mareksulik/Documents/GitHub/lastfm/c308.txt"
    output_file = "/Users/mareksulik/Documents/GitHub/lastfm/funrecords_catalog.json"

    albums = load_funrecords_catalog(catalog_file)
    save_catalog_json(albums, output_file)

    # Create search index
    index = create_search_index(albums)

    # Save index
    index_file = "/Users/mareksulik/Documents/GitHub/lastfm/funrecords_index.json"
    print(f"Saving search index to {index_file}...")
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved search index")

    print("\n" + "="*50)
    print("STATISTICS:")
    print(f"Total albums in catalog: {len(albums)}")
    print(f"Search index entries: {len(index)}")
    print("="*50)
