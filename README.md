# Last.fm to Funrecords Matcher

Nástroj na nájdenie vašich najpočúvanejších Last.fm albumov v katalógu funrecords.de eshop.

## Výsledky

- **Analyzovaných Last.fm albumov:** 8,371
- **Nájdených zhôd na funrecords.de:** 797
- **Match rate:** 9.5%
- **Funrecords katalóg:** 370,640 albumov

## Súbory

### Výstupné súbory (použite tieto!)
- `final_matches.json` - JSON dáta so všetkými zhodami
- `final_matches.txt` - Prehľadný textový zoznam
- `final_matches.csv` - Pre import do Excel/Google Sheets

### Zdrojové dáta
- `scrobbles-shulo-1761666593.csv` - Export z Last.fm (22MB)
- `c308.txt` - Katalóg funrecords.de (32MB, 370,640 albumov)
- `lastfm_albums_from_csv.json` - Agregované Last.fm albumy (1.4MB)

### Skripty
- `final_match.py` - Hlavný matching algoritmus
- `parse_funrecords.py` - Parser funrecords katalógu
- `process_csv_and_match.py` - Spracovanie CSV (starší, pomalší)

### Dátové súbory (veľké)
- `funrecords_catalog.json` - Funrecords katalóg v JSON (96MB)
- `funrecords_index.json` - Search index (241MB)

## Ako to funguje

1. **Načítanie Last.fm dát**
   - Spracuje CSV export z Last.fm
   - Agreguje scrobbles podľa album + artist
   - Celkom 8,371 unikátnych albumov

2. **Indexovanie funrecords katalógu**
   - Streamuje c308.txt (bez načítania celého do pamäte)
   - Indexuje iba albumy od interpretov vo vašej knižnici
   - Výsledok: 15,236 relevantných albumov z 1,299 interpretov

3. **Matching algoritmus**
   - Word-based similarity (rýchle)
   - Threshold 0.6 (60% zhoda)
   - Porovnáva: artist + album názov
   - Čas behu: ~30 sekúnd

4. **Výstup**
   - Zoradené podľa počtu scrobbles (najpočúvanejšie navrchu)
   - Obsahuje: artist, album, scrobbles, cenu, typ média, ID

## TOP 10 Najpočúvanejších albumov dostupných na Funrecords

1. **Pavement - Wowee Zowee** (771 scrobbles) - 5,97€
2. **Modeselektor - Monkeytown** (656 scrobbles) - 3,06€
3. **Pavement - Crooked Rain, Crooked Rain** (617 scrobbles) - 3,19€
4. **Pixies - Trompe le Monde** (575 scrobbles) - 4,64€
5. **Arcade Fire - Reflektor** (557 scrobbles) - 6,14€
6. **Arcade Fire - The Suburbs** (518 scrobbles) - 3,10€
7. **Avalanches - Since I Left You** (498 scrobbles) - 2,56€
8. **Pixies - Bossanova** (491 scrobbles) - 5,23€
9. **Interpol - Turn on the Bright Lights** (488 scrobbles) - 9,00€
10. **Beirut - Gulag Orkestar** (424 scrobbles) - 11,90€

## Použitie

```bash
# Nainštalovať dependencies
python3 -m venv venv
source venv/bin/activate
pip install beautifulsoup4

# Spustiť matching
python3 final_match.py
```

## Technické detaily

- **Programovací jazyk:** Python 3
- **Normalizácia:** Odstránenie diakritiky, lowercase, odstránenie špeciálnych znakov
- **Similarity:** Word-based Jaccard similarity (intersection/union)
- **Optimalizácia:** Artist-based indexing (O(N+M) namiesto O(N×M))
- **Pamäťová efektivita:** Streaming read z c308.txt

## Štatistiky

- Vaše Last.fm albumy: 8,371
- Unikátni interpreti: 3,803
- Funrecords katalóg: 370,640 albumov
- Relevantné funrecords albumy: 15,236 (od 1,299 interpretov)
- Nájdené zhody: 797 (9.5% match rate)

---

Vytvorené: 30. október 2025
