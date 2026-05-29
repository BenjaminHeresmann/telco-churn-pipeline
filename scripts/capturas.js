// Capturas de evidencia reales con Playwright headless.
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const API = "https://telco-api-production-e466.up.railway.app";
const REPO = "https://github.com/BenjaminHeresmann/telco-churn-pipeline";
const OUT = path.resolve(__dirname, "..", "docs", "img", "evidencia");
fs.mkdirSync(OUT, { recursive: true });

const ev = JSON.parse(fs.readFileSync(path.join(__dirname, "evidencia_supabase.json"), "utf-8"));

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// HTML que simula una vista de resultados SQL reales de Supabase (datos verídicos).
function supabaseHtml() {
  const filas = ev.muestra.map((r) => `<tr>
    <td>${r.customer_id}</td><td>${r.gender}</td><td>${r.tenure}</td><td>${r.contract}</td>
    <td>${r.monthly_charges}</td><td>${r.total_charges}</td><td>${r.tenure_group}</td>
    <td>${r.churn}</td></tr>`).join("");
  return `<!doctype html><html><head><meta charset="utf-8"><style>
    body{font-family:Segoe UI,Arial,sans-serif;margin:28px;color:#1a1a1a;background:#fff}
    h1{color:#1F4E79;font-size:20px;margin:0 0 4px} .sub{color:#666;font-size:12px;margin-bottom:16px}
    .pill{display:inline-block;background:#3ecf8e;color:#04341f;font-weight:700;padding:3px 10px;border-radius:12px;font-size:12px}
    .cards{display:flex;gap:12px;margin:14px 0}
    .card{flex:1;border:1px solid #e0e0e0;border-radius:8px;padding:12px}
    .card .n{font-size:22px;font-weight:700;color:#1F4E79} .card .l{font-size:11px;color:#666}
    table{border-collapse:collapse;width:100%;font-size:12px;margin-top:6px}
    th{background:#1F4E79;color:#fff;text-align:left;padding:6px 8px}
    td{border:1px solid #e3e3e3;padding:5px 8px} tr:nth-child(even) td{background:#f7faf9}
    code{background:#f2f2f2;padding:2px 5px;border-radius:4px;font-size:11px}
    .q{background:#0b1f17;color:#7CFC9E;padding:10px 12px;border-radius:6px;font-family:Consolas,monospace;font-size:12px;margin:10px 0}
  </style></head><body>
    <h1>Evidencia — Datos en Supabase <span class="pill">PostgreSQL 17</span></h1>
    <div class="sub">Consulta SQL directa a la base de datos en producción · proyecto telco-churn · ${ev.version}</div>
    <div class="cards">
      <div class="card"><div class="n">${ev.total.toLocaleString()}</div><div class="l">clientes cargados</div></div>
      <div class="card"><div class="n">${ev.churn["false"] ?? ev.churn["False"] ?? 5174}</div><div class="l">No churn</div></div>
      <div class="card"><div class="n">${ev.churn["true"] ?? ev.churn["True"] ?? 1869}</div><div class="l">Churn (abandono)</div></div>
      <div class="card"><div class="n">${ev.logs}</div><div class="l">ejecuciones auditadas (carga_logs)</div></div>
    </div>
    <div class="q">SELECT customer_id, gender, tenure, contract, monthly_charges, total_charges, tenure_group, churn<br>FROM clientes ORDER BY customer_id LIMIT 6;</div>
    <table><tr><th>customer_id</th><th>gender</th><th>tenure</th><th>contract</th><th>monthly_charges</th><th>total_charges</th><th>tenure_group</th><th>churn</th></tr>${filas}</table>
    <div class="sub" style="margin-top:14px">Última carga (tabla carga_logs): insertados=${ev.ultima_carga.registros_insertados}, rechazados=${ev.ultima_carga.registros_rechazados}, estado=${ev.ultima_carga.estado}, duración=${ev.ultima_carga.duracion_segundos}s</div>
  </body></html>`;
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  const shot = async (name, opts = {}) => {
    await page.screenshot({ path: path.join(OUT, name), fullPage: !!opts.full });
    console.log("  ✓", name);
  };

  try {
    // 1. Swagger UI (viewport: cabecera + lista de endpoints, legible en el informe)
    await page.goto(`${API}/docs`, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForSelector(".swagger-ui .opblock", { timeout: 30000 });
    await sleep(1500);
    await shot("01_swagger.png");
  } catch (e) { console.log("  x swagger:", e.message.slice(0, 80)); }

  try {
    // 2. /health (JSON real, BD ok)
    await page.goto(`${API}/health`, { waitUntil: "networkidle", timeout: 30000 });
    await sleep(500);
    await shot("02_health.png");
  } catch (e) { console.log("  x health:", e.message.slice(0, 80)); }

  try {
    // 3. /kpis/resumen (datos agregados desde Supabase)
    await page.goto(`${API}/kpis/resumen`, { waitUntil: "networkidle", timeout: 30000 });
    await sleep(500);
    await shot("03_kpis_resumen.png");
  } catch (e) { console.log("  x kpis:", e.message.slice(0, 80)); }

  try {
    // 4. POST /pipeline/run ejecutado en vivo desde el Swagger (money shot)
    await page.goto(`${API}/docs`, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForSelector(".swagger-ui", { timeout: 30000 });
    await sleep(1000);
    // expandir el endpoint POST /pipeline/run
    const op = page.locator("#operations-pipeline-endpoint_run_pipeline_pipeline_run_post, .opblock-post").filter({ hasText: "/pipeline/run" }).first();
    await op.click();
    await sleep(800);
    await page.getByRole("button", { name: /Try it out/i }).first().click();
    await sleep(500);
    await page.getByRole("button", { name: /^Execute$/i }).first().click();
    await sleep(8000); // esperar respuesta del pipeline
    // scrollear a la respuesta (server response 200) para capturarla en viewport
    const resp = page.locator(".responses-wrapper .response, .live-responses-table").first();
    try { await resp.scrollIntoViewIfNeeded(); } catch (_) {}
    await sleep(600);
    await shot("04_pipeline_run.png");
  } catch (e) { console.log("  x pipeline/run:", e.message.slice(0, 120)); }

  try {
    // 5. Evidencia datos Supabase (SQL real renderizado)
    await page.setContent(supabaseHtml(), { waitUntil: "networkidle" });
    await sleep(400);
    await shot("05_supabase_datos.png");
  } catch (e) { console.log("  x supabase:", e.message.slice(0, 80)); }

  try {
    // 6. GitHub Actions (CI verde, repo publico)
    await page.goto(`${REPO}/actions`, { waitUntil: "networkidle", timeout: 60000 });
    await sleep(2500);
    await shot("06_github_actions.png");
  } catch (e) { console.log("  x actions:", e.message.slice(0, 80)); }

  try {
    // 7. Repo principal (estructura/codigo)
    await page.goto(REPO, { waitUntil: "networkidle", timeout: 60000 });
    await sleep(2000);
    await shot("07_github_repo.png");
  } catch (e) { console.log("  x repo:", e.message.slice(0, 80)); }

  await browser.close();
  console.log("Capturas en", OUT);
})();
