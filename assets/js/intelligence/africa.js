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
    alleged_support: "涉嫌支持", cross_border_link: "跨境关联", criminal_link: "犯罪关联", part_of_network: "网络组成关系"
  };
  const IMPORTANCE_LABELS = { L1: "L1 核心实体", L2: "L2 重要实体", L3: "L3 扩展实体" };
  const RING_LABELS = { inner: "结构与地理", middle: "组织与力量", outer: "人物" };
  const RISK_LABELS = { extreme: "极高风险", high: "高风险", medium: "中风险", low: "低风险" };
  const CONFIDENCE_LABELS = { high: "高", medium_high: "中高", medium: "中", low: "低", disputed: "存在争议" };
  const SECTION_LABELS = {
    lead: "导语",
    overview: "安全形势概述", regional_belonging: "所属区域", risk_assessment: "风险等级与说明",
    core_conflicts: "当前主要冲突体系", main_actors: "主要非国家武装和政治力量", security_forces: "核心国家安全力量",
    high_risk_areas: "主要高风险地区", cross_border_relations: "跨境安全关系", terrorism_risk: "恐怖主义风险",
    insurgency_risk: "反政府武装或政治军事冲突", community_risk: "社区、族群、部族或地方武装风险", crime_risk: "跨境犯罪、走私或武器流动",
    security_events: "主要安全事件类型", recent_changes: "最近三至五年的重要变化", current_trends: "当前趋势",
    security_impact: "对人员、企业和项目安全的影响", impact: "与邻国安全形势的联系及影响",
    relationships: "重要关系", related_entities: "相关实体", events: "代表性事件", current_assessment: "当前状态",
    formation_background: "成立背景", history: "历史沿革", structure: "组织结构", leadership: "领导层",
    components: "主要分支或组成力量", legal_status: "法律与政治地位", missions: "主要任务", operations: "参与的重要行动",
    ideology_goals: "意识形态与政治目标", geography: "活动范围", force_estimates: "武装力量规模",
    tactics: "主要行动方式", finance: "资金、补给与招募", adversaries: "主要敌对对象",
    regional_impact: "对区域安全的影响", controversies_uncertainties: "争议与不确定性", challenges: "当前挑战",
    core_assessment: "核心评估", name_and_translation: "名称与译名",
    gaps: "资料缺口与不确定性", biography: "生平", roles: "职务", influence: "影响", sources: "来源与注释", notes: "备注",
    // DEPTH A: encyclopedic sections (entity upgrades)
    name_identity: "名称与身份", genealogy: "组织谱系", leadership_structure: "领导与组织结构",
    force_capacity: "力量规模与能力", recruitment_social_base: "招募与社会基础", finance_logistics: "资金与后勤",
    governance: "治理实践", major_timeline: "重大时间线", external_relations: "外部关系",
    current_situation: "当前态势", background: "背景", origin: "起源", katiba_macina: "与马西纳旅",
    jnim_role: "在JNIM中的角色", false_death_history: "误报死亡历史", political_messaging: "政治信息与宣传",
    ansar_dine: "安萨尔丁阶段", leadership_style: "领导风格", sanctions_legal: "制裁与法律状态",
    organizational_relation: "组织关系", strength_capabilities: "力量与能力", jnim_rivalry: "与JNIM的竞争",
    predecessors: "前身组成", political_character: "政治性质", jnim_relation: "与JNIM的关系",
    mali_role: "在马里的角色", strength: "兵力估计", human_rights: "人权与争议", formation: "形成",
    jnim_integration: "JNIM整合", social_dynamics: "社会动力", tactics_governance: "战术与治理",
    ideology_objectives: "意识形态与目标",
    // EXPANSION A: previously unregistered keys. `uncertainties` carried authored
    // content on 51 entities but was never rendered; `asip_analysis` and
    // `watch_indicators` have dedicated partitions but produced empty TOC anchors.
    uncertainties: "不确定性与信息缺口", asip_analysis: "ASIP 分析", watch_indicators: "后续观察指标",
    network_links: "网络关联与外部联系"
  };
  const MATURITY_LABELS = {
    E0_STUB: "E0 存目", E1_BASIC: "E1 基础档案", E2_DEVELOPED: "E2 较完整档案", E3_FULL_ENCYCLOPEDIA: "E3 旗舰百科",
    R0_EDGE_ONLY: "R0 仅边", R1_BASIC: "R1 基础关系", R2_DEVELOPED_RELATIONSHIP: "R2 重要关系档案", R3_FULL_RELATIONSHIP_INTELLIGENCE: "R3 完整情报专题"
  };
  function maturityBadge(m, label) { if (!m) return ""; const l = MATURITY_LABELS[m] || m; return '<span class="intel-badge m-' + esc(m.toLowerCase()) + '">' + esc(l) + '</span>'; }
  // explicit in-text links, e.g. [[entity:actor-jas|博科圣地/JAS]] / [[country:country-nigeria|尼日利亚]] / [[region:region-lake-chad-basin|乍得湖盆地]] / [[relation:rel-jas-iswap-conflict|JAS—ISWAP 关系]]
  function inlineLinks(text) {
    return String(text).replace(/\[\[(entity|country|region|relation):([^|\]]+)\|([^\]]+)\]\]/g, function (m, kind, id, label) {
      if (kind === "entity") { const e = store.byEntityId[id] || store.byEntitySlug[id]; if (e) return '<a href="' + esc(entityHref(e.entity_id)) + '">' + esc(label) + '</a>'; }
      if (kind === "country") { const c = store.byCountryId[id]; if (c) return '<a href="' + esc(countryHref(c.country_id)) + '">' + esc(label) + '</a>'; }
      if (kind === "region") { const rg = store.byRegionId[id]; if (rg) return '<a href="' + esc(ROOT + "region/" + encodeURIComponent(rg.slug) + "/") + '">' + esc(label) + '</a>'; }
      if (kind === "relation") { const r = store.byRelId[id]; if (r) return '<a href="' + esc(relationHref(r.relationship_id)) + '">' + esc(label) + '</a>'; }
      return esc(label);
    });
  }
  function renderBody(v) {
    if (v == null || v === "") return "";
    // UI FINAL POLISH 1: entity/region/country/relation prose also gets exact-safe auto-linking.
    if (Array.isArray(v)) return '<ul class="intel-bullets">' + v.map(function (x) { return '<li>' + renderRelationText(esc(x)) + '</li>'; }).join("") + '</ul>';
    if (typeof v === "string") return '<p>' + renderRelationText(esc(v)) + '</p>';
    let html = "";
    if (v.p) html += v.p.map(function (x) { return '<p>' + renderRelationText(esc(x)) + '</p>'; }).join("");
    if (v.list) html += '<ul class="intel-bullets">' + v.list.map(function (x) { return '<li>' + renderRelationText(esc(x)) + '</li>'; }).join("") + '</ul>';
    if (v.table) {
      html += '<div class="intel-table-wrap"><table class="intel-table"><thead><tr>' + v.table.headers.map(function (x) { return '<th>' + esc(x) + '</th>'; }).join("") + '</tr></thead><tbody>' + v.table.rows.map(function (row) { return '<tr>' + row.map(function (x) { return '<td>' + renderRelationText(esc(x)) + '</td>'; }).join("") + '</tr>'; }).join("") + '</tbody></table></div>';
      if (v.table_note) html += '<p class="intel-table-note">' + renderRelationText(esc(v.table_note)) + '</p>';
    }
    if (v.timeline) {
      html += '<div class="intel-inline-timeline">' + v.timeline.map(function (x) { return '<div class="tl-item"><div class="tl-date">' + esc(x.date) + '</div><div class="tl-body"><h3>' + esc(x.event_title) + '</h3><p>' + esc(x.event_description || "") + '</p></div></div>'; }).join("") + '</div>';
      if (v.timeline_note) html += '<p class="intel-table-note">' + inlineLinks(esc(v.timeline_note)) + '</p>';
    }
    return html;
  }
  // UI/UX V2: sections whose statements are institutional/legal determinations by a
  // named authority (sanctions bodies, courts, legislatures) get an explicit chip.
  const INSTITUTIONAL_KEYS = { sanctions_legal: "机构认定", legal_status: "法律状态" };
  // UI/UX V2: scroll-spy + deep-link for the entity long-page TOC.
  function initScrollSpy(tocEl, bodyEl) {
    if (!tocEl || !bodyEl || tocEl.getAttribute("data-spy")) return;
    tocEl.setAttribute("data-spy", "1");
    const links = tocEl.querySelectorAll(".profile-toc a");
    const secs = bodyEl.querySelectorAll(".profile-section");
    const map = [];
    secs.forEach(function (sec) { if (sec.id) map.push(sec); });
    if (!map.length) return;
    function onScroll() {
      const off = 96;
      let current = "";
      for (let i = 0; i < map.length; i++) {
        if (map[i].getBoundingClientRect().top <= off) current = map[i].id;
      }
      if (!current && map.length) current = map[0].id;
      links.forEach(function (a) { a.classList.toggle("active", a.getAttribute("href") === "#" + current); });
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    if (window.location.hash.indexOf("#sec-") === 0) {
      const t = document.querySelector(window.location.hash);
      if (t) setTimeout(function () { t.scrollIntoView({ behavior: "auto", block: "start" }); }, 60);
    }
  }
  function renderSections(container, sections, opts) {
    opts = opts || {};
    const keys = Object.keys(SECTION_LABELS);
    const items = keys.filter(function (k) { return sections[k] != null && !(Array.isArray(sections[k]) && !sections[k].length) && sections[k] !== ""; });
    let html = "";
    const toc = [];
    // DEPTH A: facts (普通章节) rendered first; ASIP Analysis and Watch Indicators
    // are rendered as visually distinct partitions after the facts. UI/UX V2 also
    // lifts uncertainties out of plain paragraphs into a dedicated uncertainty card.
    // UI FINAL POLISH 1: sources/notes render at the very end (after all prose, analysis,
    // uncertainty and watch partitions) so they never interrupt the reading flow.
    const TAIL_KEYS = { sources: 1, notes: 1 };
    const facts = items.filter(function (k) { return k !== "asip_analysis" && k !== "watch_indicators" && k !== "uncertainties" && !TAIL_KEYS[k]; });
    facts.forEach(function (k) {
      const v = sections[k];
      if (k === "lead") { html += '<div class="profile-lead">' + (Array.isArray(v) ? v.map(function (x) { return '<p>' + inlineLinks(esc(x)) + '</p>'; }).join("") : '<p>' + inlineLinks(esc(v)) + '</p>') + '</div>'; return; }
      toc.push('<a href="#sec-' + esc(k) + '">' + esc(SECTION_LABELS[k]) + '</a>');
      const chip = INSTITUTIONAL_KEYS[k] ? '<span class="intel-sem-chip institutional">' + esc(INSTITUTIONAL_KEYS[k]) + '</span>' : "";
      html += '<section class="profile-section" id="sec-' + esc(k) + '"><h2>' + esc(SECTION_LABELS[k]) + chip + '</h2>' + renderBody(v) + '</section>';
    });
    const hasUnc = sections.uncertainties != null && !(Array.isArray(sections.uncertainties) && !sections.uncertainties.length) && sections.uncertainties !== "";
    if (hasUnc) {
      toc.push('<a href="#sec-uncertainties">' + esc(SECTION_LABELS.uncertainties) + '</a>');
      html += '<section class="profile-section uncertainty-partition" id="sec-uncertainties"><div class="intel-uncertainty-card"><h2>' + esc(SECTION_LABELS.uncertainties) + ' <span class="intel-sem-chip uncertainty">UNCERTAINTY</span></h2>' + renderBody(sections.uncertainties) + '</div></section>';
    }
    if (sections.asip_analysis) {
      toc.push('<a href="#sec-asip_analysis">' + esc(SECTION_LABELS.asip_analysis) + '</a>');
      html += '<section class="profile-section analysis-partition" id="sec-asip_analysis"><div class="intel-analysis-card"><h2>ASIP Analysis · 平台分析 <span class="intel-sem-chip institutional">ASIP ANALYSIS</span></h2>' + renderBody(sections.asip_analysis) + '</div></section>';
    }
    if (sections.watch_indicators && (!Array.isArray(sections.watch_indicators) || sections.watch_indicators.length)) {
      toc.push('<a href="#sec-watch_indicators">' + esc(SECTION_LABELS.watch_indicators) + '</a>');
      html += '<section class="profile-section watch-partition" id="sec-watch_indicators"><div class="intel-watch-card"><h2>Watch Indicators · 后续观察指标 <span class="intel-sem-chip uncertainty">WATCH</span></h2>' + renderBody(sections.watch_indicators) + '</div></section>';
    }
    // sources & notes always last (existing classes intel-source-notes reuse)
    const tailKeys = items.filter(function (k) { return TAIL_KEYS[k]; });
    if (tailKeys.length) {
      tailKeys.forEach(function (k) {
        const v = sections[k];
        toc.push('<a href="#sec-' + esc(k) + '">' + esc(SECTION_LABELS[k]) + '</a>');
        // UI HARD FIX A: entity pages detach sources/notes out of the prose flow;
        // they render at the very end of the page (after relations & evidence).
        if (!opts.detachTail) html += '<section class="profile-section intel-source-notes" id="sec-' + esc(k) + '"><h2>' + esc(SECTION_LABELS[k]) + '</h2>' + renderBody(v) + '</section>';
      });
    }
    const el = document.querySelector(container); if (el) el.innerHTML = html;
    // UI/UX V2: auto-generated TOC into a dedicated container. The entity page
    // template carries #entityToc; other pages (region/country) would use #<id>Toc.
    const bodyId = String(container).replace(/^#/, "");
    const tocEl = document.getElementById(bodyId === "entityBody" ? "entityToc" : (bodyId + "Toc"));
    if (tocEl) {
      if (toc.length >= 3) {
        tocEl.hidden = false;
        const details = document.createElement("details");
        details.className = "profile-toc-details";
        if (window.innerWidth > 850) details.open = true;
        details.innerHTML = '<summary><span class="toc-label">本页目录</span><button type="button" class="toc-btn" aria-label="展开或收起目录">收起</button></summary><nav class="profile-toc" aria-label="本页目录"><ol>' + toc.map(function (x) { return '<li>' + x + '</li>'; }).join("") + '</ol></nav>';
        const tbtn = details.querySelector(".toc-btn");
        const syncToc = function () { if (tbtn) tbtn.textContent = details.open ? "收起" : "展开"; };
        details.addEventListener("toggle", syncToc);
        syncToc();
        let tocAutoCollapsed = false;
        const onTocScroll = function () {
          if (window.innerWidth <= 850) return;
          if (window.scrollY > 200 && details.open) { tocAutoCollapsed = true; details.open = false; }
          else if (window.scrollY < 80 && tocAutoCollapsed && !details.open) { details.open = true; }
        };
        window.addEventListener("scroll", onTocScroll, { passive: true });
        tocEl.innerHTML = "";
        tocEl.appendChild(details);
        initScrollSpy(tocEl, el);
      } else {
        tocEl.hidden = true;
      }
    }
  }
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
  const FRESH_LABELS = { current: "当前", aging: "趋旧", stale: "过时", historical: "历史资料", unknown: "时效不明", current_as_structural_history: "结构性历史·当前" };
  function verifyBadge(s) { const l = VERIFY_LABELS[s] || s; return '<span class="intel-badge v-' + esc(s || "unknown") + '">' + esc(l) + '</span>'; }
  function freshnessBadge(s) { const l = FRESH_LABELS[s] || s; return '<span class="intel-badge f-' + esc(s || "unknown") + '">' + esc(l) + '</span>'; }
  function freshnessNote(obj) {
    if (!obj) return "";
    const f = obj.freshness_status;
    if (f === "stale" || f === "aging") {
      const asof = obj.claim_valid_as_of || obj.current_status_verified_at || "较早年份";
      return '<p class="profile-standfirst"><span class="profile-standfirst-label">时效提示</span><span>当前状态尚未获得近期公开资料确认；以下内容依据截至 ' + esc(asof) + ' 年的公开资料整理。</span></p>';
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
  // UI HARD FIX A: human-readable status labels. Raw enums (e.g.
  // reported_activity_presence / freshness codes) must never surface verbatim.
  const STATUS_LABELS = {
    'current': '持续',
    'active': '活跃',
    'historical': '历史',
    // Expansion D status vocabulary (data presentation, not a UI redesign)
    'active_but_severely_degraded': '活跃但严重削弱',
    'active_anti_junta_rebellion': '活跃·反军政府叛乱',
    'active_and_expanding_cross_border': '活跃且跨境扩张',
    'tactical_coordination': '战术协同',
    // Expansion E status vocabulary (regional security actors, data presentation)
    'ceased_operations': '停止运作',
    'closed_2023': '已结束（2023）',
    'active_framework': '活跃框架·力量生成中',
    'active_operationalizing': '活跃·组建中',
    'active_conflict': '持续冲突',
    'active_armed_conflict': '持续武装冲突',
    'active_counterinsurgency_conflict': '持续反恐冲突',
    'active_joint_operation': '持续联合行动',
    'active_joint_operations_and_transition': '持续联合行动与过渡',
    'active_intra_jihadist_rivalry': '持续圣战派系竞争',
    'current_activity_presence': '活跃存在',
    'reported_activity_presence': '据报存在活动',
    'reported_leadership_status': '据报保持领导地位',
    'reported_current_affiliation': '据报当前隶属',
    'reported_current_hostility': '据报当前敌对',
    'reported_current_branch_recognition': '据报当前分支地位',
    'reported_wartime_alignment': '据报战时结盟',
    'reported_reporting_relationship': '据报隶属汇报关系',
    'reported_constituent_unit': '据报组成单位',
    'reported_senior_figure': '据报高级人物',
    'reported_pledge_with_current_status_sensitive': '据报宣誓效忠（时效敏感）',
    'reported_network_relation': '据报网络关联',
    'reported_finance_leadership': '据报财务领导角色',
    'reported_senior_leader': '据报高级领导',
    'reported_support_relationship': '据报支持关系',
    'reported_commandership': '据报指挥关系',
    'reduced_presence': '存在减弱',
    'intermittent_or_reduced': '时断时续或减弱',
    'emerging_limited_presence': '新兴有限存在',
    'colocated_and_organizationally_linked': '同驻且有组织关联',
    'civilian_protection_countering': '平民保护与反制',
    'context_dependent_cooperation': '视情合作',
    'political_military_rivalry_under_2020_ceasefire': '2020停火下政军竞争',
    'residual_security_hostility_after_historical_combat': '历史交战后残余安全敌对',
    'current_operational_cooperation_after_historical_conflict': '历史冲突后当前行动合作',
    'current_hostility_after_historical_darfur_association': '历史关联后当前敌对',
    'detained_leader_with_fragmented_acting_command': '领导人被拘·指挥碎片化',
    'current_hostility': '当前敌对',
    'current_hostility_expanding_geographically': '当前敌对且地域扩张',
    'current_political_military_cooperation': '当前政军合作',
    'historical_formation': '历史形成',
    'historical_ended': '历史·已终结',
    'historical_or_aging': '历史或趋旧',
    'historical_constituent_relation': '历史组成关系',
    'historical_founder_relation': '历史创始关系',
    'historical_association': '历史关联',
    'historical_to_recent': '历史至近期',
    'historical_splinter_relation': '历史分裂关系',
    'historical_lineage': '历史谱系',
    'historical_alignment_then_current_affiliation': '历史结盟转当前隶属',
    'historical_staged_integration': '历史分阶段整合',
    'historical_predecessor_network': '历史前驱网络',
    'historical_precursor_fusion': '历史前驱融合',
    'historical_merger_lineage': '历史合并谱系',
    'historical_splinter': '历史分裂',
    'historical_activity': '历史活动',
    'historical_transition': '历史过渡',
    'historical_cooperation_2021_to_2024': '2021—2024历史合作',
    'historical_member_2021_to_2024': '2021—2024历史成员关系',
    'historical_pledge_recognition_shifted_to_iswap': '历史效忠认可转至ISWAP',
    'historical_nonhostility_and_limited_cooperation_2016_2019': '2016—2019非敌对有限合作',
    'structural_current': '结构性现状',
    'historical_to_structural': '历史转结构性',
    'active_network': '活跃网络',
    'active_state_force': '活跃国家力量',
    'active_reemerging': '活跃·重新抬头',
    'active_but_under_pressure': '活跃但承压',
    'active_jnim_constituent': 'JNIM组成力量',
    'active_armed_group_us_designated': '武装组织（美方认定）',
    'active_al_qaida_affiliate_in_east_africa': '基地组织东非活跃分支',
    'active_al_qaida_affiliate_with_sahel_branch_link': '基地组织活跃分支·与萨赫勒分支关联',
    'active_islamic_state_sahel_branch': '伊斯兰国萨赫勒活跃分支',
    'active_islamic_state_west_africa_branch': '伊斯兰国西非活跃分支',
    'active_islamic_state_central_africa_branch': '伊斯兰国中部非洲活跃分支',
    'active_islamic_state_regional_coordination_node': '伊斯兰国区域协调节点',
    'active_islamic_state_mozambique_province_with_cabo_delgado_enclave': '伊斯兰国莫桑比克省·占据德尔加杜角',
    'active_reduced_but_resilient_islamic_state_branch': '伊斯兰国分支·减弱但坚韧',
    'contested_label_increasingly_linked_to_is_sahel': '标签存争议·与伊斯兰国萨赫勒关联增强',
    'integrated_jnim_constituent_retaining_local_identity': '已并入JNIM·保留本地身份',
    'partly_absorbed_into_fla_formation_network': '部分并入FLA组建网络',
    'fragmented_with_fla_linkage': '碎片化·与FLA关联',
    'historical_absorbed_into_al_qaida': '历史·已并入基地组织',
    'historical_largely_defunct': '历史·大体瓦解',
    'historical_dissolved_or_absorbed_as_independent_network': '历史·已解散或被吸收',
    'historical_severely_disrupted': '历史·严重瓦解',
    'historical_disintegrated_as_coherent_organization': '历史·作为整体已解体',
    'historical_defunct_as_coherent_movement': '历史·作为整体已消亡',
    'historical_absorbed_into_isis_libya_precursor_ecosystem': '历史·并入伊斯兰国利比亚前驱体系',
    'historical_absorbed_into_murabitun_and_jnim_network': '历史·并入穆拉比通与JNIM网络',
    'historical_mission_ended_2024_07_15': '历史任务·2024年7月结束',
    'historical_mali_deployment_ended_2025_06': '历史部署·2025年6月结束',
    'historical_predecessor_with_jnim': '历史前驱·与JNIM有关',
    'historical_predecessor_with_splinter_history': '历史前驱·含分裂史',
    'deceased_2017': '已故·2017',
    'merged_into_fla_formation_network': '已并入FLA组建网络',
    'active_and_expanding_across_west_africa': '活跃·在西非扩张',
    'active_jnim_constituent_and_core_central_mali_subgroup': 'JNIM组成力量·马里中部核心分支',
    'active_jnim_amir_at_large': 'JNIM领导·在逃',
    'active_jnim_deputy_and_katiba_macina_emir': 'JNIM副手兼马西纳旅埃米尔',
    'active_fragmented_jas_constellation': '碎片化JAS集团',
    'active_al_shabaab_emir': '青年党埃米尔·在位',
    'active_isis_somalia_founder_and_al_karrar_leader': 'ISIS-Somalia创始人兼卡尔拉尔领导',
    'active_isis_somalia_leader': 'ISIS-Somalia领导人',
    'active_adf_isis_ca_overall_leader': 'ADF/IS-CA最高领导人',
    'active_al_shabaab_finance_and_amniyat_chief': '青年党财务与情报主管',
    'active_iss_finance_office_head': 'ISS财务主管',
    'active_adf_senior_leader': 'ADF高级领导',
    'reported_jnim_emir_for_niger': '据报为JNIM尼日尔埃米尔',
    'reported_defector_to_is_sahel': '据报投奔伊斯兰国萨赫勒',
    'reported_jnim_northwest_niger_operations_leader': '据报为JNIM尼日尔西北行动领导',
    'reported_dana_atem_leader': '据报为达纳阿特姆领导',
    'reported_dozos_of_macina_leader': '据报为马西纳多佐领导',
    'reported_dan_na_ambassagou_leader': '据报为丹纳安巴萨古领导',
    'jnim_burkina_leader_top_commander': 'JNIM布基纳法索领导',
    'jnim_burkina_deputy_commander': 'JNIM布基纳法索副指挥',
    'active_in_mali_burkina_borderlands': '活跃于马里—布基纳边境',
    'reduced_and_partially_demobilized_self_defense_network': '削弱且部分复员的联防网络',
    'listed_by_eu_sudanese_islamist_movement_secretary_general': '欧盟列名·苏丹伊斯兰运动总书记',
    'listed_by_eu_bbmb_commander': '欧盟列名·BBMB指挥官'
  };
  const STATUS_PREFIX = { reported: "据报", historical: "历史", active: "活跃", current: "当前" };
  const STATUS_LOW = { and: 1, or: 1, with: 1, in: 1, of: 1, under: 1, for: 1, to: 1, on: 1, the: 1 };
  function statusLabel(s) {
    if (s == null || s === "") return "未说明";
    if (STATUS_LABELS[s]) return STATUS_LABELS[s];
    const seg = String(s).split("_").filter(Boolean);
    if (!seg.length) return String(s);
    const pre = STATUS_PREFIX[seg[0]];
    const rest = seg.slice(1).map(function (w) { return STATUS_LOW[w] ? w : w.charAt(0).toUpperCase() + w.slice(1); }).join(" ");
    return (pre ? pre + " · " : "") + (rest || String(s));
  }
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
  // UI/UX V2 shared helpers (presentation-only).
  function uniq(arr) { return arr.filter(function (x, i) { return arr.indexOf(x) === i; }); }
  function sourceCategory(s) {
    const t = s.source_type || "";
    const rl = s.reliability || "";
    if (t.indexOf("official_") === 0 || ["government", "government_report", "government_profile", "government_factsheet", "sanctions_action", "sanctions_profile", "sanctions_list", "sanctions_listing", "official_counterterrorism_profile", "military_press_release", "primary_agreement_archive", "primary_document_archive", "primary_self_source", "actor_self_publication"].indexOf(t) >= 0) return "authoritative_official";
    if (["un_report", "un_resolution", "un_panel_report", "un_mission_report", "un_monitoring_report", "un_secretary_general_report", "un_statement", "un_factsheet", "un_sanctions_listing", "un_experts_report", "official_un_statement", "official_un_mission_statement", "official_un_briefing", "official_un_mission_framework", "official_au_communique", "official_au_decision", "official_au_statement", "regional_org", "regional_organization", "international_organization_statement", "international_report", "mission_report", "official_mission_page", "official_mission_news"].indexOf(t) >= 0) return "international_org";
    if (["research_analysis", "research_institute", "research_report", "conflict_analysis", "current_analysis", "security_brief", "security_council_analysis", "actor_analysis", "actor_profile", "methodology_and_actor_history", "country_current_profile", "ngo_analysis", "ngo_report", "human_rights_investigation", "human_rights_current_update", "expert_comment"].indexOf(t) >= 0 || rl === "research_institution" || rl === "research_dataset") return "research_institutional";
    if (["newswire", "newswire_investigation", "newswire_explainer", "newswire_feature", "newswire_on_un_investigation", "media", "news_media"].indexOf(t) >= 0 || rl === "news_media") return "media_other";
    return "other";
  }
  const SOURCE_CAT_LABELS = { authoritative_official: "官方权威来源", international_org: "国际组织来源", research_institutional: "研究机构来源", media_other: "媒体与其他", other: "其他来源" };
  function relIsDisputed(r) { return !!(r.disputed || r.confidence === "disputed" || (store.relationProfiles[r.relationship_id] || {}).disputed); }
  function relIsHistorical(r) { return String(r.current_status || "").indexOf("historical") >= 0 || r.freshness_status === "historical"; }

  // ============================================================
  // UI/UX V2 Fix-1: exact canonical/alias auto-linking.
  // Presentation-only. Matches ONLY known canonical names /
  // registered aliases from the existing entity index + alias_index;
  // longest-name-first, boundary-checked, denylisted, ambiguity-safe.
  // No fuzzy / substring / semantic guessing, no data modification.
  // ============================================================
  const AUTO_LINK_DENYLIST = {
    "is": 1, "the": 1, "in": 1, "of": 1, "a": 1, "an": 1, "and": 1, "for": 1,
    "on": 1, "at": 1, "to": 1, "da": 1, "de": 1, "di": 1, "al": 1, "el": 1,
    "la": 1, "le": 1, "les": 1, "des": 1, "du": 1, "au": 1, "aux": 1, "ibn": 1,
    "bin": 1, "bint": 1, "abu": 1, "abd": 1, "ben": 1, "the": 1, "state": 1,
    "movement": 1, "force": 1, "forces": 1, "front": 1, "army": 1
  };
  let AUTO_LINK_NAMES = [];
  function buildAutoLinkIndex() {
    const seen = {};
    const add = function (name, e) {
      if (!name || typeof name !== "string") return;
      name = name.trim();
      if (name.length < 2) return;
      const key = name.toLowerCase();
      if (AUTO_LINK_DENYLIST[key]) return;
      if (/^\d+$/.test(key)) return;
      if (!seen[key]) seen[key] = { name: name, entity: e, kind: e._autolinkKind || "entity", ambiguous: false };
      else if (seen[key].entity && seen[key].entity.entity_id !== e.entity_id) seen[key].ambiguous = true;
    };
    store.entities.forEach(function (e) {
      add(e.name_zh, e);
      add(e.name_en, e);
      add(e.acronym, e);
      add(e.native_name, e);
      (e.aliases || []).forEach(function (a) { add(a, e); });
    });
    Object.keys(store.aliases || {}).forEach(function (a) {
      const e = store.byEntityId[store.aliases[a]];
      if (e) add(a, e);
    });
    // UI FINAL POLISH 1: region nodes also linkable from prose (exact name match only).
    store.regions.forEach(function (r) {
      add(r.name_zh, Object.assign({}, r, { entity_id: r.region_id, _autolinkKind: "region", slug: r.slug, name_en: r.name_en, aliases: [] }));
    });
    const list = [];
    Object.keys(seen).forEach(function (key) {
      const v = seen[key];
      if (v.ambiguous) return;                 // ambiguity protection: skip conflicted aliases
      const isCJK = /[\u4e00-\u9fff]/.test(v.name);
      if (v.name.length < (isCJK ? 2 : 3)) return;  // too-short guard (non-CJK >= 3 chars)
      list.push({ key: key, name: v.name, entity: v.entity });
    });
    // longest-name-first so "ISIS-Somalia" wins over "ISIS"
    list.sort(function (a, b) { return b.name.length - a.name.length; });
    AUTO_LINK_NAMES = list;
  }
  function autoLinkExact(text) {
    if (!text || !AUTO_LINK_NAMES.length) return text == null ? "" : String(text);
    // protect URLs first (never link entity names inside URLs)
    const urls = [];
    let t = String(text).replace(/(?:https?:\/\/|www\.)[^\s<>"'()]+|\b(?:[a-z0-9-]+\.){2,}[a-z]{2,}(?:\/[^\s<>"'()]*)?/gi, function (m) { urls.push(m); return "\u0000U" + (urls.length - 1) + "\u0000"; });
    // protect machine ids (actor-*/rel-*/country-* etc, hyphens included) from substring hits
    const ids = [];
    t = t.replace(/\b(?:actor|rel|country|region|person|claim|evidence|source|ev)-[a-z0-9_-]+/gi, function (m) { ids.push(m); return "\u0000I" + (ids.length - 1) + "\u0000"; });
    const n = t.length;
    const alpha = /[A-Za-z0-9]/;
    const nameStart = /[A-Za-z0-9\u4e00-\u9fff]/;
    let out = "";
    let i = 0;
    while (i < n) {
      const ch = t[i];
      if (ch === "\u0000") { out += ch; i++; continue; }
      if (!nameStart.test(ch)) { out += ch; i++; continue; }
      const rem = n - i;
      let hit = null;
      for (let k = 0; k < AUTO_LINK_NAMES.length; k++) {
        const cand = AUTO_LINK_NAMES[k];
        if (cand.name.length > rem) continue;
        if (t.slice(i, i + cand.name.length).toLowerCase() !== cand.key) continue;
        const isCJK = /[\u4e00-\u9fff]/.test(cand.name);
        if (!isCJK) {
          const before = i > 0 ? t[i - 1] : "";
          const after = i + cand.name.length < n ? t[i + cand.name.length] : "";
          if ((before && alpha.test(before)) || (after && alpha.test(after))) continue;
        }
        hit = cand;
        break;
      }
      if (hit) {
        const href = hit.entity._autolinkKind === "region" ? regionHref(hit.entity.entity_id) : entityHref(hit.entity.entity_id);
        out += '<a class="intel-entity-link auto" href="' + esc(href) + '">' + esc(t.slice(i, i + hit.name.length)) + '</a>';
        i += hit.name.length;
      } else {
        out += ch;
        i++;
      }
    }
    out = out.replace(/\u0000U(\d+)\u0000/g, function (m, d) { return urls[+d]; });
    out = out.replace(/\u0000I(\d+)\u0000/g, function (m, d) { return ids[+d]; });
    return out;
  }
  // relation-page text renderer: explicit [[...]] markers first (existing
  // inlineLinks renderer, already-linked content is never re-linked), then
  // exact auto-linking on the remaining plain segments.
  function renderRelationText(text) {
    if (text == null) return "";
    return String(text).split(/(\[\[(?:entity|country|region|relation):[^|\]]+\|[^\]]*\]\])/g).map(function (seg) {
      if (seg.indexOf("[[") === 0) return inlineLinks(seg);
      return autoLinkExact(seg);
    }).join("");
  }
  function entityLink(id, label) { const e = store.byEntityId[id]; if (!e) return esc(label || id); return '<a class="intel-entity-link" href="' + esc(entityHref(id)) + '">' + esc(label || title(e)) + '</a>'; }
  // I3-D1: relation endpoints may reference a region (e.g. rel-d1-fu-aes-region -> region-central-sahel);
  // titleFor() falls back to the region display name or the raw id instead of calling title(undefined).
  function titleFor(id) { const e = store.byEntityId[id]; if (e) return title(e); const r = store.byRegionId[id]; if (r) return r.name_zh; return id; }
  function countryLink(id) { const c = store.byCountryId[id]; return c ? '<a class="intel-entity-link" href="' + esc(countryHref(id)) + '">' + esc(c.name_zh) + '</a>' : esc(id); }
  function regionLink(id) { const r = store.byRegionId[id]; return r ? '<a class="intel-entity-link" href="' + esc(regionHref(id)) + '">' + esc(r.name_zh) + '</a>' : esc(id); }
  function sourceLink(id) { const s = store.sources.find(function (x) { return x.source_id === id; }); return s ? '<a target="_blank" rel="noopener noreferrer" href="' + esc(s.url) + '">' + esc(s.publisher) + '</a>' : esc(id); }
  function sourceList(ids) { return (ids || []).map(sourceLink).join(" · "); }
  function evidenceCountFor(ids) { return store.evidence.filter(function (ev) { return (ev.entity_ids || []).some(function (x) { return ids.indexOf(x) >= 0; }) || (ev.relation_ids || []).some(function (x) { return ids.indexOf(x) >= 0; }); }).length; }
  function importanceBadge(e) { return '<span class="intel-badge imp-' + esc(e.importance_level || "L3") + '">' + esc(impLabel(e.importance_level)) + '</span>'; }
  function riskBadge(c) { return '<span class="intel-badge risk-' + esc(c.risk_level || "medium") + '">' + esc(riskLabel(c.risk_level)) + '</span>'; }
  function typeBadge(e) { return '<span class="intel-badge type-entity">' + esc(typeLabel(e.primary_type || e.entity_type)) + '</span>'; }
  function entityCard(e) { const rels = store.relationships.filter(function (r) { return r.source_entity_id === e.entity_id || r.target_entity_id === e.entity_id; }); return '<a class="intel-card" href="' + esc(entityHref(e.entity_id)) + '"><div class="intel-card-top"><span class="intel-code">' + esc(e.entity_id) + '</span>' + typeBadge(e) + '</div><div class="intel-card-title-row"><h3>' + esc(title(e)) + '</h3><span class="intel-level-mini">' + esc(e.importance_level || "L3") + '</span></div><p class="intel-en">' + esc(e.name_en) + '</p><p>' + esc(e.short_description) + '</p><div class="intel-card-foot"><span>' + rels.length + ' 条直接关系</span><span>证据 ' + evidenceCountFor([e.entity_id]) + '</span></div></a>'; }
  function countryCard(c) { const chips = (c.region_ids || []).map(function (rid) { const r = store.byRegionId[rid]; return r ? '<a class="intel-region-chip" href="' + esc(regionHref(rid)) + '">' + esc(r.name_zh) + '</a>' : esc(rid); }).join(""); return '<a class="intel-card" href="' + esc(countryHref(c.country_id)) + '"><div class="intel-card-top"><span class="intel-code">' + esc(c.iso_alpha3 || c.country_id) + '</span>' + riskBadge(c) + '</div><h3>' + esc(c.name_zh) + '</h3><p class="intel-en">' + esc(c.name_en) + '</p><span class="intel-code-sm">' + esc(c.country_id) + '</span><div class="intel-region-chips">' + (chips || '<span class="intel-region-chip">未说明</span>') + '</div><p class="intel-country-summary">' + esc(c.risk_level_reason || "国家安全风险分析入口。") + '</p></a>'; }
  function regionCard(r) { return '<a class="intel-card" href="' + esc(regionHref(r.region_id)) + '"><div class="intel-card-top"><span class="intel-code">' + esc(r.region_id) + '</span></div><h3>' + esc(r.name_zh) + '</h3><p class="intel-en">' + esc(r.name_en) + '</p><p>' + esc((r.definition || "").slice(0, 90)) + '…</p></a>'; }
  function renderTopbar() { const t = document.querySelector("#topbar"); if (t) { const home = ROOT.indexOf("/intelligence/") >= 0 ? ROOT.slice(0, ROOT.indexOf("/intelligence/")) + "index.html" : "../../index.html"; t.innerHTML = '<div class="intel-topbar"><div><a class="intel-back" href="' + esc(ROOT) + '">← ASIP非洲安全情报知识库</a><span class="intel-kicker">Stage 8A 导航整合 · 数据截至 2026-08-06</span></div><div class="intel-topmeta"><a href="' + esc(home) + '">平台首页</a> · 统一数据底座 · 已接入正式导航</div></div>'; } }
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
  function initEntities() {
    const g = document.getElementById("allEntities"); if (!g) return;
    const ents = store.entities.filter(function (e) { return !e.entity_id.startsWith("country-"); });
    const P_ = { q: "entityQ", type: "entityType", imp: "entityImp", status: "entityStatus", region: "entityRegion", maturity: "entityMaturity", sort: "entitySort" };
    function readState() {
      const p = new URLSearchParams(window.location.search);
      return { q: (p.get(P_.q) || "").toLowerCase(), type: p.get(P_.type) || "", imp: p.get(P_.imp) || "", status: p.get(P_.status) || "", region: p.get(P_.region) || "", maturity: p.get(P_.maturity) || "", sort: p.get(P_.sort) || "importance" };
    }
    let st = readState();
    function fillSel(id, opts, val) {
      const el = document.getElementById(id); if (!el) return;
      el.innerHTML = opts; el.value = val;
    }
    fillSel("entityTypeFilter", '<option value="">全部类型</option>' + Object.keys(TYPE_LABELS).map(function (t) { return '<option value="' + esc(t) + '">' + esc(TYPE_LABELS[t]) + '</option>'; }).join(""), st.type);
    fillSel("entityImpFilter", '<option value="">全部重要程度</option>' + ["L1", "L2", "L3"].map(function (l) { return '<option value="' + l + '">' + esc(impLabel(l)) + '</option>'; }).join(""), st.imp);
    fillSel("entityStatusFilter", '<option value="">全部状态</option>' + uniq(ents.map(function (e) { return e.current_status; }).filter(Boolean)).sort().map(function (x) { return '<option value="' + esc(x) + '">' + esc(x) + '</option>'; }).join(""), st.status);
    fillSel("entityRegionFilter", '<option value="">全部区域</option>' + store.regions.map(function (r) { return '<option value="' + esc(r.region_id) + '">' + esc(r.name_zh) + '</option>'; }).join(""), st.region);
    fillSel("entityMaturityFilter", '<option value="">全部档案深度</option>' + ["E0_STUB", "E1_BASIC", "E2_DEVELOPED", "E3_FULL_ENCYCLOPEDIA"].map(function (m) { return '<option value="' + m + '">' + esc(MATURITY_LABELS[m] || m) + '</option>'; }).join(""), st.maturity);
    fillSel("entitySort", '<option value="importance">按重要程度</option><option value="name">按名称</option><option value="verified">按最后核验</option><option value="rels">按关系数</option>', st.sort);
    function maturityOf(e) { const pr = store.entityProfiles[e.entity_id] || {}; return pr.content_maturity || pr.profile_depth || ""; }
    function relCountOf(id) { let n = 0; store.relationships.forEach(function (r) { if (r.source_entity_id === id || r.target_entity_id === id) n++; }); return n; }
    function matches(e) {
      if (st.q) {
        const hay = [e.entity_id, e.slug, e.name_zh, e.name_en, e.acronym || "", e.native_name || ""].concat(e.aliases || []).join(" ").toLowerCase();
        if (hay.indexOf(st.q) < 0) return false;
      }
      if (st.type && (e.primary_type || e.entity_type) !== st.type) return false;
      if (st.imp && (e.importance_level || "L3") !== st.imp) return false;
      if (st.status && (e.current_status || "") !== st.status) return false;
      if (st.region && (e.region_ids || []).indexOf(st.region) < 0) return false;
      if (st.maturity && maturityOf(e) !== st.maturity) return false;
      return true;
    }
    function sortFn(a, b) {
      if (st.sort === "name") return (a.name_zh || "").localeCompare(b.name_zh || "", "zh");
      if (st.sort === "verified") return String(b.last_verified_at || b.record_reviewed_at || "").localeCompare(String(a.last_verified_at || a.record_reviewed_at || ""));
      if (st.sort === "rels") return relCountOf(b.entity_id) - relCountOf(a.entity_id);
      const order = { L1: 0, L2: 1, L3: 2 };
      return (order[a.importance_level || "L3"] - order[b.importance_level || "L3"]) || (a.name_zh || "").localeCompare(b.name_zh || "", "zh");
    }
    function render() {
      const list = ents.filter(matches).sort(sortFn);
      const cnt = document.getElementById("entityCount");
      if (cnt) cnt.textContent = "当前结果 " + list.length + " / 总计 " + ents.length;
      g.innerHTML = list.length ? list.map(entityCard).join("") : '<div class="list-empty">没有符合条件的实体。请调整搜索或筛选条件。</div>';
    }
    function push() {
      const p = new URLSearchParams();
      if (st.q) p.set(P_.q, st.q);
      if (st.type) p.set(P_.type, st.type);
      if (st.imp) p.set(P_.imp, st.imp);
      if (st.status) p.set(P_.status, st.status);
      if (st.region) p.set(P_.region, st.region);
      if (st.maturity) p.set(P_.maturity, st.maturity);
      if (st.sort && st.sort !== "importance") p.set(P_.sort, st.sort);
      const u = new URL(window.location.href); u.search = p.toString();
      window.history.pushState({}, "", u);
    }
    const searchEl = document.getElementById("entityListSearch");
    let debounceT = null;
    if (searchEl) searchEl.addEventListener("input", function () {
      st.q = searchEl.value.trim().toLowerCase();
      render();
      if (debounceT) clearTimeout(debounceT);
      debounceT = setTimeout(push, 350);
    });
    [
      ["entityTypeFilter", function (v) { st.type = v; }],
      ["entityImpFilter", function (v) { st.imp = v; }],
      ["entityStatusFilter", function (v) { st.status = v; }],
      ["entityRegionFilter", function (v) { st.region = v; }],
      ["entityMaturityFilter", function (v) { st.maturity = v; }],
      ["entitySort", function (v) { st.sort = v; }]
    ].forEach(function (pair) {
      const el = document.getElementById(pair[0]);
      if (el) el.addEventListener("change", function () { pair[1](el.value); render(); push(); });
    });
    window.addEventListener("popstate", function () { st = readState(); render(); });
    if (searchEl) searchEl.value = st.q;
    render();
  }
  function initRelations() {
    const g = document.getElementById("relationList"); if (!g) return;
    const P_ = { q: "relQ", type: "relType", status: "relStatus", maturity: "relMaturity", disputed: "relDisputed", ts: "relTimeSensitive" };
    function readState() {
      const p = new URLSearchParams(window.location.search);
      return { q: (p.get(P_.q) || "").toLowerCase(), type: p.get(P_.type) || "", status: p.get(P_.status) || "", maturity: p.get(P_.maturity) || "", disputed: p.get(P_.disputed) === "1", ts: p.get(P_.ts) === "1" };
    }
    let st = readState();
    const relTypes = uniq(store.relationships.map(function (r) { return r.relationship_type; })).sort();
    const matOpts = ['<option value="">全部档案深度</option>'].concat(["R0_EDGE_ONLY", "R1_BASIC", "R2_DEVELOPED_RELATIONSHIP", "R3_FULL_RELATIONSHIP_INTELLIGENCE"].map(function (m) { return '<option value="' + m + '">' + esc(MATURITY_LABELS[m] || m) + '</option>'; })).join("");
    function fillSel(id, opts, val) { const el = document.getElementById(id); if (!el) return; el.innerHTML = opts; el.value = val; }
    fillSel("relTypeFilter", '<option value="">全部关系类型</option>' + relTypes.map(function (t) { return '<option value="' + esc(t) + '">' + esc(relLabel(t)) + '</option>'; }).join(""), st.type);
    fillSel("relMaturityFilter", matOpts, st.maturity);
    function maturityOf(r) { const pr = store.relationProfiles[r.relationship_id] || store.relationProfiles[r.slug] || null; return pr ? (pr.relation_maturity || "") : ""; }
    function hay(r) {
      const s2 = store.byEntityId[r.source_entity_id], t2 = store.byEntityId[r.target_entity_id];
      const parts = [r.relationship_id, r.slug || ""];
      [s2, t2].forEach(function (e) { if (e) parts.push(e.name_zh, e.name_en, e.acronym || "", e.entity_id, e.native_name || ""); if (e && e.aliases) parts.push.apply(parts, e.aliases); });
      return parts.join(" ").toLowerCase();
    }
    function matches(r) {
      if (st.q && hay(r).indexOf(st.q) < 0) return false;
      if (st.type && r.relationship_type !== st.type) return false;
      if (st.status === "historical" && !relIsHistorical(r)) return false;
      if (st.status === "current" && relIsHistorical(r)) return false;
      if (st.maturity && maturityOf(r) !== st.maturity) return false;
      if (st.disputed && !relIsDisputed(r)) return false;
      if (st.ts && !(r.temporal_sensitive || r.freshness_status === "aging" || r.freshness_status === "stale")) return false;
      return true;
    }
    function row(r) {
      const s2 = store.byEntityId[r.source_entity_id], t2 = store.byEntityId[r.target_entity_id];
      const dis = relIsDisputed(r) ? ' <span class="intel-badge disputed">争议</span>' : "";
      return '<div class="intel-rel-row"><div class="intel-rel-main"><span class="intel-rel-kind">' + esc(relLabel(r.relationship_type)) + '</span> ' + entityLink(r.source_entity_id, s2 ? title(s2) : r.source_entity_id) + ' <b>' + (r.direction === "bidirectional" ? "↔" : "→") + '</b> ' + entityLink(r.target_entity_id, t2 ? title(t2) : r.target_entity_id) + ' <a class="intel-rel-archive" href="' + esc(relationHref(r.relationship_id)) + '">档案 →</a>' + dis + '</div><div class="intel-rel-desc">' + esc(r.relation_summary || "") + '</div><div class="intel-rel-meta">时间：' + esc(period(r)) + ' · 状态：' + esc(statusLabel(r.current_status)) + ' · 可信度：' + esc(confLabel(r.confidence)) + '</div></div>';
    }
    function render() {
      const list = store.relationships.filter(matches);
      const cnt = document.getElementById("relCount");
      if (cnt) cnt.textContent = "当前结果 " + list.length + " / 总计 " + store.relationships.length;
      g.innerHTML = list.length ? list.map(row).join("") : '<div class="list-empty">没有符合条件的关系。请调整搜索或筛选条件。</div>';
    }
    function push() {
      const p = new URLSearchParams();
      if (st.q) p.set(P_.q, st.q);
      if (st.type) p.set(P_.type, st.type);
      if (st.status) p.set(P_.status, st.status);
      if (st.maturity) p.set(P_.maturity, st.maturity);
      if (st.disputed) p.set(P_.disputed, "1");
      if (st.ts) p.set(P_.ts, "1");
      const u = new URL(window.location.href); u.search = p.toString();
      window.history.pushState({}, "", u);
    }
    const searchEl = document.getElementById("relListSearch");
    let debounceT = null;
    if (searchEl) searchEl.addEventListener("input", function () {
      st.q = searchEl.value.trim().toLowerCase();
      render();
      if (debounceT) clearTimeout(debounceT);
      debounceT = setTimeout(push, 350);
    });
    [
      ["relTypeFilter", function (v) { st.type = v; }],
      ["relStatusFilter", function (v) { st.status = v; }],
      ["relMaturityFilter", function (v) { st.maturity = v; }]
    ].forEach(function (pair) {
      const el = document.getElementById(pair[0]);
      if (el) el.addEventListener("change", function () { pair[1](el.value); render(); push(); });
    });
    const dEl = document.getElementById("relDisputedOnly");
    if (dEl) { dEl.checked = st.disputed; dEl.addEventListener("change", function () { st.disputed = dEl.checked; render(); push(); }); }
    const tEl = document.getElementById("relTimeSensitive");
    if (tEl) { tEl.checked = st.ts; tEl.addEventListener("change", function () { st.ts = tEl.checked; render(); push(); }); }
    window.addEventListener("popstate", function () { st = readState(); render(); });
    if (searchEl) searchEl.value = st.q;
    render();
  }
  function initSources() {
    const g = document.getElementById("sourceGrid"); if (!g) return;
    const groups = {};
    store.sources.forEach(function (src) { const c = sourceCategory(src); (groups[c] = groups[c] || []).push(src); });
    const order = ["authoritative_official", "international_org", "research_institutional", "media_other", "other"];
    const evCount = function (sid) { return store.evidence.filter(function (ev) { return ev.source_id === sid; }).length; };
    g.innerHTML = order.map(function (c) {
      const items = groups[c] || [];
      if (!items.length) return "";
      return '<details class="source-group" open><summary>' + esc(SOURCE_CAT_LABELS[c] || c) + '（' + items.length + '）</summary><div class="source-group-items">' +
        items.map(function (src) {
          return '<a target="_blank" rel="noopener noreferrer" href="' + esc(src.url) + '"><b>' + esc(src.title) + '</b><span>' + esc(src.publisher) + ' · ' + esc(src.published_at || "未标注") + '</span><span>' + esc(src.source_type || "") + (src.reliability ? ' · ' + esc(src.reliability) : '') + ' · 证据 ' + evCount(src.source_id) + ' 条</span></a>';
        }).join("") + '</div></details>';
    }).join("");
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
      core_conflicts: region.core_topics, relationships: region.key_cross_border_relations.map(function (rid) { const r = store.byRelId[rid]; return r ? entityLink(r.source_entity_id, titleFor(r.source_entity_id)) + " " + esc(relLabel(r.relationship_type)) + " " + entityLink(r.target_entity_id, titleFor(r.target_entity_id)) : esc(rid); }),
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
    // I3-A/B: country lead (导语) rendered above the section body
    if (profile.lead) {
      const cb = document.querySelector("#countryBody");
      if (cb) {
        const paras = Array.isArray(profile.lead) ? profile.lead : [profile.lead];
        const leadHtml = '<div class="profile-lead">' + paras.map(function (x) { return '<p>' + inlineLinks(esc(x)) + '</p>'; }).join("") + '</div>';
        cb.innerHTML = leadHtml + cb.innerHTML;
      }
    }
    const actors = document.querySelector("#countryActors"); if (actors) actors.innerHTML = country.main_actors.map(function (id) { const e = store.byEntityId[id]; return e ? entityCard(e) : ""; }).join("");
    const rels = store.relationships.filter(function (r) { return country.main_actors.indexOf(r.source_entity_id) >= 0 || country.main_actors.indexOf(r.target_entity_id) >= 0 || r.source_entity_id === country.country_id || r.target_entity_id === country.country_id; });
    const rl = document.querySelector("#countryRelations"); if (rl) rl.innerHTML = rels.slice(0, 12).map(function (r) { return '<div class="intel-rel-row"><div class="intel-rel-main">' + entityLink(r.source_entity_id, titleFor(r.source_entity_id)) + ' <b>↔</b> ' + entityLink(r.target_entity_id, titleFor(r.target_entity_id)) + ' <span class="intel-rel-kind">' + esc(relLabel(r.relationship_type)) + '</span>' + freshnessBadge(r.freshness_status) + '</div></div>'; }).join("");
    const ev = document.querySelector("#countryEvidence"); if (ev) ev.innerHTML = '<div class="relationship-count">相关证据记录 ' + evidenceCountFor(country.main_actors.concat([country.country_id])) + ' 条</div>' + '<div class="ib-row"><dt>当前状态核验</dt><dd>' + esc(country.current_status_verified_at || "未单独核验") + '</dd></div><div class="ib-row"><dt>事实有效截至</dt><dd>' + esc(country.claim_valid_as_of || "未说明") + '</dd></div><p class="muted">证据通过 source_id 关联来源；' + esc(country.freshness_status === "stale" || country.freshness_status === "aging" ? "本页当前状态依赖较早来源，须谨慎解读。" : "关键事实见各关系与实体档案。") + '</p>';
  }
  function initEntity() {
    const slug = document.body.getAttribute("data-entity-slug");
    const entity = store.entities.find(function (e) { return e.slug === slug || e.entity_id === slug; });
    if (!entity) { const el = document.querySelector("#intelError"); if (el) { el.hidden = false; el.textContent = "实体不存在：" + slug; } return; }
    const profile = store.entityProfiles[entity.entity_id] || { sections: {} };
    document.title = title(entity) + " · ASIP非洲安全情报知识库";
    // UI/UX V2: h1 is the Chinese primary name (+acronym); the full English name
    // renders as its own second line. disputed entities carry an explicit
    // "身份/归属存在争议" badge generated from the existing disputed flag.
    const disBadge = entity.disputed ? '<span class="intel-badge disputed">身份/归属存在争议</span>' : '';
    const h = document.querySelector("#entityHeading"); if (h) h.innerHTML = '<div class="intel-heading-code">' + esc(entity.entity_id) + '</div><h1>' + esc(title(entity)) + '</h1><p class="intel-title-en">' + esc(entity.name_en) + '</p><div class="intel-badges">' + typeBadge(entity) + importanceBadge(entity) + maturityBadge(profile.content_maturity || entity.content_maturity) + '<span class="intel-badge status">' + esc(statusLabel(entity.current_status)) + '</span>' + freshnessBadge(entity.freshness_status) + disBadge + '</div>' + freshnessNote(entity);
    renderSections("#entityBody", profile.sections, { detachTail: true });
    // UI HARD FIX A: sources & notes always render at the very end of the entity
    // page (after body, direct relations and evidence) — never in the prose flow.
    const srcBox = document.querySelector("#entitySources");
    if (srcBox) {
      const sv = profile.sections || {};
      let sh = "";
      ["sources", "notes"].forEach(function (k) {
        const v = sv[k];
        if (v == null || (Array.isArray(v) && !v.length) || v === "") return;
        sh += '<section class="profile-section intel-source-notes" id="sec-' + esc(k) + '"><h2>' + esc(SECTION_LABELS[k]) + '</h2>' + renderBody(v) + '</section>';
      });
      if (sh) { srcBox.innerHTML = sh; } else { srcBox.remove(); }
    }
    // UI/UX V2: compact key-facts strip generated from existing data only.
    // Missing fields are simply omitted; nothing is invented.
    const kf = document.getElementById("entityKeyFacts");
    if (kf) {
      const relsE = store.relationships.filter(function (r) { return r.source_entity_id === entity.entity_id || r.target_entity_id === entity.entity_id; });
      let cells = [];
      const leadRels = relsE.filter(function (r) { return (r.relationship_type === "led_by" || r.relationship_type === "founded_by") && r.target_entity_id === entity.entity_id; });
      if (leadRels.length) cells.push({ label: "领导/核心人物", html: uniq(leadRels.map(function (r) { return entityLink(r.source_entity_id, titleFor(r.source_entity_id)); })).join("、") });
      const est = store.forceEstimates[entity.entity_id];
      if (est && est.length) cells.push({ label: "估计武装规模", html: est.map(function (x) { return esc(x.estimate_text) + "（" + esc(x.estimate_date) + "）"; }).join("；") });
      const ctry = (entity.country_ids || []).map(countryLink).join("、");
      if (ctry) cells.push({ label: "活动国家/地区", html: ctry });
      const regs = (entity.region_ids || []).map(regionLink).join("、");
      if (regs) cells.push({ label: "所属区域", html: regs });
      const affTypes = ["affiliated_with", "pledged_allegiance_to", "constituent_of", "part_of_network", "member_of_force"];
      const aff = relsE.filter(function (r) { return affTypes.indexOf(r.relationship_type) >= 0 && r.target_entity_id === entity.entity_id; }).map(function (r) { return entityLink(r.source_entity_id, titleFor(r.source_entity_id)); });
      if (aff.length) cells.push({ label: "归属/所属网络", html: uniq(aff).join("、") });
      const lv = entity.last_verified_at || entity.record_reviewed_at || entity.current_status_verified_at;
      if (lv) cells.push({ label: "最后核验", html: esc(lv) });
      if (cells.length) kf.innerHTML = cells.map(function (c) { return '<div><b>' + esc(c.label) + '</b><span>' + c.html + '</span></div>'; }).join("");
    }
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
    const rl = document.querySelector("#entityRelations"); if (rl) rl.innerHTML = rels.map(function (r) { const other = r.source_entity_id === entity.entity_id ? r.target_entity_id : r.source_entity_id; return '<div class="intel-rel-row"><div class="intel-rel-main"><span class="intel-rel-kind">' + esc(relLabel(r.relationship_type)) + '</span> ' + entityLink(other, titleFor(other)) + ' <a class="intel-rel-archive" href="' + esc(relationHref(r.relationship_id)) + '">档案 →</a></div><div class="intel-rel-meta">' + esc(period(r)) + ' · ' + esc(statusLabel(r.current_status)) + '</div></div>'; }).join("") || '<p class="muted">暂无直接关系。</p>';
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
    const st = titleFor(rel.source_entity_id), tt = titleFor(rel.target_entity_id);
    document.title = relLabel(rel.relationship_type) + "：" + st + "—" + tt;
    const disRelBadge = relIsDisputed(rel) ? '<span class="intel-badge disputed">关系状态存在争议</span>' : '';
    const techRows = [];
    techRows.push('<div class="tech-row">关系 ID：<code>' + esc(rel.relationship_id) + '</code></div>');
    if (rel.display_ring) techRows.push('<div class="tech-row">圈层：<code>' + esc(rel.display_ring) + '</code></div>');
    if (rel.freshness_status) techRows.push('<div class="tech-row">freshness_status：<code>' + esc(rel.freshness_status) + '</code></div>');
    if (rel.relationship_semantics_note) techRows.push('<div class="tech-row">语义说明：' + esc(rel.relationship_semantics_note) + '</div>');
    if (profile && profile.relation_maturity) techRows.push('<div class="tech-row">档案成熟度：<code>' + esc(profile.relation_maturity) + '</code></div>');
    const techDetails = techRows.length ? '<details class="rel-tech-details"><summary>技术元数据（展开）</summary><div class="rel-tech-body">' + techRows.join("") + '</div></details>' : '';
    const h = document.querySelector("#relationHeading");
    if (h) h.innerHTML = '<h1 class="rel-hero-title">' + esc(st) + ' <span class="rel-arrow">↔</span> ' + esc(tt) + '</h1><p class="intel-title-en">' + esc(relLabel(rel.relationship_type)) + ' · ' + esc(statusLabel(rel.current_status)) + '</p><div class="intel-badges">' + maturityBadge(profile ? profile.relation_maturity : null) + freshnessBadge(rel.freshness_status) + disRelBadge + '</div>' + freshnessNote(rel) + techDetails;
    // UI/UX V2: relation hero — Party A card → summary → Party B card.
    // Desktop renders left—middle—right; CSS collapses to A ↓ relation ↓ B on mobile.
    const pp = document.getElementById("relationParties");
    if (pp) {
      const partyCard = function (e) {
        if (!e) return '<div class="relation-party-card"><b>未解析实体</b><span>' + esc(e) + '</span></div>';
        return '<a class="relation-party-card" href="' + esc(entityHref(e.entity_id)) + '"><b>' + esc(title(e)) + '</b><span class="intel-title-en">' + esc(e.name_en) + '</span><span>' + typeBadge(e) + ' · ' + esc(impLabel(e.importance_level)) + (e.current_status ? ' · ' + esc(statusLabel(e.current_status)) : '') + '</span></a>';
      };
      const rhRow = function (l, v) { if (v == null || v === "") return ""; return '<div class="rh-row"><dt>' + esc(l) + '</dt><dd>' + v + '</dd></div>'; };
      pp.innerHTML = partyCard(s) +
        '<div class="relation-hero-summary"><div class="relation-hero-arrow">↔</div><h2>关系摘要</h2>' +
        rhRow("关系类型", '<b>' + esc(relLabel(rel.relationship_type)) + '</b>') +
        rhRow("状态", esc(statusLabel(rel.current_status))) +
        rhRow("时间", esc(period(rel))) +
        rhRow("可信度", esc(confLabel(rel.confidence))) +
        rhRow("时效", freshnessBadge(rel.freshness_status)) +
        rhRow("争议", relIsDisputed(rel) ? '<span class="intel-badge disputed">争议</span>' : "否") +
        '</div>' + partyCard(t);
    }
    const ov = document.querySelector("#relationOverview"); if (ov) ov.innerHTML = '<p class="intel-lead">' + renderRelationText(esc(profile ? (profile.overview || profile.relationship_summary || rel.relation_summary) : rel.relation_summary)) + '</p>';
    const body = document.querySelector("#relationBody"); if (body) {
      let html = "";
      if (profile) {
        // evolution stages support both {period,title,description} and {period,detail}
        const stageHtml = function (x) { const t = x.title || x.detail || ""; const d = x.description || x.detail || ""; return '<li><b>' + renderRelationText(esc(x.period + (t && t !== x.period ? " · " + t : ""))) + '</b>' + (d ? '<p>' + renderRelationText(esc(d)) + '</p>' : '') + '</li>'; };
        if (profile.formation_background) html += '<section class="profile-section"><h2>关系形成背景</h2><p>' + renderRelationText(esc(profile.formation_background)) + '</p></section>';
        if (profile.initial_relationship) html += '<section class="profile-section"><h2>双方最初的关系</h2><p>' + renderRelationText(esc(profile.initial_relationship)) + '</p></section>';
        if (profile.evolution_stages && profile.evolution_stages.length) html += '<section class="profile-section"><h2>历史演变阶段</h2><ul>' + profile.evolution_stages.map(stageHtml).join("") + '</ul></section>';
        if (profile.nature && typeof profile.nature === "object") {
          html += '<section class="profile-section"><h2>关系性质</h2><ul class="intel-bullets">' + Object.keys(profile.nature).filter(function (k) { return k !== "type"; }).map(function (k) { return '<li><b>' + esc(k) + '</b>：' + renderRelationText(esc(Array.isArray(profile.nature[k]) ? profile.nature[k].join("、") : profile.nature[k])) + '</li>'; }).join("") + '</ul></section>';
        }
        if (profile.drivers && profile.drivers.length) html += '<section class="profile-section"><h2>驱动因素</h2><ul>' + profile.drivers.map(function (x) { return '<li>' + renderRelationText(esc(x)) + '</li>'; }).join("") + '</ul></section>';
        if (profile.constraints) {
          if (typeof profile.constraints === "string") html += '<section class="profile-section"><h2>约束条件</h2><p>' + renderRelationText(esc(profile.constraints)) + '</p></section>';
          else if (profile.constraints.length) html += '<section class="profile-section"><h2>约束条件</h2><ul>' + profile.constraints.map(function (x) { return '<li>' + renderRelationText(esc(x)) + '</li>'; }).join("") + '</ul></section>';
        }
        if (profile.third_party_effects && profile.third_party_effects.length) html += '<section class="profile-section"><h2>第三方影响</h2><ul>' + profile.third_party_effects.map(function (x) { return '<li>' + renderRelationText(esc(x)) + '</li>'; }).join("") + '</ul></section>';
        if (profile.personnel_flows) html += '<section class="profile-section"><h2>人员流动</h2><p>' + renderRelationText(esc(profile.personnel_flows)) + '</p></section>';
        if (profile.cooperation_dimensions && profile.cooperation_dimensions.length) html += '<section class="profile-section"><h2>合作维度</h2><ul>' + profile.cooperation_dimensions.map(function (x) { return '<li>' + renderRelationText(esc(x)) + '</li>'; }).join("") + '</ul></section>';
        if (profile.continuities && profile.continuities.length) html += '<section class="profile-section"><h2>连续性</h2><ul>' + profile.continuities.map(function (x) { return '<li>' + renderRelationText(esc(x)) + '</li>'; }).join("") + '</ul></section>';
        if (profile.differences && profile.differences.length) html += '<section class="profile-section"><h2>差异</h2><ul>' + profile.differences.map(function (x) { return '<li>' + renderRelationText(esc(x)) + '</li>'; }).join("") + '</ul></section>';
        // EXPANSION A: this block was duplicated verbatim, rendering "形成原因" twice on every relation page that has causes.
        if (profile.causes && profile.causes.length) html += '<section class="profile-section"><h2>形成原因</h2><ul>' + profile.causes.map(function (x) { return '<li>' + renderRelationText(esc(x)) + '</li>'; }).join("") + '</ul></section>';
        if (profile.key_turning_points && profile.key_turning_points.length) html += '<section class="profile-section"><h2>关键转折</h2><ul>' + profile.key_turning_points.map(function (x) { return '<li><b>' + renderRelationText(esc(x.event)) + '</b><p>' + renderRelationText(esc(x.impact)) + '</p></li>'; }).join("") + '</ul></section>';
        if (profile.current_status) html += '<section class="profile-section"><h2>当前状态</h2><p>' + renderRelationText(esc(profile.current_status)) + '</p></section>';
        if (profile.current_assessment && profile.current_assessment !== profile.current_status) html += '<section class="profile-section"><h2>当前评估</h2><p>' + renderRelationText(esc(profile.current_assessment)) + '</p></section>';
        if (profile.regional_differences) html += '<section class="profile-section"><h2>地区差异</h2><p>' + renderRelationText(esc(profile.regional_differences)) + '</p></section>';
        if (profile.impact_on_security) html += '<section class="profile-section"><h2>对区域安全的影响</h2><p>' + renderRelationText(esc(profile.impact_on_security)) + '</p></section>';
        if (profile.why_it_matters) html += '<section class="profile-section"><h2>为什么重要</h2><p>' + renderRelationText(esc(profile.why_it_matters)) + '</p></section>';
        if (profile.uncertainties) html += '<section class="profile-section uncertainty-partition"><div class="intel-uncertainty-card"><h2>不确定性与争议 <span class="intel-sem-chip uncertainty">UNCERTAINTY</span></h2><p>' + renderRelationText(esc(profile.uncertainties)) + '</p></div></section>';
        if (profile.organizational_balance) html += '<section class="profile-section"><h2>组织平衡</h2><p>' + renderRelationText(esc(profile.organizational_balance)) + '</p></section>';
        if (profile.role) html += '<section class="profile-section"><h2>角色</h2><p>' + renderRelationText(esc(profile.role)) + '</p></section>';
        if (profile.asip_analysis) html += '<section class="profile-section analysis-partition"><div class="intel-analysis-card"><h2>ASIP Analysis · 平台分析 <span class="intel-sem-chip institutional">ASIP ANALYSIS</span></h2><p>' + renderRelationText(esc(profile.asip_analysis)) + '</p></div></section>';
        if (profile.watch_indicators && profile.watch_indicators.length) html += '<section class="profile-section watch-partition"><div class="intel-watch-card"><h2>Watch Indicators · 后续观察指标 <span class="intel-sem-chip uncertainty">WATCH</span></h2><ul>' + profile.watch_indicators.map(function (x) { return '<li>' + renderRelationText(esc(x)) + '</li>'; }).join("") + '</ul></div></section>';
      } else {
        html += '<section class="profile-section"><h2>关系概述</h2><p>' + renderRelationText(esc(rel.relation_summary)) + '</p></section>';
        html += '<section class="profile-section"><h2>当前状态</h2><p>' + renderRelationText(esc(rel.current_status_detail || rel.current_status)) + '</p></section>';
      }
      body.innerHTML = html;
    }
    const tl = document.querySelector("#relationTimeline"); if (tl) {
      let tlHtml = '<h2>关系历史时间轴</h2>';
      // UI/UX V2: current-phase banner uses existing profile fields only (no inference).
      if (profile && (profile.current_status || profile.current_assessment)) {
        const cur = (profile.current_assessment && profile.current_assessment !== profile.current_status) ? profile.current_assessment : profile.current_status;
        tlHtml += '<div class="rtl-current-banner"><b>当前阶段</b>：' + renderRelationText(esc(cur)) + '</div>';
      }
      tlHtml += (timeline.length ? '<div class="rtl-h">' + timeline.map(function (x) {
        return '<div class="rtl-stage-card"><span class="rtl-phase">' + esc(x.date) + '</span><h3>' + renderRelationText(esc(x.event_title)) + '</h3>' +
          (x.event_description ? '<p>' + renderRelationText(esc(x.event_description)) + '</p>' : '') +
          (x.impact_on_relationship ? '<p class="rtl-impact"><b>对关系的影响：</b>' + renderRelationText(esc(x.impact_on_relationship)) + '</p>' : '') +
          '<p class="rtl-meta">可信度：' + esc(confLabel(x.confidence)) + ' · 来源：' + sourceList(x.source_ids) + '</p></div>';
      }).join("") + '</div>' : '<p class="muted">暂无已核验时间轴条目。</p>');
      tl.innerHTML = tlHtml;
    }
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
    // UI/UX V2: relation-level filters + optional 2-hop expansion.
    const relFilters = { type: "", status: "", disputed: false };
    let twoHop = false;
    const TWO_HOP_CAP = 20;
    // UI FINAL POLISH 1: label tiers + interactive legend visibility groups.
    let labelMode = "auto"; // auto | full | focus
    const nodeVisGroup = { organization: true, person: true, country: true };
    const relVisGroup = { conflict: true, allegiance: true, presence: true, cooperation: true, other: true };
    const RINGS = { inner: 175, middle: 265, outer: 345 };
    const RING_ORDER = ["inner", "middle", "outer"];
    const MIN = 96;
    const RING_PHASE = { inner: 0, middle: Math.PI / 6, outer: Math.PI / 3 };
    const MAX_RADIUS = 350;
    function ringFor(rel) { if (rel.display_ring && RINGS[rel.display_ring] != null) return rel.display_ring; if (["affiliated_with", "constituent_of", "operates_in", "member_of_force", "pledged_allegiance_to"].indexOf(rel.relationship_type) >= 0) return "inner"; if (["hostile_to", "historically_associated_with", "allied_with", "cooperates_with", "fought_against", "competes_with"].indexOf(rel.relationship_type) >= 0) return "middle"; return "outer"; }
    function typeName(e) { return e.primary_type || e.entity_type; }
    function visible(e) { return filters.imp[e.importance_level || "L3"] !== false && (!filters.type || typeName(e) === filters.type) && (!filters.region || (e.region_ids || []).indexOf(filters.region) >= 0 || (e.entity_id === "actor-jnim" && filters.region === "region-central-sahel")) && (!filters.country || (e.country_ids || []).indexOf(filters.country) >= 0); }
    function color(e) { return ({ organization: "#14507e", armed_group: "#14507e", terrorist_group: "#a94b4b", insurgent_group: "#9a6b17", militia: "#7d5a94", community_self_defense: "#37715c", state_security_force: "#0f3a5d", regional_force: "#2e6e8e", political_movement: "#8a641c", person: "#9a6b17", country: "#37715c", international_network: "#52606d" })[typeName(e)] || "#52606d"; }
    function mk(tag, attrs) { const n = document.createElementNS(NS, tag); Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); }); return n; }
    function layout(center, visibleEntities, rels) {
      const cx = 450, cy = 315, narrow = document.getElementById("graphWrap") ? document.getElementById("graphWrap").clientWidth < 560 : false;
      const min = narrow ? 80 : MIN;
      const yk = 0.9;
      const next = {}; next[center.entity_id] = { x: cx, y: cy };
      const byRing = {};
      rels.forEach(function (r) {
        [r.source_entity_id, r.target_entity_id].forEach(function (eid) {
          if (eid === center.entity_id) return;
          const o = store.byEntityId[eid]; if (!o || !visible(o)) return;
          const ring = ringFor(r); (byRing[ring] = byRing[ring] || []);
          if (!byRing[ring].some(function (x) { return x.entity_id === o.entity_id; })) byRing[ring].push(o);
        });
      });
      RING_ORDER.forEach(function (ring, ringIndex) {
        const items = (byRing[ring] || []).slice();
        let radius = RINGS[ring];
        // auto-expand radius so same-ring nodes keep the min spacing on a full circle
        if (items.length > 1) {
          for (let i = 0; i < 8; i++) {
            if (items.length <= 2 || (2 * radius * Math.PI / items.length) >= min) break;
            radius = Math.min(MAX_RADIUS, radius + 26);
          }
        }
        // full-circle uniform spread with per-ring phase to avoid collinear rays
        const start = -Math.PI / 2 + RING_PHASE[ring];
        const spread = 2 * Math.PI;
        items.forEach(function (e, i) {
          const off = { organization: 0, armed_group: 0, terrorist_group: 0, insurgent_group: 0, state_security_force: Math.PI * 0.05, regional_force: Math.PI * 0.1, person: Math.PI * 0.07, country: Math.PI * 0.14, international_network: Math.PI * 0.18 }[typeName(e)] || 0;
          const angle = items.length === 1 ? start + Math.PI : start + off + spread * i / items.length;
          const px = positions[e.entity_id];
          const target = { x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius * yk };
          next[e.entity_id] = (px && Math.hypot(px.x - target.x, px.y - target.y) < 200) ? { x: px.x * 0.3 + target.x * 0.7, y: px.y * 0.3 + target.y * 0.7 } : target;
        });
      });
      visibleEntities.forEach(function (e) { if (!next[e.entity_id]) next[e.entity_id] = { x: cx, y: cy }; });
      const ids = Object.keys(next);
      function collide(passes) {
        for (let p = 0; p < passes; p++) ids.forEach(function (a) { if (a === center.entity_id) return; ids.forEach(function (b) { if (b === center.entity_id || b <= a) return; const pa = next[a], pb = next[b]; const dx = pa.x - pb.x, dy = pa.y - pb.y, d = Math.hypot(dx, dy); if (d < min && d > 0) { const push = (min - d) / 2, ux = dx / d, uy = dy / d; pa.x += ux * push; pa.y += uy * push; pb.x -= ux * push; pb.y -= uy * push; } }); });
      }
      collide(3);
      // balance: shift non-center nodes so the visual centroid returns near the center,
      // preventing one-sided crowding even when min spacing is satisfied.
      let sx = 0, sy = 0, n = 0;
      ids.forEach(function (k) { if (k === center.entity_id) return; sx += next[k].x; sy += next[k].y; n++; });
      if (n > 0) {
        const mx2 = sx / n, my2 = sy / n;
        const ddx = cx - mx2, ddy = cy - my2;
        if (Math.hypot(ddx, ddy) > 14) {
          ids.forEach(function (k) { if (k === center.entity_id) return; next[k].x += ddx * 0.6; next[k].y += ddy * 0.6; });
          collide(2);
        }
      }
      // UI FINAL POLISH 1: safe margins keep nodes + labels inside the 900x630 viewBox.
      const XMIN = 96, XMAX = 900 - 96, YMIN = 66, YMAX = 630 - 96;
      ids.forEach(function (k) { const q = next[k]; q.x = Math.max(XMIN, Math.min(XMAX, q.x)); q.y = Math.max(YMIN, Math.min(YMAX, q.y)); });
      positions = next;
    }
    function maxSafeZoom() {
      let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
      Object.keys(positions).forEach(function (k) {
        const p = positions[k];
        minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x);
        minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y);
      });
      if (maxX < minX || maxY < minY) return 1;
      const LM = 90, TM = 50, BM = 70;
      const zx1 = 450 / (450 - minX + LM), zx2 = 450 / (maxX - 450 + LM);
      const zy1 = 315 / (315 - minY + TM), zy2 = 315 / (maxY - 315 + BM);
      return Math.max(0.55, Math.min(1.5, zx1, zx2, zy1, zy2));
    }
    function edgePoint(a, b, dist) { const dx = b.x - a.x, dy = b.y - a.y, l = Math.max(Math.hypot(dx, dy), 1); return { x: a.x + dx / l * dist, y: a.y + dy / l * dist }; }
    function relationGroup(r) {
      const t = r.relationship_type;
      if (t === "hostile_to" || t === "fought_against" || t === "competes_with") return "conflict";
      if (t === "pledged_allegiance_to" || t === "affiliated_with" || t === "constituent_of" || t === "part_of_network") return "allegiance";
      if (t === "operates_in" || t === "active_in_region") return "presence";
      if (t === "cross_border_link") return "crossborder";
      if (t === "cooperates_with" || t === "allied_with") return "cooperation";
      if (t === "supported_by" || t === "supports" || t === "alleged_support") return "support";
      if (t === "historically_associated_with") return "historical";
      if (["led_by", "founded_by", "member_of_force", "deployed_in", "political_affiliation"].indexOf(t) >= 0) return "leadership";
      if (r.temporal_sensitive || String(r.current_status || "").indexOf("historical") >= 0) return "temporal";
      return "normal";
    }
    const EDGE_GROUPS = ["normal", "leadership", "presence", "historical", "temporal", "disputed", "conflict", "allegiance", "crossborder", "cooperation", "support"];
    // UI FINAL POLISH 1: node/edge visibility groups for the interactive legend.
    function nodeGroup(e) { const t = typeName(e); if (t === "person") return "person"; if (t === "country") return "country"; return "organization"; }
    function relGroup(r) { const g = relationGroup(r); if (g === "conflict") return "conflict"; if (g === "allegiance" || g === "leadership") return "allegiance"; if (g === "presence") return "presence"; if (g === "cooperation" || g === "support" || g === "crossborder" || g === "historical") return "cooperation"; return "other"; }
    function shortLabel(e) { const a = acronymOf(e); if (a && String(a).length <= 10) return a; const zh = e.name_zh || ""; return zh.length <= 6 ? zh : zh.slice(0, 5) + "…"; }
    function tinyLabel(e) { const a = acronymOf(e); if (a && String(a).length <= 6) return a; return (e.name_zh || "").slice(0, 2); }
    function nodeDetailHtml(e) {
      if (!e) return "";
      const relsN = store.relationships.filter(function (r) { return r.source_entity_id === e.entity_id || r.target_entity_id === e.entity_id; });
      const isCountry = e.entity_type === "country" || e.primary_type === "country";
      return '<div class="intel-node-detail"><h2>' + esc(title(e)) + '</h2><p class="intel-title-en">' + esc(e.name_en) + '</p><div class="intel-badges">' + typeBadge(e) + importanceBadge(e) + (e.current_status ? '<span class="intel-badge status">' + esc(statusLabel(e.current_status)) + '</span>' : '') + (e.disputed ? '<span class="intel-badge disputed">争议</span>' : '') + '</div><p class="nd-meta">' + esc(e.entity_id) + (e.freshness_status ? ' · ' + freshnessBadge(e.freshness_status) : '') + '</p><p class="nd-meta">' + esc(e.short_description || "") + '</p><p class="nd-rels">' + relsN.length + ' 条关键关系：' + relsN.slice(0, 8).map(function (r) { const other = r.source_entity_id === e.entity_id ? r.target_entity_id : r.source_entity_id; return '<a href="' + esc(relationHref(r.relationship_id)) + '">' + esc(titleFor(other)) + '</a>'; }).join("") + '</p><a class="intel-button sm" href="' + esc(entityHref(e.entity_id)) + '">' + (isCountry ? '进入国家页 →' : '查看详细档案 →') + '</a></div>';
    }
    function draw() {
      const center = store.byEntityId[focusId]; if (!center) return;
      const token = ++drawToken;
      function relVisible(r) {
        if (relFilters.type && r.relationship_type !== relFilters.type) return false;
        if (relFilters.status === "historical" && !relIsHistorical(r)) return false;
        if (relFilters.status === "current" && relIsHistorical(r)) return false;
        if (relFilters.disputed && !relIsDisputed(r)) return false;
        return true;
      }
      let rels = store.relationships.filter(function (r) { return (r.source_entity_id === focusId || r.target_entity_id === focusId) && relVisible(r) && relVisGroup[relGroup(r)] !== false; });
      const neighbors = rels.map(function (r) { return store.byEntityId[r.source_entity_id === focusId ? r.target_entity_id : r.source_entity_id]; }).filter(function (e, i, all) { return e && visible(e) && nodeVisGroup[nodeGroup(e)] !== false && all.findIndex(function (x) { return x && x.entity_id === e.entity_id; }) === i; });
      let extraNodes = [];
      const densityNote = document.getElementById("densityNote");
      if (twoHop && neighbors.length) {
        const seenRel = {};
        rels.forEach(function (r) { seenRel[r.relationship_id] = 1; });
        const hop2 = [];
        neighbors.forEach(function (n) {
          store.relationships.forEach(function (r) {
            if (seenRel[r.relationship_id]) return;
            if (r.source_entity_id !== n.entity_id && r.target_entity_id !== n.entity_id) return;
            const other = store.byEntityId[r.source_entity_id === n.entity_id ? r.target_entity_id : r.source_entity_id];
            if (!other || other.entity_id === focusId || !visible(other) || !relVisible(r) || nodeVisGroup[nodeGroup(other)] === false) return;
            seenRel[r.relationship_id] = 1;
            hop2.push({ rel: r, node: other });
          });
        });
        // density protection: importance-first, then cap; never dump a spider web.
        const order = { L1: 0, L2: 1, L3: 2 };
        hop2.sort(function (a, b) { return (order[a.node.importance_level || "L3"] - order[b.node.importance_level || "L3"]); });
        const capped = hop2.slice(0, TWO_HOP_CAP);
        if (densityNote) {
          if (hop2.length > TWO_HOP_CAP) {
            densityNote.hidden = false;
            densityNote.textContent = "第二层展开候选较大（" + hop2.length + " 个二度节点）：已按重要程度优先展示前 " + TWO_HOP_CAP + " 个，请使用筛选缩小范围。";
          } else densityNote.hidden = true;
        }
        extraNodes = capped.map(function (x) { return x.node; });
        rels = rels.concat(capped.map(function (x) { return x.rel; }));
      } else if (densityNote) densityNote.hidden = true;
      const seenNode = {};
      const visibleEntities = [];
      [center].concat(neighbors, extraNodes).forEach(function (e) { if (e && !seenNode[e.entity_id]) { seenNode[e.entity_id] = 1; visibleEntities.push(e); } });
      // UI HARD FIX A: never draw dangling edges — drop any relation whose
      // endpoint was hidden by the legend / node visibility filter.
      const visId = {};
      visibleEntities.forEach(function (e) { visId[e.entity_id] = 1; });
      rels = rels.filter(function (r) { return visId[r.source_entity_id] && visId[r.target_entity_id]; });
      layout(center, visibleEntities, rels);
      viewport.innerHTML = "";
      const defs = mk("defs");
      EDGE_GROUPS.forEach(function (k) { const m = mk("marker", { id: "af-arrow-" + k, markerWidth: "9", markerHeight: "9", refX: "8", refY: "4.5", orient: "auto", markerUnits: "strokeWidth" }); m.appendChild(mk("path", { d: "M0,0 L9,4.5 L0,9 z", class: "arrow-head " + k })); defs.appendChild(m); });
      RING_ORDER.forEach(function (ring) { const rr = RINGS[ring]; defs.appendChild(mk("ellipse", { cx: 450, cy: 315, rx: rr, ry: Math.round(rr * 0.9), class: "ring-guide ring-" + ring, "aria-hidden": "true" })); });
      viewport.appendChild(defs);
      const hitLayer = mk("g", { class: "graph-edge-hits" }); const edgeLayer = mk("g", { class: "graph-edges" }); const labelLayer = mk("g", { class: "graph-edge-labels" }); const nodeLayer = mk("g", { class: "graph-nodes" });
      const showLabels = rels.length <= 8;
      const relInfo = document.getElementById("relationInfo");
      rels.forEach(function (r) {
        const ea = store.byEntityId[r.source_entity_id], eb = store.byEntityId[r.target_entity_id];
        if (!ea || !eb || !positions[ea.entity_id] || !positions[eb.entity_id]) return;
        const a = positions[ea.entity_id], b = positions[eb.entity_id];
        const kindBase = relationGroup(r);
        const kind = kindBase + (relIsDisputed(r) ? " disputed" : "");
        const da = (ea.primary_type === "country" || ea.entity_type === "country") ? 44 : 52;
        const db = (eb.primary_type === "country" || eb.entity_type === "country") ? 44 : 52;
        const p1 = edgePoint(a, b, da), p2 = edgePoint(b, a, db);
        const g = mk("g", { class: "graph-edge-group " + kind });
        g.appendChild(mk("line", { x1: p1.x, y1: p1.y, x2: p2.x, y2: p2.y, class: "graph-edge-hit " + kind }));
        g.appendChild(mk("line", { x1: p1.x, y1: p1.y, x2: p2.x, y2: p2.y, class: "graph-edge " + kind, "marker-end": "url(#af-arrow-" + kindBase + ")", "aria-label": relLabel(r.relationship_type) + "：" + title(eb), tabindex: "0", role: "button" }));
        g.addEventListener("click", function (ev) { ev.stopPropagation(); document.querySelectorAll(".graph-edge-group.selected").forEach(function (x) { x.classList.remove("selected"); }); g.classList.add("selected"); if (relInfo) relInfo.innerHTML = '<h2>关系详情</h2><div class="relation-pair">' + entityLink(r.source_entity_id, title(store.byEntityId[r.source_entity_id])) + ' <b>↔</b> ' + entityLink(r.target_entity_id, title(store.byEntityId[r.target_entity_id])) + '</div><p class="relation-label">' + esc(relLabel(r.relationship_type)) + ' · ' + esc(ringLabel(ringFor(r))) + '圈层</p>' + (r.relationship_type === "pledged_allegiance_to" ? '<p class="ib-note">宣誓效忠（bay\'ah）为独立关系语义，不同于一般网络关联（affiliated_with）。</p>' : '') + '<p>' + esc(r.relation_summary) + '</p><dl class="intel-detail-list"><dt>时间范围</dt><dd>' + esc(period(r)) + '</dd><dt>状态</dt><dd>' + esc(statusLabel(r.current_status)) + '</dd><dt>可信度</dt><dd>' + esc(confLabel(r.confidence)) + '</dd><dt>时效</dt><dd>' + freshnessBadge(r.freshness_status) + '</dd><dt>来源</dt><dd>' + sourceList(r.source_refs) + '</dd></dl><a class="intel-button sm" href="' + esc(relationHref(r.relationship_id)) + '">查看完整关系沿革 →</a>'; });
        g.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") g.dispatchEvent(new MouseEvent("click", { bubbles: true })); });
        hitLayer.appendChild(g);
        if (showLabels) {
          // place the label at ~62% along the line (near the target node, away from the center
          // ring) plus a perpendicular offset, so labels do not crowd around the center.
          const t = 0.62;
          const mx = p1.x + (p2.x - p1.x) * t, my = p1.y + (p2.y - p1.y) * t, dx = p2.x - p1.x, dy = p2.y - p1.y, l = Math.max(Math.hypot(dx, dy), 1);
          const flip = dy > 0 ? 1 : -1;
          const wrap = mk("g", { class: "graph-edge-label-wrap " + kind, transform: "translate(" + (mx - dy / l * 16 * flip) + "," + (my + dx / l * 16 * flip) + ")", "pointer-events": "none" });
          const text = relLabel(r.relationship_type); const w = Math.max(44, text.length * 12 + 16);
          wrap.appendChild(mk("rect", { x: -w / 2, y: -12, width: w, height: 18, rx: 8 }));
          const t2 = mk("text", { x: 0, y: 1, class: "graph-edge-label", "text-anchor": "middle" }); t2.textContent = text; wrap.appendChild(t2);
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
        const nt = title(e);
        // UI HARD FIX A: strict default label policy — only the focus node gets a
        // full label; L1 key neighbors get a short/acronym label; everything else
        // stays as a clean dot so the default graph reads as structure, not text.
        const isKeyNeighbor = !isCenter && (e.importance_level === "L1");
        let labelText = "";
        if (labelMode === "full") labelText = nt;
        else if (labelMode === "focus") labelText = isCenter ? nt : "";
        else if (isCenter) labelText = nt;
        else if (labelMode === "auto") labelText = isKeyNeighbor ? shortLabel(e) : "";
        // adapt label placement so text never clips at the canvas edges
        const nearBottom = pos.y > 448, nearTop = pos.y < 96;
        const nearRight = pos.x > 760, nearLeft = pos.x < 140;
        const ly = isCenter ? 76 : (nearBottom ? -44 : 54);
        const anchor = nearLeft ? "start" : (nearRight ? "end" : "middle");
        const lx = nearLeft ? 16 : (nearRight ? -16 : 0);
        let labelCls = "node-label";
        if (isCenter) labelCls += " center-label";
        else if (labelMode === "auto") labelCls += (labelText ? " short" : " hidden-label");
        else if (labelMode === "focus") labelCls += " hidden-label";
        const name = mk("text", { x: lx, y: ly, class: labelCls, "text-anchor": anchor, "pointer-events": "none" });
        name.textContent = labelText; g.appendChild(name);
        if (!isCenter) { const tp = mk("title"); tp.textContent = nt + " " + (e.name_en || ""); g.appendChild(tp); }
        if (isCenter) { const en = mk("text", { x: 0, y: 94, class: "node-sub-label", "text-anchor": "middle" }); en.textContent = e.name_en.length > 30 ? e.name_en.slice(0, 28) + "…" : e.name_en; g.appendChild(en); }
        const showImp = isCenter || (e.importance_level === "L1") || labelMode !== "auto";
        if (showImp) { const tag = mk("text", { x: 0, y: isCenter ? -48 : -38, class: "node-imp-tag", "text-anchor": "middle" }); tag.textContent = e.importance_level || "L3"; g.appendChild(tag); }
        g.addEventListener("click", function (ev) {
          if (isCenter) { window.location.href = entityHref(e.entity_id); return; }
          const ni = document.getElementById("nodeInfo");
          if (ni) ni.innerHTML = nodeDetailHtml(e);
          focusId = e.entity_id; const u = new URL(window.location.href); u.searchParams.set("focus", focusId); window.history.pushState({ focus: focusId }, "", u); draw(); if (relInfo) relInfo.innerHTML = '<h2>关系详情</h2><p class="muted">点击关系线查看双方、类型、时间与来源。</p>';
        });
        nodeLayer.appendChild(g);
      });
      viewport.appendChild(hitLayer); viewport.appendChild(edgeLayer); viewport.appendChild(labelLayer); viewport.appendChild(nodeLayer);
      // UI FINAL POLISH 1: empty state when the interactive legend hides everything.
      const existingEmpty = document.querySelector(".graph-empty");
      if (visibleEntities.length <= 1) {
        const graphWrapEl = document.getElementById("graphWrap");
        if (!existingEmpty && graphWrapEl) { const d = document.createElement("div"); d.className = "graph-empty"; d.textContent = "当前筛选条件下无可见节点，请重新勾选图例项。"; graphWrapEl.appendChild(d); }
      } else if (existingEmpty) { existingEmpty.remove(); }
      const vs = document.getElementById("graphVisStats");
      if (vs) vs.innerHTML = '当前可见 <b>' + visibleEntities.length + '</b> 个节点 · <b>' + rels.length + '</b> 条关系' + (twoHop ? ' · 已展开第二层' : '');
      const hint = document.getElementById("graphHint");
      if (hint) hint.textContent = visibleEntities.length + " 个节点 · " + rels.length + " 条关系 · " + (twoHop ? "已展开第二层（上限 " + TWO_HOP_CAP + "）" : "一度关系") + " · 图例可控制节点/关系显示 · 点击中心节点进入详细档案页";
      const stats = document.getElementById("importanceStats");
      if (stats) { const cnt = {}; visibleEntities.forEach(function (e) { const l = e.importance_level || "L3"; cnt[l] = (cnt[l] || 0) + 1; }); stats.textContent = "可见 " + visibleEntities.length + " · L1 " + (cnt.L1 || 0) + " · L2 " + (cnt.L2 || 0) + " · L3 " + (cnt.L3 || 0); }
      // focus entry points: header link + right card + focus name/id refresh
      const fn = document.getElementById("focusName"); if (fn) fn.textContent = title(center);
      const fi = document.getElementById("focusId"); if (fi) fi.textContent = center.entity_id;
      const fl = document.getElementById("focusLink"); if (fl) { fl.setAttribute("href", entityHref(center.entity_id)); fl.textContent = (center.entity_type === "country" || center.primary_type === "country") ? "进入国家页" : "查看档案"; }
      const ni = document.getElementById("nodeInfo");
      if (ni) ni.innerHTML = nodeDetailHtml(center) + '<p class="ib-note">外围节点点击可切换中心并在此查看详情。</p>';
      const wrap = document.getElementById("graphWrap");
      if (wrap && wrap.clientWidth < 560 && visibleEntities.length !== lastFit) { lastFit = visibleEntities.length; zoom = Math.max(0.62, Math.min(1, (wrap.clientWidth - 60) / 700)); const zv = document.getElementById("zoomValue"); if (zv) zv.textContent = Math.round(zoom * 100) + "%"; }
      viewport.setAttribute("transform", "translate(" + (450 - 450 * zoom) + " " + (315 - 315 * zoom) + ") scale(" + zoom + ")");
    }
    function bind() {
      document.querySelectorAll("[data-imp-filter]").forEach(function (el) { el.addEventListener("change", function () { filters.imp[el.getAttribute("data-imp-filter")] = el.checked; lastFit = -1; draw(); }); });
      document.querySelectorAll("[data-view-filter]").forEach(function (el) { el.addEventListener("click", function () { const v = el.getAttribute("data-view-filter"); filters.imp = v === "core" ? { L1: true, L2: false, L3: false } : v === "priority" ? { L1: true, L2: true, L3: false } : { L1: true, L2: true, L3: true }; document.querySelectorAll("[data-imp-filter]").forEach(function (x) { x.checked = filters.imp[x.getAttribute("data-imp-filter")]; }); lastFit = -1; draw(); }); });
      const regionSel = document.getElementById("regionFilter"); if (regionSel) { regionSel.innerHTML = '<option value="">全部区域</option>' + store.regions.map(function (r) { return '<option value="' + esc(r.region_id) + '">' + esc(r.name_zh) + '</option>'; }).join(""); regionSel.addEventListener("change", function () { filters.region = regionSel.value; lastFit = -1; draw(); }); }
      const countrySel = document.getElementById("countryFilter"); if (countrySel) { countrySel.innerHTML = '<option value="">全部国家</option>' + store.countries.map(function (c) { return '<option value="' + esc(c.country_id) + '">' + esc(c.name_zh) + '</option>'; }).join(""); countrySel.addEventListener("change", function () { filters.country = countrySel.value; lastFit = -1; draw(); }); }
      const typeSel = document.getElementById("typeFilter"); if (typeSel) { typeSel.innerHTML = '<option value="">全部类型</option>' + Object.keys(TYPE_LABELS).map(function (t) { return '<option value="' + esc(t) + '">' + esc(TYPE_LABELS[t]) + '</option>'; }).join(""); typeSel.addEventListener("change", function () { filters.type = typeSel.value; lastFit = -1; draw(); }); }
      const search = document.getElementById("entitySearch"); if (search) search.addEventListener("input", function () { const term = search.value.trim().toLowerCase(); if (!term) return; const hit = store.entities.find(function (e) { return [e.entity_id, e.slug, e.name_zh, e.name_en, e.acronym || "", e.native_name || ""].concat(e.aliases).join(" ").toLowerCase().indexOf(term) >= 0; }); if (hit) { if (!visible(hit)) { filters.imp[hit.importance_level || "L3"] = true; document.querySelectorAll("[data-imp-filter]").forEach(function (x) { x.checked = filters.imp[x.getAttribute("data-imp-filter")]; }); } focusId = hit.entity_id; lastFit = -1; draw(); const u = new URL(window.location.href); u.searchParams.set("focus", focusId); window.history.pushState({ focus: focusId }, "", u); } });
      document.getElementById("zoomIn").addEventListener("click", function () { zoom = Math.min(maxSafeZoom(), zoom + 0.12); draw(); });
      document.getElementById("zoomOut").addEventListener("click", function () { zoom = Math.max(0.55, zoom - 0.12); draw(); });
      document.getElementById("fitGraph").addEventListener("click", function () { zoom = 1; lastFit = -1; draw(); });
      document.getElementById("backFocus").addEventListener("click", function () { window.history.back(); });
      document.getElementById("resetFocus").addEventListener("click", function () { focusId = "actor-jnim"; lastFit = -1; draw(); });
      // UI/UX V2: relation-type filter
      const relTypeSel = document.getElementById("relTypeFilter");
      if (relTypeSel) {
        relTypeSel.innerHTML = '<option value="">全部关系类型</option>' + Object.keys(REL_LABELS).map(function (t) { return '<option value="' + esc(t) + '">' + esc(REL_LABELS[t]) + '</option>'; }).join("");
        relTypeSel.addEventListener("change", function () { relFilters.type = relTypeSel.value; lastFit = -1; draw(); });
      }
      const relStatusSel = document.getElementById("relStatusFilter");
      if (relStatusSel) relStatusSel.addEventListener("change", function () { relFilters.status = relStatusSel.value; lastFit = -1; draw(); });
      const relDisSel = document.getElementById("relDisputedOnly");
      if (relDisSel) relDisSel.addEventListener("change", function () { relFilters.disputed = relDisSel.checked; lastFit = -1; draw(); });
      const th = document.getElementById("twoHopToggle");
      if (th) th.addEventListener("click", function () {
        twoHop = !twoHop;
        th.classList.toggle("active", twoHop);
        th.setAttribute("aria-pressed", twoHop ? "true" : "false");
        th.textContent = twoHop ? "收起第二层" : "展开第二层";
        lastFit = -1; draw();
      });
      window.addEventListener("popstate", function () { const f = new URLSearchParams(window.location.search).get("focus"); if (f && store.byEntityId[f]) { focusId = f; draw(); } });
      // UI FINAL POLISH 1: interactive legend — node type toggles.
      [["lvNodeOrg", "organization"], ["lvNodePerson", "person"], ["lvNodeCountry", "country"]].forEach(function (pair) {
        const el = document.getElementById(pair[0]);
        if (el) el.addEventListener("change", function () { nodeVisGroup[pair[1]] = el.checked; lastFit = -1; draw(); });
      });
      // relation type toggles.
      [["lvRelConflict", "conflict"], ["lvRelAllegiance", "allegiance"], ["lvRelPresence", "presence"], ["lvRelCoop", "cooperation"], ["lvRelOther", "other"]].forEach(function (pair) {
        const el = document.getElementById(pair[0]);
        if (el) el.addEventListener("change", function () { relVisGroup[pair[1]] = el.checked; lastFit = -1; draw(); });
      });
      const legendNodeAll = document.getElementById("legendNodeAll");
      if (legendNodeAll) legendNodeAll.addEventListener("click", function () { ["organization", "person", "country"].forEach(function (g) { nodeVisGroup[g] = true; }); document.querySelectorAll("#lvNodeOrg,#lvNodePerson,#lvNodeCountry").forEach(function (x) { x.checked = true; }); lastFit = -1; draw(); });
      const legendRelAll = document.getElementById("legendRelAll");
      if (legendRelAll) legendRelAll.addEventListener("click", function () { ["conflict", "allegiance", "presence", "cooperation", "other"].forEach(function (g) { relVisGroup[g] = true; }); document.querySelectorAll("#lvRelConflict,#lvRelAllegiance,#lvRelPresence,#lvRelCoop,#lvRelOther").forEach(function (x) { x.checked = true; }); lastFit = -1; draw(); });
      const legendReset = document.getElementById("legendReset");
      if (legendReset) legendReset.addEventListener("click", function () {
        nodeVisGroup.organization = nodeVisGroup.person = nodeVisGroup.country = true;
        relVisGroup.conflict = relVisGroup.allegiance = relVisGroup.presence = relVisGroup.cooperation = relVisGroup.other = true;
        document.querySelectorAll(".graph-legend input[type=checkbox]").forEach(function (x) { x.checked = true; });
        labelMode = "auto";
        document.querySelectorAll("[data-label-mode]").forEach(function (b) { b.classList.toggle("active", b.getAttribute("data-label-mode") === "auto"); });
        focusId = "actor-jnim"; lastFit = -1; draw();
      });
      document.querySelectorAll("[data-label-mode]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          labelMode = btn.getAttribute("data-label-mode");
          document.querySelectorAll("[data-label-mode]").forEach(function (b) { b.classList.toggle("active", b === btn); });
          lastFit = -1; draw();
        });
      });
    }
    bind(); draw();
  }

  window.ASIP_AFRICA = { store: store, title: title, typeLabel: typeLabel, relLabel: relLabel, impLabel: impLabel, riskLabel: riskLabel, confLabel: confLabel, entityHref: entityHref, countryHref: countryHref, regionHref: regionHref, relationHref: relationHref, networkHref: networkHref, entityLink: entityLink, sourceLink: sourceLink, esc: esc, autoLinkExact: autoLinkExact, buildAutoLinkIndex: buildAutoLinkIndex };
  renderTopbar(); renderFooter();
  const loadSignal = beginLoad();
  loadJson("regions.json", loadSignal).then(function (r) { store.regions = r.regions; r.regions.forEach(function (x) { store.byRegionId[x.region_id] = x; }); return loadJson("countries.json", loadSignal); }).then(function (c) { store.countries = c.countries; c.countries.forEach(function (x) { store.byCountryId[x.country_id] = x; }); return loadJson("entities.json", loadSignal); }).then(function (e) { store.entities = e.entities; e.entities.forEach(function (x) { store.byEntityId[x.entity_id] = x; store.byEntitySlug[x.slug] = x; }); return loadJson("relationships.json", loadSignal); }).then(function (r) { store.relationships = r.relationships; r.relationships.forEach(function (x) { store.byRelId[x.relationship_id] = x; if (x.slug) store.byRelId[x.slug] = x; });     return Promise.all([loadJson("sources.json", loadSignal), loadJson("evidence_records.json", loadSignal), loadJson("relation_profiles.json", loadSignal), loadJson("relation_timelines.json", loadSignal), loadJson("force_estimates.json", loadSignal), loadJson("external_links.json", loadSignal), loadJson("entity_profiles.json", loadSignal), loadJson("country_profiles.json", loadSignal), loadJson("catalog_metrics.json", loadSignal), loadJson("audit_records.json", loadSignal), loadJson("alias_index.json", loadSignal)]); }).then(function (items) {
    store.sources = items[0].sources; store.evidence = items[1].evidence; store.relationProfiles = items[2].profiles || {}; store.relationTimelines = items[3].timelines || {}; store.forceEstimates = items[4].estimates || {}; store.externalLinks = items[5].links || {}; store.entityProfiles = items[6].profiles || {}; store.countryProfiles = items[7].profiles || {}; store.metrics = items[8] || null; store.audit = (items[9] && items[9].records) || []; store.aliases = (items[10] && items[10].aliases) || {};
    // merge countries into the unified entity table (one ID per entity)
    store.countries.forEach(function (c) {
      if (!store.byEntityId[c.country_id]) {
        var ce = { entity_id: c.country_id, entity_type: "country", primary_type: "country", slug: c.slug, name_zh: c.name_zh, name_en: c.name_en, acronym: "", native_name: c.name_en, aliases: [], historical_names: [], importance_level: "L1", short_description: c.risk_level_reason || c.name_zh + " 国家入口", current_status: "monitored", region_ids: c.region_ids || [], country_ids: [c.country_id], source_refs: [], confidence: "high", temporal_sensitive: false, disputed: false, last_verified_at: c.last_verified_at, record_reviewed_at: c.record_reviewed_at, current_status_verified_at: c.current_status_verified_at, claim_valid_as_of: c.claim_valid_as_of, freshness_status: c.freshness_status };
        store.entities.push(ce); store.byEntityId[ce.entity_id] = ce; store.byEntitySlug[ce.slug] = ce;
      }
    });
    // UI FINAL POLISH 1: build the exact auto-link index AFTER countries are merged so
    // country names (e.g. 尼日尔) are linkable from prose.
    buildAutoLinkIndex();
    const page = document.body.getAttribute("data-africa-page");
    if (page === "home") initHome(); if (page === "regions") initRegions(); if (page === "countries") initCountries(); if (page === "entities") initEntities(); if (page === "relations") initRelations(); if (page === "sources") initSources(); if (page === "region") initRegion(); if (page === "country") initCountry(); if (page === "entity") initEntity(); if (page === "relation") initRelation(); if (page === "network") initNetwork();
  }).catch(function (error) {
    if (error && error.name === "AbortError") return; // navigation aborted a previous load; not a product error
    const el = document.querySelector("#intelError"); if (el) { el.hidden = false; el.textContent = "非洲知识库数据加载失败：" + (error && error.message ? error.message : error); }
  });
})();
