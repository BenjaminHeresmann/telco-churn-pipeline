// Exporta las slides reveal.js a PDF (modo print-pdf) como respaldo.
const { chromium } = require("playwright");
const path = require("path");

const INDEX = "file://" + path.resolve(__dirname, "..", "docs", "slides", "index.html").replace(/\\/g, "/") + "?print-pdf";
const OUT = path.resolve(__dirname, "..", "docs", "slides", "Presentacion_Defensa_Evaluacion2.pdf");

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newContext({ deviceScaleFactor: 2 }).then(c => c.newPage());
  await page.goto(INDEX, { waitUntil: "networkidle", timeout: 90000 });
  await page.waitForTimeout(3000); // dejar que el iframe de la demo cargue
  await page.pdf({
    path: OUT,
    width: "1280px",
    height: "720px",
    printBackground: true,
    margin: { top: 0, right: 0, bottom: 0, left: 0 },
    pageRanges: "1-",
  });
  console.log("PDF:", OUT);
  await browser.close();
})();
