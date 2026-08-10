// Static file server for the built site (dist) on 127.0.0.1:4174
const http = require("http");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..", "dist");
const PORT = 4174;
const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml",
  ".webp": "image/webp", ".ico": "image/x-icon",
};

const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split("?")[0]);
  if (p.endsWith("/")) p += "index.html";
  let fp = path.join(ROOT, p);
  if (!fp.startsWith(ROOT)) { res.writeHead(403); res.end("forbidden"); return; }
  fs.readFile(fp, (err, data) => {
    if (err) {
      // SPA-ish fallback: serve index.html for unknown paths (avoid 404 noise for hash routes)
      if (!path.extname(p)) {
        fs.readFile(path.join(ROOT, "index.html"), (e2, d2) => {
          if (e2) { res.writeHead(404); res.end("not found"); return; }
          res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
          res.end(d2);
        });
      } else { res.writeHead(404); res.end("not found"); }
      return;
    }
    res.writeHead(200, { "Content-Type": MIME[path.extname(fp).toLowerCase()] || "application/octet-stream" });
    res.end(data);
  });
});

server.listen(PORT, "127.0.0.1", () => console.log(`static server on http://127.0.0.1:${PORT}`));
