(function () {
  "use strict";
  const api = window.ASIP_INTEL;
  let focusId = "actor-jnim";
  let historyStack = [];
  let zoom = 1;
  let positions = {};
  let selectedRelation = null;
  let drawToken = 0;
  let importanceFilter = { L1: true, L2: true, L3: false };
  const NS = "http://www.w3.org/2000/svg";
  const svg = document.getElementById("graphSvg");
  const viewport = document.getElementById("graphViewport");
  const info = document.getElementById("nodeInfo");
  if (!svg || !viewport) return;

  const RINGS = {
    inner: { label: "结构与地理", radius: 168 },
    middle: { label: "组织与力量", radius: 258 },
    outer: { label: "人物", radius: 348 }
  };
  const RING_ORDER = ["inner", "middle", "outer"];

  function queryFocus() {
    const raw = new URLSearchParams(window.location.search).get("focus");
    return raw && api.entityById(raw) ? raw : "actor-jnim";
  }
  function ringFor(rel) {
    if (rel.display_ring && RINGS[rel.display_ring]) return rel.display_ring;
    const type = rel.relationship_type;
    if (["affiliated_with", "constituent_of", "operates_in", "part_of_network"].indexOf(type) >= 0) return "inner";
    if (["hostile_to", "historically_associated_with"].indexOf(type) >= 0) return "middle";
    if (["led_by", "founded_by"].indexOf(type) >= 0) return "outer";
    return "middle";
  }
  function relationClass(rel) {
    if (rel.relationship_type === "hostile_to") return "hostile";
    if (rel.disputed) return "disputed";
    if (rel.temporal_sensitive || String(rel.current_status || "").indexOf("historical") >= 0) return "historical";
    if (["led_by", "founded_by"].indexOf(rel.relationship_type) >= 0) return "leadership";
    if (rel.relationship_type === "operates_in") return "presence";
    return "normal";
  }
  function relGroupFilter(rel) {
    const group = rel.relationship_type;
    return ["affiliated_with", "constituent_of", "led_by", "founded_by", "operates_in", "hostile_to", "historically_associated_with", "part_of_network"].indexOf(group) >= 0 ? group : "other";
  }
  function filters() {
    const typeFilters = {};
    document.querySelectorAll("[data-type-filter]").forEach(function (input) { typeFilters[input.getAttribute("data-type-filter")] = input.checked; });
    const relFilters = {};
    document.querySelectorAll("[data-rel-filter]").forEach(function (input) { relFilters[input.getAttribute("data-rel-filter")] = input.checked; });
    return { types: typeFilters, rels: relFilters };
  }
  function importanceVisible(entity) { return importanceFilter[entity.importance_level || "L3"] !== false; }
  function color(entity) {
    return ({ organization: "#14507e", person: "#9a6b17", country: "#37715c", region: "#6b4f8b" })[entity.entity_type] || "#52606d";
  }
  function makeNode(tag, attrs) {
    const node = document.createElementNS(NS, tag);
    Object.keys(attrs || {}).forEach(function (key) { node.setAttribute(key, attrs[key]); });
    return node;
  }
  function entitySort(a, b) {
    const rank = { organization: 0, person: 1, country: 2, region: 3 };
    return (rank[a.entity_type] - rank[b.entity_type]) || a.name_zh.localeCompare(b.name_zh, "zh");
  }
  function ringAngleFor(entity, ring, index, count, startAngle) {
    const typeOffset = { organization: 0, person: Math.PI * 0.11, country: Math.PI * 0.22, region: Math.PI * 0.33 }[entity.entity_type] || 0;
    const base = startAngle + typeOffset;
    const spread = Math.min(Math.PI * 1.15, Math.max(Math.PI * 0.42, count * 0.3));
    const start = base - spread / 2;
    return count === 1 ? base : start + spread * index / (count - 1);
  }
  function layout(center, visibleEntities, rels) {
    const cx = 450, cy = 315;
    const narrow = !!document.getElementById("graphWrap") && document.getElementById("graphWrap").clientWidth < 560;
    const minSpacing = narrow ? 84 : 100;
    const next = {};
    next[center.entity_id] = { x: cx, y: cy };
    const byRing = {};
    rels.forEach(function (rel) {
      const other = api.otherSide(rel, center.entity_id);
      if (!other || !importanceVisible(other)) return;
      const ring = ringFor(rel);
      if (!byRing[ring]) byRing[ring] = [];
      if (byRing[ring].some(function (item) { return item.entity_id === other.entity_id; })) return;
      byRing[ring].push(other);
    });
    const ringRadius = {};
    RING_ORDER.forEach(function (ringName) {
      const items = (byRing[ringName] || []).slice().sort(entitySort);
      const spec = RINGS[ringName];
      let radius = spec.radius + Math.min(36, Math.max(0, items.length - 2) * 10);
      if (items.length > 1) {
        let needed = radius;
        for (let iter = 0; iter < 6; iter++) {
          const arc = needed * Math.PI * 1.15 / (items.length - 1);
          if (arc >= minSpacing) break;
          needed = minSpacing * (items.length - 1) / (Math.PI * 1.15);
        }
        radius = Math.max(radius, needed + 14);
      }
      ringRadius[ringName] = radius;
      const startAngle = -Math.PI / 2 - (Math.PI * 0.55);
      items.forEach(function (entity, index) {
        const angle = ringAngleFor(entity, ringName, index, items.length, startAngle);
        const target = { x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius * 0.92 };
        const previous = positions[entity.entity_id];
        if (previous && Math.hypot(previous.x - target.x, previous.y - target.y) < 220) {
          next[entity.entity_id] = { x: previous.x * 0.3 + target.x * 0.7, y: previous.y * 0.3 + target.y * 0.7 };
        } else {
          next[entity.entity_id] = target;
        }
      });
    });
    visibleEntities.forEach(function (entity) {
      if (!next[entity.entity_id]) next[entity.entity_id] = { x: cx, y: cy };
    });
    // Cross-ring polar angle separation: avoid same-type nodes on different rings sharing nearly the same ray.
    const angular = [];
    Object.keys(next).forEach(function (id) {
      if (id === center.entity_id) return;
      const p = next[id];
      angular.push({ id: id, angle: Math.atan2(p.y - cy, p.x - cx), r: Math.hypot(p.x - cx, p.y - cy) });
    });
    angular.sort(function (a, b) { return a.r - b.r; });
    for (let i = 0; i < angular.length; i++) {
      for (let j = 0; j < angular.length; j++) {
        if (i === j) continue;
        const a = angular[i], b = angular[j];
        let gap = Math.abs(a.angle - b.angle);
        if (gap > Math.PI) gap = Math.PI * 2 - gap;
        if (gap < 0.21 && a.r < b.r) {
          const delta = (0.21 - gap) * (a.angle < b.angle ? 1 : -1) + 0.06;
          const np = next[b.id];
          const r = Math.hypot(np.x - cx, np.y - cy);
          const na = b.angle + delta;
          np.x = cx + Math.cos(na) * r;
          np.y = cy + Math.sin(na) * r * 0.92;
          b.angle = na;
        }
      }
    }
    const keys = Object.keys(next);
    for (let pass = 0; pass < 4; pass++) {
      keys.forEach(function (a) {
        if (a === center.entity_id) return;
        keys.forEach(function (b) {
          if (b === center.entity_id || b <= a) return;
          const pa = next[a], pb = next[b];
          const dx = pa.x - pb.x, dy = pa.y - pb.y;
          const dist = Math.hypot(dx, dy);
          if (dist < minSpacing && dist > 0) {
            const push = (minSpacing - dist) / 2;
            const ux = dx / dist, uy = dy / dist;
            pa.x += ux * push; pa.y += uy * push;
            pb.x -= ux * push; pb.y -= uy * push;
          }
        });
      });
    }
    positions = next;
  }
  function edgePoint(a, b, distance) {
    const dx = b.x - a.x, dy = b.y - a.y, len = Math.max(Math.hypot(dx, dy), 1);
    return { x: a.x + dx / len * distance, y: a.y + dy / len * distance };
  }
  function addDefs() {
    const defs = makeNode("defs");
    ["normal", "leadership", "presence", "historical", "disputed", "hostile"].forEach(function (kind) {
      const marker = makeNode("marker", { id: "arrow-" + kind, markerWidth: "9", markerHeight: "9", refX: "8", refY: "4.5", orient: "auto", markerUnits: "strokeWidth" });
      marker.appendChild(makeNode("path", { d: "M0,0 L9,4.5 L0,9 z", class: "arrow-head " + kind }));
      defs.appendChild(marker);
    });
    ["inner", "middle", "outer"].forEach(function (ring) {
      const circle = makeNode("circle", { cx: 450, cy: 315, r: RINGS[ring].radius, class: "ring-guide ring-" + ring, "aria-hidden": "true" });
      defs.appendChild(circle);
    });
    viewport.appendChild(defs);
  }
  function smooth() { return 420; }
  function animateNodes(animated, token) {
    if (!animated.length) return;
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      animated.forEach(function (item) { item.element.setAttribute("transform", "translate(" + item.to.x + "," + item.to.y + ")"); item.element.style.opacity = "1"; });
      return;
    }
    const started = performance.now();
    const duration = 420;
    function frame(now) {
      if (token !== drawToken) return;
      const progress = Math.min(1, (now - started) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      animated.forEach(function (item) {
        const x = item.from.x + (item.to.x - item.from.x) * eased;
        const y = item.from.y + (item.to.y - item.from.y) * eased;
        item.element.setAttribute("transform", "translate(" + x + "," + y + ")");
        item.element.style.opacity = String(Math.max(.08, progress));
      });
      if (progress < 1) window.requestAnimationFrame(frame);
      else animated.forEach(function (item) { item.element.style.opacity = "1"; });
    }
    window.requestAnimationFrame(frame);
  }
  function addRelationLabel(layer, rel, p1, p2, className, showLabels) {
    if (!showLabels) return;
    const mx = (p1.x + p2.x) / 2;
    const my = (p1.y + p2.y) / 2;
    const dx = p2.x - p1.x, dy = p2.y - p1.y;
    const len = Math.max(Math.hypot(dx, dy), 1);
    const offset = 12;
    const x = mx - dy / len * offset;
    const y = my + dx / len * offset;
    const text = api.relationLabel(rel.relationship_type);
    const width = Math.max(42, text.length * 13 + 14);
    const wrap = makeNode("g", { class: "graph-edge-label-wrap " + className, transform: "translate(" + x + "," + y + ")", "pointer-events": "none" });
    wrap.appendChild(makeNode("rect", { x: -width / 2, y: -12, width: width, height: 18, rx: 8 }));
    const label = makeNode("text", { x: 0, y: 1, class: "graph-edge-label", "text-anchor": "middle" });
    label.textContent = text;
    wrap.appendChild(label);
    layer.appendChild(wrap);
  }
  function updateImportanceStats(visible, center) {
    const statNode = document.getElementById("importanceStats");
    if (!statNode) return;
    const counts = { L1: 0, L2: 0, L3: 0 };
    visible.forEach(function (e) { const lv = e.importance_level || "L3"; counts[lv] = (counts[lv] || 0) + 1; });
    const hidden = api.store.entities.filter(function (e) { return !importanceVisible(e); }).length;
    statNode.innerHTML = "可见 " + visible.length + " 个实体 · L1 " + (counts.L1 || 0) + " · L2 " + (counts.L2 || 0) + " · L3 " + (counts.L3 || 0) + (hidden ? " · 已隐藏 " + hidden + " 个（搜索可临时显示）" : "");
  }
  function draw(centerId) {
    const center = api.entityById(centerId);
    if (!center) return;
    const token = ++drawToken;
    const filter = filters();
    const rels = api.directRelations(centerId).filter(function (rel) { return filter.rels[relGroupFilter(rel)] !== false; });
    const neighbors = rels.map(function (rel) { return api.otherSide(rel, centerId); }).filter(function (entity, index, all) { return entity && all.findIndex(function (item) { return item.entity_id === entity.entity_id; }) === index && filter.types[entity.entity_type] !== false && importanceVisible(entity); });
    const visible = [center].concat(neighbors);
    const oldPositions = Object.keys(positions).reduce(function (copy, key) { copy[key] = { x: positions[key].x, y: positions[key].y }; return copy; }, {});
    layout(center, visible, rels);
    const nextPositions = positions;
    viewport.innerHTML = "";
    addDefs();
    const edgeLayer = makeNode("g", { class: "graph-edges" });
    const edgeHitLayer = makeNode("g", { class: "graph-edge-hits" });
    const labelLayer = makeNode("g", { class: "graph-edge-labels" });
    const nodeLayer = makeNode("g", { class: "graph-nodes" });
    const animated = [];
    const showLabels = rels.length <= 8;
    rels.forEach(function (rel) {
      const other = api.otherSide(rel, centerId);
      if (!other || filter.types[other.entity_type] === false || !importanceVisible(other) || !positions[other.entity_id]) return;
      const a = positions[centerId], b = positions[other.entity_id], kind = relationClass(rel);
      const distance = center.entity_type === "organization" ? 52 : 46;
      const p1 = edgePoint(a, b, distance), p2 = edgePoint(b, a, distance);
      const group = makeNode("g", { class: "graph-edge-group " + kind, "data-relation-type": rel.relationship_type, "data-display-ring": ringFor(rel) });
      const hit = makeNode("line", { x1: p1.x, y1: p1.y, x2: p2.x, y2: p2.y, class: "graph-edge-hit " + kind, "aria-hidden": "true" });
      const line = makeNode("line", { x1: p1.x, y1: p1.y, x2: p2.x, y2: p2.y, class: "graph-edge " + kind, tabindex: "0", role: "button", "aria-label": api.relationLabel(rel.relationship_type) + "：" + api.displayTitle(other), "marker-end": "url(#arrow-" + kind + ")" });
      function selectRelation(event) { event.stopPropagation(); showRelation(rel, group); }
      hit.addEventListener("click", selectRelation);
      line.addEventListener("click", selectRelation);
      group.addEventListener("keydown", function (event) { if (event.key === "Enter" || event.key === " ") showRelation(rel, group); });
      group.appendChild(hit); group.appendChild(line);
      edgeHitLayer.appendChild(group);
      addRelationLabel(labelLayer, rel, p1, p2, kind, showLabels);
    });
    visible.forEach(function (entity) {
      if (!positions[entity.entity_id] || filter.types[entity.entity_type] === false) return;
      const pos = positions[entity.entity_id], isCenter = entity.entity_id === centerId;
      const group = makeNode("g", { class: "graph-node " + (isCenter ? "is-center" : ""), transform: "translate(" + pos.x + "," + pos.y + ")", tabindex: "0", role: "button", "aria-label": api.displayTitle(entity) + "，" + entity.name_en, "data-entity-id": entity.entity_id, "data-entity-type": entity.entity_type, "data-importance": entity.importance_level || "L3", "data-ring": isCenter ? "center" : ringFor(api.directRelations(centerId).find(function (r) { return api.otherSide(r, centerId) && api.otherSide(r, centerId).entity_id === entity.entity_id; }) || {}) });
      if (isCenter) group.appendChild(makeNode("circle", { cx: 0, cy: 0, r: 64, class: "node-halo" }));
      let shape;
      if (entity.entity_type === "person") shape = makeNode("rect", { x: isCenter ? -34 : -28, y: isCenter ? -29 : -23, width: isCenter ? 68 : 56, height: isCenter ? 58 : 46, rx: 12, fill: color(entity), class: "node-shape person" });
      else if (entity.entity_type === "country") shape = makeNode("path", { d: isCenter ? "M0,-36 L33,-19 L33,19 L0,36 L-33,19 L-33,-19 Z" : "M0,-28 L26,-14 L26,14 L0,28 L-26,14 L-26,-14 Z", fill: color(entity), class: "node-shape country" });
      else shape = makeNode("path", { d: isCenter ? "M0,-40 L36,-20 L36,20 L0,40 L-36,20 L-36,-20 Z" : "M0,-30 L27,-15 L27,15 L0,30 L-27,15 L-27,-15 Z", fill: color(entity), class: "node-shape organization" });
      group.appendChild(shape);
      const icon = makeNode("text", { x: 0, y: 5, class: "node-icon", "text-anchor": "middle" }); icon.textContent = entity.entity_type === "person" ? "人" : entity.entity_type === "country" ? "国" : "组"; group.appendChild(icon);
      const nameText = api.displayTitle(entity);
      const name = makeNode("text", { x: 0, y: isCenter ? 78 : 56, class: "node-label " + (isCenter ? "center-label" : ""), "text-anchor": "middle", "pointer-events": "none" }); name.textContent = nameText.length > 16 ? nameText.slice(0, 15) + "…" : nameText; group.appendChild(name);
      if (isCenter) { const en = makeNode("text", { x: 0, y: 96, class: "node-sub-label", "text-anchor": "middle" }); en.textContent = entity.name_en.length > 30 ? entity.name_en.slice(0, 28) + "…" : entity.name_en; group.appendChild(en); }
      const impTag = makeNode("text", { x: 0, y: isCenter ? -50 : -40, class: "node-imp-tag", "text-anchor": "middle" }); impTag.textContent = entity.importance_level || "L3"; group.appendChild(impTag);
      group.addEventListener("click", function () { setFocus(entity.entity_id, true); });
      group.addEventListener("keydown", function (event) { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setFocus(entity.entity_id, true); } });
      nodeLayer.appendChild(group);
      animated.push({ element: group, from: oldPositions[entity.entity_id] || nextPositions[centerId], to: pos });
    });
    viewport.appendChild(edgeHitLayer); viewport.appendChild(edgeLayer); viewport.appendChild(labelLayer); viewport.appendChild(nodeLayer);
    animateNodes(animated, token);
    viewport.setAttribute("transform", "translate(0 0) scale(" + zoom + ")");
    document.getElementById("graphHint").textContent = visible.length + " 个节点 · " + rels.length + " 条直接关系 · 内圈结构与地理 · 中圈组织与力量 · 外圈人物 · 点击节点切换中心";
    updateImportanceStats(visible, center);
    updateFocusPanel(center, rels);
    fitAfterFilter(visible.length);
  }
  let lastFitCount = -1;
  function fitAfterFilter(count) {
    const el = document.getElementById("graphWrap");
    if (!el) return;
    if (count !== lastFitCount) { lastFitCount = count; const w = el.clientWidth; if (w > 0 && w < 560) { zoom = Math.max(0.62, Math.min(1, (w - 60) / 700)); document.getElementById("zoomValue").textContent = Math.round(zoom * 100) + "%"; viewport.setAttribute("transform", "translate(0 0) scale(" + zoom + ")"); } }
  }
  function updateFocusPanel(entity, rels) {
    const level = api.importanceLabel(entity.importance_level);
    document.getElementById("focusName").textContent = api.displayTitle(entity);
    document.getElementById("focusId").textContent = entity.entity_id;
    info.innerHTML = '<div class="intel-info-head"><div class="intel-info-symbol">' + api.typeLabel(entity.entity_type).slice(0, 1) + '</div><div><span class="focus-ribbon">当前焦点</span><h2>' + api.esc(api.displayTitle(entity)) + '</h2><p>' + api.esc(entity.name_en) + '</p></div></div><div class="intel-badges"><span class="intel-badge type-' + api.esc(entity.entity_type) + '">' + api.esc(api.typeLabel(entity.entity_type)) + '</span><span class="intel-badge imp-' + api.esc(entity.importance_level || "L3") + '">' + api.esc(level) + '</span><span class="intel-badge status">' + api.esc(api.statusLabel(entity.current_status)) + '</span></div><p>' + api.esc(entity.short_description) + '</p><div class="intel-kv-mini"><span>直接关系<b>' + rels.length + '</b></span><span>可信度<b>' + api.esc(api.confidenceLabel(entity.confidence)) + '</b></span><span>最后核验<b>' + api.esc(entity.last_verified_at) + '</b></span></div><a class="intel-button sm" href="' + api.entityHref(entity.entity_id) + '">查看完整档案 →</a>';
  }
  function showRelation(rel, group) {
    selectedRelation = rel;
    document.querySelectorAll(".graph-edge-group.selected").forEach(function (item) { item.classList.remove("selected"); });
    document.querySelectorAll(".graph-edge.selected").forEach(function (item) { item.classList.remove("selected"); });
    if (group) { group.classList.add("selected"); const line = group.querySelector(".graph-edge"); if (line) line.classList.add("selected"); }
    const source = api.entityById(rel.source_entity_id), target = api.entityById(rel.target_entity_id);
    const status = rel.temporal_sensitive ? "时间敏感 · " + rel.current_status : rel.current_status;
    const relProfile = api.store.relationProfiles[rel.relationship_id] || api.store.relationProfiles[rel.slug];
    const stages = (relProfile && relProfile.evolution_stages) || [];
    const stagesHtml = stages.length ? '<p class="rel-card-sub"><b>主要历史阶段：</b>' + stages.slice(0, 3).map(function (s) { return api.esc(s.period + " " + s.title); }).join("；") + (stages.length > 3 ? "；…" : "") + '</p>' : '';
    document.getElementById("relationInfo").innerHTML = '<h2>关系详情</h2><div class="relation-pair">' + api.entityLink(source.entity_id, api.displayTitle(source)) + ' <b>' + (rel.direction === "bidirectional" ? "↔" : "→") + '</b> ' + api.entityLink(target.entity_id, api.displayTitle(target)) + '</div><p class="relation-label">' + api.esc(api.relationLabel(rel.relationship_type)) + ' · 圈层：' + api.esc(api.ringLabel(rel.display_ring)) + '</p>' + (rel.relation_summary ? '<p>' + api.esc(rel.relation_summary) + '</p>' : '') + (rel.formation_background ? '<p class="rel-card-sub"><b>形成背景：</b>' + api.esc(rel.formation_background.length > 120 ? rel.formation_background.slice(0, 118) + "…" : rel.formation_background) + '</p>' : '') + stagesHtml + (rel.why_it_matters ? '<p class="rel-card-sub"><b>为什么重要：</b>' + api.esc(rel.why_it_matters) + '</p>' : '') + '<dl class="intel-detail-list"><dt>时间范围</dt><dd>' + api.esc(api.period(rel)) + '</dd><dt>当前状态</dt><dd>' + api.esc(status) + '</dd><dt>涉及地区</dt><dd>' + api.esc(rel.geographic_scope || "未说明") + '</dd><dt>可信度</dt><dd>' + api.esc(api.confidenceLabel(rel.confidence)) + '</dd><dt>最后核验</dt><dd>' + api.esc(rel.last_verified_at) + '</dd><dt>来源</dt><dd>' + (rel.source_refs || []).map(function (id) { const s = api.store.sources.find(function (item) { return item.source_id === id; }); return s ? '<a target="_blank" rel="noopener noreferrer" href="' + api.esc(s.url) + '">' + api.esc(s.publisher) + '</a>' : api.esc(id); }).join(" · ") + '（' + (rel.source_refs || []).length + ' 个来源）</dd>' + (rel.uncertainties ? '<dt>不确定性</dt><dd>' + api.esc(rel.uncertainties.length > 90 ? rel.uncertainties.slice(0, 88) + "…" : rel.uncertainties) + '</dd>' : '') + '</dl><a class="intel-button sm" href="' + api.relationHref(rel.relationship_id) + '">查看完整关系沿革 →</a>';
  }
  function setFocus(next, push) {
    if (!api.entityById(next) || next === focusId && !push) return;
    if (push && focusId !== next) historyStack.push(focusId);
    focusId = next;
    const url = new URL(window.location.href); url.searchParams.set("focus", next); window.history.pushState({ focus: next }, "", url);
    selectedRelation = null; draw(focusId);
    document.getElementById("relationInfo").innerHTML = '<h2>关系详情</h2><p class="muted">点击关系线查看双方、类型、时间与来源。</p>';
  }
  function updateZoom(next) { zoom = Math.max(0.55, Math.min(1.5, next)); document.getElementById("zoomValue").textContent = Math.round(zoom * 100) + "%"; draw(focusId); }
  function applyImportanceChange() {
    document.querySelectorAll("[data-imp-filter]").forEach(function (input) { importanceFilter[input.getAttribute("data-imp-filter")] = input.checked; });
    lastFitCount = -1;
    draw(focusId);
  }
  function bind() {
    document.getElementById("resetFocus").addEventListener("click", function () { historyStack = []; setFocus("actor-jnim", true); });
    document.getElementById("backFocus").addEventListener("click", function () { const prev = historyStack.pop(); if (prev) setFocus(prev, false); else window.history.back(); });
    document.getElementById("zoomIn").addEventListener("click", function () { updateZoom(zoom + .12); }); document.getElementById("zoomOut").addEventListener("click", function () { updateZoom(zoom - .12); }); document.getElementById("fitGraph").addEventListener("click", function () { lastFitCount = -1; updateZoom(1); });
    document.querySelectorAll("[data-type-filter], [data-rel-filter]").forEach(function (input) { input.addEventListener("change", function () { draw(focusId); }); });
    document.querySelectorAll("[data-imp-filter]").forEach(function (input) { input.addEventListener("change", applyImportanceChange); });
    document.querySelectorAll("[data-view-filter]").forEach(function (button) { button.addEventListener("click", function () { const view = button.getAttribute("data-view-filter"); if (view === "core") importanceFilter = { L1: true, L2: false, L3: false }; else if (view === "priority") importanceFilter = { L1: true, L2: true, L3: false }; else importanceFilter = { L1: true, L2: true, L3: true }; document.querySelectorAll("[data-imp-filter]").forEach(function (input) { input.checked = importanceFilter[input.getAttribute("data-imp-filter")]; }); lastFitCount = -1; draw(focusId); }); });
    document.getElementById("entitySearch").addEventListener("input", function (event) { const term = event.target.value.trim().toLowerCase(); if (!term) return; const result = api.store.entities.find(function (e) { return [e.entity_id, e.slug, e.name_zh, e.name_en, e.acronym || "", e.native_name || ""].concat(e.aliases).join(" ").toLowerCase().indexOf(term) >= 0; }); if (!result) return; if (!importanceVisible(result)) { importanceFilter[result.importance_level || "L3"] = true; document.querySelectorAll("[data-imp-filter]").forEach(function (input) { input.checked = importanceFilter[input.getAttribute("data-imp-filter")]; }); } lastFitCount = -1; setFocus(result.entity_id, true); const hint = document.getElementById("graphHint"); if (hint) hint.textContent = "已按搜索结果显示 " + api.displayTitle(result) + "（如该实体曾被重要程度筛选隐藏，现已临时显示）"; });
    window.addEventListener("popstate", function () { const next = queryFocus(); focusId = next; selectedRelation = null; draw(focusId); });
  }
  function initNetwork() { focusId = queryFocus(); bind(); draw(focusId); }
  window.addEventListener("asip-intel-data-ready", initNetwork);
  if (api.store.entities && api.store.entities.length) initNetwork();
})();
