#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 7B §十七 — Provider-agnostic Report Runner。

task_type → prompt → schema → provider。
不绑定 GLM/Hy3/DeepSeek；metadata 记录 provider_name/model_name/prompt_version/
usage_purpose（§十八 development_test）。

流程：
1. 读 input JSON（report input contract）
2. 装配 prompt（system=prompt md 全文，user=input JSON）
3. provider.generate → 文本
4. 解析严格 JSON → dict
5. 注入 generation_metadata
6. 返回 (report_dict, meta, ok)
"""

import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROMPTS_DIR = ROOT / "config" / "prompts"

from scripts.report.gen.providers import (  # noqa: E402
    make_provider, ProviderUnavailable,
)

# task_type → (prompt 文件, output schema 文件)
TASK_CONTRACT = {
    "africa_daily": ("africa_daily_report_v1.md", "africa_daily_report.schema.json"),
    "country_weekly": ("country_weekly_report_v1.md", "country_weekly_report.schema.json"),
    "major_event_brief": ("major_event_brief_v1.md", "major_event_brief.schema.json"),
}
PROMPT_VERSION = "1.0.0"
USAGE_PURPOSE = "development_test"


def _extract_json(text):
    """容错提取 JSON（去围栏/前后文本）。"""
    if not text:
        return None
    t = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(t[start:end + 1])
    except json.JSONDecodeError:
        return None


def load_prompt(task_type):
    fname, _ = TASK_CONTRACT[task_type]
    p = PROMPTS_DIR / fname
    if not p.exists():
        raise FileNotFoundError("prompt missing: %s" % p)
    return p.read_text(encoding="utf-8")


def run_report(task_type, report_input, provider=None, usage_purpose=None):
    """生成一份报告。report_input: dict（report input contract）。
    返回 (report_dict, meta, status)：
      status in ("generated", "mock_fallback", "failed")
    """
    fname, schema_name = TASK_CONTRACT[task_type]
    prompt = load_prompt(task_type)
    user = json.dumps(report_input, ensure_ascii=False)
    prov = provider or make_provider()
    meta = {"provider_name": prov.name, "model_name": prov.model,
            "prompt_version": PROMPT_VERSION,
            "usage_purpose": usage_purpose or USAGE_PURPOSE,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")}
    try:
        text, pm = prov.generate(prompt, user)
        meta.update(pm or {})
    except ProviderUnavailable as e:
        # §二十：credential 缺失 → 记录并回退 mock，不阻断工程合同
        meta["credential_status"] = str(e)
        prov_mock = make_provider("mock")
        text, pm = prov_mock.generate(prompt, user)
        meta.update(pm or {})
        meta["mock_fallback"] = True
        parsed = _extract_json(text)
        if parsed is None:
            return None, meta, "failed"
        parsed["generation_metadata"] = {
            **meta, "report_status": "draft"}
        return parsed, meta, "mock_fallback"
    parsed = _extract_json(text)
    if parsed is None:
        return None, meta, "failed"
    parsed["generation_metadata"] = {
        **meta, "report_status": "draft"}
    return parsed, meta, "generated"
