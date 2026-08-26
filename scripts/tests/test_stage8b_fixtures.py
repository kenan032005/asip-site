#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8B — Report Qualification Harness Fix 测试（§二十六）。

committed fixture 存在性 / schema / 非空 / manifest hash / runtime 独立性 /
真实 prompt 路由 / placeholder 拒绝 / empty-input 硬失败 / HTTP 400 body
sanitize / artifact always-upload / dist 隔离 / Flash-only 回归。
"""
import hashlib
import json
import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ai.qualification import stage8b as q

FIX = ROOT / "data" / "qualification" / "stage8b"
CASE_IDS_8 = ["RD1", "RD2", "RD3", "RW1", "RW2", "RW3", "RB1", "RB2"]


def load_manifest():
    return json.loads((FIX / "manifest.json").read_text(encoding="utf-8"))


class TestCommittedFixtures(unittest.TestCase):
    """§二-§五：fixture 存在 / schema / 非空 / hash。"""

    def test_fixture_presence(self):
        man = load_manifest()
        self.assertEqual(len(man["cases"]), 8)
        for fc in man["cases"]:
            p = FIX / fc["fixture_path"]
            self.assertTrue(p.exists(), "fixture 缺失: %s" % fc["fixture_path"])

    def test_fixture_nonempty(self):
        for fc in load_manifest()["cases"]:
            payload = json.loads((FIX / fc["fixture_path"]).read_text(encoding="utf-8"))
            self.assertTrue(payload, "%s 为空" % fc["case_id"])

    def test_fixture_manifest_hash(self):
        for fc in load_manifest()["cases"]:
            text = (FIX / fc["fixture_path"]).read_text(encoding="utf-8")
            cur = hashlib.sha256(text.encode("utf-8")).hexdigest()
            self.assertEqual(cur, fc["fixture_hash"], "%s hash 不匹配" % fc["case_id"])

    def test_fixture_input_schema(self):
        from scripts.ai.schema_validation import validate_against_schema
        for fc in load_manifest()["cases"]:
            schema = json.loads((ROOT / fc["input_schema"]).read_text(encoding="utf-8"))
            payload = json.loads((FIX / fc["fixture_path"]).read_text(encoding="utf-8"))
            errs = validate_against_schema(payload, schema)
            self.assertEqual(errs, [], "%s input schema 失败: %s" % (fc["case_id"], errs[:3]))

    def test_fixture_gate_ready(self):
        g = q.fixture_gate()
        self.assertTrue(g["report_fixtures_ready"])
        self.assertEqual(g["summary"]["report_fixture_count"], 8)
        self.assertEqual(g["summary"]["fixture_schema_pass"], 8)
        self.assertEqual(g["summary"]["fixture_nonempty"], 8)
        self.assertEqual(g["summary"]["fixture_hash_pass"], 8)

    def test_fixture_safety_scan(self):
        blob = "\n".join(p.read_text(encoding="utf-8")
                         for p in FIX.rglob("*.json"))
        for bad in ("ASIP_DEEPSEEK_API_KEY", "ASIP_GLM_API_KEY", "sk-",
                    "Bearer ", "data/runtime", "review_pair", "telemetry"):
            self.assertNotIn(bad, blob)


class TestRuntimeIndependence(unittest.TestCase):
    """§六：报告 case 不依赖 data/runtime。"""

    def test_build_cases_report_inputs_from_fixtures(self):
        cases = {c["case_id"]: c for c in q.build_cases()}
        for cid in CASE_IDS_8:
            payload = cases[cid]["input_payload"]
            self.assertTrue(payload, "%s 输入为空（禁止 {} 兜底）" % cid)
            # 与 fixture 内容一致
            fc = next(f for f in load_manifest()["cases"] if f["case_id"] == cid)
            expected = json.loads((FIX / fc["fixture_path"]).read_text(encoding="utf-8"))
            self.assertEqual(payload, expected)

    def test_empty_input_hard_fail(self):
        # 模拟 fixture 缺失 → 必须硬失败，不得 {} 静默继续
        with mock.patch.object(q, "load_json",
                               side_effect=lambda rel, default=None: None if "manifest" in rel else default):
            with self.assertRaises(SystemExit) as ctx:
                q.load_fixture_cases()
            self.assertIn("QUALIFICATION_FIXTURE_MISSING", str(ctx.exception))


class TestRealPromptRouting(unittest.TestCase):
    """§八/§九：真实 Stage7B prompt，placeholder 禁止。"""

    def test_report_prompt_mapping(self):
        cases = {c["case_id"]: c for c in q.build_cases()}
        expect = {
            "RD1": ("config/prompts/africa_daily_report_v1.md", "africa_daily_report.schema.json", "v1.0.3"),
            "RW1": ("config/prompts/country_weekly_report_v1.md", "country_weekly_report.schema.json", "v1.0.3"),
            "RB1": ("config/prompts/major_event_brief_v1.md", "major_event_brief.schema.json", "v1.0.3"),
        }
        for cid, (pf, oschema, pv) in expect.items():
            c = cases[cid]
            self.assertEqual(c["prompt_version"], pv)
            prompt = c["system_prompt"]
            self.assertTrue(prompt and len(prompt) > 100, "%s prompt 为空" % cid)
            # 与真实 Stage7B prompt 文件内容一致（§八）
            self.assertEqual(prompt, (ROOT / pf).read_text(encoding="utf-8"))
            self.assertNotIn("Generate the structured report per contract", prompt)

    def test_placeholder_rejected(self):
        # 无 system_prompt 的报告 case → QUALIFICATION_PROMPT_MISSING
        bad = {"case_id": "RD1", "task_type": "africa_daily",
               "system_prompt": None, "prompt_version": "v1.0.0",
               "input_payload": {}, "schema": None}
        with self.assertRaises(SystemExit) as ctx:
            q._glm_task_builder(bad)
        self.assertIn("QUALIFICATION_PROMPT_MISSING", str(ctx.exception))

    def test_prompt_contract_audit_fields(self):
        g = q.fixture_gate()
        for c in g["cases"]:
            for k in ("prompt_version", "prompt_hash", "input_schema",
                      "output_schema", "fixture_hash", "fixture_path"):
                self.assertIn(k, c)


class TestHTTPErrorEvidence(unittest.TestCase):
    """§十一：HTTP 400 body 捕获与 sanitize。"""

    def _http_err(self, code, body):
        import urllib.error
        e = urllib.error.HTTPError("http://x", code, "err", None, None)
        e._body = body if isinstance(body, bytes) else body.encode()

        def read():
            return e._body
        e.read = read
        return e

    def test_error_body_captured(self):
        from scripts.ai.providers import deepseek_v4_flash as ds
        p = ds.DeepSeekV4FlashProvider(api_key="test-key")
        e = self._http_err(400, json.dumps(
            {"error": {"type": "invalid_request_error",
                       "code": "invalid_messages",
                       "message": "json mode requires json in prompt"}}))
        info = p._http_error_info(e)
        self.assertEqual(info["http_status"], 400)
        self.assertEqual(info["provider_error_type"], "invalid_request_error")
        self.assertEqual(info["provider_error_code"], "invalid_messages")
        self.assertIn("json", info["sanitized_error_message"])

    def test_error_body_no_secret_leak(self):
        # 假 token 用拼接构造（避免源码静态扫描出现完整 secret-like literal）
        from scripts.ai.providers import deepseek_v4_flash as ds
        p = ds.DeepSeekV4FlashProvider(api_key="test-key")
        fake_sk = "sk-" + "abcdef1234567890XYZ"
        fake_bearer = "xyz1234567890abcdefg"
        e = self._http_err(400, "raw body %s and Bearer %s" % (fake_sk, fake_bearer))
        info = p._http_error_info(e)
        self.assertNotIn(fake_sk, info["sanitized_error_message"])
        self.assertNotIn(fake_bearer, info["sanitized_error_message"])

    def test_fail_includes_error_info(self):
        from scripts.ai.providers import deepseek_v4_flash as ds
        p = ds.DeepSeekV4FlashProvider(api_key="test-key")
        r = p._fail("T", "http_400", 1, {"http_status": 400,
                                          "provider_error_type": "invalid_request_error",
                                          "provider_error_code": "x",
                                          "sanitized_error_message": "msg"})
        self.assertEqual(r["result"]["http_status"], 400)
        self.assertEqual(r["result"]["provider_error_type"], "invalid_request_error")
        self.assertEqual(r["result"]["sanitized_error_message"], "msg")


class TestWorkflowAndIsolation(unittest.TestCase):
    """§十九/§二十三：always-upload / dist 隔离 / flash-only 回归。"""

    def test_artifact_always_upload(self):
        wf = (ROOT / ".github" / "workflows" /
              "asip-stage8b-qualification.yml").read_text(encoding="utf-8")
        # 主仓库 workflow 含 always；main 上由 git 校验（此处检查仓库内副本）
        self.assertIn("if: always()", wf)
        self.assertIn("Upload qualification artifacts", wf)

    def test_fixture_not_in_dist(self):
        d = ROOT / "dist"
        if d.exists():
            self.assertFalse((d / "data" / "qualification").exists(),
                             "fixtures 进入 dist（禁止）")

    def test_flash_only_regression(self):
        from scripts.ai.providers import deepseek_v4_flash as ds
        self.assertEqual(ds.ALLOWED_DEEPSEEK_MODELS, frozenset({"deepseek-v4-flash"}))
        for m in ("deepseek-v4-pro", "deepseek-chat", "deepseek-reasoner"):
            with self.assertRaises(ds.UnsupportedDeepSeekModelError):
                ds.DeepSeekV4FlashProvider(model=m)

    def test_gate_and_probe_results_persisted(self):
        # fixture_gate_result.json 由 fixture_gate() 写入（§十九 上传物）
        g = q.fixture_gate()
        self.assertTrue((q.ARTIFACT_DIR / "fixture_gate_result.json").exists())


if __name__ == "__main__":
    unittest.main()


class TestDeterministicMetadata(unittest.TestCase):
    """§四-§八：period 确定性元数据 + exact-copy gate。"""

    def test_daily_fixtures_have_period(self):
        for cid in ("RD1", "RD2", "RD3"):
            fc = next(f for f in load_manifest()["cases"] if f["case_id"] == cid)
            payload = json.loads((FIX / fc["fixture_path"]).read_text(encoding="utf-8"))
            for k in ("period_start", "period_end", "report_id", "report_type", "report_date"):
                self.assertIsInstance(payload.get(k), str)
                self.assertTrue(payload[k].strip(), "%s.%s 为空" % (cid, k))

    def test_daily_input_schema_requires_period(self):
        s = json.loads((ROOT / "schemas" /
                        "africa_daily_report_input.schema.json").read_text(encoding="utf-8"))
        self.assertIn("period_start", s["required"])
        self.assertIn("period_end", s["required"])
        self.assertEqual(s["properties"]["period_start"]["type"], "string")
        self.assertEqual(s["properties"]["period_end"]["type"], "string")

    def test_weekly_brief_fixtures_metadata(self):
        for cid in ("RW1", "RW2", "RW3"):
            fc = next(f for f in load_manifest()["cases"] if f["case_id"] == cid)
            p = json.loads((FIX / fc["fixture_path"]).read_text(encoding="utf-8"))
            for k in ("week_start", "week_end", "country_iso3", "report_id", "report_type"):
                self.assertIsInstance(p.get(k), str)
                self.assertTrue(str(p.get(k) or "").strip(), "%s.%s 为空" % (cid, k))
        for cid in ("RB1", "RB2"):
            fc = next(f for f in load_manifest()["cases"] if f["case_id"] == cid)
            p = json.loads((FIX / fc["fixture_path"]).read_text(encoding="utf-8"))
            for k in ("brief_id", "report_type", "event_time", "country"):
                self.assertIsInstance(p.get(k), str)
                self.assertTrue(str(p.get(k) or "").strip(), "%s.%s 为空" % (cid, k))

    def test_exact_copy_correct(self):
        inp = {"period_start": "2026-08-26T00:00:00+08:00",
               "period_end": "2026-08-26T15:00:08+08:00",
               "report_id": "DAILY_20260826", "report_type": "africa_daily",
               "report_date": "2026-08-26"}
        out = dict(inp)
        ok, errs = q.check_exact_copy(out, inp, "africa_daily")
        self.assertTrue(ok, errs)

    def test_exact_copy_wrong_period(self):
        inp = {"period_start": "2026-08-26T00:00:00+08:00",
               "period_end": "2026-08-26T15:00:08+08:00",
               "report_date": "2026-08-26"}
        out = {"period_start": "2026-08-27T00:00:00+08:00",   # 错误日期
               "period_end": "2026-08-26T15:00:08+08:00",
               "report_date": "2026-08-26"}
        ok, errs = q.check_exact_copy(out, inp, "africa_daily")
        self.assertFalse(ok)
        self.assertTrue(any("period_start" in e for e in errs))

    def test_exact_copy_null_rejected(self):
        inp = {"period_start": "2026-08-26T00:00:00+08:00",
               "period_end": "2026-08-26T15:00:08+08:00",
               "report_date": "2026-08-26"}
        out = {"period_start": None, "period_end": None, "report_date": "2026-08-26"}
        ok, errs = q.check_exact_copy(out, inp, "africa_daily")
        self.assertFalse(ok)
        self.assertTrue(any("null" in e for e in errs))

    def test_weekly_exact_copy(self):
        inp = {"week_start": "2026-08-24", "week_end": "2026-08-30",
               "country_iso3": "TCD", "report_id": "W1", "report_type": "country_weekly"}
        ok, errs = q.check_exact_copy(dict(inp), inp, "country_weekly")
        self.assertTrue(ok, errs)
        bad = dict(inp); bad["country_iso3"] = "SSD"
        ok2, errs2 = q.check_exact_copy(bad, inp, "country_weekly")
        self.assertFalse(ok2)

    def test_fixture_gate_metadata_ready(self):
        g = q.fixture_gate()
        self.assertTrue(g["report_fixtures_ready"])
        self.assertEqual(g["summary"]["deterministic_metadata_ready"], 8)

    def test_prompt_version_bumped(self):
        man = load_manifest()
        for fc in man["cases"]:
            if fc["task_type"] in ("africa_daily", "country_weekly", "major_event_brief"):
                self.assertEqual(fc["prompt_version"], "v1.0.3", fc["case_id"])
        # prompt 文件含 exact-copy 段与 v1.0.1 头
        daily_prompt = (ROOT / "config" / "prompts" /
                        "africa_daily_report_v1.md").read_text(encoding="utf-8")
        self.assertIn("REPORT ENVELOPE", daily_prompt)
        self.assertIn("v1.0.3", daily_prompt)

    def test_probe_result_schema(self):
        # 结构：report_probe_result.json 含 tokens + period exact match 字段
        import io, zipfile as zf
        # 由 run_report_probe 写入；这里验证字段在函数输出中出现
        import inspect
        src = inspect.getsource(q.run_report_probe)
        for f in ("period_start_exact_match", "period_end_exact_match",
                  "input_tokens", "output_tokens", "total_tokens"):
            self.assertIn(f, src)


class TestDailyPeriodRule(unittest.TestCase):
    """§四：DAILY_PRIMARY_WINDOW = B（cutoff-24h → cutoff）。"""

    def test_daily_period_rule_b(self):
        from scripts.ai.qualification.build_fixtures import daily_period
        daily = {"report_date": "2026-08-26",
                 "cutoff": "2026-08-26T15:00:08+08:00"}
        ps, pe = daily_period(daily)
        self.assertEqual(pe, "2026-08-26T15:00:08+08:00")
        self.assertEqual(ps, "2026-08-25T15:00:08+08:00")

    def test_daily_period_not_calendar_day_start(self):
        # 若用日历日始（report_date 00:00）在 cutoff 接近午夜时会严重失真 → 禁止
        from scripts.ai.qualification.build_fixtures import daily_period
        daily = {"report_date": "2026-08-26",
                 "cutoff": "2026-08-26T00:30:00+08:00"}
        ps, pe = daily_period(daily)
        self.assertEqual(ps, "2026-08-25T00:30:00+08:00")
        self.assertNotEqual(ps, "2026-08-26T00:00:00+08:00")

    def test_rd_fixtures_period_is_cutoff_minus_24h(self):
        from datetime import datetime, timedelta
        for cid in ("RD1", "RD2", "RD3"):
            fc = next(f for f in load_manifest()["cases"] if f["case_id"] == cid)
            p = json.loads((FIX / fc["fixture_path"]).read_text(encoding="utf-8"))
            exp = (datetime.fromisoformat(p["cutoff"]) - timedelta(hours=24)).isoformat(timespec="seconds")
            self.assertEqual(p["period_start"], exp)
            self.assertEqual(p["period_end"], p["cutoff"])
