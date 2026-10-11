// ASIP shared data client.
// 优先使用嵌入快照 window.__DB__（GitHub Pages 静态快照健壮性），
// 否则回退到相对路径 fetch data/<name>.json（本地 server 或 Pages 均可）。
// 所有对外读取统一走 API.get(name)。
window.API = {
  _cache: {},
  async get(name) {
    if (window.__DB__ && window.__DB__[name] != null) {
      return window.__DB__[name];
    }
    if (this._cache[name]) return this._cache[name];
    // 含子路径（如 reports/chad/index）按相对路径直接取，否则从 data/ 取
    const url = name.indexOf("/") >= 0 ? (name + ".json") : ("data/" + name + ".json");
    try {
      const r = await fetch(url, { credentials: "same-origin" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const d = await r.json();
      this._cache[name] = d;
      return d;
    } catch (e) {
      // 本地缓存回退（上一版成功数据）
      const cached = this._localGet(name);
      if (cached) return cached;
      throw e;
    }
  },
  _localGet(name) {
    try {
      const raw = localStorage.getItem("asip:" + name);
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  },
  _localSet(name, d) {
    try { localStorage.setItem("asip:" + name, JSON.stringify(d)); } catch (e) {}
  },
  // 成功取到后写入本地缓存，作为失败回退
  async getCached(name) {
    try {
      const d = await this.get(name);
      this._localSet(name, d);
      return d;
    } catch (e) { throw e; }
  }
};
