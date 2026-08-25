#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 4 — C 包 Hy3 桥接 Provider 审计测试（§十一 新增）。

覆盖：
- 注册：get_provider("hy3") 返回 Hy3Stage4Provider；list_providers / VALID_PROVIDERS 含 "hy3"；
- produce：enqueue_event 入队合法 AI 任务（通过 validate_ai_task）、写 Prompt 文件、维护索引；
- collect-missing：消费者尚未写回 -> 抛 ProviderTerminalError（绝不伪造 / 绝不回退 Mock）；
- collect-success：从 data/ai/completed 读取真实结果并以统一结构返回（ok=True，严格 JSON 通过）；
- 端到端：EnrichmentProcessor + 桥接 Provider（collect）装配 enrichment_results.json，
  记录 ai_provider="hy3"、ai_model 与 expected_model 一致、processing_status=succeeded；
- 安全：本 Provider 模块不导入任何网络库（socket/requests/urllib），不伪造 token 用量。
"""

import json
import os
import sys
import shutil
import tempfile
import unittest
import re
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "ai"))

from ai.hy3_stage4_provider import Hy3Stage4Provider
from ai.prompt_contract import load_prompt_contract
from ai.enrichment_processor import EnrichmentProcessor
from ai.enrichment_validator import parse_json_response_strict, MODEL_OUTPUT_FIELDS
from ai.enrichment_eligibility import eligibility_status
from ai.contracts import validate_ai_task, validate_ai_result
from ai.schema_validation import validate_against_schema
from ai.registry import list_providers, get_provider
from ai import config as _config

PROMPT_PATH = os.path.join(ROOT, "config", "prompts", "stage4_event_enrichment_v1.md")
SCHEMA_PATH = os.path.join(ROOT, "schemas", "ai_enrichment.schema.json")
PAYLOAD_SCHEMA_PATH = os.path.join(ROOT, "schemas", "ai_enrichment_payload.schema.json")


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_payload_schema():
    with open(PAYLOAD_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def schema_validate(parsed):
    # 与 test_stage4_ai_contract 一致：校验模型语义载荷（payload schema），
    # 而非完整记录 schema（完整记录在组装后单独校验）
    errs = validate_against_schema(parsed, load_payload_schema())
    return (len(errs) == 0, errs)


def mk_event(eid="EVT_1234567890abcdef", country_iso3="TCD", body="word " * 40,
             title="Attack", bs="full_body", wc=40,
             url="https://example.com/2026/08/01/x", **kw):
    e = {
        "event_id": eid, "primary_country": "乍得",
        "country_code": "TD", "country_iso3": country_iso3,
        "canonical_url": url, "body_status": bs,
        "body_extracted": body, "article_word_count": wc,
        "event_time": "2026-08-01T09:00:00+08:00",
        "original_title": title,
        "canonical_run_id": "20260802T084000+0800_084349",
    }
    e.update(kw)
    return e


def write_consumer_result(completed_dir, task_id, result_payload, model="hy3"):
    """模拟消费者会话（内置模型）把真实结果写回 completed。"""
    os.makedirs(completed_dir, exist_ok=True)
    ai_result = {
        "task_id": task_id,
        "schema_version": "1.0",
        "status": "success",
        "provider": "workbuddy_queue",
        "model": model,
        "started_at": "2026-08-02T00:00:00+00:00",
        "completed_at": "2026-08-02T00:00:05+00:00",
        "result": result_payload,
        "error": None,
        "usage": {"input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0},
    }
    path = os.path.join(completed_dir, "%s.json" % task_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"ai_result": ai_result}, f, ensure_ascii=False, indent=2)
    return ai_result


def valid_payload(iso3="TCD", summary="本事件为基于输入正文生成的测试中文摘要，用于验证桥接。"):
    """构造一个通过 ai_enrichment_payload.schema.json 的合法语义载荷。"""
    return {
        "source_language": "fr",
        "title_zh": "乍得袭击事件验证",
        "summary_zh": summary,
        "event_type": "other_security",
        "country_iso3": iso3,
        "location": {"country_iso3": iso3, "admin1": None, "city": None,
                     "site": None, "raw_text": ""},
        "key_facts": [{"fact": "测试事实描述内容充分", "evidence_field": "body_extracted",
                       "evidence_excerpt": ""}],
        "uncertainties": [],
        "security_relevance": "direct",
        "classification_confidence": 70,
    }


class TestRegistryWiring(unittest.TestCase):
    """注册与配置枚举。"""

    def test_hy3_registered(self):
        self.assertIn("hy3", list_providers())

    def test_get_provider_hy3(self):
        p = get_provider("hy3")
        self.assertIsInstance(p, Hy3Stage4Provider)

    def test_valid_providers_includes_hy3(self):
        self.assertIn("hy3", _config.VALID_PROVIDERS)

    def test_provider_name_and_model(self):
        p = get_provider("hy3")
        self.assertEqual(p.provider_name, "hy3")
        # 默认 expected_model 取自配置 ai_model（仓库默认 hy3）
        self.assertTrue(isinstance(p.model_name, str) and p.model_name)


class TestProducerEnqueue(unittest.TestCase):
    """produce 阶段：入队合法任务 + 写 Prompt + 索引。"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.pc = load_prompt_contract(PROMPT_PATH)
        self.prov = Hy3Stage4Provider(ai_root=self.root, mode="produce")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_enqueue_creates_valid_task(self):
        ev = mk_event()
        tid = self.prov.enqueue_event(ev, self.pc)
        self.assertTrue(tid.startswith("AIT_"))
        # 队列中应存在该任务且通过契约
        qpath = os.path.join(self.root, "queue", "%s.json" % tid)
        self.assertTrue(os.path.exists(qpath))
        task = json.load(open(qpath, encoding="utf-8"))
        self.assertEqual(validate_ai_task(task), [])
        # provider_requested 必须为交接层 workbuddy_queue（契约不变）
        self.assertEqual(task["provider_requested"], "workbuddy_queue")

    def test_enqueue_writes_prompt_and_index(self):
        ev = mk_event()
        tid = self.prov.enqueue_event(ev, self.pc)
        ppath = os.path.join(self.root, "hy3_prompts", "%s.json" % tid)
        self.assertTrue(os.path.exists(ppath))
        prec = json.load(open(ppath, encoding="utf-8"))
        self.assertIn("prompt_text", prec)
        self.assertEqual(prec["event_id"], ev["event_id"])
        self.assertEqual(prec["expected_model"], self.prov.expected_model)
        # 索引可回查 task_id
        self.assertEqual(self.prov._index[ev["event_id"]]["task_id"], tid)

    def test_produce_is_idempotent(self):
        ev = mk_event()
        t1 = self.prov.enqueue_event(ev, self.pc)
        t2 = self.prov.enqueue_event(ev, self.pc)
        self.assertEqual(t1, t2, "相同事件重复入队应幂等（同一 task_id）")


class TestCollectBehavior(unittest.TestCase):
    """collect 阶段：缺失抛错，命中返回真实结果；绝不伪造。"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.pc = load_prompt_contract(PROMPT_PATH)
        self.produce = Hy3Stage4Provider(ai_root=self.root, mode="produce")
        self.collect = Hy3Stage4Provider(ai_root=self.root, mode="collect")
        self.ev = mk_event()
        self.tid = self.produce.enqueue_event(self.ev, self.pc)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_collect_missing_raises_terminal(self):
        from ai.stage4_provider import ProviderTerminalError
        with self.assertRaises(ProviderTerminalError):
            self.collect.generate_structured(self.pc.render(self.ev))

    def test_collect_returns_real_result(self):
        payload = valid_payload("TCD")
        write_consumer_result(os.path.join(self.root, "completed"), self.tid, payload)
        resp = self.collect.generate_structured(self.pc.render(self.ev))
        self.assertTrue(resp["ok"])
        parsed, _, err = parse_json_response_strict(resp["raw_text"], strict=True)
        self.assertIsNone(err)
        self.assertIn("title_zh", parsed)
        # 用量不得伪造
        self.assertEqual(resp["token_usage"],
                         {"input_tokens": 0, "output_tokens": 0,
                          "estimated_cost_usd": 0.0})
        # 结果须与消费者写回一致（不篡改、不编造）
        self.assertEqual(parsed["summary_zh"], payload["summary_zh"])


class TestEndToEndWithProcessor(unittest.TestCase):
    """端到端：EnrichmentProcessor + 桥接 Provider（collect）装配结果。"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.pc = load_prompt_contract(PROMPT_PATH)
        self.produce = Hy3Stage4Provider(ai_root=self.root, mode="produce")
        self.ev = mk_event()
        self.tid = self.produce.enqueue_event(self.ev, self.pc)
        payload = valid_payload("TCD")
        self.model = self.produce.expected_model
        write_consumer_result(os.path.join(self.root, "completed"), self.tid,
                              payload, model=self.model)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_processor_assembles_real_result(self):
        collect = Hy3Stage4Provider(ai_root=self.root, mode="collect")
        proc = EnrichmentProcessor(collect, prompt_contract=self.pc,
                                  ai_root=self.root, schema_validator=schema_validate,
                                  run_id="20260802T084000+0800_084349")
        s = proc.process_events([self.ev])
        self.assertEqual(s["succeeded"], 1)
        results = json.load(open(os.path.join(self.root, "enrichment_results.json"),
                                encoding="utf-8"))
        rec = results["items"][0]
        # 真实 provider / model 被如实记录（非 mock）
        self.assertEqual(rec["ai_provider"], "hy3")
        self.assertEqual(rec["ai_model"], self.model)
        self.assertEqual(rec["processing_status"], "succeeded")
        self.assertEqual(rec["event_id"], self.ev["event_id"])
        # 记录通过 schema
        errs = validate_against_schema(rec, load_schema())
        self.assertEqual(errs, [], f"schema 错误: {errs[:5]}")


class TestNoNetworkAndNoFabrication(unittest.TestCase):
    """安全审计：本 Provider 不发起网络请求、不伪造。"""

    def test_no_network_imports(self):
        src = open(os.path.join(ROOT, "scripts", "ai", "hy3_stage4_provider.py"),
                   encoding="utf-8").read()
        self.assertNotIn("import socket", src)
        self.assertNotIn("import requests", src)
        self.assertNotIn("import urllib", src)
        self.assertNotIn("http.client", src)

    def test_health_check_reports_no_external_network(self):
        p = get_provider("hy3")
        hc = p.health_check()
        self.assertFalse(hc["external_network"])
        self.assertFalse(hc["ai_processing_enabled"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    n_run = result.testsRun
    n_fail = len(result.failures) + len(result.errors)
    print("RESULT: PASS=%d FAIL=%d" % (n_run - n_fail, n_fail))
    sys.exit(1 if n_fail else 0)
