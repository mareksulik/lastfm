import json, sys
d = json.load(open(sys.argv[1]))
rows = [[{"album": "a", "artist": "r"}[r["kind"]], r["artist"], r["artist_rank"], r["artist_scrobbles"], r["lastfm_album"] or "",
         r["album_scrobbles"], int(r["fr_id"]), r["fr_type"], r["fr_title"], r["fr_price"],
         r["fr_url"].split("/item/")[1].rstrip("/")] for r in d["items"]]
data = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
html = open(sys.argv[2]).read().replace("/*DATA*/[]", data)
open(sys.argv[3], "w").write(html)
print(len(html))
