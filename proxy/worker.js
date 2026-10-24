// K1 keyword lookup proxy (Cloudflare Worker). Keeps DataForSEO credentials server-side.
// Secrets: DFS_LOGIN, DFS_PASSWORD (wrangler secret put). Var: ALLOW_ORIGIN.
export default {
  async fetch(req, env) {
    const origin = env.ALLOW_ORIGIN || "https://eski2108.github.io";
    const cors = { "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Methods": "POST,OPTIONS", "Access-Control-Allow-Headers": "Content-Type" };
    if (req.method === "OPTIONS") return new Response(null, { headers: cors });
    if (req.method !== "POST") return new Response("POST only", { status: 405, headers: cors });
    if (req.headers.get("Origin") !== origin) return new Response("Forbidden", { status: 403, headers: cors });
    let body; try { body = await req.json(); } catch { return new Response("Bad JSON", { status: 400, headers: cors }); }
    const kws = (body.keywords || []).map(k => String(k).toLowerCase().trim().slice(0, 80)).filter(Boolean).slice(0, 20);
    if (!kws.length) return new Response("No keywords", { status: 400, headers: cors });
    const r = await fetch("https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live", {
      method: "POST",
      headers: { "Authorization": "Basic " + btoa(env.DFS_LOGIN + ":" + env.DFS_PASSWORD), "Content-Type": "application/json" },
      body: JSON.stringify([{ keywords: kws, location_code: 2826, language_code: "en" }]) // 2826 = United Kingdom
    });
    const j = await r.json();
    const out = ((j.tasks?.[0]?.result) || []).map(x => ({
      keyword: x.keyword, volume: x.search_volume, cpc: x.cpc, competition: x.competition,
      trend: (x.monthly_searches || []).slice(0, 12).reverse().map(m => m.search_volume)
    }));
    return new Response(JSON.stringify({ results: out }), { headers: { ...cors, "Content-Type": "application/json", "Cache-Control": "max-age=86400" } });
  }
};
