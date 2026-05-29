// Genera el Informe Tecnico (Evaluacion 2) en .docx con formato de rubrica:
// Arial 11, interlineado 1.5, justificado, Letter, portada, indice, diagramas.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, ImageRun, PageBreak, Footer, PageNumber, ExternalHyperlink,
} = require("docx");

const IMG = path.resolve(__dirname, "..", "docs", "img");
const OUT = path.resolve(__dirname, "..", "docs", "Informe_Tecnico_Evaluacion2.docx");

// ---- helpers ----
const AZUL = "1F4E79", AZUL2 = "2E75B6", GRIS = "F2F2F2", BORDE = "BFBFBF";

// Lee dimensiones de un PNG (bytes 16-23) y escala a una caja max manteniendo ratio.
function fitImage(file, maxW, maxH) {
  const buf = fs.readFileSync(file);
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  const r = Math.min(maxW / w, maxH / h);
  return { data: buf, width: Math.round(w * r), height: Math.round(h * r) };
}

function img(file, maxW, maxH, alt) {
  const { data, width, height } = fitImage(file, maxW, maxH);
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 120 },
    children: [new ImageRun({ type: "png", data, transformation: { width, height },
      altText: { title: alt, description: alt, name: alt } })],
  });
}

function p(text, opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.JUSTIFIED,
    spacing: { after: opts.after ?? 120, line: 360 },
    children: parseRuns(text),
  });
}

// Soporta **negrita** y `code` inline simple.
function parseRuns(text) {
  const runs = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) runs.push(new TextRun(text.slice(last, m.index)));
    const tok = m[0];
    if (tok.startsWith("**")) runs.push(new TextRun({ text: tok.slice(2, -2), bold: true }));
    else runs.push(new TextRun({ text: tok.slice(1, -1), font: "Consolas", size: 20 }));
    last = re.lastIndex;
  }
  if (last < text.length) runs.push(new TextRun(text.slice(last)));
  return runs.length ? runs : [new TextRun(text)];
}

function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 240, after: 120 },
    children: [new TextRun({ text, bold: true, color: AZUL, font: "Arial", size: 30 })] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 160, after: 80 },
    children: [new TextRun({ text, bold: true, color: AZUL2, font: "Arial", size: 25 })] });
}
function bullet(text) {
  return new Paragraph({ numbering: { reference: "b", level: 0 },
    alignment: AlignmentType.JUSTIFIED, spacing: { after: 60, line: 360 }, children: parseRuns(text) });
}

// Tabla simple desde matriz de strings; primera fila = encabezado.
function tabla(headers, rows, colW) {
  const total = colW.reduce((a, b) => a + b, 0);
  const border = { style: BorderStyle.SINGLE, size: 1, color: BORDE };
  const borders = { top: border, bottom: border, left: border, right: border };
  const mkCell = (txt, w, head) => new TableCell({
    borders, width: { size: w, type: WidthType.DXA },
    shading: { fill: head ? AZUL : "FFFFFF", type: ShadingType.CLEAR },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ spacing: { line: 276 },
      children: head
        ? [new TextRun({ text: String(txt), bold: true, color: "FFFFFF", size: 20 })]
        : parseRuns(String(txt)) })],
  });
  const headRow = new TableRow({ tableHeader: true,
    children: headers.map((hd, i) => mkCell(hd, colW[i], true)) });
  const bodyRows = rows.map(r => new TableRow({
    children: r.map((c, i) => mkCell(c, colW[i], false)) }));
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: colW,
    rows: [headRow, ...bodyRows] });
}

function spacer(after = 120) { return new Paragraph({ spacing: { after }, children: [new TextRun("")] }); }

// ---- contenido ----
const children = [];

// PORTADA
children.push(
  new Paragraph({ spacing: { before: 1200, after: 0 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "DUOC UC", bold: true, color: AZUL, size: 28, font: "Arial" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 },
    children: [new TextRun({ text: "Escuela de Informática y Telecomunicaciones", size: 22, color: "595959" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 600, after: 120 },
    children: [new TextRun({ text: "Informe Técnico — Evaluación Parcial N°2", bold: true, size: 40, color: AZUL, font: "Arial" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 },
    children: [new TextRun({ text: "Pipeline DataOps para Predicción de Churn en Telecomunicaciones", size: 28, color: "404040" })] }),
  img(path.join(IMG, "arquitectura.png"), 560, 220, "Arquitectura cloud"),
  spacer(400),
);
// tabla de portada
children.push(new Table({
  width: { size: 7200, type: WidthType.DXA }, columnWidths: [2600, 4600],
  alignment: AlignmentType.CENTER,
  rows: [
    ["Asignatura", "ITY1101 — Gestión de Datos para IA"],
    ["Sección", "003V"],
    ["Caso", "Telco Customer Churn (clasificación de abandono)"],
    ["Integrantes", "Benjamín Heresmann — Ingeniero de Datos (ingesta, validación, arquitectura)\nDiego Hernández — Ingeniero de BD / DataOps (limpieza, carga, seguridad, deploy)"],
    ["Arquitectura", "Pipeline modular cloud (FastAPI · Railway · Supabase)"],
    ["Metodología", "PMBOK híbrido (predictivo + adaptativo)"],
    ["Fecha de entrega", "2 de junio de 2026"],
  ].map(([k, v]) => new TableRow({ children: [
    new TableCell({ width: { size: 2600, type: WidthType.DXA },
      shading: { fill: GRIS, type: ShadingType.CLEAR }, margins: { top: 60, bottom: 60, left: 120, right: 120 },
      borders: { top: { style: BorderStyle.SINGLE, size: 1, color: BORDE }, bottom: { style: BorderStyle.SINGLE, size: 1, color: BORDE }, left: { style: BorderStyle.SINGLE, size: 1, color: BORDE }, right: { style: BorderStyle.SINGLE, size: 1, color: BORDE } },
      children: [new Paragraph({ children: [new TextRun({ text: k, bold: true, size: 20 })] })] }),
    new TableCell({ width: { size: 4600, type: WidthType.DXA },
      margins: { top: 60, bottom: 60, left: 120, right: 120 },
      borders: { top: { style: BorderStyle.SINGLE, size: 1, color: BORDE }, bottom: { style: BorderStyle.SINGLE, size: 1, color: BORDE }, left: { style: BorderStyle.SINGLE, size: 1, color: BORDE }, right: { style: BorderStyle.SINGLE, size: 1, color: BORDE } },
      children: String(v).split("\n").map(linea => new Paragraph({ spacing: { after: 20 }, children: [new TextRun({ text: linea, size: 20 })] })) }),
  ] })),
}));
children.push(new Paragraph({ children: [new PageBreak()] }));

// INDICE (manual)
children.push(h1("Índice"));
[
  "1. Resumen ejecutivo",
  "2. Justificación de la metodología PMBOK",
  "3. Planificación del proyecto (WBS, hitos, Carta Gantt, seguimiento)",
  "4. Arquitectura cloud desacoplada",
  "5. Explicación técnica del pipeline (4 etapas)",
  "6. Plan de seguridad para entorno DataOps",
  "7. Estrategia de KPIs de monitoreo",
  "8. Documentación, evidencias y modelo de datos",
  "9. Conclusiones y próximos pasos",
].forEach(t => children.push(new Paragraph({ spacing: { after: 60, line: 360 },
  children: [new TextRun({ text: t, size: 22 })] })));
children.push(new Paragraph({ children: [new PageBreak()] }));

// 1. RESUMEN EJECUTIVO
children.push(h1("1. Resumen ejecutivo"));
children.push(p("Este informe documenta el diseño, planificación e implementación de un pipeline de datos automatizado, bajo principios **DataOps**, para una compañía de telecomunicaciones que enfrenta un alto índice de abandono de clientes (**churn** ≈ 26,5%). El proyecto usa el dataset público “Telco Customer Churn” (7.043 clientes, 21 variables) para construir un flujo de cuatro etapas —ingesta, limpieza y transformación, validación estructural y semántica, y carga a base de datos relacional— que deja la información lista para entrenar un modelo predictivo de IA en la Evaluación 3."));
children.push(p("El **valor para la organización** es doble: reduce el costo y los errores de la preparación manual de datos, y habilita la focalización de campañas de retención sobre los clientes con mayor probabilidad de abandono, protegiendo los ingresos recurrentes. La solución se implementa con una **arquitectura cloud-native desacoplada**: el procesamiento corre como API REST en **Railway** (cómputo), la persistencia usa **PostgreSQL gestionado en Supabase** (datos), y el código se versiona en **GitHub** con CI automatizado (pytest en cada push). No es un monolito: cada componente escala y se despliega de forma independiente. El sistema está desplegado, probado end-to-end y operativo en producción."));
children.push(p("El equipo, autorizado por el docente a operar con **dos integrantes**, dividió las responsabilidades técnicas de forma equitativa manteniendo dominio individual de toda la solución."));

// 2. PMBOK
children.push(h1("2. Justificación de la metodología PMBOK"));
children.push(p("Se adopta un **enfoque híbrido del PMBOK** (predictivo + adaptativo). El **componente predictivo** se aplica a actividades de requisitos fijos y dependencias claras —modelado de la base de datos, esquema de validación, Dockerfile e integración con el repositorio—, planificadas con cronograma, hitos y entregables. El **componente adaptativo** se aplica a lo exploratorio —afinamiento de reglas de validación semántica, KPIs y ensayo de la demo—, trabajado en ciclos cortos con revisión cruzada entre los integrantes."));
children.push(p("Una metodología puramente cascada sería rígida frente a los hallazgos que aparecen al procesar el dataset por primera vez; una puramente ágil desordenaría las dependencias técnicas. El híbrido permite **planificar lo estable e iterar lo incierto**, coherente con un equipo pequeño y un plazo acotado. El seguimiento se realiza con un tablero **Trello** (columnas Por hacer / En progreso / Terminado), elegido sobre Jira o Azure DevOps por simplicidad y escala del equipo."));

// 3. PLANIFICACION
children.push(h1("3. Planificación del proyecto"));
children.push(h2("3.1 Estructura de Desglose del Trabajo (WBS) e hitos"));
children.push(tabla(
  ["Fase", "Actividades principales", "Entregable"],
  [
    ["1. Setup", "Arquitectura, stack, repo, Docker, DDL", "Repo y entorno cloud operativo"],
    ["2. Pipeline", "Ingesta, limpieza, validación, carga, orquestador, KPIs", "Pipeline end-to-end funcional"],
    ["3. Calidad", "Tests, auditoría, plan de seguridad", "Tests verdes + reporte auditoría"],
    ["4. Documentación", "Informe, diagramas, slides, ensayo demo", "Informe PDF + presentación"],
  ], [1400, 4560, 3400]));
children.push(spacer(60));
children.push(p("**Hitos:** H1 — stack y entorno cloud operativo; H2 — pipeline end-to-end cargando datos en Supabase; H3 — documentación, auditoría y demo listas para la defensa."));
children.push(h2("3.2 Carta Gantt"));
children.push(img(path.join(IMG, "gantt.png"), 600, 320, "Carta Gantt"));

// 4. ARQUITECTURA
children.push(new Paragraph({ pageBreakBefore: true, heading: HeadingLevel.HEADING_1,
  spacing: { before: 0, after: 120 }, children: [new TextRun({ text: "4. Arquitectura cloud desacoplada", bold: true, color: AZUL, font: "Arial", size: 30 })] }));
children.push(p("A solicitud del docente, la solución **no es un monolito** y queda desplegada en la nube. Se diseñan tres servicios independientes que se comunican por interfaces estándar (HTTPS REST y SQL sobre TLS):"));
children.push(tabla(
  ["Capa", "Servicio", "Rol"],
  [
    ["Datos", "Supabase (PostgreSQL 17)", "Persiste datos curados, auditoría y rechazados; SSL nativo"],
    ["Cómputo", "Railway (Docker + FastAPI)", "Ejecuta el pipeline expuesto como API REST"],
    ["CI", "GitHub Actions", "Corre pytest en cada push (gate de calidad)"],
    ["CD", "railway up", "Deploy por comando (gate humano; auto-deploy activable)"],
  ], [1300, 3100, 4960]));
children.push(spacer(60));
children.push(p("**Por qué desacoplar:** cada servicio se actualiza, escala y reinicia por separado; si Railway cae, la BD permanece; si crece el tráfico se escala solo la API; y sustituir un componente (p. ej. cambiar Supabase por otro Postgres) solo implica actualizar la cadena de conexión. Esto reduce el radio de impacto de cualquier fallo frente a un monolito."));
children.push(img(path.join(IMG, "arquitectura.png"), 620, 240, "Arquitectura"));
children.push(p("La API expone cada etapa como endpoint REST independiente (`/pipeline/ingest`, `/clean`, `/validate`, `/load`) más un orquestador `/pipeline/run`, además de monitoreo (`/health`, `/kpis/resumen`, `/kpis/last`, `/logs/last`, `/rechazados`) y documentación interactiva autogenerada en `/docs` (Swagger)."));

// 5. PIPELINE
children.push(new Paragraph({ pageBreakBefore: true, heading: HeadingLevel.HEADING_1,
  spacing: { before: 0, after: 120 }, children: [new TextRun({ text: "5. Explicación técnica del pipeline", bold: true, color: AZUL, font: "Arial", size: 30 })] }));
children.push(img(path.join(IMG, "pipeline.png"), 300, 470, "Pipeline 4 etapas"));
children.push(h2("5.1 Ingesta"));
children.push(p("Captura el CSV fuente y lo deposita en `data/raw/` con sello temporal, sin transformarlo. Estrategia de fuentes en cascada: parámetro explícito → Supabase Storage → ruta local → **fallback por defecto: dataset versionado en el repo** (`data/source/`), que viaja dentro de la imagen Docker. Se elige **ingesta por lotes (batch)** porque el dato es un CSV estático; streaming/Kafka sería sobreingeniería. El dataset versionado hace la ingesta reproducible y sin dependencias externas en la demo."));
children.push(h2("5.2 Limpieza y transformación"));
children.push(p("Normaliza y enriquece sin aplicar reglas de negocio: (1) convierte `TotalCharges` de texto con celdas vacías a numérico —resolviendo el bug clásico del dataset—, imputando 0 a los 11 clientes con `tenure=0` (recién registrados, sin facturación, imputación justificada); (2) convierte columnas Yes/No a booleano; (3) elimina duplicados por `customerID`; (4) crea la feature derivada `tenure_group` (5 rangos). Se trabaja sobre copia, nunca sobre el crudo."));
children.push(h2("5.3 Validación estructural y semántica"));
children.push(p("**Estructural (pandera):** tipos por columna, rangos (`tenure` 0–100, `MonthlyCharges` ≥ 0), valores permitidos en categóricas y formato de `customerID` por expresión regular. **Semántica (reglas de negocio):** coherencia entre campos —si `InternetService=No`, los seis servicios derivados deben ser “No internet service”; si `PhoneService=False`, `MultipleLines` debe ser “No phone service”; coherencia de `TotalCharges` con `MonthlyCharges`×`tenure`. Las filas válidas pasan a `data/validated/`; las inválidas a `data/rejected/` con su **motivo**, y se auditan en la tabla `clientes_rechazados`. Se eligió pandera sobre Great Expectations por simplicidad e integración con pandas."));
children.push(h2("5.4 Carga a base de datos"));
children.push(p("Persiste los validados en Supabase con SQLAlchemy + psycopg2 y SSL. La carga es **full-refresh idempotente**: dentro de una transacción hace `TRUNCATE` de las tablas de estado y luego inserta, de modo que reejecutar el pipeline produzca siempre el mismo resultado (reproducibilidad DataOps), sin errores de clave duplicada. La auditoría (`carga_logs`) **nunca** se trunca. La operación es atómica: ante fallo, ROLLBACK deja la tabla intacta. El engine se cachea (singleton con pool acotado) para no agotar el pooler de Supabase."));
children.push(p("**Manejo de anomalías:** errores de conexión → estado “ERROR” registrado en `carga_logs`; violación de restricción → rollback; datos inválidos → separados y auditados, nunca descartados silenciosamente."));

// 6. SEGURIDAD
children.push(new Paragraph({ pageBreakBefore: true, heading: HeadingLevel.HEADING_1,
  spacing: { before: 0, after: 120 }, children: [new TextRun({ text: "6. Plan de seguridad para entorno DataOps", bold: true, color: AZUL, font: "Arial", size: 30 })] }));
children.push(p("El pipeline maneja datos personales bajo el alcance de la **Ley 19.628** (Protección de la Vida Privada, Chile) y la **Ley 21.459** (delitos informáticos), con controles compatibles con ISO/IEC 27001."));
children.push(tabla(
  ["Ámbito", "Medida implementada"],
  [
    ["Normas legales", "Ley 19.628 (datos personales) y Ley 21.459; tratamiento limitado al propósito declarado"],
    ["Cifrado en tránsito", "Conexión a PostgreSQL forzada con SSL (sslmode=require)"],
    ["Cifrado en reposo", "Volumen gestionado por Supabase; opción pgcrypto a nivel columna"],
    ["Control de acceso", "Rol telco_analista solo-SELECT (mínimo privilegio); credenciales por rol"],
    ["Gestión de secretos", "Variables de entorno en Railway y .env gitignored; cero credenciales en el repo"],
    ["Enmascaramiento", "customerID anonimizado; hashing SHA-256 con sal para datos identificables"],
    ["Anti-inyección", "SQLAlchemy con parámetros bindados; sin concatenación de SQL"],
    ["Logs sin PII", "Se registran conteos y tipos de error, no valores de columnas sensibles"],
    ["Auditoría", "Tabla carga_logs (quién/cuándo/cuántos/estado) + clientes_rechazados"],
  ], [2200, 7160]));

// 7. KPIs
children.push(h1("7. Estrategia de KPIs de monitoreo"));
children.push(p("Cada ejecución mide y persiste indicadores en `carga_logs`, consultables vía `/kpis/resumen` y `/kpis/last`. Si un KPI cruza su umbral, el logger emite `WARNING` (en producción, integrable a Grafana/alertas):"));
children.push(tabla(
  ["KPI", "Definición", "Umbral de alerta"],
  [
    ["Latencia total", "Segundos del pipeline completo", "> 30 s"],
    ["Latencia por etapa", "Segundos por etapa", "> 50% del total"],
    ["Tasa de validez", "% de registros que pasan validación", "< 95%"],
    ["Completitud", "% de no nulos por columna crítica", "< 95%"],
    ["Volumen", "Registros procesados", "< 5.000"],
    ["Tasa de error en carga", "% inserts fallidos / estado de ejecución", "≠ OK"],
  ], [2000, 4760, 2600]));

// 8. EVIDENCIAS + ER
children.push(new Paragraph({ pageBreakBefore: true, heading: HeadingLevel.HEADING_1,
  spacing: { before: 0, after: 120 }, children: [new TextRun({ text: "8. Documentación, evidencias y modelo de datos", bold: true, color: AZUL, font: "Arial", size: 30 })] }));
children.push(h2("8.1 Recursos en producción"));
children.push(tabla(
  ["Recurso", "Enlace"],
  [
    ["Repositorio GitHub", "github.com/BenjaminHeresmann/telco-churn-pipeline"],
    ["API en producción", "telco-api-production-e466.up.railway.app"],
    ["Swagger (demo)", "telco-api-production-e466.up.railway.app/docs"],
    ["Base de datos", "PostgreSQL 17 en Supabase (proyecto telco-churn)"],
  ], [2400, 6960]));
children.push(spacer(60));
children.push(h2("8.2 Evidencia de ejecución (extracto de logs)"));
children.push(new Paragraph({ shading: { fill: "F7F7F7", type: ShadingType.CLEAR }, spacing: { after: 120, line: 264 },
  children: [
    new TextRun({ text: "ingesta    | Ingesta completada | filas=7043 | columnas=21", font: "Consolas", size: 17 }),
  ] }));
[
  "limpieza   | TotalCharges: 11 NaN imputados con 0 (tenure=0)",
  "validacion | estructural: 7043 ok, 0 rechazados",
  "validacion | semantica:  7043 ok, 0 rechazados",
  "carga_bd   | Tablas de estado vaciadas (full-refresh)",
  "carga_bd   | Insertados 7043 registros en clientes",
  "orquestador| FIN PIPELINE | duracion total = ~2 seg",
].forEach(l => children.push(new Paragraph({ shading: { fill: "F7F7F7", type: ShadingType.CLEAR },
  spacing: { after: 0, line: 264 }, children: [new TextRun({ text: l, font: "Consolas", size: 17 })] })));
children.push(spacer(60));
children.push(p("Con un dataset que contiene errores intencionales (`scripts/inyectar_errores.py`), el pipeline los detecta y separa: **5 estructurales + 3 semánticos** rechazados y auditados, demostrando el control de calidad. Validado además con `pytest` (6/6) en CI y pruebas end-to-end en producción (idempotencia confirmada: reejecutar deja siempre 7.043 registros, 0 duplicados)."));
children.push(h2("8.3 Modelo de datos"));
children.push(img(path.join(IMG, "er.png"), 600, 360, "Modelo entidad-relación"));
children.push(p("El modelo es de **tabla única analítica** (`clientes`): cada fila es un cliente con sus atributos planos, sin claves foráneas entre entidades. La integridad se garantiza con **clave primaria** (`customer_id`), **restricciones CHECK** (rangos y dominios), **NOT NULL** y **transacciones**. `carga_logs` y `clientes_rechazados` son tablas de auditoría independiente (relación lógica por fecha, no por FK), lo que simplifica las recargas full-refresh."));

// 9. CONCLUSIONES
children.push(h1("9. Conclusiones y próximos pasos"));
children.push(p("La solución cumple los cuatro requisitos del pipeline DataOps —ingesta, limpieza, validación y carga— de forma **reproducible** (Docker + dataset versionado), **trazable** (logs y auditoría en BD), **segura** (SSL, control de acceso, secretos fuera del repo) y **escalable por módulos** (arquitectura cloud desacoplada). El sistema está desplegado y probado end-to-end en producción."));
children.push(p("**Próximos pasos:** (Evaluación 3) entrenar un modelo de clasificación binaria sobre `churn` usando las variables de mayor poder discriminante (`tenure`, `Contract`, `MonthlyCharges`, `InternetService`, `PaymentMethod`); a mediano plazo, conectar una fuente real vía la etapa de ingesta, migrar la orquestación a Airflow ante múltiples fuentes y exponer un dashboard de KPIs en Grafana o Power BI."));

// ANEXO A — EVIDENCIAS
const EV = path.join(IMG, "evidencia");
function figura(file, titulo, caption, maxW = 590, maxH = 540) {
  const out = [new Paragraph({ spacing: { before: 160, after: 40 },
    children: [new TextRun({ text: titulo, bold: true, color: AZUL2, size: 21 })] })];
  out.push(img(path.join(EV, file), maxW, maxH, titulo));
  if (caption) out.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
    children: [new TextRun({ text: caption, italics: true, size: 17, color: "808080" })] }));
  return out;
}
children.push(new Paragraph({ pageBreakBefore: true, heading: HeadingLevel.HEADING_1,
  spacing: { before: 0, after: 80 }, children: [new TextRun({ text: "Anexo A — Evidencias de ejecución", bold: true, color: AZUL, font: "Arial", size: 30 })] }));
children.push(p("El cuerpo del informe corresponde a las secciones 1 a 9 (páginas 1–11). Este anexo es material de respaldo: capturas reales del sistema en producción, tomadas el 29 de mayo de 2026."));
[
  ...figura("01_swagger.png", "A.1 — API documentada (Swagger UI en producción)",
    "Endpoints REST del pipeline expuestos y autodocumentados en /docs."),
  ...figura("04_pipeline_run.png", "A.2 — Pipeline ejecutado en vivo (POST /pipeline/run)",
    "Respuesta 200 con las 4 etapas OK y archivos generados; URL real de Railway."),
  ...figura("05_supabase_datos.png", "A.3 — Datos en Supabase (consulta SQL directa)",
    "7.043 clientes cargados en PostgreSQL 17; muestra real de la tabla clientes.", 600, 430),
  ...figura("06_github_actions.png", "A.4 — Integración continua (GitHub Actions)",
    "Workflows de CI en verde para cada push al repositorio público.", 600, 470),
].forEach(el => children.push(el));

// ---- documento ----
const doc = new Document({
  creator: "Benjamín Heresmann · Diego Hernández",
  title: "Informe Técnico Evaluación 2 - Pipeline Telco Churn",
  styles: {
    default: { document: { run: { font: "Arial", size: 22 }, paragraph: { spacing: { line: 360 } } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: AZUL, font: "Arial" }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, color: AZUL2, font: "Arial" }, paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [
    { reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 260 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Pipeline DataOps Telco Churn · ITY1101 Duoc UC · Página ", size: 16, color: "808080" }),
        new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "808080" })] })] }) },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => { fs.writeFileSync(OUT, buf); console.log("OK:", OUT, "(", buf.length, "bytes )"); });
