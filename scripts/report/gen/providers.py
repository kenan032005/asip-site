#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 7B §十七/§十八/§十九 — Provider-agnostic 报告生成 Providers。

- MockReportProvider（§十九）：确定性 fake——从 input facts 构造
  fact_summary/assessment/outlook（无真实 AI），用于 Mock Contract 测试
  与 pipeline 验证。
- DeepSeekReportProvider（§十八）：OpenAI 兼容通道（base_url 可指向
  DeepSeek / 任意兼容端点）；本地无 key → credential_unavailable，
  不伪造调用。
- 接口统一 generate(system, user) → (text, meta)；不绑定具体模型。
"""

import json
import os

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "config", "prompts")


class ProviderUnavailable(Exception):
    """凭据缺失或 provider 不可用。"""


class MockReportProvider:
    """§十九 Mock provider：确定性装配合同合规输出（不调用任何 AI）。

    从 input facts 构造 fact_summary / assessment / outlook / source_refs，
    仅回显 input 数字（保证 numeric evidence gate 通过）。
    """

    name = "mock"
    model = "mock-report-v1"

    def generate(self, system, user):
        try:
            data = json.loads(user)
        except json.JSONDecodeError:
            raise ProviderUnavailable("mock input not json")
        task_type = data.get("report_type")
        if task_type == "africa_daily":
            return json.dumps(self._mock_daily(data), ensure_ascii=False), \
                {"provider": self.name, "model": self.model}
        if task_type == "country_weekly":
            return json.dumps(self._mock_weekly(data), ensure_ascii=False), \
                {"provider": self.name, "model": self.model}
        if task_type == "major_event_brief":
            return json.dumps(self._mock_brief(data), ensure_ascii=False), \
                {"provider": self.name, "model": self.model}
        return json.dumps({"mock": True, "input_report_id": data.get("report_id", "")},
                          ensure_ascii=False), {"provider": self.name, "model": self.model}

    @staticmethod
    def _refs(ev):
        refs = []
        for se in (ev.get("source_evidence") or []):
            refs.append({"source_id": se.get("source_id"),
                         "source_name": se.get("source_name"),
                         "url": se.get("url")})
        if not refs and ev.get("source_id"):
            refs.append({"source_id": ev["source_id"]})
        return refs

    @staticmethod
    def _facts_text(ev):
        return "；".join(str(f.get("fact", "")) for f in (ev.get("facts") or [])) or \
            (ev.get("title_original") or ev.get("title") or "")

    def _mock_item(self, ev, with_facts=False):
        it = {
            "item_id": ev.get("event_id") or ev.get("master_event_id") or ev.get("disease_id"),
            "master_event_id": ev.get("master_event_id"),
            "country_iso3": ev.get("country_iso3") or ev.get("country"),
            "headline_zh": "（mock 占位标题）",
            "fact_summary": self._facts_text(ev) or "（mock 占位事实）",
            "assessment": "（mock 占位判断，待真实模型生成）",
            "outlook": "（mock 占位展望）",
            "verification_status": ev.get("verification_status") or ev.get("verification"),
            "uncertainties": ev.get("uncertainties") or [],
            "source_refs": self._refs(ev),
            "latest_update_at": ev.get("latest_update_at") or ev.get("published_at"),
            "importance_score": ev.get("importance_score") or 0,
            "selection_reasons": ev.get("selection_reasons") or [],
            "single_source_warning": bool(ev.get("single_source_warning")),
            "conflicting": bool(ev.get("conflicting")),
        }
        if with_facts:
            it["facts"] = ev.get("facts") or []
        return it

    def _mock_daily(self, data):
        sections = data.get("sections", {})
        report = {
            "report_id": data.get("report_id", "DAILY_MOCK"),
            "report_type": "africa_daily",
            "title": "非洲地区社会安全与综合形势日报（mock）",
            "report_date": data.get("report_date"),
            "period_start": None,
            "period_end": None,
            "generated_at": data.get("cutoff"),
            "report_timezone": "Asia/Shanghai",
            "executive_summary": [self._mock_item(ev)
                                  for ev in sections.get("executive_summary", [])],
            "major_security_developments": [self._mock_item(ev)
                                            for ev in sections.get("major_security_developments", [])],
            "political_social_stability": [self._mock_item(ev)
                                           for ev in sections.get("political_social_stability", [])],
            "terrorism_armed_violence": [self._mock_item(ev)
                                         for ev in sections.get("terrorism_armed_violence", [])],
            "cross_border_regional_risks": [self._mock_item(ev)
                                            for ev in sections.get("cross_border_regional", [])],
            "public_health_disease_risks": [self._mock_disease(ev)
                                            for ev in sections.get("public_health_disease", [])],
            "key_changes": [{"item_id": c.get("event_id") or c.get("master_event_id"),
                             "change_type": c.get("change_type", ""),
                             "fact_summary": "（mock）"}
                            for c in sections.get("key_changes", [])],
            "watch_items": [self._mock_item(ev) for ev in sections.get("watch_items", [])],
            "overall_assessment": "（mock 占位整体评估）",
            "source_notes": self._collect_sources(data),
            "generation_metadata": {"provider_name": self.name, "model_name": self.model,
                                    "prompt_version": "1.0.0",
                                    "usage_purpose": "development_test",
                                    "report_status": "draft",
                                    "input_report_id": data.get("report_id")},
        }
        return report

    def _mock_disease(self, ev):
        it = self._mock_item(ev)
        it["disease_id"] = ev.get("disease_id")
        it["latest_counts"] = ev.get("latest_counts") or {}
        it["as_of_date"] = ev.get("latest_counts") or {} and \
            (ev.get("latest_counts") or {}).get("as_of_date")
        return it

    def _mock_weekly(self, data):
        m = data.get("trend_metrics", {})
        report = {
            "report_id": data.get("report_id", "WEEKLY_MOCK"),
            "report_type": "country_weekly",
            "title": "重点国家周报（mock）",
            "country_iso3": data.get("country_iso3"),
            "week_start": data.get("week_start"),
            "week_end": data.get("week_end"),
            "generated_at": data.get("generated_at"),
            "report_timezone": "Asia/Shanghai",
            "executive_assessment": "（mock 占位周评估）",
            "major_events": [self._mock_item(ev)
                             for ev in data.get("sections", {}).get("major_events", [])],
            "security_trend": "（mock）本周事件数量 %s" % m.get("event_count", 0),
            "political_social_stability": [],
            "terrorism_armed_violence": [],
            "disease_public_health": [],
            "week_over_week_changes": [
                {"field": k, "direction": v}
                for k, v in (m.get("comparison") or {}).items() if v],
            "next_week_watch_items": [],
            "metrics": m,
            "source_notes": [{"source_id": s} for s in data.get("sections", {}).get("sources", [])],
            "generation_metadata": {"provider_name": self.name, "model_name": self.model,
                                    "prompt_version": "1.0.0",
                                    "usage_purpose": "development_test",
                                    "report_status": "draft",
                                    "input_report_id": data.get("report_id")},
        }
        return report

    def _mock_brief(self, data):
        report = {
            "brief_id": "BRF_%s" % data.get("event_id", "x"),
            "report_type": "major_event_brief",
            "title": "重大事件简报（mock）",
            "event_time": data.get("event_time"),
            "country": data.get("country"),
            "country_iso3": data.get("country_iso3"),
            "location": data.get("location"),
            "what_happened": "（mock 占位事件描述）",
            "confirmed_facts": [{"fact": f.get("fact"), "source_refs": [data.get("event_id")]}
                                for f in (data.get("facts") or [])],
            "uncertainties": data.get("uncertainties") or [],
            "verification_status": data.get("verification_status"),
            "verification_confidence": data.get("verification_confidence"),
            "immediate_implications": ["（mock 占位影响）"],
            "watch_items": ["（mock 占位关注点）"],
            "source_notes": [{"source_id": data.get("event_id")}],
            "generation_metadata": {"provider_name": self.name, "model_name": self.model,
                                    "prompt_version": "1.0.0",
                                    "usage_purpose": "development_test",
                                    "report_status": "draft",
                                    "input_report_id": data.get("event_id")},
        }
        return report

    @staticmethod
    def _collect_sources(data):
        seen, out = set(), []
        for sec in data.get("sections", {}).values():
            if not isinstance(sec, list):
                continue
            for ev in sec:
                for se in (ev.get("source_evidence") or []):
                    sid = se.get("source_id")
                    if sid and sid not in seen:
                        seen.add(sid)
                        out.append({"source_id": sid, "source_name": se.get("source_name")})
        return out


class DeepSeekReportProvider:
    """§十八 DeepSeek（OpenAI 兼容）provider。key 缺失 → ProviderUnavailable。"""

    name = "workbuddy_deepseek_v4_flash"
    model = "deepseek-v4-flash"

    def __init__(self, base_url=None, api_key=None, model=None, timeout=180):
        import urllib.request
        self._urllib = urllib.request
        self.base_url = base_url or os.environ.get(
            "ASIP_DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.api_key = api_key or os.environ.get(
            "ASIP_DEEPSEEK_API_KEY") or ""
        # Stage 8B：Flash-only 硬门禁。默认/任何未批准模型 → 配置错误。
        from scripts.ai.providers.deepseek_v4_flash import (
            ALLOWED_DEEPSEEK_MODELS, UnsupportedDeepSeekModelError)
        self.model = model or os.environ.get("ASIP_DEEPSEEK_MODEL", "deepseek-v4-flash")
        if self.model not in ALLOWED_DEEPSEEK_MODELS:
            raise UnsupportedDeepSeekModelError(
                "unsupported_deepseek_model: %r（仅允许 deepseek-v4-flash）" % self.model)
        self.timeout = int(os.environ.get("ASIP_DEEPSEEK_TIMEOUT_SECONDS", "180"))

    def generate(self, system, user):
        if not self.api_key:
            raise ProviderUnavailable("credential_unavailable: ASIP_DEEPSEEK_API_KEY missing")
        import json as _json
        import urllib.error
        payload = _json.dumps({
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }, ensure_ascii=False).encode("utf-8")
        req = self._urllib.Request(
            self.base_url + "/chat/completions", data=payload,
            headers={"Authorization": "Bearer %s" % self.api_key,
                     "Content-Type": "application/json"},
            method="POST")
        try:
            with self._urllib.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            raise ProviderUnavailable("http_%s" % e.code)
        data = _json.loads(body)
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        meta = {"provider": self.name, "model": data.get("model", self.model)}
        return content, meta


def make_provider(name=None):
    """按名称构造 provider；auto → key 存在用 DeepSeek，否则 mock。"""
    name = name or os.environ.get("ASIP_REPORT_PROVIDER", "auto")
    if name == "mock":
        return MockReportProvider()
    if name in ("deepseek", "workbuddy_deepseek_v4_flash"):
        return DeepSeekReportProvider()
    if name == "auto":
        dp = DeepSeekReportProvider()
        if dp.api_key:
            return dp
        return MockReportProvider()
    return MockReportProvider()
