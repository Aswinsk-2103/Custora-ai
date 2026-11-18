/* Custora AI frontend: talks to the Flask API under /api. No build step needed. */
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const esc = x => String(x).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const sym = () => $("#cur").value, mg = () => Math.min(100, Math.max(1, +$("#mar").value || 35));
const fm = n => sym() + Math.round(n).toLocaleString(), pc = p => Math.round(p * 100) + "%";
const SC = { "Champion": "var(--amber)", "Loyal regular": "var(--mint)", "At risk": "var(--coral)", "Hibernating": "var(--gray)" };
const when = t => new Date(t).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });

/* ---------- identity & API ---------- */
let CID;
try { CID = localStorage.getItem("custora-cid"); if (!CID) { CID = (crypto.randomUUID ? crypto.randomUUID() : Date.now() + "-" + Math.random().toString(16).slice(2)); localStorage.setItem("custora-cid", CID); } }
catch (e) { CID = "session-" + Math.random().toString(16).slice(2, 12); }
async function api(path, o = {}) {
  const h = { "X-Client-Id": CID };
  if (o.body && !(o.body instanceof FormData)) h["Content-Type"] = "application/json";
  const r = await fetch("/api" + path, { ...o, headers: h });
  let j = {}; try { j = await r.json(); } catch (e) { /* empty */ }
  if (!r.ok) throw new Error(j.error || "Request failed (" + r.status + ")");
  return j;
}
function toast(t) { const e = $("#toast"); e.textContent = t; e.classList.add("on"); setTimeout(() => e.classList.remove("on"), 2000); }
const guard = fn => async (...a) => { try { return await fn(...a); } catch (e) { toast(e.message); } };
async function copy(t) { try { await navigator.clipboard.writeText(t); toast("Copied to clipboard"); } catch (e) { toast("Copy not available"); } }
function save(name, text, type) { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([text], { type })); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000); }

/* ---------- tabs & theme ---------- */
const TABS = ["predict", "batch", "planner", "model", "history"];
function tab(t) {
  if (!TABS.includes(t)) t = "predict";
  $$("#tabs button").forEach(b => b.setAttribute("aria-selected", b.dataset.t == t));
  $$(".pane").forEach(p => p.classList.toggle("on", p.id == "p-" + t));
  if (location.hash != "#" + t) history.replaceState(null, "", "#" + t);
  if (t == "history") loadHistory();
}
$("#tabs").addEventListener("click", e => { const b = e.target.closest("button"); if (b) tab(b.dataset.t); });
addEventListener("hashchange", () => tab(location.hash.slice(1)));
function theme(t) { document.documentElement.dataset.theme = t; $$(".sw").forEach(b => b.setAttribute("aria-pressed", b.dataset.th == t)); try { localStorage.setItem("custora-theme", t); } catch (e) { /* ignore */ } }
$$(".sw").forEach(b => b.onclick = () => theme(b.dataset.th));
try { const t = localStorage.getItem("custora-theme"); if (t) theme(t); } catch (e) { /* ignore */ }

/* ---------- predict ---------- */
let META, LAST, pt;
function buildSliders() {
  const groups = { purchase: "Purchase behaviour", engagement: "Engagement" };
  $("#sl").innerHTML = Object.keys(groups).map(g => `<div class="tt2"><b>${groups[g]}</b></div>` +
    META.features.filter(f => f.group == g).map(f => `<div class="fld"><div class="r"><label for="f_${f.name}">${f.label}</label><b id="v_${f.name}"></b></div>
    <input type="range" id="f_${f.name}" min="${f.min}" max="${f.max}" value="${Math.round(f.default)}"></div>`).join("")).join("");
  $$("#sl input").forEach(i => i.addEventListener("input", () => { $("#v_" + i.id.slice(2)).textContent = i.value; clearTimeout(pt); pt = setTimeout(predict, 120); }));
  $$("#sl input").forEach(i => $("#v_" + i.id.slice(2)).textContent = i.value);
}
const predict = guard(async () => {
  const features = {}; META.features.forEach(f => features[f.name] = +$("#f_" + f.name).value);
  LAST = await api("/predict", { method: "POST", body: JSON.stringify({ features, margin: mg() }) });
  renderResult(LAST);
});
function renderResult(r) {
  const nm = $("#name").value || "This customer", col = SC[r.segment], vs = Math.round((r.revenue_12m / META.target_mean - 1) * 100);
  $("#res").innerHTML = `<div class="hero2"><div class="gauge" style="background:conic-gradient(${col} ${r.retention_probability * 360}deg,var(--soft) 0)"><div>${pc(r.retention_probability)}</div></div>
  <div><div class="mute sm">${esc(nm)}’s predicted 12-month value</div><div class="big">${fm(r.clv_12m)}</div><span class="pill" style="margin-top:10px;background:${col}">${r.segment}</span></div></div>
  <div class="kp"><div><span class="mute sm">Retention chance</span><b>${pc(r.retention_probability)}</b></div><div><span class="mute sm">Churn risk</span><b>${r.churn_risk}</b></div><div><span class="mute sm">Vs average customer</span><b>${vs >= 0 ? "+" : ""}${vs}%</b></div></div>`;
  const mx = Math.max(1e-9, ...r.drivers.map(d => Math.abs(d.clv_effect)));
  $("#drv").innerHTML = r.drivers.slice(0, 6).map(d => `<div class="row"><span>${esc(d.label.split(" (")[0])}</span><div class="track"><div class="fill" style="width:${Math.abs(d.clv_effect) / mx * 100}%;background:${d.clv_effect >= 0 ? "var(--teal)" : "var(--coral)"}"></div></div><span>${d.clv_effect >= 0 ? "+" : "−"}${Math.abs(Math.round(d.clv_effect))}</span></div>`).join("");
  $("#act").innerHTML = r.actions.map(a => `<li>${esc(a)}</li>`).join("");
}
$("#name").addEventListener("input", () => LAST && renderResult(LAST));
$("#cur").onchange = () => { LAST && renderResult(LAST); planner(); renderBatch(); };
$("#mar").oninput = () => { predict(); planner(); renderBatch(); };
$("#copy1").onclick = () => LAST && copy(`${$("#name").value || "Customer"}: predicted 12-month CLV ${fm(LAST.clv_12m)}, retention chance ${pc(LAST.retention_probability)}, churn risk ${LAST.churn_risk}, segment ${LAST.segment}.\nActions:\n- ${LAST.actions.join("\n- ")}`);
$("#save1").onclick = guard(async () => {
  const features = {}; META.features.forEach(f => features[f.name] = +$("#f_" + f.name).value);
  await api("/customers", { method: "POST", body: JSON.stringify({ name: $("#name").value, features, margin: mg() }) }); toast("Customer saved");
});
function openCustomer(name, f) {
  $("#name").value = name; META.features.forEach(x => { const i = $("#f_" + x.name); i.value = f[x.name]; $("#v_" + x.name).textContent = Math.round(f[x.name]); });
  predict(); tab("predict"); scrollTo({ top: 0, behavior: "smooth" });
}

/* ---------- batch scoring ---------- */
let ROWS = [], SUM = null, BM = 35, sk = "clv_12m", sd = -1, fs = "All", lim = 15;
const clvOf = r => r.clv_12m * mg() / BM;
async function upload(file) {
  $("#err").textContent = "";
  const fd = new FormData(); fd.append("file", file); fd.append("margin", mg()); fd.append("name", file.name);
  try {
    const r = await api("/predict/batch", { method: "POST", body: fd });
    ROWS = r.rows; SUM = r.summary; BM = mg(); lim = 15; fs = "All"; renderBatch(); $("#lres").hidden = false;
    toast(r.truncated ? "Scored the first 5,000 customers" : "List scored and saved");
  } catch (e) { $("#err").textContent = e.message; }
}
function renderBatch() {
  if (!SUM) return;
  const k = mg() / BM, tot = SUM.total_clv * k, ar = SUM.at_risk_clv * k, n = ROWS.length;
  $("#lkp").innerHTML = `<div><span class="mute sm">Customers</span><b>${n.toLocaleString()}</b></div><div><span class="mute sm">Total predicted CLV</span><b>${fm(tot)}</b></div><div><span class="mute sm">Average CLV</span><b>${fm(tot / n)}</b></div><div><span class="mute sm">Value at risk</span><b>${fm(ar)}</b></div>`;
  const seg = SUM.segments;
  $("#stk").innerHTML = Object.keys(SC).map(s => `<i style="width:${(seg[s] || 0) / n * 100}%;background:${SC[s]}"></i>`).join("");
  $("#leg").innerHTML = Object.keys(SC).map(s => `<span><i class="dot" style="background:${SC[s]}"></i>${s} (${seg[s] || 0})</span>`).join("");
  $("#fs").innerHTML = ["All", ...Object.keys(SC)].map(s => `<button aria-pressed="${s == fs}" data-s="${s}">${s}</button>`).join("");
  const H = [["id", "Customer"], ["clv_12m", "Predicted CLV"], ["retention_probability", "Retention"], ["segment", "Segment"], ["churn_risk", "Churn risk"]];
  $("#thr").innerHTML = H.map(h => `<th data-k="${h[0]}">${h[1]}${sk == h[0] ? (sd > 0 ? " ▲" : " ▼") : ""}</th>`).join("");
  const q = $("#q").value.toLowerCase();
  const V = ROWS.map((r, i) => ({ ...r, i })).filter(r => (fs == "All" || r.segment == fs) && r.id.toLowerCase().includes(q))
    .sort((a, b) => (a[sk] > b[sk] ? 1 : a[sk] < b[sk] ? -1 : 0) * sd);
  $("#tb").innerHTML = V.slice(0, lim).map(r => `<tr data-i="${r.i}"><td>${esc(r.id)}</td><td>${fm(clvOf(r))}</td><td>${pc(r.retention_probability)}</td><td><i class="dot" style="background:${SC[r.segment]}"></i>${r.segment}</td><td>${r.churn_risk}</td></tr>`).join("");
  $("#more").hidden = V.length <= lim;
}
$("#fs").onclick = e => { const b = e.target.closest("button"); if (b) { fs = b.dataset.s; lim = 15; renderBatch(); } };
$("#thr").onclick = e => { const h = e.target.closest("th"); if (!h) return; sd = sk == h.dataset.k ? -sd : -1; sk = h.dataset.k; renderBatch(); };
$("#q").oninput = () => { lim = 15; renderBatch(); };
$("#more").onclick = () => { lim += 25; renderBatch(); };
$("#tb").onclick = e => { const tr = e.target.closest("tr"); if (tr) { const r = ROWS[+tr.dataset.i]; openCustomer(r.id, r.features); } };
$("#pick").onclick = () => $("#file").click();
$("#file").onchange = e => { if (e.target.files[0]) upload(e.target.files[0]); e.target.value = ""; };
const dr = $("#drop");
["dragover", "dragenter"].forEach(n => dr.addEventListener(n, e => { e.preventDefault(); dr.classList.add("hot"); }));
["dragleave", "drop"].forEach(n => dr.addEventListener(n, e => { e.preventDefault(); dr.classList.remove("hot"); }));
dr.addEventListener("drop", e => { if (e.dataTransfer.files[0]) upload(e.dataTransfer.files[0]); });
$("#sample").onclick = guard(async () => { const r = await fetch("/api/sample.csv"); upload(new File([await r.blob()], "sample-customers.csv", { type: "text/csv" })); });
const csvOf = rows => "customer,predicted_clv,retention,segment,churn_risk," + META.features.map(f => f.name).join(",") + "\n" +
  rows.map(r => [r.id, Math.round(clvOf(r)), r.retention_probability.toFixed(3), r.segment, r.churn_risk, ...META.features.map(f => r.features[f.name])].join(",")).join("\n");
$("#dl").onclick = () => ROWS.length && save("custora-scored.csv", csvOf(ROWS), "text/csv");

/* ---------- planner ---------- */
let LP, plt;
const planner = guard(async () => {
  const g = id => +$("#" + id).value || 0;
  $("#vret").textContent = g("ret") + "%"; $("#vup").textContent = "+" + g("up") + " points";
  LP = { customers: g("n"), aov: g("pa"), orders_per_year: g("po"), cac: g("cac"), retention: g("ret"), uplift: g("up"), margin: mg() };
  const r = await api("/planner", { method: "POST", body: JSON.stringify(LP) });
  const col = { "Healthy": "var(--mint)", "Needs work": "var(--amber)", "Losing money": "var(--coral)" }[r.verdict];
  const msg = { "Healthy": "Each customer returns more than three times what they cost.", "Needs work": "You earn back the cost, but with thin room. Raise retention or lower acquisition cost.", "Losing money": "A customer is worth less than the cost to win them. Fix this before spending more on acquisition." }[r.verdict];
  $("#pres").innerHTML = `<div class="mute sm">Lifetime value per customer (5 years)</div><div class="big">${fm(r.ltv)}</div><span class="pill" style="margin-top:10px;background:${col}">${r.verdict}: ${r.ratio.toFixed(1)}× cost</span><p class="mute" style="margin-top:10px">${msg}</p>
  <div class="kp"><div><span class="mute sm">Payback time</span><b>${r.payback_months == null ? "–" : r.payback_months < 1 ? "<1" : Math.round(r.payback_months)} mo</b></div><div><span class="mute sm">Whole customer base</span><b>${fm(r.base_total)}</b></div><div><span class="mute sm">Gain from better retention</span><b>${fm(r.gain_total)}</b></div></div>`;
  const A = r.series_today, B = r.series_improved, lo = Math.min(...A, ...B, 0), hi = Math.max(...A, ...B, 1);
  const X = i => 40 + i * 64, Y = v => 140 - (v - lo) / (hi - lo) * 115, P = a => a.map((v, i) => (i ? "L" : "M") + X(i) + " " + Y(v).toFixed(1)).join(" ");
  $("#pch").innerHTML = `<line x1="40" x2="360" y1="${Y(0)}" y2="${Y(0)}" stroke="var(--line)" stroke-dasharray="4"/><path d="${P(A)}" fill="none" stroke="var(--coral)" stroke-width="4"/><path d="${P(B)}" fill="none" stroke="var(--teal)" stroke-width="4"/>` +
    [0, 1, 2, 3, 4, 5].map(i => `<text x="${X(i) - 8}" y="162">Y${i}</text>`).join("") + `<text x="2" y="${Y(0) + 4}">${sym()}0</text>`;
});
$$("#p-planner input").forEach(i => i.addEventListener("input", () => { clearTimeout(plt); plt = setTimeout(planner, 150); }));
$("#savep").onclick = guard(async () => { await api("/plans", { method: "POST", body: JSON.stringify(LP) }); toast("Plan saved"); });

/* ---------- model report ---------- */
function renderModel() {
  const m = META, f2 = x => x.toFixed(2), f3 = x => x.toFixed(3);
  $("#minfo").textContent = `Trained ${when(m.trained_at)} on ${m.n_samples.toLocaleString()} customers (${m.data_source}). The best model is chosen by cross-validated RMSE and reported on a held-out 20% test set.`;
  $("#mt").innerHTML = m.regressors.map(r => `<tr class="${r.name == m.best_regressor ? "best" : ""}"><td>${r.name == m.best_regressor ? "★ " : ""}${r.name}</td><td>${f2(r.rmse)}</td><td>${f2(r.mae)}</td><td>${f3(r.r2)}</td><td>${f2(r.cv_rmse)}</td></tr>`).join("");
  $("#ct").innerHTML = m.classifiers.map(r => `<tr class="${r.name == m.best_classifier ? "best" : ""}"><td>${r.name == m.best_classifier ? "★ " : ""}${r.name}</td><td>${f3(r.roc_auc)}</td><td>${f3(r.accuracy)}</td><td>${f3(r.f1)}</td></tr>`).join("");
  const top = m.importance[0].share || 1;
  $("#imp").innerHTML = m.importance.map((d, i) => `<div class="row"><span>${esc(d.label.split(" (")[0])}</span><div class="track"><div class="fill ${i ? "" : "best"}" style="width:${d.share / top * 100}%;background:${i ? "var(--teal)" : "var(--amber)"}"></div></div><span>${pc(d.share)}</span></div>`).join("");
  const mx = Math.max(...m.scatter.flat(), 1), X = v => 40 + v / mx * 300, Y = v => 190 - v / mx * 170;
  $("#sc").innerHTML = `<line x1="40" y1="190" x2="340" y2="20" stroke="var(--coral)" stroke-width="2" stroke-dasharray="5"/>` + m.scatter.map(p => `<circle cx="${X(p[0]).toFixed(1)}" cy="${Y(p[1]).toFixed(1)}" r="3.5" fill="var(--teal)" opacity=".6"/>`).join("") +
    `<text x="140" y="212">Actual revenue</text><text x="2" y="18">Predicted</text>`;
  $("#mname").textContent = m.best_regressor; $("#mr2").textContent = "R² " + f2(m.regressors.find(r => r.name == m.best_regressor).r2);
  $("#mauc").textContent = "Retention AUC " + f2(m.classifiers.find(r => r.name == m.best_classifier).roc_auc); $("#mver").textContent = "v" + m.version;
}

/* ---------- history ---------- */
let HD = { c: [], b: [], p: [] }, wipeArm = false;
const item = (t, id, title, sub, extra = "") => `<div class="item"><div><b>${esc(title)}</b><div class="mute sm">${sub}</div></div><div class="acts"><button class="btn alt sm2" data-a="open" data-t="${t}" data-id="${id}">Open</button>${extra}<button class="btn alt sm2" data-a="del" data-t="${t}" data-id="${id}" aria-label="Delete ${esc(title)}">Delete</button></div></div>`;
const loadHistory = guard(async () => {
  const [c, b, p] = await Promise.all([api("/customers"), api("/batches"), api("/plans")]); HD = { c, b, p };
  $("#dkp").innerHTML = [["Customers", c.length], ["Scored lists", b.length], ["Plans", p.length]].map(k => `<div><span class="mute sm">${k[0]}</span><b>${k[1]}</b></div>`).join("");
  $("#dc").innerHTML = c.length ? c.map(x => item("customers", x.id, x.name, `${fm(x.result.clv_12m)} predicted · ${x.result.segment} · ${pc(x.result.retention_probability)} retention · ${when(x.created_at)}`)).join("") : `<p class="empty">Nothing yet. Use Save customer on the first tab.</p>`;
  $("#dbt").innerHTML = b.length ? b.map(x => item("batches", x.id, x.name, `${x.count.toLocaleString()} customers · ${fm(x.total_clv)} total · ${when(x.created_at)}`)).join("") : `<p class="empty">Nothing yet. Upload a customer list and it is saved automatically.</p>`;
  $("#dp").innerHTML = p.length ? p.map(x => item("plans", x.id, `Plan for ${Math.round(x.inputs.customers).toLocaleString()} customers`, `${fm(x.result.ltv)} lifetime value · ${x.result.ratio}× acquisition cost · ${when(x.created_at)}`)).join("") : `<p class="empty">Nothing yet. Use Save this plan on the planner.</p>`;
});
$("#p-history").addEventListener("click", guard(async e => {
  const b = e.target.closest("button[data-a]"); if (!b) return; const { a, t, id } = b.dataset;
  if (a == "del") { await api(`/${t}/${id}`, { method: "DELETE" }); toast("Deleted"); return loadHistory(); }
  if (t == "customers") { const x = HD.c.find(y => y.id == id); openCustomer(x.name, x.features); }
  if (t == "plans") { const x = HD.p.find(y => y.id == id).inputs; $("#n").value = x.customers; $("#pa").value = x.aov; $("#po").value = x.orders_per_year; $("#cac").value = x.cac; $("#ret").value = x.retention; $("#up").value = x.uplift; $("#mar").value = x.margin; planner(); tab("planner"); }
  if (t == "batches") { const x = await api("/batches/" + id); ROWS = x.rows; SUM = { total_clv: x.total_clv, at_risk_clv: x.rows.filter(r => r.segment == "At risk").reduce((s, r) => s + r.clv_12m, 0), segments: x.segments }; BM = x.margin; lim = 15; fs = "All"; renderBatch(); $("#lres").hidden = false; tab("batch"); }
}));
$("#expj").onclick = guard(async () => save("custora-my-data.json", JSON.stringify(await api("/export"), null, 2), "application/json"));
$("#wipe").onclick = guard(async () => {
  const w = $("#wipe"); if (!wipeArm) { wipeArm = true; w.textContent = "Tap again to confirm"; setTimeout(() => { wipeArm = false; w.textContent = "Delete all my data"; }, 4000); return; }
  wipeArm = false; w.textContent = "Delete all my data"; await api("/data", { method: "DELETE" }); toast("All your data was deleted"); loadHistory();
});

/* ---------- start ---------- */
(async () => {
  const chip = (t, c) => { $("#dbs").textContent = t; $("#dbs").style.background = c; };
  try { await api("/health"); META = await api("/model"); chip("API connected", "var(--mint)"); }
  catch (e) { chip("API offline", "var(--coral)"); $("#res").innerHTML = `<p>The backend is not reachable. Start it with <b>python run.py</b>.</p>`; return; }
  buildSliders(); renderModel(); predict(); planner(); tab(location.hash.slice(1));
})();
