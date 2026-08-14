#!/usr/bin/env node
/* Online route reachability: every generated route (from dist file list) must be reachable on the public URL. */
const fs = require("fs");
const path = require("path");
const https = require("https");

const DIST = path.join(__dirname, "..", "..", "..", "asip-preview-build", "dist", "intelligence", "africa");
const BASE = "https://kenan032005.github.io/asip-site/previews/asip-intelligence-v2/intelligence/africa";
const OUT = path.join(__dirname, "..", "..", "qa-artifacts-online-preview", "online-route-reachability.json");

function listIndexes(dir) {
  const out = [];
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name);
    if (fs.statSync(p).isDirectory()) {
      out.push(...listIndexes(p));
    } else if (name === "index.html") {
      out.push(path.relative(DIST, path.dirname(p)).replace(/\\/g, "/"));
    }
  }
  return out.sort();
}

function check(url) {
  return new Promise((res) => {
    const req = https.get(url, { headers: { "User-Agent": "Mozilla/5.0" }, timeout: 20000 }, (r) => {
      r.resume();
      r.on("end", () => res(r.statusCode || 0));
    });
    req.on("error", () => res(0));
    req.on("timeout", () => { req.destroy(); res(0); });
  });
}

async function main() {
  const routes = listIndexes(DIST);
  const BATCH = 6;
  const results = [];
  let dead = [];
  for (let i = 0; i < routes.length; i += BATCH) {
    const batch = routes.slice(i, i + BATCH);
    const codes = await Promise.all(batch.map((r) => check(BASE + "/" + r + "/")));
    batch.forEach((r, j) => {
      results.push({ route: r, status: codes[j] });
      if (codes[j] !== 200) dead.push({ route: r, status: codes[j] });
    });
    await new Promise((r) => setTimeout(r, 80));
  }
  const summary = {
    base: BASE,
    routes_checked: routes.length,
    routes_200: results.filter((r) => r.status === 200).length,
    routes_non_200: dead,
    gate: dead.length === 0 ? "PASS" : "FAIL",
  };
  fs.writeFileSync(OUT, JSON.stringify({ summary, results: results.slice(0, 500) }, null, 2), "utf-8");
  console.log("=== ONLINE ROUTE REACHABILITY ===");
  console.log(JSON.stringify(summary, null, 2));
  if (dead.length) {
    console.log("NON-200 routes:", dead.slice(0, 20));
  }
  process.exit(summary.gate === "PASS" ? 0 : 1);
}

main().catch((e) => { console.error("FATAL", e); process.exit(2); });
