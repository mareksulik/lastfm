#!/usr/bin/env python3
"""
Script to process Last.fm CSV export and match with funrecords.de catalog
"""

import csv
import json
import unicodedata
import re
from pathlib import Path
from typing import Dict, List
from collections import defaultdict
from difflib import SequenceMatcher


def normalize_string(s: str) -> str:
    """
    Normalize string for comparison:
    - Remove diacritics
    - Convert to lowercase
    - Remove special characters
    - Strip whitespace
    """
    if not s:
        return ""
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


def similarity_score(s1: str, s2: str) -> float:
    """Calculate similarity between two strings (0-1)"""
    return SequenceMatcher(None, s1, s2).ratio()


def process_lastfm_csv(csv_file: str) -> List[Dict]:
    """
    Process Last.fm CSV export and aggregate scrobbles by album
    """
    print(f"Processing Last.fm CSV: {csv_file}")

    album_scrobbles = defaultdict(int)
    album_info = {}

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader, 1):
            if i % 10000 == 0:
                print(f"  Processed {i:,} scrobbles...")

            artist = row.get('artist', '').strip()
            album = row.get('album', '').strip()

            # Skip if album is empty
            if not album or not artist:
                continue

            # Create unique key
            key = f"{artist}|||{album}"
            album_scrobbles[key] += 1

            # Store album info (only once)
            if key not in album_info:
                album_info[key] = {
                    'artist': artist,
                    'album': album,
                    'artist_normalized': normalize_string(artist),
                    'album_normalized': normalize_string(album)
                }

    print(f"✓ Processed {i:,} total scrobbles")
    print(f"✓ Found {len(album_scrobbles)} unique albums")

    # Convert to list and add scrobble counts
    albums = []
    for key, count in album_scrobbles.items():
        info = album_info[key]
        info['scrobbles'] = count
        albums.append(info)

    # Sort by scrobbles (descending)
    albums.sort(key=lambda x: x['scrobbles'], reverse=True)

    return albums


def create_funrecords_index(catalog: List[Dict]) -> Dict[str, List[Dict]]:
    """Create an index by artist for faster lookups"""
    print("Creating artist index for faster matching...")
    index = defaultdict(list)

    for album in catalog:
        # Index by first few characters of normalized artist
        artist_key = album['artist_normalized'][:3] if album['artist_normalized'] else 'zzz'
        index[artist_key].append(album)

    print(f"✓ Created index with {len(index)} buckets")
    return index


def find_matches(lastfm_albums: List[Dict], funrecords_catalog: List[Dict],
                 threshold: float = 0.85) -> List[Dict]:
    """
    Match Last.fm albums with funrecords catalog (optimized with indexing)
    Returns list of matches with similarity scores
    """
    print(f"\nMatching {len(lastfm_albums)} Last.fm albums with {len(funrecords_catalog)} funrecords albums...")
    print(f"Similarity threshold: {threshold}")

    # Create index for faster lookup
    fr_index = create_funrecords_index(funrecords_catalog)

    matches = []

    for i, lfm_album in enumerate(lastfm_albums):
        if (i + 1) % 50 == 0:
            print(f"  Processing {i + 1}/{len(lastfm_albums)}... (found {len(matches)} matches so far)")

        best_match = None
        best_score = 0

        # Create search keys
        lfm_key_full = f"{lfm_album['artist_normalized']} {lfm_album['album_normalized']}"
        lfm_key_album = lfm_album['album_normalized']

        # Get candidate albums from index (same artist prefix + nearby prefixes)
        artist_prefix = lfm_album['artist_normalized'][:3] if lfm_album['artist_normalized'] else 'zzz'
        candidates = []

        # Check exact prefix and all catalog if no matches
        if artist_prefix in fr_index:
            candidates.extend(fr_index[artist_prefix])

        # If no candidates, do full scan (slow but thorough)
        if not candidates:
            candidates = funrecords_catalog

        for fr_album in candidates:
            fr_key_full = f"{fr_album['artist_normalized']} {fr_album['album_normalized']}"

            # Quick skip if completely different
            if len(set(lfm_key_full.split()) & set(fr_key_full.split())) == 0:
                continue

            # Calculate similarity scores
            score_full = similarity_score(lfm_key_full, fr_key_full)
            score_album = similarity_score(lfm_key_album, fr_album['album_normalized'])
            score_artist = similarity_score(lfm_album['artist_normalized'], fr_album['artist_normalized'])

            # Weighted score: prioritize full match, but consider album and artist separately
            final_score = max(
                score_full,
                (score_album * 0.7 + score_artist * 0.3)
            )

            if final_score > best_score:
                best_score = final_score
                best_match = fr_album

        # Only include if similarity is above threshold
        if best_score >= threshold and best_match:
            matches.append({
                'lastfm': lfm_album,
                'funrecords': best_match,
                'similarity': round(best_score, 3),
                'scrobbles': lfm_album['scrobbles']
            })

    print(f"✓ Found {len(matches)} matches (threshold: {threshold})")
    return matches


def save_matches(matches: List[Dict], output_file: str):
    """Save matches to JSON, TXT, and CSV formats"""
    # Sort by scrobbles (descending)
    matches_sorted = sorted(matches, key=lambda x: x['scrobbles'], reverse=True)

    # Save JSON
    print(f"\nSaving matches to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(matches_sorted, f, ensure_ascii=False, indent=2)

    # Save human-readable text
    txt_file = output_file.replace('.json', '.txt')
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("LAST.FM ALBUMS AVAILABLE ON FUNRECORDS.DE\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total matches found: {len(matches_sorted)}\n")
        f.write("Sorted by scrobble count (most played first)\n\n")
        f.write("=" * 80 + "\n\n")

        for i, match in enumerate(matches_sorted, 1):
            lfm = match['lastfm']
            fr = match['funrecords']

            f.write(f"{i}. {lfm['artist']} - {lfm['album']}\n")
            f.write(f"   Last.fm scrobbles: {lfm['scrobbles']:,}\n")
            f.write(f"   Funrecords: {fr['artist']} - {fr['album']}\n")
            f.write(f"   Price: {fr['price']} | Type: {fr['type']}\n")
            f.write(f"   Match similarity: {match['similarity']:.1%}\n")
            f.write(f"   Funrecords ID: {fr['id']}\n")
            f.write("\n" + "-" * 80 + "\n\n")

    print(f"✓ Saved matches to {txt_file}")

    # Save CSV for easy import to Excel
    csv_file = output_file.replace('.json', '.csv')
    with open(csv_file, 'w', encoding='utf-8') as f:
        f.write("Rank,Artist,Album,Scrobbles,Funrecords_Artist,Funrecords_Album,Price,Type,Similarity,ID\n")
        for i, match in enumerate(matches_sorted, 1):
            lfm = match['lastfm']
            fr = match['funrecords']
            f.write(f'{i},"{lfm["artist"]}","{lfm["album"]}",{lfm["scrobbles"]},')
            f.write(f'"{fr["artist"]}","{fr["album"]}","{fr["price"]}","{fr["type"]}",')
            f.write(f'{match["similarity"]},{fr["id"]}\n')

    print(f"✓ Saved CSV to {csv_file}")


if __name__ == "__main__":
    # Load funrecords catalog
    catalog_file = "/Users/mareksulik/Documents/GitHub/lastfm/funrecords_catalog.json"

    if not Path(catalog_file).exists():
        print(f"ERROR: Catalog file not found: {catalog_file}")
        print("Please run parse_funrecords.py first!")
        exit(1)

    print("Loading funrecords catalog...")
    with open(catalog_file, 'r', encoding='utf-8') as f:
        funrecords_catalog = json.load(f)
    print(f"✓ Loaded {len(funrecords_catalog):,} albums")

    # Process Last.fm CSV
    csv_file = "/Users/mareksulik/Documents/GitHub/lastfm/scrobbles-shulo-1761666593.csv"

    if not Path(csv_file).exists():
        print(f"\nERROR: CSV file not found: {csv_file}")
        exit(1)

    lastfm_albums = process_lastfm_csv(csv_file)

    # Save Last.fm albums
    lastfm_json = "/Users/mareksulik/Documents/GitHub/lastfm/lastfm_albums_from_csv.json"
    print(f"\nSaving Last.fm albums to {lastfm_json}...")
    with open(lastfm_json, 'w', encoding='utf-8') as f:
        json.dump(lastfm_albums, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved {len(lastfm_albums)} unique albums")

    # Find matches with different thresholds
    print("\n" + "=" * 80)
    print("MATCHING WITH THRESHOLD 0.80 (more matches, less strict)")
    print("=" * 80)
    matches_80 = find_matches(lastfm_albums, funrecords_catalog, threshold=0.80)
    save_matches(matches_80, "/Users/mareksulik/Documents/GitHub/lastfm/matched_albums_80.json")

    print("\n" + "=" * 80)
    print("MATCHING WITH THRESHOLD 0.90 (fewer matches, more strict)")
    print("=" * 80)
    matches_90 = find_matches(lastfm_albums, funrecords_catalog, threshold=0.90)
    save_matches(matches_90, "/Users/mareksulik/Documents/GitHub/lastfm/matched_albums_90.json")

    print("\n" + "=" * 80)
    print("FINAL SUMMARY:")
    print(f"Last.fm unique albums: {len(lastfm_albums):,}")
    print(f"Funrecords catalog: {len(funrecords_catalog):,}")
    print(f"Matches (80% threshold): {len(matches_80):,} ({len(matches_80)/len(lastfm_albums)*100:.1f}%)")
    print(f"Matches (90% threshold): {len(matches_90):,} ({len(matches_90)/len(lastfm_albums)*100:.1f}%)")
    print("=" * 80)
    print("\nTop 10 most scrobbled albums with matches (80% threshold):")
    for i, match in enumerate(matches_80[:10], 1):
        lfm = match['lastfm']
        fr = match['funrecords']
        print(f"{i}. {lfm['artist']} - {lfm['album']} ({lfm['scrobbles']:,} scrobbles) - {fr['price']}")
