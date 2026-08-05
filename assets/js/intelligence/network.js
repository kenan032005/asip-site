(function () {
  "use strict";
  const api = window.ASIP_INTEL;
  let focusId = "actor-jnim";
  let historyStack = [];
  let zoom = 1;
  let positions = {};
  let selectedRelation = null;
  const NS = "http://www.w3.org/2000/svg";
  const svg = document.getElementById("graphSvg");
  const viewport = document.getElementById("graphViewport");
  const info = document.getElementById("nodeInfo");
  if (!svg || !viewport) return;

  function queryFocus() {
    const raw = new URLSearchParams(window.location.search).get("focus");
    return raw && api.entityById(raw) ? raw : "actor-jnim";
  }
  function relationClass(rel) {
    if (rel.relationship_type === "hostile_to") return "hostile";
    if (rel.disputed || rel.current_status.indexOf("historical") >= 0) return "historical";
    return "normal";
  }
  function relGroup(rel) {
    return ["affiliated_with", "constituent_of", "led_by", "founded_by", "operates_in", "hostile_to", "historically_associated_with", "part_of_network"].indexOf(rel.relationship_type) >= 0 ? rel.relationship_type : "other";
  }
  function filters() {
    const typeFilters = {};
    document.querySelectorAll("[data-type-filter]").forEach(function (input) { typeFilters[input.getAttribute("data-type-filter")] = input.checked; });
    const relFilters = {};
    document.querySelectorAll("[data-rel-filter]").forEach(function (input) { relFilters[input.getAttribute("data-rel-filter")] = input.checked; });
    return { types: typeFilters, rels: relFilters };
  }
  function color(entity) {
    return ({ organization: "#14507e", person: "#9a6b17", country: "#37715c", region: "#6b4f8b" })[entity.entity_type] || "#52606d";
  }
  function makeNode(tag, attrs) {
    const node = document.createElementNS(NS, tag);
    Object.keys(attrs || {}).forEach(function (key) { node.setAttribute(key, attrs[key]); });
    return node;
  }
  function layout(center, visibleEntities) {
    const cx = 450, cy = 310;
    const next = {};
    next[center.entity_id] = { x: cx, y: cy };
    const others = visibleEntities.filter(function (e) { return e.entity_id !== center.entity_id; });
    const radius = Math.min(238, 125 + others.length * 13);
    others.forEach(function (entity, index) {
      const angle = (-Math.PI / 2) + (Math.PI * 2 * index / Math.max(others.length, 1));
      const previous = positions[entity.entity_id];
      const target = { x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius };
      if (previous && Math.hypot(previous.x - target.x, previous.y - target.y) < 160) next[entity.entity_id] = { x: previous.x * 0.36 + target.x * 0.64, y: previous.y * 0.36 + target.y * 0.64 };
      else next[entity.entity_id] = target;
    });
    positions = next;
  }
  function edgePoint(a, b, distance) {
    const dx = b.x - a.x, dy = b.y - a.y, len = Math.max(Math.hypot(dx, dy), 1);
    return { x: a.x + dx / len * distance, y: a.y + dy / len * distance };
  }
  function animateNodes(animated) {
    if (!animated.length) return;
    const started = performance.now();
    const duration = 420;
    function frame(now) {
      const progress = Math.min(1, (now - started) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      animated.forEach(function (item) {
        const x = item.from.x + (item.to.x - item.from.x) * eased;
        const y = item.from.y + (item.to.y - item.from.y) * eased;
        item.element.setAttribute("transform", "translate(" + x + "," + y + ")");
        item.element.style.opacity = String(Math.max(.05, progress));
      });
      if (progress < 1) window.requestAnimationFrame(frame);
      else animated.forEach(function (item) { item.element.style.opacity = "1"; });
    }
    window.requestAnimationFrame(frame);
  }
  function draw(centerId) {
    const center = api.entityById(centerId);
    if (!center) return;
    const filter = filters();
    const rels = api.directRelations(centerId).filter(function (rel) { return filter.rels[relGroup(rel)] !== false; });
    const neighbors = rels.map(function (rel) { return api.otherSide(rel, centerId); }).filter(function (entity, index, all) { return entity && all.findIndex(function (item) { return item.entity_id === entity.entity_id; }) === index && filter.types[entity.entity_type] !== false; });
    const visible = [center].concat(neighbors);
    const oldPositions = Object.keys(positions).reduce(function (copy, key) { copy[key] = { x: positions[key].x, y: positions[key].y }; return copy; }, {});
    layout(center, visible);
    const nextPositions = positions;
    viewport.innerHTML = "";
    const edgeLayer = makeNode("g", { class: "graph-edges" });
    const nodeLayer = makeNode("g", { class: "graph-nodes" });
    const animated = []; // smooth center transition and stable shared-node movement
    rels.forEach(function (rel) {
      const other = api.otherSide(rel, centerId);
      if (!other || filter.types[other.entity_type] === false || !positions[other.entity_id]) return;
      const a = positions[centerId], b = positions[other.entity_id];
      const p1 = edgePoint(a, b, 44), p2 = edgePoint(b, a, 44);
      const line = makeNode("line", { x1: p1.x, y1: p1.y, x2: p2.x, y2: p2.y, class: "graph-edge " + relationClass(rel), tabindex: "0" });
      line.addEventListener("click", function (event) { event.stopPropagation(); showRelation(rel); });
      line.addEventListener("keydown", function (event) { if (event.key === "Enter" || event.key === " ") showRelation(rel); });
      edgeLayer.appendChild(line);
      const label = makeNode("text", { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 - 5, class: "graph-edge-label" });
      label.textContent = api.relationLabel(rel.relationship_type);
      edgeLayer.appendChild(label);
    });
    visible.forEach(function (entity) {
      if (!positions[entity.entity_id] || filter.types[entity.entity_type] === false) return;
      const pos = positions[entity.entity_id], isCenter = entity.entity_id === centerId;
      const group = makeNode("g", { class: "graph-node " + (isCenter ? "is-center" : ""), transform: "translate(" + pos.x + "," + pos.y + ")", tabindex: "0", role: "button", "aria-label": entity.name_zh });
      const shape = entity.entity_type === "person" ? makeNode("rect", { x: -24, y: -24, width: 48, height: 48, rx: 8, fill: color(entity), class: "node-shape person" }) : entity.entity_type === "country" ? makeNode("rect", { x: -25, y: -25, width: 50, height: 50, rx: 5, fill: color(entity), class: "node-shape country" }) : makeNode("circle", { cx: 0, cy: 0, r: isCenter ? 42 : 32, fill: color(entity), class: "node-shape organization" });
      group.appendChild(shape);
      const icon = makeNode("text", { x: 0, y: 5, class: "node-icon" }); icon.textContent = entity.entity_type === "person" ? "人" : entity.entity_type === "country" ? "国" : "组"; group.appendChild(icon);
      const name = makeNode("text", { x: 0, y: isCenter ? 64 : 54, class: "node-label" }); name.textContent = entity.name_zh.length > 11 ? entity.name_zh.slice(0, 10) + "…" : entity.name_zh; group.appendChild(name);
      group.addEventListener("click", function () { setFocus(entity.entity_id, true); });
      group.addEventListener("keydown", function (event) { if (event.key === "Enter" || event.key === " ") setFocus(entity.entity_id, true); });
      nodeLayer.appendChild(group);
      animated.push({ element: group, from: oldPositions[entity.entity_id] || nextPositions[centerId], to: pos });
    });
    viewport.appendChild(edgeLayer); viewport.appendChild(nodeLayer);
    animateNodes(animated);
    viewport.setAttribute("transform", "translate(0 0) scale(" + zoom + ")");
    document.getElementById("graphHint").textContent = visible.length + " 个节点 · " + rels.length + " 条直接关系 · 点击节点切换中心";
    updateFocusPanel(center, rels);
  }
  function updateFocusPanel(entity, rels) {
    document.getElementById("focusName").textContent = entity.name_zh;
    document.getElementById("focusId").textContent = entity.entity_id;
    info.innerHTML = '<div class="intel-info-head"><div class="intel-info-symbol">' + api.typeLabel(entity.entity_type).slice(0, 1) + '</div><div><h2>' + api.esc(entity.name_zh) + '</h2><p>' + api.esc(entity.name_en) + '</p></div></div><div class="intel-badges">' + '<span class="intel-badge type-' + api.esc(entity.entity_type) + '">' + api.esc(api.typeLabel(entity.entity_type)) + '</span>' + '<span class="intel-badge status">' + api.esc(api.statusLabel(entity.current_status)) + '</span></div><p>' + api.esc(entity.short_description) + '</p><div class="intel-kv-mini"><span>直接关系<b>' + rels.length + '</b></span><span>可信度<b>' + api.esc(api.confidenceLabel(entity.confidence)) + '</b></span><span>最后核验<b>' + api.esc(entity.last_verified_at) + '</b></span></div><a class="intel-button sm" href="' + api.entityHref(entity.entity_id) + '">查看完整档案 →</a>';
  }
  function showRelation(rel) {
    selectedRelation = rel;
    const source = api.entityById(rel.source_entity_id), target = api.entityById(rel.target_entity_id);
    document.getElementById("relationInfo").innerHTML = '<h2>关系详情</h2><div class="relation-pair">' + api.entityLink(source.entity_id, source.name_zh) + ' <b>' + (rel.direction === "bidirectional" ? "↔" : "→") + '</b> ' + api.entityLink(target.entity_id, target.name_zh) + '</div><p class="relation-label">' + api.esc(api.relationLabel(rel.relationship_type)) + '</p><p>' + api.esc(rel.description) + '</p><dl class="intel-detail-list"><dt>时间范围</dt><dd>' + api.esc(api.period(rel)) + '</dd><dt>当前状态</dt><dd>' + api.esc(rel.current_status) + '</dd><dt>可信度</dt><dd>' + api.esc(api.confidenceLabel(rel.confidence)) + '</dd><dt>来源</dt><dd>' + rel.source_refs.map(function (id) { const s = api.store.sources.find(function (item) { return item.source_id === id; }); return s ? '<a target="_blank" rel="noopener" href="' + api.esc(s.url) + '">' + api.esc(s.publisher) + '</a>' : api.esc(id); }).join(" · ") + '</dd></dl>';
  }
  function setFocus(next, push) {
    if (!api.entityById(next) || next === focusId && !push) return;
    if (push && focusId !== next) historyStack.push(focusId);
    focusId = next;
    const url = new URL(window.location.href); url.searchParams.set("focus", next); window.history.pushState({ focus: next }, "", url);
    selectedRelation = null; draw(focusId);
    document.getElementById("relationInfo").innerHTML = '<h2>关系详情</h2><p class="muted">点击关系线查看双方、类型、时间与来源。</p>';
  }
  function updateZoom(next) { zoom = Math.max(0.72, Math.min(1.45, next)); document.getElementById("zoomValue").textContent = Math.round(zoom * 100) + "%"; draw(focusId); }
  function bind() {
    document.getElementById("resetFocus").addEventListener("click", function () { historyStack = []; setFocus("actor-jnim", true); });
    document.getElementById("backFocus").addEventListener("click", function () { const prev = historyStack.pop(); if (prev) setFocus(prev, false); else window.history.back(); });
    document.getElementById("zoomIn").addEventListener("click", function () { updateZoom(zoom + .12); }); document.getElementById("zoomOut").addEventListener("click", function () { updateZoom(zoom - .12); }); document.getElementById("fitGraph").addEventListener("click", function () { updateZoom(1); });
    document.querySelectorAll("[data-type-filter], [data-rel-filter]").forEach(function (input) { input.addEventListener("change", function () { draw(focusId); }); });
    document.getElementById("entitySearch").addEventListener("input", function (event) { const term = event.target.value.trim().toLowerCase(); const result = api.store.entities.find(function (e) { return [e.entity_id, e.slug, e.name_zh, e.name_en].concat(e.aliases).join(" ").toLowerCase().indexOf(term) >= 0; }); if (term && result) setFocus(result.entity_id, true); });
    window.addEventListener("popstate", function () { const next = queryFocus(); focusId = next; draw(focusId); });
  }
  window.addEventListener("asip-intel-data-ready", function () { focusId = queryFocus(); bind(); draw(focusId); });
})();
