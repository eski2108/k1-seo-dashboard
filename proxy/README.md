# K1 keyword lookup proxy

Cloudflare Worker that holds the DataForSEO login server-side. The public site never sees the key.
Each lookup costs one DataForSEO live task ($0.09, up to 20 keywords, UK, English). Results are cached for a day.

## Deploy (about 5 minutes)
1. Create a free Cloudflare account and a DataForSEO account (top up the $50 minimum).
2. `npm i -g wrangler && wrangler login`
3. `cd proxy && wrangler secret put DFS_LOGIN && wrangler secret put DFS_PASSWORD`
4. `wrangler deploy` and note the URL, e.g. `https://k1-keyword-proxy.<you>.workers.dev`
5. Put that URL in `config.js` (`PROXY_URL`) at the repo root, then push.

Only requests from https://eski2108.github.io are accepted. For extra protection against spend, add a Cloudflare rate-limit rule.
