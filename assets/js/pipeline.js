/**
 * pipeline.js —— ASIP Stage-1 前端管道辅助模块
 *
 * 提供：
 * 1. 模块级错误隔离（单个数据文件加载失败不影响其他模块）
 * 2. run_id 驱动的缓存失效
 * 3. 降级显示与"重新加载"按钮
 * 4. 页面底部 ASIP_BUILD_META 信息
 */

(function () {
  'use strict';

  // ── 构建元数据 ─────────────────────────────────────────
  const META = window.ASIP_BUILD_META || {};
  const PIPELINE_VERSION = META.pipeline_version || 1;
  const BUILD_RUN_ID = META.run_id || '';

  // ── 缓存键命名空间（按 run_id 隔离）─────────────────────
  function cacheKey(name) {
    return 'asip_v' + PIPELINE_VERSION + ':' + (BUILD_RUN_ID ? BUILD_RUN_ID + ':' : '') + name;
  }

  // ── localStorage 读写（尊重 run_id）─────────────────────
  function cacheGet(name) {
    try {
      const raw = localStorage.getItem(cacheKey(name));
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (e) { return null; }
  }

  function cacheSet(name, data) {
    try {
      // 只缓存有限键，防止爆满
      const allowed = ['status', 'latest-summary', 'events', 'countries'];
      if (allowed.indexOf(name) < 0) return;
      localStorage.setItem(cacheKey(name), JSON.stringify(data));
      // 清理旧版缓存
      const oldKey = 'asip:' + name;
      if (localStorage.getItem(oldKey)) {
        localStorage.removeItem(oldKey);
      }
    } catch (e) { /* quota exceeded, silently ignore */ }
  }

  // ── 清除过期缓存 ──────────────────────────────────────
  function clearStaleCache() {
    try {
      const keys = Object.keys(localStorage);
      const prefix = 'asip_v';
      for (let k of keys) {
        if (k.startsWith(prefix)) {
          // 解析版本号
          const m = k.match(/^asip_v(\d+):/);
          if (m && parseInt(m[1]) < PIPELINE_VERSION) {
            localStorage.removeItem(k);
          }
        }
      }
      // 也清除不带版本号的旧缓存
      const oldPrefix = 'asip:';
      for (let k of keys) {
        if (k.startsWith(oldPrefix) && !k.startsWith('asip_v')) {
          localStorage.removeItem(k);
        }
      }
    } catch (e) { /* ignore */ }
  }
  clearStaleCache();

  // ── 安全的 fetch（含独立 try/catch，不影响其他模块）─────
  window.ASIP = {
    META: META,
    BUILD_RUN_ID: BUILD_RUN_ID,
    PIPELINE_VERSION: PIPELINE_VERSION,

    /**
     * 安全加载单个数据文件。
     * - 优先 window.__DB__（构建时内联快照，纯回退）
     * - 否则 fetch 相对路径
     * - 加载成功写入 run_id 缓存
     * - 加载失败降级读缓存
     * @param {string} name - 数据集名（如 "status", "latest-summary", "events"）
     * @returns {Promise<object>} 数据对象
     */
    async load(name) {
      // __DB__ 快照优先（带结构一致性检查：同一 pageview 内尽量不从两个源混合取数）
      if (window.__DB__ && window.__DB__[name] != null) {
        const d = window.__DB__[name];
        cacheSet(name, d);
        return d;
      }

      // 从 gh-pages 相对路径 fetch
      const url = name.indexOf('/') >= 0 ? (name + '.json') : ('data/' + name + '.json');
      try {
        const r = await fetch(url, { credentials: 'same-origin', cache: 'no-cache' });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const d = await r.json();
        cacheSet(name, d);
        return d;
      } catch (e) {
        // 降级：读本地缓存
        const cached = cacheGet(name);
        if (cached) {
          console.warn('ASIP: ' + name + ' 加载失败（' + e.message + '），使用本地缓存。');
          return cached;
        }
        throw e;
      }
    },

    /**
     * 带错误处理的模块加载器。
     * @param {string} name - 数据集名
     * @param {HTMLElement} container - 显示数据的 DOM 容器
     * @param {function} render - 成功时渲染函数 render(data, container)
     * @returns {Promise<boolean>} true=成功, false=失败
     */
    async loadModule(name, container, render) {
      if (!container) return false;
      try {
        const data = await this.load(name);
        await render(data, container);
        return true;
      } catch (e) {
        container.innerHTML = '<div class="module-error">' +
          '<p>⚠️ 模块加载失败（' + (e.message || '未知错误') + '）</p>' +
          '<button class="btn btn-sm" onclick="location.reload()">🔄 重新加载</button>' +
          '</div>';
        return false;
      }
    },

    /**
     * 在页面底部渲染构建元数据（run_id + 最后更新时间）。
     * @param {object} status - status.json 数据
     */
    renderFooterMeta(status) {
      const footer = document.getElementById('asip-build-meta');
      if (!footer) return;
      let html = '<span class="meta-item">🔄 Pipeline v' + PIPELINE_VERSION + '</span>';
      if (BUILD_RUN_ID) {
        html += ' <span class="meta-item">📋 Run: ' + BUILD_RUN_ID.slice(0, 12) + '…</span>';
      }
      if (status) {
        const ts = status.last_updated_beijing || status.generated_at_bj || status.last_update_bj || '';
        if (ts) {
          html += ' <span class="meta-item">🕐 更新: ' + ts + '</span>';
        }
        if (status.status && status.status !== 'success') {
          html += ' <span class="meta-item meta-warn">⚠️ 状态: ' + (status.status_cn || status.status) + '</span>';
        }
      }
      footer.innerHTML = html;
    },

    /**
     * 全局错误显示。
     * @param {string} msg - 错误消息
     */
    showGlobalError(msg) {
      const el = document.getElementById('asip-global-error');
      if (el) {
        el.style.display = 'block';
        el.innerHTML = '<strong>⚠️ 数据加载异常</strong><br>' + msg +
          ' <button class="btn btn-sm" onclick="location.reload()">🔄 重新加载</button>';
      }
    },
  };
})();
