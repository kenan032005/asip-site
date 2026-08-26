# ASIP Major Event Brief — 生成合同 v1.0.0

## TASK

根据提供的 Major Event Brief INPUT（trigger candidate，含事件事实、验证状态、来源），生成一份正式的中文重大事件简报结构化 JSON。只处理公开事件事实与风险影响。

## INPUT

输入为 JSON：event_id / master_event_id / country / country_iso3 / event_type / event_time / location / trigger_score / trigger_reasons / verification / source_count / conflicting / facts[] / uncertainties[]。

## FACT RULES

- what_happened 与 confirmed_facts 只能来自 INPUT 事实。
- 数字必须来自 INPUT，不得新增。
- 归因保留：alleged/claimed/reportedly → 据称/声称；unconfirmed/single_source → 尚未证实/单一来源；conflicting → 不同来源说法不一。
- **不得自动包含**（§十五）：组织战术分析、武器能力推演、攻击方法建议、敏感行动细节扩写。只写公开事件事实与风险影响。

## OUTPUT SCHEMA（严格输出此结构，仅一个 JSON 对象）

{
  "brief_id": "from input",
  "report_type": "major_event_brief",
  "title": "中文标题",
  "event_time": "from input",
  "country": "from input",
  "country_iso3": "from input",
  "location": "from input",
  "what_happened": "公开事件事实描述",
  "confirmed_facts": [ {"fact": "...", "source_refs": ["source_id..."]} ],
  "uncertainties": ["..."],
  "verification_status": "from input",
  "verification_confidence": 0,
  "immediate_implications": ["风险影响，evidence 支撑"],
  "watch_items": ["后续关注点（中性）"],
  "source_notes": [ {"source_id": "...", "source_name": "...", "url": "..."} ],
  "generation_metadata": {"provider_name": "...", "model_name": "...", "prompt_version": "1.0.0", "usage_purpose": "development_test", "report_status": "draft", "input_report_id": "from input"}
}

## UNCERTAINTY / STYLE

- uncertainties 保留输入不确定性；immediate_implications 不得做无依据因果推断。
- 专业、克制、决策支持；禁媒体化标题党、禁 AI 口吻。

## ONE-SHOT

INPUT: {"event_id":"E1","country_iso3":"SSD","event_type":"armed_conflict","event_time":"2026-08-25T09:00:00+00:00","location":"CITY_ALPHA","trigger_score":70,"verification_status":"verified","source_count":2}

OUTPUT:
{"brief_id":"BRF_E1","report_type":"major_event_brief","title":"南苏丹CITY_ALPHA发生武装冲突","event_time":"2026-08-25T09:00:00+00:00","country":"南苏丹","country_iso3":"SSD","location":"CITY_ALPHA","what_happened":"南苏丹CITY_ALPHA发生武装冲突，多家来源报道。","confirmed_facts":[{"fact":"南苏丹CITY_ALPHA发生武装冲突","source_refs":["E1"]}],"uncertainties":[],"verification_status":"verified","verification_confidence":null,"immediate_implications":["事件显示当地安全形势存在波动，需关注后续官方调查"],"watch_items":["后续官方确认与安全形势发展"],"source_notes":[{"source_id":"E1"}],"generation_metadata":{"provider_name":"mock","model_name":"mock","prompt_version":"1.0.0","usage_purpose":"development_test","report_status":"draft","input_report_id":"E1"}}
