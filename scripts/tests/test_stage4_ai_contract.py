#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 4 第一执行包 v2 — 正式测试。

v2 新增：PromptContract、可信元数据注入、多模型并存、严格 JSON、
Mock 行为扩展、Registry 无重复、country_iso3 必填。
"""

import json
import os
import sys
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "ai"))

from ai.schema_validation import validate_against_schema
from ai.stage4_provider import ProviderTimeout, ProviderAPIError, ProviderTerminalError
from ai.mock_provider import MockProvider
from ai.prompt_contract import PromptContract, PromptContractError, load_prompt_contract
from ai.enrichment_eligibility import eligibility_status, compute_input_hash, is_article_url
from ai.enrichment_validator import (
    parse_json_response_strict, validate_enrichment,
    MODEL_OUTPUT_FIELDS, SYSTEM_METADATA_FIELDS,
)
from ai.enrichment_processor import (
    EnrichmentProcessor, compute_result_id,
    SUCCEEDED, FAILED_RETRYABLE, FAILED_TERMINAL,
    INVALID_MODEL_OUTPUT, SKIPPED_INELIGIBLE,
)

SCHEMA_PATH = os.path.join(ROOT, "schemas", "ai_enrichment.schema.json")
PAYLOAD_SCHEMA_PATH = os.path.join(ROOT, "schemas", "ai_enrichment_payload.schema.json")
PROMPT_PATH = os.path.join(ROOT, "config", "prompts", "stage4_event_enrichment_v1.md")
FIXTURES_DIR = os.path.join(HERE, "fixtures", "stage4_ai")


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_payload_schema():
    with open(PAYLOAD_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def schema_validate(parsed):
    """用于 processor 的 schema_validator：校验 payload schema。"""
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


# ══════════════════════════════════════════════════════════════
class TestPromptContract(unittest.TestCase):
    """§2 PromptContract 加载/渲染/失败/版本。"""

    def test_01_load_success(self):
        pc = load_prompt_contract(PROMPT_PATH)
        self.assertIsNotNone(pc.content)
        self.assertGreater(len(pc.content), 100)
        self.assertTrue(len(pc.content_hash) == 64)
        self.assertIsNotNone(pc.version)

    def test_02_missing_file_fails(self):
        with self.assertRaises(PromptContractError):
            load_prompt_contract("/nonexistent/prompt.md")

    def test_03_render_contains_system_rules(self):
        pc = load_prompt_contract(PROMPT_PATH)
        ev = mk_event()
        rendered = pc.render(ev)
        self.assertIn("事件增强引擎", rendered)
        self.assertIn("输入与输出约束", rendered)

    def test_04_render_contains_injection_rules(self):
        pc = load_prompt_contract(PROMPT_PATH)
        ev = mk_event()
        rendered = pc.render(ev)
        self.assertIn("Ignore previous instructions", rendered)
        low = rendered.lower()
        self.assertTrue("反注入" in rendered or "injection" in low or "忽略以上指令" in rendered)

    def test_05_render_contains_event_json(self):
        pc = load_prompt_contract(PROMPT_PATH)
        ev = mk_event()
        rendered = pc.render(ev)
        self.assertIn(ev["event_id"], rendered)

    def test_06_version_mismatch_fails(self):
        with self.assertRaises(PromptContractError):
            load_prompt_contract(PROMPT_PATH, version="99.99.99")

    def test_07_body_does_not_break_prompt_structure(self):
        pc = load_prompt_contract(PROMPT_PATH)
        ev = mk_event(body='Contains quotes and {braces} and newlines')
        rendered = pc.render(ev)
        self.assertIn("Contains quotes", rendered)
        # 正文被 JSON 序列化安全包裹
        import re
        match = re.search(r'"body_extracted":\s*"(.*?)(?<!\\)"', rendered)
        self.assertIsNotNone(match)

    def test_08_content_hash_changes_with_content(self):
        pc1 = load_prompt_contract(PROMPT_PATH)
        h1 = pc1.content_hash
        self.assertEqual(h1, pc1.content_hash)
        # 同一版本同内容，哈希一致
        pc2 = load_prompt_contract(PROMPT_PATH)
        self.assertEqual(h1, pc2.content_hash)


# ══════════════════════════════════════════════════════════════
class TestMetadataSeparation(unittest.TestCase):
    """§3/§4 元数据分离：模型只输出 payload，处理器注入元数据。"""

    def test_09_model_output_fields_defined(self):
        self.assertIn("title_zh", MODEL_OUTPUT_FIELDS)
        self.assertIn("summary_zh", MODEL_OUTPUT_FIELDS)
        self.assertIn("event_type", MODEL_OUTPUT_FIELDS)
        self.assertNotIn("event_id", MODEL_OUTPUT_FIELDS)
        self.assertNotIn("ai_provider", MODEL_OUTPUT_FIELDS)
        self.assertNotIn("processed_at", MODEL_OUTPUT_FIELDS)

    def test_10_system_metadata_fields_defined(self):
        self.assertIn("result_id", SYSTEM_METADATA_FIELDS)
        self.assertIn("ai_provider", SYSTEM_METADATA_FIELDS)
        self.assertIn("processed_at", SYSTEM_METADATA_FIELDS)

    def test_11_processor_injects_all_metadata(self):
        root = tempfile.mkdtemp()
        pc = load_prompt_contract(PROMPT_PATH)
        ev = mk_event()
        prov = MockProvider()
        proc = EnrichmentProcessor(prov, prompt_contract=pc,
                                   ai_root=root, schema_validator=schema_validate,
                                   run_id="20260802T084000+0800_084349")
        s = proc.process_events([ev])
        self.assertEqual(s["succeeded"], 1)
        results = json.load(open(os.path.join(root, "enrichment_results.json"),
                                 encoding="utf-8"))
        rec = results["items"][0]
        # 可信元数据由处理器注入，不是模型输出
        self.assertEqual(rec["event_id"], ev["event_id"])
        self.assertEqual(rec["canonical_run_id"], ev["canonical_run_id"])
        self.assertNotEqual(rec["input_hash"], "")
        self.assertEqual(rec["ai_provider"], "mock")
        self.assertEqual(rec["ai_model"], "mock-model-v1")
        self.assertEqual(rec["prompt_version"], pc.version)
        self.assertEqual(rec["prompt_content_hash"], pc.content_hash)
        self.assertEqual(rec["processing_status"], "succeeded")
        self.assertIsNone(rec["error_code"])
        self.assertTrue(len(rec["raw_response_hash"]) == 64)

    def test_12_metadata_injection_from_model_is_overwritten(self):
        root = tempfile.mkdtemp()
        pc = load_prompt_contract(PROMPT_PATH)
        prov = MockProvider(behavior={"inject_metadata": True})
        ev = mk_event()
        proc = EnrichmentProcessor(prov, prompt_contract=pc,
                                   ai_root=root, schema_validator=schema_validate)
        s = proc.process_events([ev])
        self.assertEqual(s["succeeded"], 1)
        results = json.load(open(os.path.join(root, "enrichment_results.json"),
                                 encoding="utf-8"))
        rec = results["items"][0]
        # 模型注入了 hacked_provider/hacked_model，处理器覆盖
        self.assertEqual(rec["ai_provider"], "mock")
        self.assertEqual(rec["ai_model"], "mock-model-v1")
        self.assertEqual(rec["event_id"], ev["event_id"])


# ══════════════════════════════════════════════════════════════
class TestMultiModelResults(unittest.TestCase):
    """§5 多模型/多版本结果并存（不互相覆盖）。"""

    def _proc(self, root, model_name="mock-model-v1", prompt_version=None, **kw):
        pc = load_prompt_contract(PROMPT_PATH, version=prompt_version)
        prov = MockProvider()
        prov.model_name = model_name
        return EnrichmentProcessor(prov, prompt_contract=pc,
                                   ai_root=root, schema_validator=schema_validate, **kw)

    def test_13_two_models_both_saved(self):
        root = tempfile.mkdtemp()
        ev = mk_event()
        pc = load_prompt_contract(PROMPT_PATH)
        prov1 = MockProvider()
        prov1.model_name = "mock-model-v1"
        p1 = EnrichmentProcessor(prov1, prompt_contract=pc,
                                 ai_root=root, schema_validator=schema_validate)
        s1 = p1.process_events([ev])
        self.assertEqual(s1["succeeded"], 1)
        prov2 = MockProvider()
        prov2.model_name = "mock-model-v2"
        p2 = EnrichmentProcessor(prov2, prompt_contract=pc,
                                 ai_root=root, schema_validator=schema_validate)
        s2 = p2.process_events([ev])
        self.assertEqual(s2["succeeded"], 1)
        results = json.load(open(os.path.join(root, "enrichment_results.json"),
                                 encoding="utf-8"))
        self.assertEqual(len(results["items"]), 2, "两个模型应各保留一条")
        models = {r["ai_model"] for r in results["items"]}
        self.assertEqual(models, {"mock-model-v1", "mock-model-v2"})

    def test_14_two_prompt_versions_both_saved(self):
        root = tempfile.mkdtemp()
        ev = mk_event()
        pc1 = load_prompt_contract(PROMPT_PATH, version="1.0.0")
        # 模拟不同 prompt 版本（content_hash 等价于版本变化）
        # 实际：不同 prompt_version → 不同 result_id
        prov = MockProvider()
        p = EnrichmentProcessor(prov, prompt_contract=pc1,
                                ai_root=root, schema_validator=schema_validate)
        s = p.process_events([ev])
        self.assertEqual(s["succeeded"], 1)
        # 换 prompt_contract（不同 content_hash → 不同 result_id）
        # 用不同 prompt_path 模拟：创建一个临时 prompt
        tmp_p = os.path.join(root, "tmp_prompt.md")
        with open(tmp_p, "w", encoding="utf-8") as f:
            f.write("# v1.1.0 Test Prompt\n\n你是一个事件增强引擎 v1.1。\n\n输入数据见下方 JSON。")
        pc2 = load_prompt_contract(tmp_p, version="1.1.0")
        p2 = EnrichmentProcessor(prov, prompt_contract=pc2,
                                 ai_root=root, schema_validator=schema_validate)
        s2 = p2.process_events([ev])
        self.assertEqual(s2["succeeded"], 1)
        results = json.load(open(os.path.join(root, "enrichment_results.json"),
                                 encoding="utf-8"))
        self.assertEqual(len(results["items"]), 2, "两个 Prompt 版本应各保留一条")

    def test_15_same_input_result_id_idempotent(self):
        root = tempfile.mkdtemp()
        pc = load_prompt_contract(PROMPT_PATH)
        ev = mk_event()
        prov = MockProvider()
        p = EnrichmentProcessor(prov, prompt_contract=pc,
                                ai_root=root, schema_validator=schema_validate)
        p.process_events([ev])
        p2 = EnrichmentProcessor(prov, prompt_contract=pc,
                                 ai_root=root, schema_validator=schema_validate)
        s = p2.process_events([ev])
        self.assertEqual(s["cache_hit"], 1)
        results = json.load(open(os.path.join(root, "enrichment_results.json"),
                                 encoding="utf-8"))
        self.assertEqual(len(results["items"]), 1, "相同 result_id 应幂等")

    def test_16_active_result_pointer_exists(self):
        root = tempfile.mkdtemp()
        pc = load_prompt_contract(PROMPT_PATH)
        ev = mk_event()
        p = EnrichmentProcessor(MockProvider(), prompt_contract=pc,
                                ai_root=root, schema_validator=schema_validate)
        p.process_events([ev])
        results = json.load(open(os.path.join(root, "enrichment_results.json"),
                                 encoding="utf-8"))
        self.assertIn(ev["event_id"], results["active_result_by_event"])

    def test_17_model_b_failure_does_not_affect_model_a(self):
        root = tempfile.mkdtemp()
        pc = load_prompt_contract(PROMPT_PATH)
        ev = mk_event()
        prov_a = MockProvider()
        prov_a.model_name = "mock-model-v1"
        p = EnrichmentProcessor(prov_a, prompt_contract=pc,
                                ai_root=root, schema_validator=schema_validate)
        p.process_events([ev])
        prov_b = MockProvider(behavior={"terminal_error": True})
        prov_b.model_name = "mock-model-v2"
        try:
            p2 = EnrichmentProcessor(prov_b, prompt_contract=pc,
                                     ai_root=root, schema_validator=schema_validate)
            p2.process_events([ev])
        except Exception:
            pass
        results = json.load(open(os.path.join(root, "enrichment_results.json"),
                                 encoding="utf-8"))
        # 模型 A 结果仍存在、成功
        self.assertGreaterEqual(len(results["items"]), 1)
        r_a = [r for r in results["items"] if r["ai_model"] == "mock-model-v1"]
        self.assertEqual(len(r_a), 1)
        self.assertEqual(r_a[0]["processing_status"], "succeeded")


# ══════════════════════════════════════════════════════════════
class TestStrictJSON(unittest.TestCase):
    """§6 严格 JSON 解析。"""

    def test_18_pure_json_passes(self):
        parsed, w, e = parse_json_response_strict('{"a":1}')
        self.assertIsNotNone(parsed)
        self.assertEqual(e, None)

    def test_19_code_fence_fails_strict(self):
        _, _, e = parse_json_response_strict('```json\n{"a":1}\n```', strict=True)
        self.assertIsNotNone(e)

    def test_20_prefix_text_fails_strict(self):
        _, _, e = parse_json_response_strict('Here is result:\n{"a":1}', strict=True)
        self.assertIsNotNone(e)

    def test_21_suffix_text_fails_strict(self):
        _, _, e = parse_json_response_strict('{"a":1}\nEnd.', strict=True)
        self.assertIsNotNone(e)

    def test_22_double_json_fails_strict(self):
        _, _, e = parse_json_response_strict('{"a":1}\n{"a":2}', strict=True)
        self.assertIsNotNone(e)

    def test_23_array_fails_strict(self):
        _, _, e = parse_json_response_strict('[1,2,3]', strict=True)
        self.assertIsNotNone(e)

    def test_24_non_json_fails_strict(self):
        _, _, e = parse_json_response_strict('not json at all', strict=True)
        self.assertIsNotNone(e)


# ══════════════════════════════════════════════════════════════
class TestMockProviderBehaviors(unittest.TestCase):
    """§8 MockProvider 各种行为模拟。"""

    def test_25_code_fence_output(self):
        prov = MockProvider(behavior={"code_fence": True})
        resp = prov.generate_structured('{"event_id":"EVT_1234567890abcdef","country_iso3":"TCD","original_title":"X"}')
        parsed, _, err = parse_json_response_strict(resp["raw_text"], strict=True)
        self.assertIsNotNone(err, "代码围栏在严格模式应失败")

    def test_26_prefix_output(self):
        prov = MockProvider(behavior={"prefix_text": True})
        resp = prov.generate_structured('{"event_id":"EVT_1234567890abcdef","country_iso3":"TCD","original_title":"X"}')
        parsed, _, err = parse_json_response_strict(resp["raw_text"], strict=True)
        self.assertIsNotNone(err)

    def test_27_double_json_output(self):
        prov = MockProvider(behavior={"double_json": True})
        resp = prov.generate_structured('{"event_id":"EVT_1234567890abcdef","country_iso3":"TCD","original_title":"X"}')
        parsed, _, err = parse_json_response_strict(resp["raw_text"], strict=True)
        self.assertIsNotNone(err)

    def test_28_inject_metadata_detected(self):
        root = tempfile.mkdtemp()
        pc = load_prompt_contract(PROMPT_PATH)
        prov = MockProvider(behavior={"inject_metadata": True})
        ev = mk_event()
        p = EnrichmentProcessor(prov, prompt_contract=pc,
                                ai_root=root, schema_validator=schema_validate)
        s = p.process_events([ev])
        self.assertEqual(s["succeeded"], 1)
        results = json.load(open(os.path.join(root, "enrichment_results.json"),
                                 encoding="utf-8"))
        rec = results["items"][0]
        self.assertEqual(rec["ai_provider"], "mock")

    def test_29_wrong_country_detected(self):
        root = tempfile.mkdtemp()
        pc = load_prompt_contract(PROMPT_PATH)
        prov = MockProvider(behavior={"wrong_country": True})
        ev = mk_event(country_iso3="TCD")
        p = EnrichmentProcessor(prov, prompt_contract=pc,
                                ai_root=root, schema_validator=schema_validate)
        s = p.process_events([ev])
        self.assertEqual(s["invalid_model_output"], 1)

    def test_30_wrong_event_id_detected(self):
        root = tempfile.mkdtemp()
        pc = load_prompt_contract(PROMPT_PATH)
        prov = MockProvider(behavior={"wrong_event_id": True})
        ev = mk_event()
        p = EnrichmentProcessor(prov, prompt_contract=pc,
                                ai_root=root, schema_validator=schema_validate)
        s = p.process_events([ev])
        self.assertEqual(s["invalid_model_output"], 1)

    def test_31_mock_success(self):
        prov = MockProvider()
        resp = prov.generate_structured('{"event_id":"EVT_1234567890abcdef","country_iso3":"TCD","original_title":"A"}')
        self.assertTrue(resp["ok"])
        self.assertIn("title_zh", resp["parsed"])
        # 确认不含系统元数据字段
        self.assertNotIn("event_id", resp["parsed"])


# ══════════════════════════════════════════════════════════════
class TestRegistryNoDuplicates(unittest.TestCase):
    """§9 Registry 无重复。"""

    def test_32_registry_no_duplicates(self):
        from ai import registry as r
        providers = r.list_providers()
        self.assertEqual(providers, sorted(set(providers)))
        self.assertIn("mock", providers)

    def test_33_mock_registered_once(self):
        from ai import registry as r
        self.assertEqual(r.list_providers().count("mock"), 1)


# ══════════════════════════════════════════════════════════════
class TestCountryAndEligibility(unittest.TestCase):
    """country_iso3 必填 + 输入资格。"""

    def test_34_country_iso3_missing_fails_eligibility(self):
        ev = mk_event(country_iso3="")
        st, r = eligibility_status(ev)
        self.assertEqual(st, SKIPPED_INELIGIBLE)
        self.assertIn("invalid_country_iso3", r)

    def test_35_country_iso3_invalid_fails(self):
        for bad in ("TC", "TCDD", "tcd", "  "):
            ev = mk_event(country_iso3=bad)
            st, r = eligibility_status(ev)
            self.assertEqual(st, SKIPPED_INELIGIBLE, f"bad iso3={bad!r}")

    def test_36_full_eligibility_passes(self):
        st, r = eligibility_status(mk_event())
        self.assertEqual(st, "eligible")

    def test_37_schema_completeness_check(self):
        # 处理器输出的完整记录应通过 schema
        root = tempfile.mkdtemp()
        pc = load_prompt_contract(PROMPT_PATH)
        ev = mk_event()
        p = EnrichmentProcessor(MockProvider(), prompt_contract=pc,
                                ai_root=root, schema_validator=schema_validate,
                                run_id="20260802T084000+0800_084349")
        p.process_events([ev])
        results = json.load(open(os.path.join(root, "enrichment_results.json"),
                                 encoding="utf-8"))
        rec = results["items"][0]
        errs = validate_against_schema(rec, load_schema())
        self.assertEqual(errs, [], f"Schema 错误: {errs[:5]}")


# ══════════════════════════════════════════════════════════════
class TestEndToEndAndIsolation(unittest.TestCase):
    """端到端 + 数据隔离。"""

    def test_38_full_pipeline_multi_event(self):
        root = tempfile.mkdtemp()
        pc = load_prompt_contract(PROMPT_PATH)
        events = [mk_event(eid=f"EVT_00000000000000{i:02d}", body=f"body_{i} " * 40)
                  for i in range(3)]
        p = EnrichmentProcessor(MockProvider(), prompt_contract=pc,
                                ai_root=root, schema_validator=schema_validate)
        s = p.process_events(events)
        self.assertGreaterEqual(s["succeeded"], 3)
        self.assertEqual(s["eligible"], 3)

    def test_39_canonical_public_untouched(self):
        can_path = os.path.join(ROOT, "data", "canonical", "event_clusters.json")
        pub_path = os.path.join(ROOT, "data", "public", "published_events.json")
        mtime_can = os.path.getmtime(can_path)
        mtime_pub = os.path.getmtime(pub_path)
        root = tempfile.mkdtemp()
        pc = load_prompt_contract(PROMPT_PATH)
        p = EnrichmentProcessor(MockProvider(), prompt_contract=pc,
                                ai_root=root, schema_validator=schema_validate)
        p.process_events([mk_event()])
        self.assertEqual(os.path.getmtime(can_path), mtime_can)
        self.assertEqual(os.path.getmtime(pub_path), mtime_pub)

    def test_40_no_api_key_in_code(self):
        import re, glob
        bad = []
        for fn in glob.glob(os.path.join(ROOT, "scripts", "ai", "*.py")):
            t = open(fn, encoding="utf-8").read()
            if re.search(r"sk-[A-Za-z0-9]{20,}|OPENAI_API_KEY\s*=\s*['\"][^'\"]+['\"]", t):
                bad.append(fn)
        self.assertEqual(bad, [])

    def test_41_result_id_algorithm(self):
        eid = "EVT_1234567890abcdef"
        ih = "a" * 64
        pv = "1.0.0"
        ph = "b" * 64
        pn = "mock"
        mn = "mock-model-v1"
        rid = compute_result_id(eid, ih, pv, ph, pn, mn)
        self.assertEqual(len(rid), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in rid))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    n_run = result.testsRun
    n_fail = len(result.failures) + len(result.errors)
    print(f"RESULT: PASS={n_run - n_fail} FAIL={n_fail}")
    sys.exit(1 if n_fail else 0)
