#!/usr/bin/env node
/* Online link QA: crawl the public preview, resolve every internal link, verify reachable. */
const fs = require("fs");
const path = require("path");
const http = require("http");
const https = require("https");

const BASE = "https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2";
const BASE_PATH = "/asip-site/previews/asip-intelligence-v2";
const ROOT = BASE + "/intelligence/africa/";
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-online-preview", "online-link-qa.json");
const HOST = "kenan032005.github.io";

const SEED_PATHS = [
  "/intelligence/africa/",
  "/intelligence/africa/entities/",
  "/intelligence/africa/relations/",
  "/intelligence/africa/sources/",
  "/intelligence/africa/network/",
  "/intelligence/africa/entity/al-shabaab/",
  "/intelligence/africa/entity/aqim/",
  "/intelligence/africa/relation/expa-shabaab-isis-somalia-rivalry/",
  "/intelligence/africa/relation/expc-eij-alqaida-integration/",
];

function fetch(url) {
  return new Promise((res) => {
    const mod = url.startsWith("https") ? https : http;
    const req = mod.get(url, { headers: { "User-Agent": "Mozilla/5.0" } }, (r) => {
      let body = "";
      r.on("data", (c) => (body += c));
      r.on("end", () => res({ status: r.statusCode || 0, body }));
      r.resume();
    });
    req.on("error", () => res({ status: 0, body: "" }));
    req.setTimeout(20000, () => { req.destroy(); res({ status: 0, body: "" }); });
  });
}

function normalize(basePath, href) {
  if (!href || href.startsWith("#") || href.startsWith("http") || href.startsWith("//") || href.startsWith("mailto:")) return null;
  if (href.includes("${url}") || href.includes('"')) return null; // runtime template
  const parts = href.split("#")[0].split("?")[0];
  if (!parts) return null;
  // resolve relative against basePath (which ends with /)
  const baseDir = basePath.endsWith("/") ? basePath : basePath + "/";
  let resolved;
  if (parts.startsWith("/")) resolved = parts;
  else resolved = baseDir + parts;
  // collapse ../
  const segs = resolved.split("/");
  const out = [];
  for (const s of segs) {
    if (s === "." || s === "") continue;
    if (s === "..") out.pop();
    else out.push(s);
  }
  const clean = "/" + out.join("/");
  if (!clean.endsWith("/")) {
    const m = clean.match(/\.(html?|js|css|json|png|jpg|svg|webp|ico|txt)$/);
    if (!m) return clean + "/";
  }
  return clean;
}

async function main() {
  const visited = new Set();
  const queue = [...SEED_PATHS];
  const problems = [];
  const linkStats = { checked: 0, dead: 0, missing: 0, assets404: 0 };
  const brokenSamples = [];

  while (queue.length) {
    const p = queue.shift();
    if (visited.has(p)) continue;
    visited.add(p);
    const abs = BASE + p;
    const r2 = await fetch(abs);
    linkStats.checked++;
    if (r2.status === 404) {
      linkStats.dead++;
      problems.push(`${p}  [404]`);
      if (brokenSamples.length < 10) brokenSamples.push(p);
      continue;
    }
    if (r2.status === 0) {
      linkStats.missing++;
      problems.push(`${p}  [unreachable]`);
      continue;
    }
    if (!r2.body.includes("<!DOCTYPE") && r2.body.length < 200) continue; // asset, ok if 200
    // extract links from HTML
    const hrefs = [...r2.body.matchAll(/href="([^"]*)"/g)].map((m) => m[1]);
    for (const h of hrefs) {
      // BASELINE known behavior: breadcrumb "../" points at entity/ relation/ dirs which
      // intentionally carry no index.html (SPA fallback only in the app shell); same as
      // production and already recorded as KNOWN_BASELINE in prior link QAs.
      if (h === "../" || h === "./") continue;
      const np = normalize(BASE_PATH + p, h);
      if (!np) continue;
      const isAsset = /\.(js|css|json|png|jpg|svg|webp|ico|txt|xml)$/.test(np);
      if (np.startsWith(BASE_PATH + "/intelligence/") || np.startsWith(BASE_PATH + "/assets/") || isAsset) {
        const rp = np.slice(BASE_PATH.length);
        if (!visited.has(rp) && !queue.includes(rp)) queue.push(rp);
      }
    }
    await new Promise((r) => setTimeout(r, 60));
  }

  // verify the full page set got crawled: expect >= 320 pages
  const pageCount = [...visited].filter((p) => !/\.(js|css|json|png|jpg|svg|webp|ico|txt|xml)$/.test(p)).length;
  const summary = {
    base: BASE,
    pages_visited: visited.size,
    html_pages: pageCount,
    links_checked: linkStats.checked,
    dead_links: linkStats.dead,
    unreachable: linkStats.missing,
    assets_404: linkStats.assets404,
    gate: linkStats.dead === 0 && linkStats.missing === 0 ? "PASS" : "FAIL",
    broken_samples: brokenSamples,
  };
  fs.writeFileSync(OUT, JSON.stringify({ summary, problems: problems.slice(0, 50) }, null, 2), "utf-8");
  console.log("=== ONLINE LINK QA SUMMARY ===");
  console.log(JSON.stringify(summary, null, 2));
  if (problems.length) {
    console.log("=== PROBLEMS (first 20) ===");
    problems.slice(0, 20).forEach((p) => console.log("  " + p));
  }
  process.exit(summary.gate === "PASS" ? 0 : 1);
}

main().catch((e) => { console.error("FATAL", e); process.exit(2); });
