#!/usr/bin/env python3
"""Porovná Last.fm export scrobblov s katalógom Fun Records (formát cNNN.txt).

Použitie: python3 match_c325.py <katalog.txt> <scrobbles.csv> <vystup.json>
"""
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict

CD_TYPES = {"CD", "2CD", "3CD", "4CD", "5CD", "XCD"}
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
            if len(parts) < 5 or parts[1].strip() not in CD_TYPES:
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

    # 1) Top albumy, ktoré sú v ponuke
    album_rows = []
    for (a, t), n in album_cnt.most_common():
        if n < MIN_ALBUM_SCROBBLES or not t:
            continue
        hits = []
        for it in catalogue.get(a, []):
            key = it["title_key"]
            if key == t or (key in ("same", "s t", "self titled") and t == a):
                hits.append(it)
        if not hits:
            continue
        hits.sort(key=lambda x: (x["price"] is None, x["price"]))
        best = hits[0]
        album_rows.append({
            "album_rank": album_rank[(a, t)],
            "artist": artist_name[a],
            "album": album_name[(a, t)],
            "scrobbles": n,
            "artist_scrobbles": artist_cnt[a],
            "offers": len(hits),
            **{f"fr_{k}": v for k, v in best.items() if k != "title_key"},
        })

    matched_ids = {r["fr_id"] for r in album_rows}
    matched_keys = {(norm(r["artist"]), strip_album(r["album"])) for r in album_rows}

    # 2) Ďalšie CD od top interpretov (albumy, ktoré veľa nepočúvaš alebo ich nepoznáš)
    artist_rows = []
    for a, n in artist_cnt.most_common(TOP_ARTISTS):
        for it in catalogue.get(a, []):
            if it["id"] in matched_ids or (a, it["title_key"]) in matched_keys:
                continue
            artist_rows.append({
                "artist_rank": artist_rank[a],
                "artist": artist_name[a],
                "artist_scrobbles": n,
                "album_scrobbles": album_cnt.get((a, it["title_key"]), 0),
                **{f"fr_{k}": v for k, v in it.items() if k != "title_key"},
            })

    top_artists = [
        {"rank": artist_rank[a], "artist": artist_name[a], "scrobbles": n,
         "cd_in_catalogue": len(catalogue.get(a, []))}
        for a, n in artist_cnt.most_common(TOP_ARTISTS)
    ]

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"albums": album_rows, "artist_cds": artist_rows,
                   "top_artists": top_artists,
                   "stats": {"scrobbles": sum(artist_cnt.values()),
                             "artists": len(artist_cnt), "albums": len(album_cnt)}},
                  f, ensure_ascii=False, indent=1)
    print(f"albums matched: {len(album_rows)}, artist CDs: {len(artist_rows)}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
