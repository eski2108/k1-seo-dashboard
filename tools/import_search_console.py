#!/usr/bin/env python3
"""Import Google Search Console data as the preferred ranking source.
Input: the 'Queries.csv' from Search Console > Performance > Export > CSV
(columns: Top queries, Clicks, Impressions, CTR, Position), optionally a
'Pages.csv' is ignored. Each tracked keyword found in the export gets a new
history entry with source 'Google Search Console (avg position, <range>)'.
Keywords not in the export are recorded as not_ranking for that source
(no impressions = not seen in Google for the period).
Usage: python3 tools/import_search_console.py Queries.csv --range "28 days to 25 Oct"
Then: python3 tools/check_rankings.py --rebuild-only
"""
import argparse, csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_rankings as cr
ap = argparse.ArgumentParser(); ap.add_argument("csv"); ap.add_argument("--range", default="last 28 days")
a = ap.parse_args()
rows = {}
for r in csv.DictReader(open(a.csv, encoding="utf-8-sig")):
    q = (r.get("Top queries") or r.get("Query") or "").strip().lower()
    if q: rows[q] = r
kws = cr.build_keywords(); hist = cr.load(cr.HIST, {}); src = f"Google Search Console (avg position, {a.range})"; n = 0
for k in kws:
    r = rows.get(k["keyword"])
    pos = round(float(r["Position"]), 1) if r else None
    hist.setdefault(k["keyword"], []).append(dict(position=pos, url=None, checked_depth=None, source=src, checked_at=cr.now(),
        clicks=int(r["Clicks"]) if r else 0, impressions=int(r["Impressions"]) if r else 0)); n += bool(r)
json.dump(hist, open(cr.HIST, "w"), indent=1); cr.rebuild(kws)
print(f"Imported {n} matching queries out of {len(kws)} tracked keywords")
