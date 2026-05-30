// Renderiza diagramas Mermaid a PNG de ALTA RESOLUCION (proyector) con mermaid-cli.
// scale 3 + fontSize grande + lineas gruesas => texto legible en sala de clases.
// Uso: node gen_diagramas_hd.js   (desde build/)
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(ROOT, "docs", "img");
const TMP = path.join(__dirname, "diagramas");
const MMDC_CLI = path.join(__dirname, "node_modules", "@mermaid-js", "mermaid-cli", "src", "cli.js");
fs.mkdirSync(TMP, { recursive: true });
fs.writeFileSync(path.join(TMP, "puppeteer.json"), JSON.stringify({ args: ["--no-sandbox", "--disable-setuid-sandbox"] }));

// Tema coherente con el sistema de diseno de las slides, con fuente grande.
const INIT = (fs) =>
  `%%{init: {'theme':'base','themeVariables':{` +
  `'fontFamily':'Inter, Segoe UI, Arial','fontSize':'${fs}px',` +
  `'primaryColor':'#EAF1F9','primaryBorderColor':'#15406b','primaryTextColor':'#0F172A',` +
  `'lineColor':'#475569','tertiaryColor':'#F1F5F9','clusterBkg':'#F8FAFC','clusterBorder':'#CBD5E1'}}}%%\n`;

// Pipeline: esqueleto LIMPIO (el detalle de cada etapa va en las slides 9-12).
const PIPELINE =
  INIT(26) +
  `flowchart TB
  SRC([CSV fuente · repo]):::src --> E1[<b>1 · Ingesta</b>]:::e
  E1 --> E2[<b>2 · Limpieza</b>]:::e
  E2 --> E3[<b>3 · Validación</b>]:::e
  E3 --> VAL([Válidos]):::ok
  E3 --> REJ([Rechazados<br/>+ motivo]):::ko
  VAL --> E4[<b>4 · Carga BD</b>]:::e
  E4 --> DB[(Supabase<br/>PostgreSQL 17)]:::db
  REJ -. audita .-> DB
  classDef src fill:#FEF6E7,stroke:#D9A21B,color:#0F172A,stroke-width:2px
  classDef e fill:#EAF1F9,stroke:#15406b,color:#0F172A,stroke-width:2.5px
  classDef ok fill:#E7F8F0,stroke:#0E9F6E,color:#0F172A,stroke-width:2px
  classDef ko fill:#FDECEA,stroke:#DC4C3E,color:#0F172A,stroke-width:2px
  classDef db fill:#F1EBFB,stroke:#7C3AED,color:#0F172A,stroke-width:2.5px
`;

// Salida SOLO para slides (pipeline_slide.png). Los PNG del informe
// (pipeline.png, er.png, arquitectura.png, gantt.png) NO se tocan: los mantiene gen_diagramas.py.
const DIAGRAMS = { pipeline_slide: PIPELINE };

for (const [name, code] of Object.entries(DIAGRAMS)) {
  const src = path.join(TMP, `${name}.mmd`);
  const dst = path.join(OUT, `${name}.png`);
  fs.writeFileSync(src, code);
  execFileSync(process.execPath, [MMDC_CLI, "-i", src, "-o", dst, "-p", path.join(TMP, "puppeteer.json"), "-b", "white", "-s", "3"], {
    stdio: "inherit",
  });
  const kb = Math.round(fs.statSync(dst).size / 1024);
  console.log(`  OK ${name}.png  (${kb} KB)`);
}
console.log("Diagramas HD listos en docs/img/");
