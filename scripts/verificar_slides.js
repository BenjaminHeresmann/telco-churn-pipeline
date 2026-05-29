// Captura cada slide del reveal.js para revisar el diseño.
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const INDEX = "file://" + path.resolve(__dirname, "..", "docs", "slides", "index.html").replace(/\\/g, "/");
const OUT = path.resolve(__dirname, "preview_slides");
fs.mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1.5 }).then(c => c.newPage());
  await page.goto(INDEX, { waitUntil: "networkidle", timeout: 60000 });
  await sleep(1200);
  const total = await page.evaluate(() => Reveal.getTotalSlides());
  console.log("Total slides:", total);
  for (let i = 0; i < total; i++) {
    await page.evaluate((n) => Reveal.slide(n, 0), i);
    await sleep(700);
    await page.screenshot({ path: path.join(OUT, `s${String(i + 1).padStart(2, "0")}.png`) });
  }
  console.log("Capturas en", OUT);
  await browser.close();
})();
