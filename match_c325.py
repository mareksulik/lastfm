#!/usr/bin/env python3
"""Porovná Last.fm export scrobblov s katalógom Fun Records (formát cNNN.txt), CD aj LP.

Použitie: python3 match_c325.py <katalog.txt> <scrobbles.csv> <vystup.json>
"""
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict

FORMATS = {"CD", "2CD", "3CD", "4CD", "5CD", "XCD",
           "LP", "2LP", "3LP", "4LP", "5LP", "XLP"}
TOP_ARTISTS = 150
MIN_ALBUM_SCROBBLES = 20

EDITION_WORDS = (
    r"deluxe|remaster(ed)?|expanded|anniversary|edition|version|bonus|reissue|"
    r"special|collector'?s|legacy|super|mono|stereo|explicit|digipak|digi"
)


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"^the ", "", s.strip())
    return re.sub(r"\s+", " ", s).strip()


def strip_album(title):
    """Odstráni z názvu albumu doplnky ako (1995), [Deluxe Edition], - Remastered."""
    t = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", title)
    t = re.sub(r"\s+-\s+.*(" + EDITION_WORDS + r").*$", "", t, flags=re.I)
    t = re.sub(r":\s+.*(" + EDITION_WORDS + r").*$", "", t, flags=re.I)
    return norm(t)


def slug(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def parse_price(p):
    m = re.match(r"\s*([\d.,]+)\s*Eur", p)
    return float(m.group(1).replace(",", ".")) if m else None


def main(cat_path, csv_path, out_path):
    # Last.fm
    artist_cnt = Counter()
    album_cnt = Counter()
    artist_name, album_name = {}, {}
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            a = norm(row["artist"])
            if not a:
                continue
            artist_cnt[a] += 1
            artist_name.setdefault(a, row["artist"])
            if row["album"]:
                k = (a, strip_album(row["album"]))
                album_cnt[k] += 1
                album_name.setdefault(k, row["album"])

    artist_rank = {a: i for i, (a, _) in enumerate(artist_cnt.most_common(), 1)}
    album_rank = {k: i for i, (k, _) in enumerate(album_cnt.most_common(), 1)}
    wanted_artists = set(artist_cnt)

    # Katalóg
    catalogue = defaultdict(list)
    with open(cat_path, encoding="cp1252", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\r\n").split("---")
            if len(parts) < 5 or parts[1].strip() not in FORMATS:
                continue
            a = norm(parts[2])
            if a not in wanted_artists:
                continue
            item_id, typ, fr_artist, fr_title = (p.strip() for p in parts[:4])
            catalogue[a].append({
                "id": item_id,
                "type": typ,
                "artist": fr_artist,
                "title": fr_title,
                "title_key": strip_album(fr_title),
                "price": parse_price(parts[4]),
                "url": f"https://www.funrecords.de/en/catalogue/item/{item_id}-{slug(fr_title)}-{slug(fr_artist)}/",
            })

    # Každá ponuka (CD/LP) od interpreta z knižnice, ak ide o počúvaný album
    # alebo o interpreta z top N.
    top_set = {a for a, _ in artist_cnt.most_common(TOP_ARTISTS)}
    items = []
    for a, offers in catalogue.items():
        for it in offers:
            key = (a, it["title_key"])
            if it["title_key"] in ("same", "s t", "self titled"):
                key = (a, a)
            n = album_cnt.get(key, 0)
            if n >= MIN_ALBUM_SCROBBLES:
                kind = "album"
            elif a in top_set:
                kind = "artist"
            else:
                continue
            items.append({
                "kind": kind,
                "artist": artist_name[a],
                "artist_rank": artist_rank[a],
                "artist_scrobbles": artist_cnt[a],
                "lastfm_album": album_name.get(key) if n else None,
                "album_scrobbles": n,
                **{f"fr_{k}": v for k, v in it.items() if k != "title_key"},
            })
    items.sort(key=lambda r: (-r["album_scrobbles"], r["artist_rank"], r["fr_price"] or 0))

    top_artists = [
        {"rank": artist_rank[a], "artist": artist_name[a], "scrobbles": n,
         "offers_in_catalogue": len(catalogue.get(a, []))}
        for a, n in artist_cnt.most_common(TOP_ARTISTS)
    ]

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"items": items,
                   "top_artists": top_artists,
                   "stats": {"scrobbles": sum(artist_cnt.values()),
                             "artists": len(artist_cnt), "albums": len(album_cnt)}},
                  f, ensure_ascii=False, indent=1)
    kinds = Counter((r["kind"], "LP" if "LP" in r["fr_type"] else "CD") for r in items)
    print(f"items: {len(items)}", dict(kinds))


if __name__ == "__main__":
    main(*sys.argv[1:4])
