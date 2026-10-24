#!/usr/bin/env python3
"""Fill real search volumes into data.json and the keyword CSV.
Usage:
  python3 scripts/import_volumes.py planner_export.csv      # Google Keyword Planner export (UTF-16 or UTF-8)
  python3 scripts/import_volumes.py dataforseo.json         # DataForSEO search_volume response
Options: --csv PATH (default ../seomachine/research/k1-keywords-300.csv)
Only keywords found in the source are updated. Nothing is estimated."""
import csv, io, json, re, sys, os, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def num(v):
    if v in (None, ""): return None
    s = str(v).replace(",", "").replace("£", "").replace("$", "").strip()
    if re.fullmatch(r"[\d.]+", s): return float(s) if "." in s else int(s)
    return None
def read_planner(path):
    raw = open(path, "rb").read()
    txt = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig")
    lines = txt.splitlines()
    start = next(i for i, l in enumerate(lines) if re.match(r"keyword[\t,]", l.lower()))
    delim = "\t" if "\t" in lines[start] else ","
    out = {}
    for r in csv.DictReader(io.StringIO("\n".join(lines[start:])), delimiter=delim):
        kw = (r.get("Keyword") or "").strip().lower()
        if not kw: continue
        months = [k for k in r if k and k.startswith("Searches:")]
        lo, hi = num(r.get("Top of page bid (low range)")), num(r.get("Top of page bid (high range)"))
        out[kw] = {"volume": num(r.get("Avg. monthly searches")), "volume_range": None if num(r.get("Avg. monthly searches")) is not None else (r.get("Avg. monthly searches") or None),
                   "cpc": round((lo + hi) / 2, 2) if lo is not None and hi is not None else (hi or lo),
                   "trend": [num(r[m]) for m in months][-12:] or None, "vol_source": "Google Keyword Planner"}
    return out
def read_dfs(path):
    j = json.load(open(path)); out = {}
    items = j.get("results") if isinstance(j, dict) and "results" in j else [x for t in j.get("tasks", []) for x in (t.get("result") or [])]
    for x in items:
        tr = x.get("trend") or [m.get("search_volume") for m in reversed((x.get("monthly_searches") or [])[:12])]
        out[x["keyword"].lower()] = {"volume": x.get("search_volume", x.get("volume")), "cpc": x.get("cpc"), "trend": tr or None, "vol_source": "DataForSEO (Google Ads), UK"}
    return out
def main():
    a = sys.argv[1:]; csvp = os.path.join(ROOT, "..", "seomachine", "research", "k1-keywords-300.csv")
    if "--csv" in a: i = a.index("--csv"); csvp = a[i + 1]; del a[i:i + 2]
    src = a[0]; V = read_dfs(src) if src.endswith(".json") else read_planner(src)
    dp = os.path.join(ROOT, "data.json"); D = json.load(open(dp)); n = 0
    for k in D["keywords"]:
        v = V.get(k["keyword"].lower())
        if v: k.update(v); n += 1
    D["volumes_updated"] = datetime.date.today().isoformat(); D["volume_source"] = next(iter(V.values()))["vol_source"] if V else None
    json.dump(D, open(dp, "w"), ensure_ascii=False, indent=1)
    if os.path.exists(csvp):
        rows = list(csv.DictReader(open(csvp))); f = list(rows[0].keys())
        for c in ("cpc", "trend"):
            if c not in f: f.append(c)
        for r in rows:
            v = V.get(r["keyword"].lower())
            if v:
                r["volume"] = v["volume"] if v["volume"] is not None else (v.get("volume_range") or "")
                r["cpc"] = v["cpc"] if v["cpc"] is not None else ""; r["trend"] = " ".join(str(t) for t in (v["trend"] or []) if t is not None); r["source"] = v["vol_source"]
        w = csv.DictWriter(open(csvp, "w", newline=""), fieldnames=f); w.writeheader(); w.writerows(rows)
    print(f"Updated {n} of {len(D['keywords'])} keywords from {src}")
if __name__ == "__main__": main()
