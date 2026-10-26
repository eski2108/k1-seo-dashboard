#!/usr/bin/env python3
"""K1 Removals rank checker.
Builds the keyword list (keyword strategy + Google Ads set), checks where
k1removals.com ranks, updates data/rankings-history.json and data/rankings.json,
and optionally commits + pushes.  Never invents positions.

Usage:
  python3 tools/check_rankings.py                 # check all, write JSON
  python3 tools/check_rankings.py --push          # ... and git commit/push
  python3 tools/check_rankings.py --limit 5       # test on 5 keywords
  python3 tools/check_rankings.py --rebuild-only  # just rebuild rankings.json
Source: Google UK results page in headless Chrome (gl=uk, hl=en-GB, pws=0,
non-personalised, no login), top DEPTH results. If Google shows a captcha the
keyword falls back to Bing UK (cc=GB) and is labelled as such.
"""
import argparse, base64, csv, io, json, os, random, re, subprocess, sys, time, urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRATEGY = os.environ.get("K1_KW_STRATEGY", "/workspace/k1/seo/keyword-strategy-2026-10-25.md")
ADS = os.environ.get("K1_ADS_DIR", "/workspace/k1/ads")
HIST = os.path.join(ROOT, "data", "rankings-history.json")
OUT = os.path.join(ROOT, "data", "rankings.json")
KWS = os.path.join(ROOT, "data", "rank-keywords.json")
DOMAIN = "k1removals.com"
DDG_LABEL = "DuckDuckGo UK (not Google) – interim"
GOOGLE_LABEL = "Google UK (live SERP, non-personalised)"
BRAVE_LABEL = "Brave Search UK (not Google) – interim"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
EXTRA = [(f"removals {a}", "") for a in ("putney","wandsworth","barnes")] + [(f"{a} removals", "") for a in ("putney","wandsworth","barnes")]
LDN = ZoneInfo("Europe/London")

W_LONDON = ["chiswick","w4","ealing","hammersmith","richmond","kensington","acton","brentford","isleworth",
            "twickenham","notting hill","white city","shepherds bush","kew","hounslow","chelsea","gunnersbury","west london","fulham","putney","wandsworth","barnes"]
INTL = ["international","spain","dubai","australia","usa","france","portugal","abroad","overseas","europe","uae","america"]
UK = ["manchester","birmingham","bristol","edinburgh","leeds","glasgow","liverpool","uk","nationwide","long distance","scotland","wales","cardiff"]

def group_of(k):
    s = k.lower()
    if "shred" in s: return "Shredding (service not confirmed)"
    if any(w in s for w in INTL): return "International"
    if any(w in s for w in ["office","commercial","business","relocation","corporate","school","clinic","lab","retail"]): return "Office & commercial"
    if "storage" in s: return "Storage"
    if any(w in s for w in W_LONDON): return "West London"
    if any(re.search(r"\b%s\b" % w, s) for w in UK) and "london" not in s.replace("london to","").split()[:1]: return "UK routes & cities"
    if "london" in s: return "Wider London"
    return "Brand & other"

def area_of(k):
    s = k.lower()
    for w in W_LONDON + INTL + UK:
        if re.search(r"\b%s\b" % re.escape(w), s): return w.title().replace("W4","W4")
    return "London" if "london" in s else ""

def build_keywords():
    kws = {}
    # 1) keyword strategy table
    for line in open(STRATEGY, encoding="utf-8"):
        m = re.match(r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|.*?\|\s*(/[^|\s]*)\s*\|", line)
        if m:
            k = m.group(2).lower()
            vol = m.group(3)
            kws[k] = dict(keyword=k, volume_band=int(vol) if vol.isdigit() else None,
                          target_page=m.group(5), origin="Keyword strategy 25 Oct", priority=int(m.group(1)))
    # 2) planner volumes for ads keywords
    planner = {}
    p = os.path.join(ADS, "keyword-planner-historical-metrics.csv")
    if os.path.exists(p):
        rows = list(csv.reader(io.StringIO(open(p, "rb").read().decode("utf-16")), delimiter="\t"))
        for r in rows[3:]:
            if len(r) > 3 and r[0] and r[3]:
                try: planner[r[0].strip().lower()] = int(float(r[3]))
                except ValueError: pass
    # 3) Google Ads keyword set
    camp = json.load(open(os.path.join(ADS, "campaign.json")))
    for g in camp["groups"]:
        for k in g["keywords"]:
            k = k.strip().lower().strip('[]"+')
            if k in kws: kws[k]["origin"] += " + Google Ads"; continue
            kws[k] = dict(keyword=k, volume_band=None, target_page=urllib.parse.urlparse(g["url"]).path,
                          origin="Google Ads: " + g["name"], priority=None)
    csvp = os.path.join(ADS, "k1-google-ads-campaign.csv")
    if os.path.exists(csvp):
        for r in csv.DictReader(open(csvp, encoding="utf-8")):
            k = (r.get("Keyword") or "").strip().lower()
            if "negative" in (r.get("Criterion Type") or "").lower(): continue
            if k and k not in kws:
                kws[k] = dict(keyword=k, volume_band=None, target_page=urllib.parse.urlparse(r.get("Final URL") or "").path or "",
                              origin="Google Ads: " + (r.get("Ad Group") or ""), priority=None)
    # 4) extra tracked keywords (added 26 Oct)
    for k, page in EXTRA:
        if k not in kws:
            kws[k] = dict(keyword=k, volume_band=None, target_page=page, origin="Added 26 Oct (SW London areas)", priority=None)
    for k, v in kws.items():
        if v["volume_band"] is None and k in planner: v["volume_band"] = planner[k]
        v["group"] = group_of(k); v["area"] = area_of(k)
    return sorted(kws.values(), key=lambda x: (x["group"], x["keyword"]))

def now(): return datetime.now(LDN).strftime("%Y-%m-%d %H:%M %Z")

class Checker:
    def __init__(self, depth, engine="auto", cooldown=20, max_waits=4):
        self.engine = engine; self.cooldown = cooldown; self.max_waits = max_waits
        self.g_until = self.d_until = 0; self.start = time.time(); self.max_minutes = 240; self.gdepth = 10
        self.depth = depth; self.google_blocked = False; self.blocks = 0
        if engine == "brave": self.b = None; return
        from playwright.sync_api import sync_playwright
        self.p = sync_playwright().start()
        self.b = self.p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True,
                                        args=["--disable-blink-features=AutomationControlled"])
        self.pg = self.b.new_page(locale="en-GB", user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
        self.google_blocked = False; self.blocks = 0
    def close(self):
        if self.b: self.b.close(); self.p.stop()
    def google(self, q, retry=True):
        seen = 0
        for start in range(0, self.gdepth if self.engine == "auto" else self.depth, 10):
            u = "https://www.google.co.uk/search?" + urllib.parse.urlencode(dict(q=q, gl="uk", hl="en-GB", pws=0, start=start))
            self.pg.goto(u, wait_until="domcontentloaded"); self.pg.wait_for_timeout(2000)
            if "/sorry/" in self.pg.url or "unusual traffic" in self.pg.content().lower():
                self.blocks += 1
                if not retry: return None
                if self.engine == "google" and self.blocks <= self.max_waits:
                    print(f"Google captcha – waiting {self.cooldown} min then retrying ({self.blocks}/{self.max_waits})", file=sys.stderr, flush=True)
                    time.sleep(self.cooldown * 60); return self.google(q)
                print("Google captcha – giving up on Google for this run", file=sys.stderr, flush=True)
                self.google_blocked = True; return None
            res = self.pg.eval_on_selector_all("#search a:has(h3)",
                  "els=>els.map(e=>{const b=e.closest('[data-hveid]')||e.parentElement;const c=b.querySelector('cite');return c?c.innerText:''})")
            if not res: break
            for cite in res:
                seen += 1
                host = cite.split(" › ")[0].replace("https://","").replace("http://","")
                if host.endswith(DOMAIN):
                    path = "/".join(x.strip() for x in cite.split(" › ")[1:]) if " › " in cite else ""
                    return dict(position=seen, url="https://" + host + ("/" + path if path else "/"), checked_depth=seen)
            time.sleep(random.uniform(3, 6))
        return dict(position=None, url=None, checked_depth=seen)
    def bing(self, q):
        seen = 0
        for first in range(1, self.depth, 10):
            u = "https://www.bing.com/search?" + urllib.parse.urlencode(dict(q=q, cc="GB", setlang="en-GB", first=first))
            self.pg.goto(u, wait_until="domcontentloaded"); self.pg.wait_for_timeout(2000)
            hrefs = self.pg.eval_on_selector_all("li.b_algo h2 a", "els=>els.map(e=>e.href)")
            if not hrefs: break
            for h in hrefs:
                seen += 1
                m = re.search(r"[?&]u=a1([^&]+)", h)
                if m:
                    s = m.group(1); h = base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)).decode("utf-8", "ignore")
                if DOMAIN in urllib.parse.urlparse(h).netloc:
                    return dict(position=seen, url=h, checked_depth=seen)
            time.sleep(random.uniform(3, 6))
        return dict(position=None, url=None, checked_depth=seen)
    def ddg(self, q):
        u = "https://duckduckgo.com/?" + urllib.parse.urlencode(dict(q=q, kl="uk-en", kp="-2", ia="web"))
        self.pg.goto(u, wait_until="load"); self.pg.wait_for_timeout(3000)
        sel = "article[data-testid=result] a[data-testid=result-title-a]"
        for _ in range(10):
            hrefs = self.pg.eval_on_selector_all(sel, "els=>els.map(e=>e.href)")
            if len(hrefs) >= self.depth: break
            btn = self.pg.query_selector("#more-results, button:has-text('More results')")
            if not btn: break
            try: btn.click(timeout=8000)
            except Exception: break
            self.pg.wait_for_timeout(random.uniform(2500, 4000))
            if len(self.pg.query_selector_all(sel)) <= len(hrefs): break
        hrefs = self.pg.eval_on_selector_all(sel, "els=>els.map(e=>e.href)")[: self.depth]
        for i, h in enumerate(hrefs, 1):
            if urllib.parse.urlparse(h).netloc.endswith(DOMAIN):
                return dict(position=i, url=h, checked_depth=len(hrefs))
        return dict(position=None, url=None, checked_depth=len(hrefs))
    def brave(self, q):
        import urllib.request
        seen = 0
        for off in range(0, 10):
            u = "https://search.brave.com/search?" + urllib.parse.urlencode(dict(q=q, country="gb", source="web", offset=off))
            req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9"})
            for attempt in range(3):
                try: html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore"); break
                except Exception as e:
                    print("brave retry", e, file=sys.stderr, flush=True); time.sleep(60 * (attempt + 1)); html = ""
            links = re.findall(r'data-type="web"[^>]*>.*?<a href="(https?://[^"]+)"', html, re.S)
            if not links: break
            for h in links:
                seen += 1
                if urllib.parse.urlparse(h).netloc.endswith(DOMAIN):
                    return dict(position=seen, url=h, checked_depth=seen)
            if seen >= self.depth: break
            time.sleep(random.uniform(4, 7))
        return dict(position=None, url=None, checked_depth=seen)
    def auto(self, q):
        """Google UK when it isn't rate-limiting us, else DuckDuckGo UK; waits if both are cooling down."""
        while True:
            t = time.time()
            if t >= self.g_until:
                r = self.google(q, retry=False)
                if r is not None and r["checked_depth"]:
                    r["source"] = GOOGLE_LABEL; return r
                self.g_until = time.time() + self.cooldown * 60; print("Google cooling down", file=sys.stderr, flush=True)
            if t >= self.d_until:
                r = self.ddg(q)
                if r["checked_depth"]:
                    r["source"] = DDG_LABEL; return r
                self.d_until = time.time() + self.cooldown * 60; print("DuckDuckGo cooling down", file=sys.stderr, flush=True)
            if time.time() - self.start > self.max_minutes * 60: raise TimeoutError("run time limit")
            time.sleep(max(30, min(self.g_until, self.d_until) - time.time()))
    def check(self, q):
        if self.engine == "auto": return self.auto(q)
        if self.engine == "brave":
            r = self.brave(q); r["source"] = BRAVE_LABEL; return r
        if self.engine == "google":
            r = self.google(q)
            if r is None: raise RuntimeError("google blocked")
            r["source"] = GOOGLE_LABEL; return r
        if self.engine == "ddg":
            r = self.ddg(q); r["source"] = DDG_LABEL; return r
        if not self.google_blocked:
            r = self.google(q)
            if r is not None and r["checked_depth"] > 0:
                r["source"] = GOOGLE_LABEL; return r
        r = self.ddg(q); r["source"] = DDG_LABEL; return r

def load(p, d):
    return json.load(open(p)) if os.path.exists(p) else d

def rebuild(kws):
    hist = load(HIST, {})
    rows = []
    for k in kws:
        h = hist.get(k["keyword"], [])
        last = h[-1] if h else None
        same = [x for x in h[:-1] if last and x["source"] == last["source"]]
        prev = same[-1] if same else None
        row = dict(k)
        if not last:
            row.update(status="not_checked", position=None, url=None, source=None, checked_at=None, change=None, movement="—")
        else:
            pos = last["position"]
            row.update(position=pos, url=last.get("url"), source=last["source"], checked_at=last["checked_at"],
                       checked_depth=last.get("checked_depth"), status="ranking" if pos else "not_ranking")
            if prev is None: row.update(change=None, movement="new" if pos else "—")
            else:
                pp = prev["position"]
                if pp and pos: row.update(change=pp - pos, movement="improved" if pos < pp else "declined" if pos > pp else "same")
                elif pos and not pp: row.update(change=None, movement="new")
                elif pp and not pos: row.update(change=None, movement="lost")
                else: row.update(change=None, movement="—")
        ranked = [x["position"] for x in h if x["position"]]
        row["best"] = min(ranked) if ranked else None
        row["history"] = [dict(d=x["checked_at"], p=x["position"]) for x in h if last and x["source"] == last["source"]][-20:]
        others = {}
        for x in h:
            if last and x["source"] != last["source"]: others[x["source"]] = x
        row["other_sources"] = [dict(source=x["source"], position=x["position"], depth=x.get("checked_depth"), checked_at=x["checked_at"], url=x.get("url")) for x in others.values()]
        rows.append(row)
    pos = [r["position"] for r in rows if r["position"]]
    checked = [r for r in rows if r["status"] != "not_checked"]
    srcs = sorted({r["source"] for r in checked if r["source"]})
    summary = dict(total=len(rows), checked=len(checked), top3=sum(p <= 3 for p in pos), top10=sum(p <= 10 for p in pos),
                   top100=sum(p <= 100 for p in pos), ranking=len(pos), avg_position=round(sum(pos)/len(pos), 1) if pos else None,
                   improved=sum(r["movement"] == "improved" for r in rows), declined=sum(r["movement"] == "declined" for r in rows),
                   new=sum(r["movement"] == "new" for r in rows), lost=sum(r["movement"] == "lost" for r in rows))
    dates = sorted(r["checked_at"] for r in checked if r["checked_at"])
    out = dict(generated=now(), last_checked=dates[-1] if dates else None, sources=srcs, summary=summary,
               volume_source="Google Keyword Planner UK, avg monthly searches (approximate bands: 0 / 50 / 500 / 5,000)",
               note="Positions are real readings only. Organic results counted (ads, map pack and 'People also ask' excluded). Where a keyword has no reading it says 'Not checked yet'.",
               keywords=rows)
    json.dump(out, open(OUT, "w"), indent=1, ensure_ascii=False)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true"); ap.add_argument("--limit", type=int)
    ap.add_argument("--depth", type=int, default=int(os.environ.get("K1_RANK_DEPTH", 30)))
    ap.add_argument("--engine", choices=["auto", "google", "brave", "ddg"], default="auto",
                    help="auto = Google UK first, switch to DuckDuckGo UK if Google shows a captcha")
    ap.add_argument("--gap", type=float, default=40, help="seconds between keywords (min)")
    ap.add_argument("--resume", action="store_true", help="skip keywords already checked today with this engine")
    ap.add_argument("--rebuild-only", action="store_true")
    a = ap.parse_args()
    kws = build_keywords(); json.dump(kws, open(KWS, "w"), indent=1)
    if not a.rebuild_only:
        hist = load(HIST, {}); ck = Checker(a.depth, a.engine)
        try:
            todo = kws[: a.limit] if a.limit else kws
            for i, k in enumerate(todo):
                if a.resume and any(x["checked_at"][:10] == now()[:10] and (a.engine == "auto" or {"ddg":"duckduckgo","google":"google","brave":"brave"}[a.engine] in x["source"].lower()) for x in hist.get(k["keyword"], [])):
                    continue
                if ck.google_blocked and a.engine == "google": print("stopping: Google blocked"); break
                try: r = ck.check(k["keyword"])
                except TimeoutError: print("run time limit reached; rest left as not checked"); break
                except Exception as e: print("ERR", k["keyword"], e, file=sys.stderr); continue
                if not r.get("checked_depth"):
                    print(f"[{i+1}] {k['keyword']}: no results returned (blocked?) – left as not checked", flush=True); continue
                r["checked_at"] = now()
                hist.setdefault(k["keyword"], []).append(r)
                json.dump(hist, open(HIST, "w"), indent=1)
                print(f"[{i+1}/{len(kws)}] {k['keyword']}: {r['position'] or 'not in top '+str(r['checked_depth'])} {r['url'] or ''} ({r['source'][:6]})", flush=True)
                time.sleep(random.uniform(a.gap, a.gap * 1.5))
        finally: ck.close()
    out = rebuild(kws); print(json.dumps(out["summary"]))
    if a.push:
        subprocess.run(["git", "-C", ROOT, "add", "data", "tools"], check=True)
        if subprocess.run(["git", "-C", ROOT, "diff", "--cached", "--quiet"]).returncode:
            subprocess.run(["git", "-C", ROOT, "-c", "user.name=K1 SEO", "-c", "user.email=seo@k1removals.com",
                            "commit", "-m", "Rankings check " + now()], check=True)
            subprocess.run(["git", "-C", ROOT, "push"], check=True)

if __name__ == "__main__": main()
