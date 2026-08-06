/* ASIP Africa security intelligence production frontend (I2-A).
   One unified Africa dataset: regions, countries, entities, relationships,
   evidence, sources. Region/country views are filters, not data copies. */
(function () {
  "use strict";

  const path = window.location.pathname;
  const marker = "/intelligence/africa/";
  const markerIndex = path.indexOf(marker);
  const ROOT = markerIndex >= 0 ? path.slice(0, markerIndex) + marker : "../../";
  const DATA = ROOT + "data/";
  const TYPE_LABELS = {
    armed_group: "武装组织", terrorist_group: "恐怖主义/极端组织", insurgent_group: "反政府武装",
    militia: "民兵/地方武装", community_self_defense: "社区/地方自卫组织", state_security_force: "国家军队/安全力量",
    regional_force: "地区联合部队/国际军事力量", political_movement: "政治运动/政治-军事组织",
    criminal_network: "跨境犯罪网络", person: "关键人物", country: "国家", region: "区域",
    international_network: "跨国组织体系/国际网络", organization: "组织"
  };
  const REL_LABELS = {
    affiliated_with: "存在关联", pledged_allegiance_to: "宣誓效忠于", constituent_of: "组成关系",
    split_from: "分裂自", merged_from: "合并自", led_by: "领导", founded_by: "创始人",
    operates_in: "活动于", active_in_region: "活跃于区域", allied_with: "同盟",
    cooperates_with: "合作", supported_by: "获得支持", supports: "支持", hostile_to: "敌对",
    competes_with: "竞争", fought_against: "交战", historically_associated_with: "历史关联",
    deployed_in: "部署于", member_of_force: "部队成员", political_affiliation: "政治归属",
    alleged_support: "涉嫌支持", cross_border_link: "跨境关联", criminal_link: "犯罪关联"
  };
  const IMPORTANCE_LABELS = { L1: "L1 核心实体", L2: "L2 重要实体", L3: "L3 扩展实体" };
  const RING_LABELS = { inner: "结构与地理", middle: "组织与力量", outer: "人物" };
  const RISK_LABELS = { extreme: "极高风险", high: "高风险", medium: "中风险", low: "低风险" };
  const CONFIDENCE_LABELS = { high: "高", medium_high: "中高", medium: "中", low: "低", disputed: "存在争议" };
  const SECTION_LABELS = {
    overview: "概述", regional_belonging: "所属区域", risk_assessment: "风险等级与说明",
    core_conflicts: "核心冲突体系", main_actors: "主要武装和政治实体", security_forces: "国家军队和安全力量",
    high_risk_areas: "主要高风险地区", cross_border_relations: "跨境安全关系", terrorism_risk: "恐怖主义风险",
    insurgency_risk: "反政府武装风险", community_risk: "社区、部族或地方武装风险", crime_risk: "跨境犯罪风险",
    security_events: "主要安全事件类型", current_trends: "当前趋势", impact: "与邻国安全形势的联系及影响",
    relationships: "重要关系", events: "代表性事件", current_assessment: "当前状态",
    formation_background: "成立背景", history: "历史沿革", structure: "组织结构", leadership: "领导层",
    ideology_goals: "意识形态与目标", geography: "活动范围", force_estimates: "武装力量规模",
    tactics: "主要行动方式", regional_impact: "区域影响", controversies_uncertainties: "争议与不确定性",
    gaps: "资料缺口", biography: "生平", roles: "职务", influence: "影响", sources: "来源", notes: "备注"
  };
  const store = { regions: [], countries: [], entities: [], relationships: [], sources: [], evidence: [], relationProfiles: {}, relationTimelines: {}, forceEstimates: {}, externalLinks: {}, entityProfiles: {}, countryProfiles: {}, aliases: {}, byEntityId: {}, byEntitySlug: {}, byRelId: {}, byCountryId: {}, byRegionId: {}, metrics: null, audit: [] };

  function esc(v) { return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]; }); }
  function dataUrl(n) { return DATA + n; }
  let loadController = null;
  function beginLoad() {
    if (loadController) loadController.abort();   // cancel the previous page's in-flight load
    loadController = new AbortController();
    return loadController.signal;
  }
  function loadJson(n, signal) {
    return fetch(dataUrl(n), signal ? { signal: signal } : undefined).then(function (r) { if (!r.ok) throw new Error("load failed: " + n); return r.json(); });
  }
  const VERIFY_LABELS = { verified: "已核验", partially_verified: "部分核验", pending_review: "待复核", disputed: "存在争议", unsupported: "无来源支持" };
  const FRESH_LABELS = { current: "当前", aging: "趋旧", stale: "过时", historical: "历史资料", unknown: "时效不明" };
  function verifyBadge(s) { const l = VERIFY_LABELS[s] || s; return '<span class="intel-badge v-' + esc(s || "unknown") + '">' + esc(l) + '</span>'; }
  function freshnessBadge(s) { const l = FRESH_LABELS[s] || s; return '<span class="intel-badge f-' + esc(s || "unknown") + '">' + esc(l) + '</span>'; }
  function freshnessNote(obj) {
    if (!obj) return "";
    const f = obj.freshness_status;
    if (f === "stale" || f === "aging") {
      const asof = obj.claim_valid_as_of || obj.current_status_verified_at || "较早年份";
      return '<p class="profile-standfirst"><span class="profile-standfirst-label">时效提示</span><span>当前状态尚未获得近期公开资料确认；以下内容依据截至 ' + esc(asof) + ' 年的公开资料，freshness=' + esc(f) + '。</span></p>';
    }
    if (f === "historical") return '<p class="profile-standfirst"><span class="profile-standfirst-label">历史资料</span><span>该记录为历史资料，不代表当前状态。</span></p>';
    return "";
  }
  function dateRow(obj) {
    if (!obj) return "";
    let out = "";
    if (obj.record_reviewed_at) out += '<div class="ib-row"><dt>数据记录检查</dt><dd>' + esc(obj.record_reviewed_at) + '</dd></div>';
    if (obj.current_status_verified_at) out += '<div class="ib-row"><dt>当前状态核验</dt><dd>' + esc(obj.current_status_verified_at) + '</dd></div>';
    if (obj.claim_valid_as_of) out += '<div class="ib-row"><dt>事实有效截至</dt><dd>' + esc(obj.claim_valid_as_of) + '</dd></div>';
    if (obj.freshness_status) out += '<div class="ib-row"><dt>时效状态</dt><dd>' + freshnessBadge(obj.freshness_status) + '</dd></div>';
    return out;
  }
  function acronymOf(e) { return e.acronym && String(e.acronym).trim() ? String(e.acronym).trim() : ""; }
  function title(e) { const a = acronymOf(e); return a ? e.name_zh + "（" + a + "）" : e.name_zh; }
  function typeLabel(t) { return TYPE_LABELS[t] || t; }
  function relLabel(t) { return REL_LABELS[t] || t; }
  function impLabel(l) { return IMPORTANCE_LABELS[l] || l || "未分级"; }
  function riskLabel(r) { return RISK_LABELS[r] || r; }
  function confLabel(c) { return CONFIDENCE_LABELS[c] || c || "未说明"; }
  function ringLabel(r) { return RING_LABELS[r] || r; }
  function period(rel) { const s = rel.time_start || rel.start_year; const e = rel.time_end || rel.end_year; if (!s && !e) return "未说明"; if (s && e) return s + "—" + e; return s ? s + "—至今" : "截至 " + e; }
  function entityHref(id) {
    const e = store.byEntityId[id]; if (!e) return ROOT;
    if (e.entity_type === "country" || e.primary_type === "country") {
      const c = store.byCountryId[id] || store.byCountryId[e.country_ids && e.country_ids[0]];
      if (c) return ROOT + "country/" + encodeURIComponent(c.slug) + "/";
    }
    return ROOT + "entity/" + encodeURIComponent(e.slug) + "/";
  }
  function countryHref(id) { const c = store.byCountryId[id]; return c ? ROOT + "country/" + encodeURIComponent(c.slug) + "/" : ROOT; }
  function regionHref(id) { const r = store.byRegionId[id]; return r ? ROOT + "region/" + encodeURIComponent(r.slug) + "/" : ROOT; }
  function relationHref(id) { const r = store.byRelId[id]; return r ? ROOT + "relation/" + encodeURIComponent(r.slug || r.relationship_id) + "/" : ROOT; }
  function networkHref(id) { return ROOT + "network/?focus=" + encodeURIComponent(id || "actor-jnim"); }
  function entityLink(id, label) { const e = store.byEntityId[id]; if (!e) return esc(label || id); return '<a class="intel-entity-link" href="' + esc(entityHref(id)) + '">' + esc(label || title(e)) + '</a>'; }
  function countryLink(id) { const c = store.byCountryId[id]; return c ? '<a class="intel-entity-link" href="' + esc(countryHref(id)) + '">' + esc(c.name_zh) + '</a>' : esc(id); }
  function regionLink(id) { const r = store.byRegionId[id]; return r ? '<a class="intel-entity-link" href="' + esc(regionHref(id)) + '">' + esc(r.name_zh) + '</a>' : esc(id); }
  function sourceLink(id) { const s = store.sources.find(function (x) { return x.source_id === id; }); return s ? '<a target="_blank" rel="noopener noreferrer" href="' + esc(s.url) + '">' + esc(s.publisher) + '</a>' : esc(id); }
  function sourceList(ids) { return (ids || []).map(sourceLink).join(" · "); }
  function evidenceCountFor(ids) { return store.evidence.filter(function (ev) { return (ev.entity_ids || []).some(function (x) { return ids.indexOf(x) >= 0; }) || (ev.relation_ids || []).some(function (x) { return ids.indexOf(x) >= 0; }); }).length; }
  function importanceBadge(e) { return '<span class="intel-badge imp-' + esc(e.importance_level || "L3") + '">' + esc(impLabel(e.importance_level)) + '</span>'; }
  function riskBadge(c) { return '<span class="intel-badge risk-' + esc(c.risk_level || "medium") + '">' + esc(riskLabel(c.risk_level)) + '</span>'; }
  function typeBadge(e) { return '<span class="intel-badge type-entity">' + esc(typeLabel(e.primary_type || e.entity_type)) + '</span>'; }
  function entityCard(e) { const rels = store.relationships.filter(function (r) { return r.source_entity_id === e.entity_id || r.target_entity_id === e.entity_id; }); return '<a class="intel-card" href="' + esc(entityHref(e.entity_id)) + '"><div class="intel-card-top"><span class="intel-code">' + esc(e.entity_id) + '</span>' + typeBadge(e) + '</div><div class="intel-card-title-row"><h3>' + esc(title(e)) + '</h3><span class="intel-level-mini">' + esc(e.importance_level || "L3") + '</span></div><p class="intel-en">' + esc(e.name_en) + '</p><p>' + esc(e.short_description) + '</p><div class="intel-card-foot"><span>' + rels.length + ' 条直接关系</span><span>证据 ' + evidenceCountFor([e.entity_id]) + '</span></div></a>'; }
  function countryCard(c) { const regionNames = (c.region_ids || []).map(regionLink).join(" · "); return '<a class="intel-card" href="' + esc(countryHref(c.country_id)) + '"><div class="intel-card-top"><span class="intel-code">' + esc(c.iso_alpha3 || c.country_id) + '</span>' + riskBadge(c) + '</div><h3>' + esc(c.name_zh) + '</h3><p class="intel-en">' + esc(c.name_en) + '</p><p>区域：' + (regionNames || "未说明") + '</p><p class="intel-card-foot">' + esc((c.risk_level_reason || "").slice(0, 60)) + '</p></a>'; }
  function regionCard(r) { return '<a class="intel-card" href="' + esc(regionHref(r.region_id)) + '"><div class="intel-card-top"><span class="intel-code">' + esc(r.region_id) + '</span></div><h3>' + esc(r.name_zh) + '</h3><p class="intel-en">' + esc(r.name_en) + '</p><p>' + esc((r.definition || "").slice(0, 90)) + '…</p></a>'; }
  function renderTopbar() { const t = document.querySelector("#topbar"); if (t) t.innerHTML = '<div class="intel-topbar"><div><a class="intel-back" href="' + esc(ROOT) + '">← ASIP非洲安全情报知识库</a><span class="intel-kicker">正式知识库 V1.0 · 生产数据层</span></div><div class="intel-topmeta">统一数据底座 · 核验至 2026-08-06</div></div>'; }
  function renderFooter() { const f = document.querySelector("footer.site"); if (f) f.innerHTML = 'ASIP非洲安全情报知识库 V1.0 · 区域视图为数据库过滤而非独立数据副本 · <a href="' + esc(ROOT) + '">返回首页</a> · <a href="' + esc((ROOT.match(/\/intelligence\//) ? ROOT.slice(0, ROOT.indexOf("/intelligence/") + 14) : "../") + "demo/") + '">历史 Demo</a>'; }

  function initHome() {
    const regionGrid = document.querySelector("#regionGrid"); if (regionGrid) regionGrid.innerHTML = store.regions.map(regionCard).join("");
    const countryGrid = document.querySelector("#countryGrid"); if (countryGrid) countryGrid.innerHTML = store.countries.map(countryCard).join("");
    const entityGrid = document.querySelector("#entityGrid"); if (entityGrid) entityGrid.innerHTML = store.entities.filter(function (e) { return !e.entity_id.startsWith("country-"); }).sort(function (a, b) { return (a.importance_level === b.importance_level) ? 0 : (a.importance_level === "L1" ? -1 : 1); }).slice(0, 12).map(entityCard).join("");
    const stats = document.querySelector("#statEntity"); if (stats) stats.textContent = store.entities.filter(function (e) { return !e.entity_id.startsWith("country-"); }).length;
    const statRel = document.querySelector("#statRelation"); if (statRel) statRel.textContent = store.relationships.length;
    const statCountry = document.querySelector("#statCountry"); if (statCountry) statCountry.textContent = store.countries.length;
    const statRegion = document.querySelector("#statRegion"); if (statRegion) statRegion.textContent = store.regions.length;
    const statEvidence = document.querySelector("#statEvidence"); if (statEvidence) statEvidence.textContent = store.evidence.length;
    const statSource = document.querySelector("#statSource"); if (statSource) statSource.textContent = store.sources.length;
    const statVerified = document.querySelector("#statVerified"); if (statVerified) statVerified.textContent = store.metrics ? store.metrics.evidence_by_status.verified : "—";
    const statFull = document.querySelector("#statFull"); if (statFull) statFull.textContent = store.metrics ? store.metrics.encyclopedia_full_count : "—";
    const statAudit = document.querySelector("#statAudit"); if (statAudit) statAudit.textContent = store.audit.length;
    const metricNote = document.querySelector("#metricNote"); if (metricNote && store.metrics) metricNote.textContent = "统计口径：区域 " + store.metrics.region_count + " · 国家 " + store.metrics.country_count + " · 非国家实体 " + store.metrics.non_country_entity_count + " · 知识对象 " + store.metrics.unique_knowledge_object_count + " · 关系 " + store.metrics.relationship_count + " · 来源 " + store.metrics.source_count + " · 证据 " + store.metrics.evidence_record_count + "（已核验 " + store.metrics.evidence_by_status.verified + " / 部分核验 " + store.metrics.evidence_by_status.partially_verified + " / 待复核 " + store.metrics.evidence_by_status.pending_review + "）· 路由 " + store.metrics.route_count;
  }
  function initRegions() { const g = document.querySelector("#allRegions"); if (g) g.innerHTML = store.regions.map(regionCard).join(""); }
  function initCountries() { const g = document.querySelector("#allCountries"); if (g) g.innerHTML = store.countries.map(countryCard).join(""); const f = document.querySelector("#countryRiskNote"); if (f) f.innerHTML = '<p class="profile-standfirst"><span class="profile-standfirst-label">风险等级说明</span><span>国家风险等级（极高/高/中/低）为平台基于公开来源的安全分析视图，与实体重要程度（L1/L2/L3）及事实可信度相互独立。</span></p>'; }
  function initEntities() { const g = document.querySelector("#allEntities"); if (g) g.innerHTML = store.entities.filter(function (e) { return !e.entity_id.startsWith("country-"); }).map(entityCard).join(""); }
  function initRelations() {
    const rows = store.relationships.map(function (r) {
      const s = store.byEntityId[r.source_entity_id], t = store.byEntityId[r.target_entity_id];
      return '<div class="intel-rel-row"><div class="intel-rel-main"><span class="intel-rel-kind">' + esc(relLabel(r.relationship_type)) + '</span> ' + entityLink(r.source_entity_id, s ? title(s) : r.source_entity_id) + ' <b>' + (r.direction === "bidirectional" ? "↔" : "→") + '</b> ' + entityLink(r.target_entity_id, t ? title(t) : r.target_entity_id) + ' <a class="intel-rel-archive" href="' + esc(relationHref(r.relationship_id)) + '">档案 →</a></div><div class="intel-rel-desc">' + esc(r.relation_summary || "") + '</div><div class="intel-rel-meta">时间：' + esc(period(r)) + ' · 状态：' + esc(r.current_status) + ' · 可信度：' + esc(confLabel(r.confidence)) + '</div></div>';
    }).join("");
    const g = document.querySelector("#relationList"); if (g) g.innerHTML = rows;
  }
  function initSources() { const g = document.querySelector("#sourceGrid"); if (g) g.innerHTML = store.sources.map(function (s) { return '<a target="_blank" rel="noopener noreferrer" class="intel-source-grid-item" href="' + esc(s.url) + '"><b>' + esc(s.publisher) + '</b><span>' + esc(s.title) + '</span><span class="intel-rel-meta">' + esc(s.reliability) + ' · 发布 ' + esc(s.published_at || "未标注") + ' · 访问 ' + esc(s.accessed_at || "—") + '</span></a>'; }).join(""); }
  function renderSections(container, sections) {
    const keys = Object.keys(SECTION_LABELS);
    const html = keys.filter(function (k) { return sections[k] != null && !(Array.isArray(sections[k]) && !sections[k].length) && sections[k] !== ""; }).map(function (k) {
      const v = sections[k];
      const body = Array.isArray(v) ? '<ul>' + v.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join("") + '</ul>' : '<p>' + esc(v) + '</p>';
      return '<section class="profile-section" id="sec-' + esc(k) + '"><h2>' + esc(SECTION_LABELS[k]) + '</h2>' + body + '</section>';
    }).join("");
    const el = document.querySelector(container); if (el) el.innerHTML = html;
  }
  function initRegion() {
    const slug = document.body.getAttribute("data-region-slug");
    const region = store.regions.find(function (r) { return r.slug === slug || r.region_id === slug; });
    if (!region) { const el = document.querySelector("#intelError"); if (el) { el.hidden = false; el.textContent = "区域不存在：" + slug; } return; }
    document.title = region.name_zh + " · ASIP非洲安全情报知识库";
    const h = document.querySelector("#regionHeading"); if (h) h.innerHTML = '<div class="intel-heading-code">' + esc(region.region_id) + '</div><h1>' + esc(region.name_zh) + '</h1><p class="intel-title-en">' + esc(region.name_en) + '</p><div class="intel-badges"><span class="intel-badge status">区域安全分析视图</span></div>';
    renderSections("#regionBody", {
      overview: region.definition, regional_belonging: region.geographic_scope,
      main_actors: "纳入国家：" + region.countries.map(countryLink).join("、"),
      core_conflicts: region.core_topics, relationships: region.key_cross_border_relations.map(function (rid) { const r = store.byRelId[rid]; return r ? entityLink(r.source_entity_id, title(store.byEntityId[r.source_entity_id])) + " " + esc(relLabel(r.relationship_type)) + " " + entityLink(r.target_entity_id, title(store.byEntityId[r.target_entity_id])) : esc(rid); }),
      current_trends: region.current_trends, impact: "与其他区域的联系：" + region.links_to_other_regions.map(regionLink).join("、"),
      gaps: region.notes, sources: sourceList(region.source_ids)
    });
    const ent = document.querySelector("#regionEntities"); if (ent) ent.innerHTML = region.main_actors.map(function (id) { const e = store.byEntityId[id]; return e ? entityCard(e) : ""; }).join("");
    const note = document.querySelector("#regionNote"); if (note) note.innerHTML = '<p class="profile-standfirst"><span class="profile-standfirst-label">区域定义说明</span><span>本区域划分用于 ASIP 安全分析，不等同于唯一的正式地理分类；区域允许重叠，国家可同时属于多个区域。</span></p>';
  }
  function initCountry() {
    const slug = document.body.getAttribute("data-country-slug");
    const country = store.countries.find(function (c) { return c.slug === slug || c.country_id === slug; });
    if (!country) { const el = document.querySelector("#intelError"); if (el) { el.hidden = false; el.textContent = "国家不存在：" + slug; } return; }
    const profile = store.countryProfiles[country.country_id] || { sections: {} };
    document.title = country.name_zh + " · ASIP非洲安全情报知识库";
    const h = document.querySelector("#countryHeading"); if (h) h.innerHTML = '<div class="intel-heading-code">' + esc(country.iso_alpha3 || country.country_id) + '</div><h1>' + esc(country.name_zh) + '</h1><p class="intel-title-en">' + esc(country.name_en) + '</p><div class="intel-badges">' + riskBadge(country) + freshnessBadge(country.freshness_status) + '<span class="intel-badge status">数据检查 ' + esc(country.record_reviewed_at || country.last_verified_at) + '</span></div>' + freshnessNote(country);
    renderSections("#countryBody", profile.sections);
    const actors = document.querySelector("#countryActors"); if (actors) actors.innerHTML = country.main_actors.map(function (id) { const e = store.byEntityId[id]; return e ? entityCard(e) : ""; }).join("");
    const rels = store.relationships.filter(function (r) { return country.main_actors.indexOf(r.source_entity_id) >= 0 || country.main_actors.indexOf(r.target_entity_id) >= 0 || r.source_entity_id === country.country_id || r.target_entity_id === country.country_id; });
    const rl = document.querySelector("#countryRelations"); if (rl) rl.innerHTML = rels.slice(0, 12).map(function (r) { return '<div class="intel-rel-row"><div class="intel-rel-main">' + entityLink(r.source_entity_id, title(store.byEntityId[r.source_entity_id])) + ' <b>↔</b> ' + entityLink(r.target_entity_id, title(store.byEntityId[r.target_entity_id])) + ' <span class="intel-rel-kind">' + esc(relLabel(r.relationship_type)) + '</span>' + freshnessBadge(r.freshness_status) + '</div></div>'; }).join("");
    const ev = document.querySelector("#countryEvidence"); if (ev) ev.innerHTML = '<div class="relationship-count">相关证据记录 ' + evidenceCountFor(country.main_actors.concat([country.country_id])) + ' 条</div>' + '<div class="ib-row"><dt>当前状态核验</dt><dd>' + esc(country.current_status_verified_at || "未单独核验") + '</dd></div><div class="ib-row"><dt>事实有效截至</dt><dd>' + esc(country.claim_valid_as_of || "未说明") + '</dd></div><p class="muted">证据通过 source_id 关联来源；' + esc(country.freshness_status === "stale" || country.freshness_status === "aging" ? "本页当前状态依赖较早来源，须谨慎解读。" : "关键事实见各关系与实体档案。") + '</p>';
  }
  function initEntity() {
    const slug = document.body.getAttribute("data-entity-slug");
    const entity = store.entities.find(function (e) { return e.slug === slug || e.entity_id === slug; });
    if (!entity) { const el = document.querySelector("#intelError"); if (el) { el.hidden = false; el.textContent = "实体不存在：" + slug; } return; }
    const profile = store.entityProfiles[entity.entity_id] || { sections: {} };
    document.title = title(entity) + " · ASIP非洲安全情报知识库";
    const h = document.querySelector("#entityHeading"); if (h) h.innerHTML = '<div class="intel-heading-code">' + esc(entity.entity_id) + '</div><h1>' + esc(title(entity)) + '</h1><p class="intel-title-en">' + esc(entity.name_en) + '</p><div class="intel-badges">' + typeBadge(entity) + importanceBadge(entity) + '<span class="intel-badge status">' + esc(entity.current_status) + '</span>' + freshnessBadge(entity.freshness_status) + '</div>' + freshnessNote(entity);
    renderSections("#entityBody", profile.sections);
    const ib = document.querySelector("#entityInfobox"); if (ib) {
      let rows = "";
      function row(l, v) { if (v != null && v !== "" && !(Array.isArray(v) && !v.length)) rows += '<div class="ib-row"><dt>' + esc(l) + '</dt><dd>' + v + '</dd></div>'; }
      row("重要程度", '<b>' + esc(impLabel(entity.importance_level)) + '</b><p class="ib-note">平台内部重要程度，非政府或联合国认定等级。</p>');
      row("档案深度", esc(profile.profile_depth || "basic"));
      row("实体类型", typeLabel(entity.primary_type || entity.entity_type));
      row("别名", entity.aliases.map(esc).join(" · "));
      row("历史名称", (entity.historical_names || []).map(esc).join(" · "));
      row("活动国家", (entity.country_ids || []).map(countryLink).join(" · "));
      row("所属区域视图", (entity.region_ids || []).map(regionLink).join(" · "));
      const est = store.forceEstimates[entity.entity_id];
      if (est && est.length) row("估计武装规模", '<b>' + est.map(function (x) { return esc(x.estimate_text) + "（" + esc(x.estimate_date) + "）"; }).join("；") + '</b>');
      const links = store.externalLinks[entity.entity_id];
      if (links && links.wikipedia && links.wikipedia.length) row("Wikipedia", links.wikipedia.map(function (l) { return '<a class="ext-link" target="_blank" rel="noopener noreferrer" href="' + esc(l.url) + '">' + esc(l.language + " · " + l.label) + ' ↗</a>'; }).join(" · "));
      rows += dateRow(entity);
      ib.innerHTML = '<h2>结构化信息框</h2><dl>' + rows + '</dl>';
    }
    const rels = store.relationships.filter(function (r) { return r.source_entity_id === entity.entity_id || r.target_entity_id === entity.entity_id; });
    const rl = document.querySelector("#entityRelations"); if (rl) rl.innerHTML = rels.map(function (r) { const other = r.source_entity_id === entity.entity_id ? r.target_entity_id : r.source_entity_id; return '<div class="intel-rel-row"><div class="intel-rel-main"><span class="intel-rel-kind">' + esc(relLabel(r.relationship_type)) + '</span> ' + entityLink(other, title(store.byEntityId[other])) + ' <a class="intel-rel-archive" href="' + esc(relationHref(r.relationship_id)) + '">档案 →</a></div><div class="intel-rel-meta">' + esc(period(r)) + ' · ' + esc(r.current_status) + '</div></div>'; }).join("") || '<p class="muted">暂无直接关系。</p>';
    const gl = document.querySelector("#graphLink"); if (gl) gl.setAttribute("href", networkHref(entity.entity_id));
    const ev = document.querySelector("#entityEvidence"); if (ev) ev.innerHTML = '<div class="relationship-count">相关证据记录 ' + evidenceCountFor([entity.entity_id]) + ' 条</div><p class="muted">关键事实经 evidence_id 与 source_id 关联追溯。</p>';
  }
  function initRelation() {
    const slug = document.body.getAttribute("data-relation-slug");
    const rel = store.byRelId[slug];
    if (!rel) { const el = document.querySelector("#intelError"); if (el) { el.hidden = false; el.textContent = "关系不存在：" + slug; } return; }
    const profile = store.relationProfiles[rel.relationship_id] || store.relationProfiles[rel.slug] || null;
    const timeline = store.relationTimelines[rel.relationship_id] || store.relationTimelines[rel.slug] || [];
    const s = store.byEntityId[rel.source_entity_id], t = store.byEntityId[rel.target_entity_id];
    document.title = relLabel(rel.relationship_type) + "：" + title(s) + "—" + title(t);
    const h = document.querySelector("#relationHeading"); if (h) h.innerHTML = '<div class="intel-heading-code">' + esc(rel.relationship_id) + '</div><h1>' + esc(title(s)) + ' <span class="rel-arrow">↔</span> ' + esc(title(t)) + '</h1><p class="intel-title-en">' + esc(relLabel(rel.relationship_type)) + ' · ' + esc(ringLabel(rel.display_ring)) + '圈层 · ' + esc(rel.current_status) + '</p><div class="intel-badges">' + importanceBadge(s) + importanceBadge(t) + freshnessBadge(rel.freshness_status) + '</div>' + freshnessNote(rel);
    const ov = document.querySelector("#relationOverview"); if (ov) ov.innerHTML = '<p class="intel-lead">' + esc(profile ? profile.overview : rel.relation_summary) + '</p>';
    const body = document.querySelector("#relationBody"); if (body) {
      let html = "";
      if (profile) {
        html += '<section class="profile-section"><h2>关系形成背景</h2><p>' + esc(profile.formation_background) + '</p></section>';
        html += '<section class="profile-section"><h2>双方最初的关系</h2><p>' + esc(profile.initial_relationship) + '</p></section>';
        if (profile.evolution_stages && profile.evolution_stages.length) html += '<section class="profile-section"><h2>历史演变阶段</h2><ul>' + profile.evolution_stages.map(function (x) { return '<li><b>' + esc(x.period + " · " + x.title) + '</b><p>' + esc(x.description) + '</p></li>'; }).join("") + '</ul></section>';
        if (profile.causes && profile.causes.length) html += '<section class="profile-section"><h2>形成原因</h2><ul>' + profile.causes.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join("") + '</ul></section>';
        if (profile.key_turning_points && profile.key_turning_points.length) html += '<section class="profile-section"><h2>关键转折</h2><ul>' + profile.key_turning_points.map(function (x) { return '<li><b>' + esc(x.event) + '</b><p>' + esc(x.impact) + '</p></li>'; }).join("") + '</ul></section>';
        html += '<section class="profile-section"><h2>当前状态</h2><p>' + esc(profile.current_status) + '</p></section>';
        if (profile.regional_differences) html += '<section class="profile-section"><h2>地区差异</h2><p>' + esc(profile.regional_differences) + '</p></section>';
        if (profile.impact_on_security) html += '<section class="profile-section"><h2>对区域安全的影响</h2><p>' + esc(profile.impact_on_security) + '</p></section>';
        if (profile.why_it_matters) html += '<section class="profile-section"><h2>为什么重要</h2><p>' + esc(profile.why_it_matters) + '</p></section>';
        if (profile.uncertainties) html += '<section class="profile-section"><h2>不确定性与争议</h2><p>' + esc(profile.uncertainties) + '</p></section>';
      } else {
        html += '<section class="profile-section"><h2>关系概述</h2><p>' + esc(rel.relation_summary) + '</p></section>';
        html += '<section class="profile-section"><h2>当前状态</h2><p>' + esc(rel.current_status_detail || rel.current_status) + '</p></section>';
      }
      body.innerHTML = html;
    }
    const tl = document.querySelector("#relationTimeline"); if (tl) tl.innerHTML = '<h2>关系历史时间轴</h2>' + (timeline.length ? '<div class="relation-timeline">' + timeline.map(function (x) { return '<div class="tl-item"><div class="tl-date">' + esc(x.date) + '</div><div class="tl-body"><h3>' + esc(x.event_title) + '</h3><p>' + esc(x.event_description) + '</p><p class="tl-impact"><b>对关系的影响：</b>' + esc(x.impact_on_relationship) + '</p><p class="tl-meta">可信度：' + esc(confLabel(x.confidence)) + ' · 来源：' + sourceList(x.source_ids) + '</p></div></div>'; }).join("") + '</div>' : '<p class="muted">暂无已核验时间轴条目。</p>');
    const src = document.querySelector("#relationSources"); if (src) src.innerHTML = '<h2>来源与证据</h2><div class="intel-source-list">' + sourceList(rel.source_refs) + '</div><p class="muted">证据 ' + evidenceCountFor([rel.relationship_id]) + ' 条，关键事实可追溯。</p>' + (rel.relationship_semantics_note ? '<p class="ib-note">' + esc(rel.relationship_semantics_note) + '</p>' : '');
    const gb = document.querySelector("#relationGraphBack"); if (gb) gb.setAttribute("href", networkHref(rel.source_entity_id));
  }

  function initNetwork() {
    const svg = document.getElementById("graphSvg"); if (!svg) return;
    const NS = "http://www.w3.org/2000/svg";
    const viewport = document.getElementById("graphViewport");
    let focusId = new URLSearchParams(window.location.search).get("focus");
    if (!store.byEntityId[focusId]) focusId = "actor-jnim";
    let positions = {};
    let zoom = 1, drawToken = 0, lastFit = -1;
    const filters = { region: "", country: "", type: "", imp: { L1: true, L2: true, L3: true } };
    const RINGS = { inner: 158, middle: 248, outer: 338 };
    const RING_ORDER = ["inner", "middle", "outer"];
    const MIN = 96;
    function ringFor(rel) { if (rel.display_ring && RINGS[rel.display_ring] != null) return rel.display_ring; if (["affiliated_with", "constituent_of", "operates_in", "member_of_force", "pledged_allegiance_to"].indexOf(rel.relationship_type) >= 0) return "inner"; if (["hostile_to", "historically_associated_with", "allied_with", "cooperates_with", "fought_against", "competes_with"].indexOf(rel.relationship_type) >= 0) return "middle"; return "outer"; }
    function typeName(e) { return e.primary_type || e.entity_type; }
    function visible(e) { return filters.imp[e.importance_level || "L3"] !== false && (!filters.type || typeName(e) === filters.type) && (!filters.region || (e.region_ids || []).indexOf(filters.region) >= 0 || (e.entity_id === "actor-jnim" && filters.region === "region-central-sahel")) && (!filters.country || (e.country_ids || []).indexOf(filters.country) >= 0); }
    function color(e) { return ({ organization: "#14507e", armed_group: "#14507e", terrorist_group: "#a94b4b", insurgent_group: "#9a6b17", militia: "#7d5a94", community_self_defense: "#37715c", state_security_force: "#0f3a5d", regional_force: "#2e6e8e", political_movement: "#8a641c", person: "#9a6b17", country: "#37715c", international_network: "#52606d" })[typeName(e)] || "#52606d"; }
    function mk(tag, attrs) { const n = document.createElementNS(NS, tag); Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); }); return n; }
    function layout(center, visibleEntities, rels) {
      const cx = 450, cy = 315, narrow = document.getElementById("graphWrap") ? document.getElementById("graphWrap").clientWidth < 560 : false;
      const min = narrow ? 80 : MIN;
      const next = {}; next[center.entity_id] = { x: cx, y: cy };
      const byRing = {};
      rels.forEach(function (r) { const o = store.byEntityId[r.source_entity_id === center.entity_id ? r.target_entity_id : r.source_entity_id]; if (!o || !visible(o)) return; const ring = ringFor(r); (byRing[ring] = byRing[ring] || []); if (!byRing[ring].some(function (x) { return x.entity_id === o.entity_id; })) byRing[ring].push(o); });
      RING_ORDER.forEach(function (ring) {
        const items = (byRing[ring] || []).slice();
        let radius = RINGS[ring];
        if (items.length > 1) { let need = radius; for (let i = 0; i < 6; i++) { if (need * Math.PI / (items.length - 1) >= min) break; need = min * (items.length - 1) / Math.PI; } radius = Math.max(radius, need + 10); }
        const start = -Math.PI / 2 - Math.PI * 0.55;
        const spread = Math.min(Math.PI * 1.15, Math.max(Math.PI * 0.42, items.length * 0.3));
        items.forEach(function (e, i) {
          const off = { organization: 0, armed_group: 0, terrorist_group: 0, insurgent_group: 0, state_security_force: Math.PI * 0.08, regional_force: Math.PI * 0.16, person: Math.PI * 0.11, country: Math.PI * 0.22, international_network: Math.PI * 0.28 }[typeName(e)] || 0;
          const angle = items.length === 1 ? start + Math.PI * 0.55 : start + off + spread * i / (items.length - 1);
          const px = positions[e.entity_id];
          const target = { x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius * 0.92 };
          next[e.entity_id] = (px && Math.hypot(px.x - target.x, px.y - target.y) < 200) ? { x: px.x * 0.3 + target.x * 0.7, y: px.y * 0.3 + target.y * 0.7 } : target;
        });
      });
      visibleEntities.forEach(function (e) { if (!next[e.entity_id]) next[e.entity_id] = { x: cx, y: cy }; });
      const ids = Object.keys(next);
      for (let p = 0; p < 4; p++) ids.forEach(function (a) { if (a === center.entity_id) return; ids.forEach(function (b) { if (b === center.entity_id || b <= a) return; const pa = next[a], pb = next[b]; const dx = pa.x - pb.x, dy = pa.y - pb.y, d = Math.hypot(dx, dy); if (d < min && d > 0) { const push = (min - d) / 2, ux = dx / d, uy = dy / d; pa.x += ux * push; pa.y += uy * push; pb.x -= ux * push; pb.y -= uy * push; } }); });
      positions = next;
    }
    function edgePoint(a, b, dist) { const dx = b.x - a.x, dy = b.y - a.y, l = Math.max(Math.hypot(dx, dy), 1); return { x: a.x + dx / l * dist, y: a.y + dy / l * dist }; }
    function classFor(r) { if (r.relationship_type === "hostile_to" || r.relationship_type === "fought_against" || r.relationship_type === "competes_with") return "hostile"; if (r.temporal_sensitive || String(r.current_status || "").indexOf("historical") >= 0) return "historical"; if (["led_by", "founded_by", "member_of_force"].indexOf(r.relationship_type) >= 0) return "leadership"; if (r.relationship_type === "operates_in" || r.relationship_type === "cross_border_link") return "presence"; return "normal"; }
    function draw() {
      const center = store.byEntityId[focusId]; if (!center) return;
      const token = ++drawToken;
      const rels = store.relationships.filter(function (r) { return r.source_entity_id === focusId || r.target_entity_id === focusId; });
      const neighbors = rels.map(function (r) { return store.byEntityId[r.source_entity_id === focusId ? r.target_entity_id : r.source_entity_id]; }).filter(function (e, i, all) { return e && visible(e) && all.findIndex(function (x) { return x.entity_id === e.entity_id; }) === i; });
      const visibleEntities = [center].concat(neighbors);
      layout(center, visibleEntities, rels);
      viewport.innerHTML = "";
      const defs = mk("defs");
      ["normal", "leadership", "presence", "historical", "disputed", "hostile"].forEach(function (k) { const m = mk("marker", { id: "af-arrow-" + k, markerWidth: "9", markerHeight: "9", refX: "8", refY: "4.5", orient: "auto", markerUnits: "strokeWidth" }); m.appendChild(mk("path", { d: "M0,0 L9,4.5 L0,9 z", class: "arrow-head " + k })); defs.appendChild(m); });
      RING_ORDER.forEach(function (ring) { defs.appendChild(mk("circle", { cx: 450, cy: 315, r: RINGS[ring], class: "ring-guide ring-" + ring, "aria-hidden": "true" })); });
      viewport.appendChild(defs);
      const hitLayer = mk("g", { class: "graph-edge-hits" }); const edgeLayer = mk("g", { class: "graph-edges" }); const labelLayer = mk("g", { class: "graph-edge-labels" }); const nodeLayer = mk("g", { class: "graph-nodes" });
      const showLabels = rels.length <= 8;
      const relInfo = document.getElementById("relationInfo");
      rels.forEach(function (r) {
        const other = store.byEntityId[r.source_entity_id === focusId ? r.target_entity_id : r.source_entity_id];
        if (!other || !visible(other) || !positions[other.entity_id]) return;
        const a = positions[focusId], b = positions[other.entity_id], kind = classFor(r);
        const d = center.primary_type === "country" || center.entity_type === "country" ? 44 : 52;
        const p1 = edgePoint(a, b, d), p2 = edgePoint(b, a, d);
        const g = mk("g", { class: "graph-edge-group " + kind });
        g.appendChild(mk("line", { x1: p1.x, y1: p1.y, x2: p2.x, y2: p2.y, class: "graph-edge-hit " + kind }));
        g.appendChild(mk("line", { x1: p1.x, y1: p1.y, x2: p2.x, y2: p2.y, class: "graph-edge " + kind, "marker-end": "url(#af-arrow-" + kind + ")", "aria-label": relLabel(r.relationship_type) + "：" + title(other), tabindex: "0", role: "button" }));
        g.addEventListener("click", function (ev) { ev.stopPropagation(); document.querySelectorAll(".graph-edge-group.selected").forEach(function (x) { x.classList.remove("selected"); }); g.classList.add("selected"); if (relInfo) relInfo.innerHTML = '<h2>关系详情</h2><div class="relation-pair">' + entityLink(r.source_entity_id, title(store.byEntityId[r.source_entity_id])) + ' <b>↔</b> ' + entityLink(r.target_entity_id, title(store.byEntityId[r.target_entity_id])) + '</div><p class="relation-label">' + esc(relLabel(r.relationship_type)) + ' · ' + esc(ringLabel(ringFor(r))) + '圈层</p>' + (r.relationship_type === "pledged_allegiance_to" ? '<p class="ib-note">宣誓效忠（bay\'ah）为独立关系语义，不同于一般网络关联（affiliated_with）。</p>' : '') + '<p>' + esc(r.relation_summary) + '</p><dl class="intel-detail-list"><dt>时间范围</dt><dd>' + esc(period(r)) + '</dd><dt>状态</dt><dd>' + esc(r.current_status) + '</dd><dt>可信度</dt><dd>' + esc(confLabel(r.confidence)) + '</dd><dt>时效</dt><dd>' + freshnessBadge(r.freshness_status) + '</dd><dt>来源</dt><dd>' + sourceList(r.source_refs) + '</dd></dl><a class="intel-button sm" href="' + esc(relationHref(r.relationship_id)) + '">查看完整关系沿革 →</a>'; });
        g.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") g.dispatchEvent(new MouseEvent("click", { bubbles: true })); });
        hitLayer.appendChild(g);
        if (showLabels) {
          const mx = (p1.x + p2.x) / 2, my = (p1.y + p2.y) / 2, dx = p2.x - p1.x, dy = p2.y - p1.y, l = Math.max(Math.hypot(dx, dy), 1);
          const wrap = mk("g", { class: "graph-edge-label-wrap " + kind, transform: "translate(" + (mx - dy / l * 12) + "," + (my + dx / l * 12) + ")", "pointer-events": "none" });
          const text = relLabel(r.relationship_type); const w = Math.max(42, text.length * 12 + 14);
          wrap.appendChild(mk("rect", { x: -w / 2, y: -12, width: w, height: 18, rx: 8 }));
          const t = mk("text", { x: 0, y: 1, class: "graph-edge-label", "text-anchor": "middle" }); t.textContent = text; wrap.appendChild(t);
          labelLayer.appendChild(wrap);
        }
      });
      visibleEntities.forEach(function (e) {
        const pos = positions[e.entity_id]; if (!pos) return;
        const isCenter = e.entity_id === focusId;
        const g = mk("g", { class: "graph-node " + (isCenter ? "is-center" : ""), transform: "translate(" + pos.x + "," + pos.y + ")", tabindex: "0", role: "button", "aria-label": title(e) + "，" + e.name_en, "data-entity-id": e.entity_id });
        if (isCenter) g.appendChild(mk("circle", { cx: 0, cy: 0, r: 60, class: "node-halo" }));
        const col = color(e); let shape;
        if (typeName(e) === "person") shape = mk("rect", { x: isCenter ? -32 : -26, y: isCenter ? -27 : -21, width: isCenter ? 64 : 52, height: isCenter ? 54 : 42, rx: 11, fill: col, class: "node-shape person" });
        else if (typeName(e) === "country") shape = mk("path", { d: isCenter ? "M0,-34 L31,-18 L31,18 L0,34 L-31,18 L-31,-18 Z" : "M0,-27 L25,-13 L25,13 L0,27 L-25,13 L-25,-13 Z", fill: col, class: "node-shape country" });
        else shape = mk("path", { d: isCenter ? "M0,-38 L34,-19 L34,19 L0,38 L-34,19 L-34,-19 Z" : "M0,-28 L25,-14 L25,14 L0,28 L-25,14 L-25,-14 Z", fill: col, class: "node-shape organization" });
        g.appendChild(shape);
        const icon = mk("text", { x: 0, y: 5, class: "node-icon", "text-anchor": "middle" }); icon.textContent = typeName(e) === "person" ? "人" : typeName(e) === "country" ? "国" : "组"; g.appendChild(icon);
        const name = mk("text", { x: 0, y: isCenter ? 76 : 54, class: "node-label " + (isCenter ? "center-label" : ""), "text-anchor": "middle", "pointer-events": "none" }); const nt = title(e); name.textContent = nt.length > 16 ? nt.slice(0, 15) + "…" : nt; g.appendChild(name);
        if (isCenter) { const en = mk("text", { x: 0, y: 94, class: "node-sub-label", "text-anchor": "middle" }); en.textContent = e.name_en.length > 30 ? e.name_en.slice(0, 28) + "…" : e.name_en; g.appendChild(en); }
        const tag = mk("text", { x: 0, y: isCenter ? -48 : -38, class: "node-imp-tag", "text-anchor": "middle" }); tag.textContent = e.importance_level || "L3"; g.appendChild(tag);
        g.addEventListener("click", function () { focusId = e.entity_id; const u = new URL(window.location.href); u.searchParams.set("focus", focusId); window.history.pushState({ focus: focusId }, "", u); draw(); if (relInfo) relInfo.innerHTML = '<h2>关系详情</h2><p class="muted">点击关系线查看双方、类型、时间与来源。</p>'; });
        nodeLayer.appendChild(g);
      });
      viewport.appendChild(hitLayer); viewport.appendChild(edgeLayer); viewport.appendChild(labelLayer); viewport.appendChild(nodeLayer);
      const hint = document.getElementById("graphHint");
      if (hint) hint.textContent = visibleEntities.length + " 个节点 · " + rels.length + " 条直接关系 · 内圈结构与地理 · 中圈组织与力量 · 外圈人物 · 宣誓效忠（pledged_allegiance_to）为独立关系语义";
      const stats = document.getElementById("importanceStats");
      if (stats) { const cnt = {}; visibleEntities.forEach(function (e) { const l = e.importance_level || "L3"; cnt[l] = (cnt[l] || 0) + 1; }); stats.textContent = "可见 " + visibleEntities.length + " · L1 " + (cnt.L1 || 0) + " · L2 " + (cnt.L2 || 0) + " · L3 " + (cnt.L3 || 0); }
      const wrap = document.getElementById("graphWrap");
      if (wrap && wrap.clientWidth < 560 && visibleEntities.length !== lastFit) { lastFit = visibleEntities.length; zoom = Math.max(0.62, Math.min(1, (wrap.clientWidth - 60) / 700)); const zv = document.getElementById("zoomValue"); if (zv) zv.textContent = Math.round(zoom * 100) + "%"; }
      viewport.setAttribute("transform", "translate(0 0) scale(" + zoom + ")");
    }
    function bind() {
      document.querySelectorAll("[data-imp-filter]").forEach(function (el) { el.addEventListener("change", function () { filters.imp[el.getAttribute("data-imp-filter")] = el.checked; lastFit = -1; draw(); }); });
      document.querySelectorAll("[data-view-filter]").forEach(function (el) { el.addEventListener("click", function () { const v = el.getAttribute("data-view-filter"); filters.imp = v === "core" ? { L1: true, L2: false, L3: false } : v === "priority" ? { L1: true, L2: true, L3: false } : { L1: true, L2: true, L3: true }; document.querySelectorAll("[data-imp-filter]").forEach(function (x) { x.checked = filters.imp[x.getAttribute("data-imp-filter")]; }); lastFit = -1; draw(); }); });
      const regionSel = document.getElementById("regionFilter"); if (regionSel) { regionSel.innerHTML = '<option value="">全部区域</option>' + store.regions.map(function (r) { return '<option value="' + esc(r.region_id) + '">' + esc(r.name_zh) + '</option>'; }).join(""); regionSel.addEventListener("change", function () { filters.region = regionSel.value; lastFit = -1; draw(); }); }
      const countrySel = document.getElementById("countryFilter"); if (countrySel) { countrySel.innerHTML = '<option value="">全部国家</option>' + store.countries.map(function (c) { return '<option value="' + esc(c.country_id) + '">' + esc(c.name_zh) + '</option>'; }).join(""); countrySel.addEventListener("change", function () { filters.country = countrySel.value; lastFit = -1; draw(); }); }
      const typeSel = document.getElementById("typeFilter"); if (typeSel) { typeSel.innerHTML = '<option value="">全部类型</option>' + Object.keys(TYPE_LABELS).map(function (t) { return '<option value="' + esc(t) + '">' + esc(TYPE_LABELS[t]) + '</option>'; }).join(""); typeSel.addEventListener("change", function () { filters.type = typeSel.value; lastFit = -1; draw(); }); }
      const search = document.getElementById("entitySearch"); if (search) search.addEventListener("input", function () { const term = search.value.trim().toLowerCase(); if (!term) return; const hit = store.entities.find(function (e) { return [e.entity_id, e.slug, e.name_zh, e.name_en, e.acronym || "", e.native_name || ""].concat(e.aliases).join(" ").toLowerCase().indexOf(term) >= 0; }); if (hit) { if (!visible(hit)) { filters.imp[hit.importance_level || "L3"] = true; document.querySelectorAll("[data-imp-filter]").forEach(function (x) { x.checked = filters.imp[x.getAttribute("data-imp-filter")]; }); } focusId = hit.entity_id; lastFit = -1; draw(); } });
      document.getElementById("zoomIn").addEventListener("click", function () { zoom = Math.min(1.5, zoom + 0.12); draw(); });
      document.getElementById("zoomOut").addEventListener("click", function () { zoom = Math.max(0.55, zoom - 0.12); draw(); });
      document.getElementById("fitGraph").addEventListener("click", function () { zoom = 1; lastFit = -1; draw(); });
      document.getElementById("backFocus").addEventListener("click", function () { window.history.back(); });
      document.getElementById("resetFocus").addEventListener("click", function () { focusId = "actor-jnim"; lastFit = -1; draw(); });
      window.addEventListener("popstate", function () { const f = new URLSearchParams(window.location.search).get("focus"); if (f && store.byEntityId[f]) { focusId = f; draw(); } });
    }
    bind(); draw();
  }

  window.ASIP_AFRICA = { store: store, title: title, typeLabel: typeLabel, relLabel: relLabel, impLabel: impLabel, riskLabel: riskLabel, confLabel: confLabel, entityHref: entityHref, countryHref: countryHref, regionHref: regionHref, relationHref: relationHref, networkHref: networkHref, entityLink: entityLink, sourceLink: sourceLink, esc: esc };
  renderTopbar(); renderFooter();
  const loadSignal = beginLoad();
  loadJson("regions.json", loadSignal).then(function (r) { store.regions = r.regions; r.regions.forEach(function (x) { store.byRegionId[x.region_id] = x; }); return loadJson("countries.json", loadSignal); }).then(function (c) { store.countries = c.countries; c.countries.forEach(function (x) { store.byCountryId[x.country_id] = x; }); return loadJson("entities.json", loadSignal); }).then(function (e) { store.entities = e.entities; e.entities.forEach(function (x) { store.byEntityId[x.entity_id] = x; store.byEntitySlug[x.slug] = x; }); return loadJson("relationships.json", loadSignal); }).then(function (r) { store.relationships = r.relationships; r.relationships.forEach(function (x) { store.byRelId[x.relationship_id] = x; if (x.slug) store.byRelId[x.slug] = x; });     return Promise.all([loadJson("sources.json", loadSignal), loadJson("evidence_records.json", loadSignal), loadJson("relation_profiles.json", loadSignal), loadJson("relation_timelines.json", loadSignal), loadJson("force_estimates.json", loadSignal), loadJson("external_links.json", loadSignal), loadJson("entity_profiles.json", loadSignal), loadJson("country_profiles.json", loadSignal), loadJson("catalog_metrics.json", loadSignal), loadJson("audit_records.json", loadSignal)]); }).then(function (items) {
    store.sources = items[0].sources; store.evidence = items[1].evidence; store.relationProfiles = items[2].profiles || {}; store.relationTimelines = items[3].timelines || {}; store.forceEstimates = items[4].estimates || {}; store.externalLinks = items[5].links || {}; store.entityProfiles = items[6].profiles || {}; store.countryProfiles = items[7].profiles || {}; store.metrics = items[8] || null; store.audit = (items[9] && items[9].records) || [];
    // merge countries into the unified entity table (one ID per entity)
    store.countries.forEach(function (c) {
      if (!store.byEntityId[c.country_id]) {
        var ce = { entity_id: c.country_id, entity_type: "country", primary_type: "country", slug: c.slug, name_zh: c.name_zh, name_en: c.name_en, acronym: "", native_name: c.name_en, aliases: [], historical_names: [], importance_level: "L1", short_description: c.risk_level_reason || c.name_zh + " 国家入口", current_status: "monitored", region_ids: c.region_ids || [], country_ids: [c.country_id], source_refs: [], confidence: "high", temporal_sensitive: false, disputed: false, last_verified_at: c.last_verified_at, record_reviewed_at: c.record_reviewed_at, current_status_verified_at: c.current_status_verified_at, claim_valid_as_of: c.claim_valid_as_of, freshness_status: c.freshness_status };
        store.entities.push(ce); store.byEntityId[ce.entity_id] = ce; store.byEntitySlug[ce.slug] = ce;
      }
    });
    const page = document.body.getAttribute("data-africa-page");
    if (page === "home") initHome(); if (page === "regions") initRegions(); if (page === "countries") initCountries(); if (page === "entities") initEntities(); if (page === "relations") initRelations(); if (page === "sources") initSources(); if (page === "region") initRegion(); if (page === "country") initCountry(); if (page === "entity") initEntity(); if (page === "relation") initRelation(); if (page === "network") initNetwork();
  }).catch(function (error) {
    if (error && error.name === "AbortError") return; // navigation aborted a previous load; not a product error
    const el = document.querySelector("#intelError"); if (el) { el.hidden = false; el.textContent = "非洲知识库数据加载失败：" + (error && error.message ? error.message : error); }
  });
})();
