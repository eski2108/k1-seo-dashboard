# K1 Removals – SEO dashboard
Static site (HTML/CSS/JS, no build step), served by GitHub Pages. Set to noindex with robots.txt `Disallow: /`. Holds data only: no secrets.
## Update the data
```
python3 scripts/build_data.py /workspace/k1/seo /workspace/seomachine
git add data.json && git commit -m "Update data" && git push
```
Sources: `keywords-300.csv`, `stats-board-data.json`, `weekend-*/research/backlink-pr-opportunities-*.csv`, `weekend-*/pages/README.md`, `weekend-*/blog-briefs/*.md`, `seomachine/topics/*.md`.
Local preview: `python3 -m http.server` → http://localhost:8000

## Keyword rankings board (#rankings)
Front-end: `rankings.js` reads `data/rankings.json` (static, no secrets).
Pipeline: `tools/check_rankings.py`
- Keyword list = `/workspace/k1/seo/keyword-strategy-2026-10-25.md` table + Google Ads set (`/workspace/k1/ads/campaign.json`, `k1-google-ads-campaign.csv`, negatives excluded), deduped → `data/rank-keywords.json`. Volumes: Google Keyword Planner UK (approximate bands).
- Positions are real readings only. Engines: `--engine auto` (Google UK, gl=uk hl=en-GB pws=0, headless Chrome; switches to DuckDuckGo UK on captcha), `google`, `ddg`. Each reading stores position / URL / source / depth / time (Europe/London) in `data/rankings-history.json`; change is only computed between readings from the same source.
- Run: `python3 tools/check_rankings.py --engine ddg --depth 50 --push` (≈1 hour for ~116 keywords; polite 8–15 s gaps). `--limit N` to test, `--rebuild-only` to just rebuild JSON.
- Needs: `pip install playwright` and Google Chrome at /usr/bin/google-chrome.

### Search Console (preferred source, once verified)
Search Console → Performance → Search results → Export → CSV, then:
```
python3 tools/import_search_console.py Queries.csv --range "28 days to DD Mon"
git add data && git commit -m "GSC rankings import" && git push
```
Search Console positions are averages over the date range; they're labelled as such on the board.
