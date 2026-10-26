#!/usr/bin/env python3
"""Regenerate data.json for the K1 SEO dashboard.
Usage: python3 scripts/build_data.py [K1_SEO_DIR] [SEOMACHINE_DIR]
Defaults: /workspace/k1/seo and /workspace/seomachine. Reads keywords-300.csv,
stats-board-data.json, weekend PR CSV, weekend pages README, blog briefs and seomachine topics/."""
import csv, json, re, sys, pathlib, glob
SEO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/workspace/k1/seo")
SM = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "/workspace/seomachine")
OUT = pathlib.Path(__file__).resolve().parent.parent / "data.json"
sb = json.load(open(SEO / "stats-board-data.json"))
kw = [{"keyword": r["keyword"], "group": r["cluster"], "intent": r["intent"], "page": r["target_page"],
       "status": r["page_status"], "priority": int(r["priority"] or 3),
       "volume": r["volume"] or None, "difficulty": r["difficulty"] or None}
      for r in csv.DictReader(open(SEO / "keywords-300.csv"))]
pr = []
for f in sorted(glob.glob(str(SEO / "weekend-*/research/backlink-pr-opportunities-*.csv"))):
    for r in csv.DictReader(open(f)):
        g = lambda *ks: next((r[k].strip() for k in ks if r.get(k)), "")
        pr.append({"name": g("name"), "url": g("url"), "type": g("type"),
                   "why_relevant": g("why_relevant", "why"),
                   "how_to_pitch": g("how_to_pitch", "how to approach", "how_to_approach"),
                   "cost_or_caveat": g("cost_or_caveat", *[k for k in r if k and k.lower().startswith("cost")])})
drafts = []
for f in sorted(glob.glob(str(SEO / "weekend-*/pages/README.md"))):
    for line in open(f):
        m = re.match(r"\| ([a-z0-9-]+) \| (/[^|]*) \| ([^|]*) \| (.*) \|$", line.strip())
        if m: drafts.append({"type": "Page", "name": m[1], "url": m[2].strip(), "words": m[3].strip(), "notes": m[4].strip(), "status": "Awaiting Dean's OK"})
for f in sorted(glob.glob(str(SEO / "weekend-*/blog-briefs/*.md"))):
    t = open(f).readline().lstrip("# ").strip()
    drafts.append({"type": "Blog brief", "name": pathlib.Path(f).stem, "url": "", "words": "", "notes": t, "status": "Brief ready"})
briefs = []
for f in sorted((SM / "topics").glob("*.md")):
    if f.name.startswith("example"): continue
    txt = open(f).read()
    get = lambda k: (re.search(rf"\*\*{k}\*\*:\s*(.+)", txt) or [None, ""])[1].strip()
    briefs.append({"slug": f.stem, "title": txt.splitlines()[0].lstrip("# ").strip(), "url": get("URL"),
                   "primary": get("Primary keyword"), "secondary": get("Secondary"), "intent": get("Intent"),
                   "length": get("Length"), "command": f"/write topics/{f.name}"})
data = {"updated": sb["updated"], "rank_check_note": sb["rank_check_note"], "pages": sb["pages"],
        "citations": sb["citations"], "backlinks": sb["backlinks"], "outreach": sb["outreach"],
        "tracked_keywords": sb["keywords"], "not_targeting": sb["not_targeting"], "blockers": sb["blockers"],
        "work_log": sb["work_log"], "weekly_plan": sb["weekly_plan"], "keywords": kw, "pr_leads": pr,
        "drafts": drafts, "briefs": briefs}
if OUT.exists():  # keep fields written by other scripts (e.g. import_volumes.py)
    old = json.load(open(OUT))
    for k in ("volumes_updated", "volume_source"):
        if k in old: data[k] = old[k]
    if "keywords" in old:  # keep imported volumes
        vol = {x["keyword"]: x for x in old["keywords"]}
        for x in kw:
            o = vol.get(x["keyword"], {})
            for k, v in o.items():
                if x.get(k) in (None, ""): x[k] = v
def scrub(o):  # never publish the registered-office address
    if isinstance(o, dict): return {k: scrub(v) for k, v in o.items()}
    if isinstance(o, list): return [scrub(v) for v in o]
    if isinstance(o, str):
        return re.sub(r"\(?Gable House[^)\n]*?W4 1QP\)?", "(see NAP rules)", o)
    return o
data = scrub(data)
json.dump(data, open(OUT, "w"), indent=1, ensure_ascii=False)
print(f"wrote {OUT}: {len(kw)} keywords, {len(pr)} PR leads, {len(drafts)} drafts, {len(briefs)} briefs")
