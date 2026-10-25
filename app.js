const $=s=>document.querySelector(s),esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const io=new IntersectionObserver(es=>es.forEach(e=>{if(!e.isIntersecting)return;const t=e.target;t.classList.add("in");
 t.querySelectorAll("[data-count]").forEach(countUp);t.querySelectorAll(".bar i").forEach(b=>b.style.width=b.dataset.w);
 t.querySelectorAll("circle[data-off]").forEach(c=>c.style.strokeDashoffset=c.dataset.off);io.unobserve(t)}),{threshold:.12});
function countUp(el){const n=+el.dataset.count,t0=performance.now();(function f(t){const p=Math.min(1,(t-t0)/1400);el.textContent=Math.round(n*(1-Math.pow(1-p,3))).toLocaleString();if(p<1)requestAnimationFrame(f)})(t0)}
const bars=(el,obj)=>{const mx=Math.max(...Object.values(obj));el.innerHTML=Object.entries(obj).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`<div class="row"><span>${esc(k)}</span><div class="bar"><i data-w="${v/mx*100}%"></i></div><b>${v}</b></div>`).join("")};
const count=(a,k)=>a.reduce((o,x)=>(o[x[k]]=(o[x[k]]||0)+1,o),{});
const stCls={live:"g",draft:"a",new:"",["needs-confirm"]:"r"};
fetch("data.json").then(r=>r.json()).then(D=>{
 $("#upd").textContent=D.updated;const P=D.pages;
 $("#heroStats").innerHTML=[[D.keywords.length,"keywords mapped"],[P.live,"pages live"],[P.drafts_new,"new drafts ready"],[D.pr_leads.length,"PR leads"],[D.backlinks.targets,"backlink targets"]].map(([n,l])=>`<div class="stat"><b data-count="${n}">0</b><span>${l}</span></div>`).join("");
 countUpAll();
 $("#auditCards").innerHTML=[[P.live_services_areas,"Live service & area pages"],[P.live_blogs,"Live blog posts"],[P.drafts_duplicate,"Duplicate drafts merged"],[D.citations.researched,"Citations researched ("+D.citations.submitted+" submitted)"],[D.outreach.prospects,"Outreach prospects ("+D.outreach.sent+" sent)"],[P.published_by_bot,"Published by bot (login blocked)"]].map(([n,l])=>`<div class="kc"><b data-count="${n}">0</b><p>${esc(l)}</p></div>`).join("");
 bars($("#pagesBars"),{"Live":P.live,"Service/area live":P.live_services_areas,"Blogs live":P.live_blogs,"Drafts (new)":P.drafts_new,"Drafts (duplicate)":P.drafts_duplicate,"Blocked":P.blocked});
 $("#worklog").innerHTML=D.work_log.map(w=>`<li><b>${esc(w.date)} · ${esc(w.type)}</b><br>${esc(w.detail)}</li>`).join("");
 $("#notT").innerHTML=D.not_targeting.map(n=>`<div><b>${esc(n.keyword)}</b><br><span class="ph">${esc(n.reason)}</span></div>`).join("");
 $("#loopSteps").innerHTML=[["Monday briefs","Grok Bot writes 3 page briefs into seomachine/topics/ with keywords, competitors and local details."],["Weekly to-do","Dean gets a short weekly list: which briefs to run and what needs his OK."],["Claude writes","Run /write on each brief. Claude researches, writes and optimises, then saves to drafts/."],["Review","Grok Bot checks every draft against the rules: no prices, insured up to £1 million, real services only, no duplicate pages."],["Dean approves","Nothing gets published without Dean's OK."],["Track","Rankings are tracked against the keyword map, with real data once Search Console is connected."]].map(([h,p])=>`<div class="step"><h4>${h}</h4><p>${p}</p></div>`).join("");
 $("#plan").innerHTML=D.weekly_plan.map(w=>`<div><b>${esc(w.week)}</b>${esc(w.tasks)}</div>`).join("");
 // keywords
 const fv=k=>k.volume!=null?(+k.volume).toLocaleString():(k.volume_range?esc(k.volume_range):"—");
 const spark=t=>{t=(t||[]).filter(x=>x!=null);if(t.length<2)return"—";const m=Math.max(...t,1);return`<svg width="80" height="20"><polyline fill="none" stroke="#3F7CC4" stroke-width="2" points="${t.map((v,i)=>`${i*80/(t.length-1)},${19-v/m*18}`).join(" ")}"/></svg>`};
 {const KV=D.keywords.filter(k=>k.volume!=null);
  if(KV.length){bars($("#volBars"),Object.fromEntries(KV.sort((a,b)=>b.volume-a.volume).slice(0,15).map(k=>[k.keyword,k.volume])));
   bars($("#grpVol"),KV.reduce((o,k)=>(o[k.group]=(o[k.group]||0)+k.volume,o),{}))}
  else{$("#volBars").innerHTML=$("#grpVol").innerHTML='<p class="ph">— No real volume data yet. Waiting on a Keyword Planner export or DataForSEO.</p>'}}
 const lookup=async()=>{const q=$("#lk").value.trim().toLowerCase();if(!q)return;const o=$("#lkOut");
  const P=(window.K1_CONFIG||{}).PROXY_URL;
  if(P){o.textContent="Checking Google…";try{const r=await fetch(P,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({keywords:[q]})});const j=await r.json();const x=j.results&&j.results[0];
   o.innerHTML=x?`<b>${esc(x.keyword)}</b>: <b>${x.volume!=null?(+x.volume).toLocaleString():"no data"}</b> searches/month (UK) · CPC ${x.cpc!=null?"£"+(+x.cpc).toFixed(2):"—"} ${spark(x.trend)}`:"No data from Google for that keyword.";return}catch(e){o.textContent="Live lookup failed. Showing saved data."}}
  const m=D.keywords.filter(k=>k.keyword.includes(q)).slice(0,10);
  o.innerHTML=(P?"":"<b>Live lookup not connected yet.</b> Searching our saved keywords:<br>")+(m.length?m.map(k=>`${esc(k.keyword)}: <b>${fv(k)}</b>`).join("<br>"):"Not in our keyword list.")};
 $("#lkBtn").onclick=lookup;$("#lk").addEventListener("keydown",e=>e.key=="Enter"&&lookup());
 const K=D.keywords;$("#kwTotal").textContent=K.length;bars($("#groupBars"),count(K,"group"));
 const sc=count(K,"status"),cols={live:"#8CC63F",draft:"#D9922E",new:"#3F7CC4","needs-confirm":"#D14343"},C=2*Math.PI*70;let acc=0;
 $("#donut").innerHTML=`<div class="donut"><svg width="180" height="180" viewBox="0 0 180 180"><g transform="rotate(-90 90 90)">${Object.entries(sc).map(([k,v])=>{const len=v/K.length*C,s=`<circle cx="90" cy="90" r="70" fill="none" stroke="${cols[k]||"#999"}" stroke-width="26" stroke-dasharray="${len} ${C}" stroke-dashoffset="${len}" data-off="${-acc}" style="stroke-dashoffset:${len}"/>`;acc+=len;return s}).join("")}</g><text x="90" y="88" text-anchor="middle" font-size="30" font-weight="800" fill="#12285A">${K.length}</text><text x="90" y="110" text-anchor="middle" font-size="12" fill="#5A6A8A">keywords</text></svg><div class="legend">${Object.entries(sc).map(([k,v])=>`<div><i style="background:${cols[k]}"></i>${k}: <b>${v}</b></div>`).join("")}</div></div>`;
 [...new Set(K.map(k=>k.group))].sort().forEach(g=>$("#fg").insertAdjacentHTML("beforeend",`<option>${esc(g)}</option>`));
 Object.keys(sc).forEach(s=>$("#fs").insertAdjacentHTML("beforeend",`<option>${esc(s)}</option>`));
 let sk="priority",dir=1;const val=k=>sk=="trend"?(k.trend||[]).filter(x=>x!=null).slice(-1)[0]:k[sk];const cmp=(a,b)=>{const x=val(a),y=val(b);if(x==null&&y==null)return 0;if(x==null)return 1;if(y==null)return -1;return (x>y?1:x<y?-1:0)*dir};const draw=()=>{const q=$("#q").value.toLowerCase(),g=$("#fg").value,p=$("#fp").value,s=$("#fs").value;
  const r=K.filter(k=>(!q||(k.keyword+k.page).toLowerCase().includes(q))&&(!g||k.group==g)&&(!p||k.priority==p)&&(!s||k.status==s)).sort((a,b)=>cmp(a,b));
  $("#cnt").textContent=`${r.length} of ${K.length}`;
  $("#kwBody").innerHTML=r.map(k=>`<tr><td><b>${esc(k.keyword)}</b></td><td>${esc(k.group)}</td><td>${esc(k.intent)}</td><td><code>${esc(k.page)}</code></td><td>${fv(k)}</td><td>${spark(k.trend)}</td><td>${k.cpc!=null?"£"+(+k.cpc).toFixed(2):"—"}</td><td><span class="tag ${k.priority==1?"g":""}">P${k.priority}</span></td><td><span class="tag ${stCls[k.status]??""}">${esc(k.status)}</span></td></tr>`).join("")};
 ["#q","#fg","#fp","#fs"].forEach(s=>$(s).addEventListener("input",draw));
 document.querySelectorAll("#keywords th").forEach(th=>th.onclick=()=>{dir=sk==th.dataset.k?-dir:1;sk=th.dataset.k;draw()});draw();
 $("#briefCards").innerHTML=D.briefs.map(b=>`<div class="card"><span class="tag g">Brief</span><span class="tag">${esc(b.intent.split(".")[0])}</span><h4>${esc(b.title)}</h4><p><b>URL:</b> <code>${esc(b.url)}</code></p><p><b>Primary:</b> ${esc(b.primary)}</p><p><b>Secondary:</b> ${esc(b.secondary)}</p><p><b>Length:</b> ${esc(b.length)}</p><div class="cmd"><code>${esc(b.command)}</code><button onclick="navigator.clipboard.writeText('${esc(b.command)}');this.textContent='Copied'">Copy</button></div></div>`).join("");
 $("#draftCards").innerHTML=D.drafts.map(d=>`<div class="card"><span class="tag a">${esc(d.status)}</span><span class="tag">${esc(d.type)}</span><h4>${esc(d.name.replace(/-/g," "))}</h4>${d.url?`<p><code>${esc(d.url)}</code> · ${esc(d.words)} words</p>`:""}<p>${esc(d.notes)}</p></div>`).join("");
 $("#prCards").innerHTML=D.pr_leads.map(p=>`<div class="card"><span class="tag">${esc(p.type)}</span><h4><a href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.name)}</a></h4><p>${esc(p.why_relevant)}</p><p><b>Pitch:</b> ${esc(p.how_to_pitch)}</p><p class="ph">${esc(p.cost_or_caveat)}</p></div>`).join("");
 $("#blockCards").innerHTML=D.blockers.map(b=>`<div class="card" style="border-left:5px solid ${b.sev=="Critical"?"var(--red)":b.sev=="High"?"var(--amber)":"var(--blue)"}"><span class="tag ${b.sev=="Critical"?"r":"a"}">${esc(b.sev)}</span><span class="tag">Owner: ${esc(b.owner)}</span><h4>${esc(b.t)}</h4><p>${esc(b.impact)}</p><p class="ph">${esc(b.status)}</p></div>`).join("");
 document.querySelectorAll(".sec,.panel,.kc").forEach(e=>{e.classList.add("reveal");io.observe(e)});
});
function countUpAll(){document.querySelectorAll(".hero [data-count]").forEach(countUp)}
