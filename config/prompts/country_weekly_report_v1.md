# ASIP Priority Country Weekly Report — 生成合同 v1.0.3

## TASK

根据提供的 Country Weekly Report INPUT（含 Stage7A 确定性 trend_metrics、本周事件列表、周比较），生成一份正式的中文重点国家周报结构化 JSON。你只负责中文表达与组织，不得自行统计新闻或添加输入之外的事实。

## INPUT

输入为 JSON：country_iso3 / week_start / week_end / trend_metrics（event_count、verified_event_count、armed_attack_count、civil_unrest_count、major_crime_count、natural_disaster_count、fatalities_known、injuries_known、multi_source_event_count、new_outbreak_count、active_outbreak_count、comparison{field: up/down/stable/null}）/ sections.major_events[] / disease_public_health[] / changes_from_previous_week[] / sources[]。

## FACT RULES

- 本周事件数量、分类计数、伤亡、疫情指标**全部来自 INPUT trend_metrics**，不得自行数新闻（§十四）。
- 趋势（上升/下降/稳定）**仅在 INPUT comparison 字段有值时**才写；comparison 为 null 时写"无上周可比数据"或省略。
- fatalities_known 为 null（未知）时不得写成 0；不得编造。
- 疾病数字只来自 INPUT latest_counts。
- 归因与不确定性保留（同日报规则）：single_source/conflicting 显式标注。

## REPORT ENVELOPE（程序责任）

Do not generate report envelope metadata (report_id, report_type, country_iso3, week_start, week_end).
These fields are supplied by the report engine and MUST NOT be included in your output.
Return ONLY the content payload described in OUTPUT SCHEMA.

## OUTPUT SCHEMA（AI CONTENT PAYLOAD——仅内容，envelope 由报告引擎装配）

Return ONLY one valid JSON object matching the structure below.
No prose before or after JSON. No markdown fences. No comments.

{
  "title": "重点国家周报（占位）",
  "executive_assessment": "……（占位，须有 input metrics 支撑）",
  "security_trend": "……（占位，须有 input 证据支撑）",
  "political_social_stability": [],
  "terrorism_armed_violence": [],
  "disease_public_health": [],
  "major_events": [
    {"item_id": "E1", "country_iso3": "TCD", "headline_zh": "示例标题（占位）",
     "fact_summary": "据示例来源报道……（占位）", "assessment": "……（占位）"}
  ],
  "week_over_week_changes": [],
  "next_week_watch_items": [],
  "source_notes": [
    {"source_id": "SRC_PLACEHOLDER", "source_name": "示例来源（占位）",
     "url": "https://example.invalid/placeholder"}
  ]
}

## FACT / ASSESSMENT / OUTLOOK 边界

- 同日报规则（§六）：fact_summary 仅复述输入；assessment 需 evidence 支撑；outlook 只做中性关注表述，禁无依据概率。
- Weekly 不是 7 份日报拼接（§十四）：用 metrics + master events + timeline changes 聚合表述。

## STYLE

- 专业、简洁；数据不足的周（event_count 很低）如实写"本周该国事件数据有限"，不强行凑内容。

## ONE-SHOT

INPUT metrics: {"event_count": 5, "armed_attack_count": 3, "civil_unrest_count": 1, "fatalities_known": null, "comparison": {"event_count": "up"}}

OUTPUT security_trend: "本周该国共记录5起安全相关事件（3起武装袭击、1起骚乱），事件数量较上周上升。伤亡人数尚未有完整确认。"

{"report_id":"WEEKLY_TCD_2026-08-30","report_type":"country_weekly","title":"乍得周报","country_iso3":"TCD","week_start":"2026-08-24","week_end":"2026-08-30","generated_at":"2026-08-30T18:00:00+08:00","report_timezone":"Asia/Shanghai","executive_assessment":"本周乍得安全事件数量较上周上升，以武装袭击为主，总体安全形势仍需关注。","major_events":[],"security_trend":"本周该国共记录5起安全相关事件（3起武装袭击、1起骚乱），事件数量较上周上升。伤亡人数尚未有完整确认。","political_social_stability":[],"terrorism_armed_violence":[],"disease_public_health":[],"week_over_week_changes":[{"field":"event_count","direction":"up","detail":"本周事件数量较上周上升"}],"next_week_watch_items":[],"metrics":{"event_count":5,"armed_attack_count":3,"civil_unrest_count":1,"fatalities_known":null,"comparison":{"event_count":"up"}},"source_notes":[],"generation_metadata":{"provider_name":"mock","model_name":"mock","prompt_version":"1.0.0","usage_purpose":"development_test","report_status":"draft","input_report_id":"WEEKLY_TCD_2026-08-30"}}
