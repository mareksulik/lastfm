#!/usr/bin/env python3
"""
Final matching script - optimized and guaranteed to work
"""

import json
import unicodedata
import re
from collections import defaultdict
from typing import Dict, List, Set


def normalize_string(s: str) -> str:
    """Normalize string for comparison"""
    if not s:
        return ""
    # Remove diacritics
    s = ''.join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')
    # Lowercase and remove special chars
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s]', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def word_similarity(s1: str, s2: str) -> float:
    """Fast word-based similarity"""
    words1 = set(s1.split())
    words2 = set(s2.split())

    if not words1 or not words2:
        return 0.0

    intersection = len(words1 & words2)
    union = len(words1 | words2)

    return intersection / union if union > 0 else 0.0


def parse_funrecords_line(line: str) -> Dict | None:
    """Parse single line from c308.txt"""
    parts = line.split('---')
    if len(parts) < 5:
        return None

    try:
        return {
            'id': parts[0].strip(),
            'type': parts[1].strip(),
            'artist': parts[2].strip(),
            'album': parts[3].strip(),
            'price': parts[4].strip()
        }
    except:
        return None


# STEP 1: Load Last.fm albums
print("=" * 80)
print("STEP 1: Loading Last.fm albums...")
print("=" * 80)

with open('/Users/mareksulik/Documents/GitHub/lastfm/lastfm_albums_from_csv.json', 'r', encoding='utf-8') as f:
    lastfm_albums = json.load(f)

print(f"✓ Loaded {len(lastfm_albums):,} Last.fm albums")

# Create set of artists we care about
lastfm_artists = set()
for album in lastfm_albums:
    lastfm_artists.add(album['artist_normalized'])

print(f"✓ Extracted {len(lastfm_artists):,} unique artists from your library")


# STEP 2: Build targeted index from c308.txt
print("\n" + "=" * 80)
print("STEP 2: Building targeted index from funrecords catalog...")
print("=" * 80)

funrecords_index = defaultdict(list)
total_lines = 0
indexed_albums = 0

with open('/Users/mareksulik/Documents/GitHub/lastfm/c308.txt', 'r', encoding='utf-8', errors='ignore') as f:
    for line_num, line in enumerate(f, 1):
        total_lines = line_num

        if line_num % 50000 == 0:
            print(f"  Processed {line_num:,} lines... (indexed {indexed_albums:,} relevant albums)")

        fr = parse_funrecords_line(line)
        if not fr:
            continue

        artist_norm = normalize_string(fr['artist'])

        # Only index if this artist is in your Last.fm library
        if artist_norm in lastfm_artists:
            album_norm = normalize_string(fr['album'])
            funrecords_index[artist_norm].append({
                'artist': fr['artist'],
                'album': fr['album'],
                'album_norm': album_norm,
                'price': fr['price'],
                'type': fr['type'],
                'id': fr['id']
            })
            indexed_albums += 1

print(f"✓ Processed {total_lines:,} total lines")
print(f"✓ Indexed {indexed_albums:,} relevant albums from {len(funrecords_index):,} matching artists")


# STEP 3: Match albums
print("\n" + "=" * 80)
print("STEP 3: Matching albums...")
print("=" * 80)

matches = []

for i, lfm in enumerate(lastfm_albums, 1):
    if i % 100 == 0:
        print(f"  Matching {i:,}/{len(lastfm_albums):,}... (found {len(matches):,} matches)")

    artist_norm = lfm['artist_normalized']
    album_norm = lfm['album_normalized']

    # Get funrecords albums for this artist
    fr_albums = funrecords_index.get(artist_norm, [])

    if not fr_albums:
        continue

    # Find best match
    best_match = None
    best_score = 0

    lfm_full = f"{artist_norm} {album_norm}"

    for fr in fr_albums:
        fr_full = f"{artist_norm} {fr['album_norm']}"

        # Calculate similarity
        score = word_similarity(lfm_full, fr_full)

        if score > best_score:
            best_score = score
            best_match = fr

    # Accept if good enough match
    if best_score >= 0.6 and best_match:
        matches.append({
            'lastfm_artist': lfm['artist'],
            'lastfm_album': lfm['album'],
            'scrobbles': lfm['scrobbles'],
            'funrecords_artist': best_match['artist'],
            'funrecords_album': best_match['album'],
            'price': best_match['price'],
            'type': best_match['type'],
            'id': best_match['id'],
            'similarity': round(best_score, 3)
        })

print(f"✓ Completed matching")
print(f"✓ Found {len(matches):,} matches out of {len(lastfm_albums):,} albums")


# STEP 4: Sort and save
print("\n" + "=" * 80)
print("STEP 4: Saving results...")
print("=" * 80)

matches.sort(key=lambda x: x['scrobbles'], reverse=True)

# JSON
output_json = '/Users/mareksulik/Documents/GitHub/lastfm/final_matches.json'
with open(output_json, 'w', encoding='utf-8') as f:
    json.dump(matches, f, ensure_ascii=False, indent=2)
print(f"✓ Saved {output_json}")

# TXT
output_txt = '/Users/mareksulik/Documents/GitHub/lastfm/final_matches.txt'
with open(output_txt, 'w', encoding='utf-8') as f:
    f.write("LAST.FM ALBUMS DOSTUPNÉ NA FUNRECORDS.DE\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"Celkovo nájdených: {len(matches):,} albumov\n")
    f.write(f"Z vašich {len(lastfm_albums):,} albumov\n")
    f.write(f"Match rate: {len(matches)/len(lastfm_albums)*100:.1f}%\n\n")
    f.write("Zoradené podľa počtu scrobbles (najviac počúvané hore)\n\n")
    f.write("=" * 80 + "\n\n")

    for i, m in enumerate(matches, 1):
        f.write(f"{i}. {m['lastfm_artist']} - {m['lastfm_album']}\n")
        f.write(f"   Scrobbles: {m['scrobbles']:,}\n")
        f.write(f"   Funrecords: {m['funrecords_artist']} - {m['funrecords_album']}\n")
        f.write(f"   Cena: {m['price']} | Typ: {m['type']}\n")
        f.write(f"   Zhoda: {m['similarity']:.0%} | ID: {m['id']}\n")
        f.write("\n" + "-" * 80 + "\n\n")

print(f"✓ Saved {output_txt}")

# CSV
output_csv = '/Users/mareksulik/Documents/GitHub/lastfm/final_matches.csv'
with open(output_csv, 'w', encoding='utf-8') as f:
    f.write("Rank,Artist,Album,Scrobbles,FR_Artist,FR_Album,Price,Type,Match,ID\n")
    for i, m in enumerate(matches, 1):
        f.write(f'{i},"{m["lastfm_artist"]}","{m["lastfm_album"]}",{m["scrobbles"]},')
        f.write(f'"{m["funrecords_artist"]}","{m["funrecords_album"]}","{m["price"]}","{m["type"]}",')
        f.write(f'{m["similarity"]},{m["id"]}\n')

print(f"✓ Saved {output_csv}")


# SUMMARY
print("\n" + "=" * 80)
print("ZHRNUTIE:")
print("=" * 80)
print(f"Vaše Last.fm albumy: {len(lastfm_albums):,}")
print(f"Funrecords katalóg: {total_lines:,} albumov")
print(f"Relevantné funrecords albumy: {indexed_albums:,}")
print(f"Nájdené zhody: {len(matches):,}")
print(f"Match rate: {len(matches)/len(lastfm_albums)*100:.1f}%")
print("=" * 80)

if matches:
    print("\nTOP 10 NAJPOČÚVANEJŠÍCH S ZHODOU:")
    print("-" * 80)
    for i, m in enumerate(matches[:10], 1):
        print(f"{i}. {m['lastfm_artist']} - {m['lastfm_album']}")
        print(f"   {m['scrobbles']:,} scrobbles | {m['price']} | {m['similarity']:.0%} zhoda")
