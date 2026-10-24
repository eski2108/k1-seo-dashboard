# K1 Removals – SEO dashboard
Static site (HTML/CSS/JS, no build step), served by GitHub Pages. Set to noindex with robots.txt `Disallow: /`. Holds data only: no secrets.
## Update the data
```
python3 scripts/build_data.py /workspace/k1/seo /workspace/seomachine
git add data.json && git commit -m "Update data" && git push
```
Sources: `keywords-300.csv`, `stats-board-data.json`, `weekend-*/research/backlink-pr-opportunities-*.csv`, `weekend-*/pages/README.md`, `weekend-*/blog-briefs/*.md`, `seomachine/topics/*.md`.
Local preview: `python3 -m http.server` → http://localhost:8000
