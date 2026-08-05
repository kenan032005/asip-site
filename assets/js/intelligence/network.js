(function () {
  "use strict";
  const api = window.ASIP_INTEL;
  let focusId = "actor-jnim";
  let historyStack = [];
  let zoom = 1;
  let positions = {};
  let selectedRelation = null;
  let drawToken = 0;
  const NS = "http://www.w3.org/2000/svg";
  const svg = document.getElementById("graphSvg");
  const viewport = document.getElementById("graphViewport");
  const info = document.getElementById("nodeInfo");
  if (!svg || !viewport) return;

  const GROUPS = {
    upper: { label: "体系与领导", angle: -Math.PI / 2, radius: 208 },
    left: { label: "组成与历史", angle: Math.PI, radius: 214 },
    right: { label: "人物与领导", angle: 0, radius: 214 },
    lower: { label: "敌对与冲突", angle: Math.PI / 2, radius: 224 },
    outer: { label: "活动与存在", angle: Math.PI * 0.78, radius: 252 },
    other: { label: "其他关系", angle: -Math.PI * 0.78, radius: 232 }
  };
  const GROUP_ORDER = ["upper", "left", "right", "lower", "outer", "other"];

  function queryFocus() {
    const raw = new URLSearchParams(window.location.search).get("focus");
    return raw && api.entityById(raw) ? raw : "actor-jnim";
  }
  function groupFor(rel) {
    if (rel.display_group && GROUPS[rel.display_group]) return rel.display_group;
    const type = rel.relationship_type;
    if (["led_by", "founded_by", "affiliated_with", "part_of_network"].indexOf(type) >= 0) return "upper";
    if (type === "constituent_of" || type === "historically_associated_with") return "left";
    if (type === "hostile_to") return "lower";
    if (type === "operates_in") return "outer";
    return "other";
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
  function layout(center, visibleEntities, rels) {
    const cx = 450, cy = 310;
    const next = {};
    next[center.entity_id] = { x: cx, y: cy };
    const byGroup = {};
    rels.forEach(function (rel) {
      const other = api.otherSide(rel, center.entity_id);
      if (!other) return;
      const group = groupFor(rel);
      if (!byGroup[group]) byGroup[group] = [];
      if (byGroup[group].some(function (item) { return item.entity_id === other.entity_id; })) return;
      byGroup[group].push(other);
    });
    Object.keys(byGroup).forEach(function (groupName) {
      byGroup[groupName].sort(entitySort);
      const spec = GROUPS[groupName] || GROUPS.other;
      const items = byGroup[groupName];
      const span = Math.min(Math.PI * 0.78, Math.max(Math.PI * 0.34, items.length * 0.28));
      const start = spec.angle - span / 2;
      items.forEach(function (entity, index) {
        const angle = items.length === 1 ? spec.angle : start + span * index / (items.length - 1);
        const radius = spec.radius + Math.min(36, Math.max(0, items.length - 2) * 8);
        const target = { x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius };
        const previous = positions[entity.entity_id];
        if (previous && Math.hypot(previous.x - target.x, previous.y - target.y) < 190) {
          next[entity.entity_id] = { x: previous.x * 0.32 + target.x * 0.68, y: previous.y * 0.32 + target.y * 0.68 };
        } else {
          next[entity.entity_id] = target;
        }
      });
    });
    visibleEntities.forEach(function (entity) {
      if (!next[entity.entity_id]) next[entity.entity_id] = { x: cx, y: cy };
    });
    positions = next;
  }
  function edgePoint(a, b, distance) {
    const dx = b.x - a.x, dy = b.y - a.y, len = Math.max(Math.hypot(dx, dy), 1);
    return { x: a.x + dx / len * distance, y: a.y + dy / len * distance };
  }
  function addDefs() {
    const defs = makeNode("defs");
    ["normal", "leadership", "presence", "historical", "disputed", "hostile"].forEach(function (kind) {
      const marker = makeNode("marker", { id: "arrow-" + kind, markerWidth: "8", markerHeight: "8", refX: "7", refY: "4", orient: "auto", markerUnits: "strokeWidth" });
      marker.appendChild(makeNode("path", { d: "M0,0 L8,4 L0,8 z", class: "arrow-head " + kind }));
      defs.appendChild(marker);
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
    const x = (p1.x + p2.x) / 2;
    const y = (p1.y + p2.y) / 2 - 7;
    const text = api.relationLabel(rel.relationship_type);
    const width = Math.max(42, text.length * 13 + 14);
    const wrap = makeNode("g", { class: "graph-edge-label-wrap " + className, transform: "translate(" + x + "," + y + ")" });
    wrap.appendChild(makeNode("rect", { x: -width / 2, y: -12, width: width, height: 18, rx: 8 }));
    const label = makeNode("text", { x: 0, y: 1, class: "graph-edge-label", "text-anchor": "middle" });
    label.textContent = text;
    wrap.appendChild(label);
    layer.appendChild(wrap);
  }
  function draw(centerId) {
    const center = api.entityById(centerId);
    if (!center) return;
    const token = ++drawToken;
    const filter = filters();
    const rels = api.directRelations(centerId).filter(function (rel) { return filter.rels[relGroupFilter(rel)] !== false; });
    const neighbors = rels.map(function (rel) { return api.otherSide(rel, centerId); }).filter(function (entity, index, all) { return entity && all.findIndex(function (item) { return item.entity_id === entity.entity_id; }) === index && filter.types[entity.entity_type] !== false; });
    const visible = [center].concat(neighbors);
    const oldPositions = Object.keys(positions).reduce(function (copy, key) { copy[key] = { x: positions[key].x, y: positions[key].y }; return copy; }, {});
    layout(center, visible, rels);
    const nextPositions = positions;
    viewport.innerHTML = "";
    addDefs();
    const edgeLayer = makeNode("g", { class: "graph-edges" });
    const nodeLayer = makeNode("g", { class: "graph-nodes" });
    const animated = [];
    const showLabels = rels.length <= 8;
    rels.forEach(function (rel) {
      const other = api.otherSide(rel, centerId);
      if (!other || filter.types[other.entity_type] === false || !positions[other.entity_id]) return;
      const a = positions[centerId], b = positions[other.entity_id], kind = relationClass(rel);
      const distance = center.entity_type === "organization" ? 48 : 43;
      const p1 = edgePoint(a, b, distance), p2 = edgePoint(b, a, distance);
      const line = makeNode("line", { x1: p1.x, y1: p1.y, x2: p2.x, y2: p2.y, class: "graph-edge " + kind, tabindex: "0", role: "button", "aria-label": api.relationLabel(rel.relationship_type) + "：" + other.name_zh, "data-relation-type": rel.relationship_type, "data-display-group": groupFor(rel), "marker-end": "url(#arrow-" + kind + ")" });
      line.addEventListener("click", function (event) { event.stopPropagation(); showRelation(rel, line); });
      line.addEventListener("keydown", function (event) { if (event.key === "Enter" || event.key === " ") showRelation(rel, line); });
      edgeLayer.appendChild(line);
      addRelationLabel(edgeLayer, rel, p1, p2, kind, showLabels);
    });
    visible.forEach(function (entity) {
      if (!positions[entity.entity_id] || filter.types[entity.entity_type] === false) return;
      const pos = positions[entity.entity_id], isCenter = entity.entity_id === centerId;
      const group = makeNode("g", { class: "graph-node " + (isCenter ? "is-center" : ""), transform: "translate(" + pos.x + "," + pos.y + ")", tabindex: "0", role: "button", "aria-label": entity.name_zh, "data-entity-id": entity.entity_id, "data-entity-type": entity.entity_type });
      if (isCenter) group.appendChild(makeNode("circle", { cx: 0, cy: 0, r: 60, class: "node-halo" }));
      let shape;
      if (entity.entity_type === "person") shape = makeNode("rect", { x: isCenter ? -32 : -27, y: isCenter ? -27 : -22, width: isCenter ? 64 : 54, height: isCenter ? 54 : 44, rx: 12, fill: color(entity), class: "node-shape person" });
      else if (entity.entity_type === "country") shape = makeNode("path", { d: isCenter ? "M0,-35 L32,-18 L32,18 L0,35 L-32,18 L-32,-18 Z" : "M0,-29 L27,-15 L27,15 L0,29 L-27,15 L-27,-15 Z", fill: color(entity), class: "node-shape country" });
      else shape = makeNode("circle", { cx: 0, cy: 0, r: isCenter ? 46 : 34, fill: color(entity), class: "node-shape organization" });
      group.appendChild(shape);
      const icon = makeNode("text", { x: 0, y: 5, class: "node-icon", "text-anchor": "middle" }); icon.textContent = entity.entity_type === "person" ? "人" : entity.entity_type === "country" ? "国" : "组"; group.appendChild(icon);
      const name = makeNode("text", { x: 0, y: isCenter ? 72 : 52, class: "node-label " + (isCenter ? "center-label" : ""), "text-anchor": "middle" }); name.textContent = entity.name_zh.length > 12 ? entity.name_zh.slice(0, 11) + "…" : entity.name_zh; group.appendChild(name);
      if (isCenter) { const en = makeNode("text", { x: 0, y: 88, class: "node-sub-label", "text-anchor": "middle" }); en.textContent = entity.name_en.length > 24 ? entity.name_en.slice(0, 22) + "…" : entity.name_en; group.appendChild(en); }
      group.addEventListener("click", function () { setFocus(entity.entity_id, true); });
      group.addEventListener("keydown", function (event) { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setFocus(entity.entity_id, true); } });
      nodeLayer.appendChild(group);
      animated.push({ element: group, from: oldPositions[entity.entity_id] || nextPositions[centerId], to: pos });
    });
    viewport.appendChild(edgeLayer); viewport.appendChild(nodeLayer);
    animateNodes(animated, token);
    viewport.setAttribute("transform", "translate(0 0) scale(" + zoom + ")");
    document.getElementById("graphHint").textContent = visible.length + " 个节点 · " + rels.length + " 条直接关系 · 按关系语义分区 · 点击节点切换中心";
    updateFocusPanel(center, rels);
  }
  function updateFocusPanel(entity, rels) {
    const level = api.profileLevelLabel ? api.profileLevelLabel(entity.profile_level) : (entity.profile_level || "基础档案");
    document.getElementById("focusName").textContent = entity.name_zh;
    document.getElementById("focusId").textContent = entity.entity_id;
    info.innerHTML = '<div class="intel-info-head"><div class="intel-info-symbol">' + api.typeLabel(entity.entity_type).slice(0, 1) + '</div><div><span class="focus-ribbon">当前焦点</span><h2>' + api.esc(entity.name_zh) + '</h2><p>' + api.esc(entity.name_en) + '</p></div></div><div class="intel-badges"><span class="intel-badge type-' + api.esc(entity.entity_type) + '">' + api.esc(api.typeLabel(entity.entity_type)) + '</span><span class="intel-badge profile-level">' + api.esc(level) + '</span><span class="intel-badge status">' + api.esc(api.statusLabel(entity.current_status)) + '</span></div><p>' + api.esc(entity.short_description) + '</p><div class="intel-kv-mini"><span>直接关系<b>' + rels.length + '</b></span><span>可信度<b>' + api.esc(api.confidenceLabel(entity.confidence)) + '</b></span><span>最后核验<b>' + api.esc(entity.last_verified_at) + '</b></span></div><a class="intel-button sm" href="' + api.entityHref(entity.entity_id) + '">查看完整档案 →</a>';
  }
  function showRelation(rel, line) {
    selectedRelation = rel;
    if (line) { document.querySelectorAll(".graph-edge.selected").forEach(function (item) { item.classList.remove("selected"); }); line.classList.add("selected"); }
    const source = api.entityById(rel.source_entity_id), target = api.entityById(rel.target_entity_id);
    const status = rel.temporal_sensitive ? "时间敏感 · " + rel.current_status : rel.current_status;
    document.getElementById("relationInfo").innerHTML = '<h2>关系详情</h2><div class="relation-pair">' + api.entityLink(source.entity_id, source.name_zh) + ' <b>' + (rel.direction === "bidirectional" ? "↔" : "→") + '</b> ' + api.entityLink(target.entity_id, target.name_zh) + '</div><p class="relation-label">' + api.esc(api.relationLabel(rel.relationship_type)) + '</p><p>' + api.esc(rel.description) + '</p><dl class="intel-detail-list"><dt>展示分区</dt><dd>' + api.esc((GROUPS[groupFor(rel)] || GROUPS.other).label) + '</dd><dt>时间范围</dt><dd>' + api.esc(api.period(rel)) + '</dd><dt>当前状态</dt><dd>' + api.esc(status) + '</dd><dt>可信度</dt><dd>' + api.esc(api.confidenceLabel(rel.confidence)) + '</dd><dt>来源</dt><dd>' + rel.source_refs.map(function (id) { const s = api.store.sources.find(function (item) { return item.source_id === id; }); return s ? '<a target="_blank" rel="noopener" href="' + api.esc(s.url) + '">' + api.esc(s.publisher) + '</a>' : api.esc(id); }).join(" · ") + '</dd></dl>';
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
    window.addEventListener("popstate", function () { const next = queryFocus(); focusId = next; selectedRelation = null; draw(focusId); });
  }
  function initNetwork() { focusId = queryFocus(); bind(); draw(focusId); }
  window.addEventListener("asip-intel-data-ready", initNetwork);
  if (api.store.entities && api.store.entities.length) initNetwork();
})();
