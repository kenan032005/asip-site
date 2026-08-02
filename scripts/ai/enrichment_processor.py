#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 4 — AI 增强处理器（状态机 + 幂等缓存 + 结果存储）。

状态机：
  pending → processing → succeeded
                        → failed_retryable（可重试）
                        → failed_terminal（不可重试）
                        → invalid_model_output
  未资格事件 → skipped_ineligible

约束：
- 单条失败不中断批次；
- 缓存键 = event_id + input_hash + prompt_version + ai_provider + ai_model；
- 相同输入/相同 Prompt/相同模型不重复调用；
- 正文变化 / Prompt 版本变化必须重新处理；
- 模型变化允许独立结果；
- 失败不覆盖已有成功结果；
- 写入原子化（临时文件 + os.replace）；
- runtime 缓存不入 Git、不进 dist。
"""

import json
import os
import tempfile
from pathlib import Path

from .stage4_provider import (
    ProviderTimeout,
    ProviderAPIError,
    ProviderTerminalError,
)
from .enrichment_eligibility import eligibility_status, compute_input_hash
from .enrichment_validator import parse_json_response, validate_enrichment

# 状态常量
PENDING = "pending"
PROCESSING = "processing"
SUCCEEDED = "succeeded"
FAILED_RETRYABLE = "failed_retryable"
FAILED_TERMINAL = "failed_terminal"
SKIPPED_INELIGIBLE = "skipped_ineligible"
INVALID_MODEL_OUTPUT = "invalid_model_output"

# 合法状态迁移
ALLOWED_TRANSITIONS = {
    PENDING: {PROCESSING, SKIPPED_INELIGIBLE, FAILED_TERMINAL},
    PROCESSING: {SUCCEEDED, FAILED_RETRYABLE, FAILED_TERMINAL, INVALID_MODEL_OUTPUT},
    FAILED_RETRYABLE: {PROCESSING, FAILED_TERMINAL},
}

# 默认 AI 输出目录（runtime，gitignore 排除）
DEFAULT_AI_ROOT = Path(__file__).resolve().parents[2] / "data" / "ai"


class EnrichmentProcessor:
    """事件增强处理器。"""

    def __init__(self, provider, prompt_version="1.0.0",
                 ai_root=None, schema_validator=None, run_id=None,
                 min_word_count=None):
        self.provider = provider
        self.prompt_version = prompt_version
        self.ai_root = Path(ai_root) if ai_root else DEFAULT_AI_ROOT
        self.schema_validator = schema_validator  # fn(parsed)->(ok, errors)
        self.run_id = run_id
        self.min_word_count = min_word_count
        self._state_path = self.ai_root / "enrichment_state.json"
        self._results_path = self.ai_root / "enrichment_results.json"
        self._cache_path = self.ai_root / "enrichment_cache.json"

    # ── 状态与持久化 ──────────────────────────────────────────
    def _load_state(self):
        if self._state_path.exists():
            try:
                return json.loads(self._state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"records": {}}

    def _save_state(self, state):
        self._atomic_write(self._state_path, state)

    def _load_results(self):
        if self._results_path.exists():
            try:
                return json.loads(self._results_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"items": []}

    def _save_results(self, results):
        self._atomic_write(self._results_path, results)

    def _load_cache(self):
        if self._cache_path.exists():
            try:
                return json.loads(self._cache_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"entries": {}}

    def _save_cache(self, cache):
        self._atomic_write(self._cache_path, cache)

    @staticmethod
    def _atomic_write(path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass

    # ── 缓存键 ────────────────────────────────────────────────
    def cache_key(self, event, input_hash):
        return "|".join([
            event.get("event_id", ""),
            input_hash,
            self.prompt_version,
            self.provider.provider_name,
            self.provider.model_name,
        ])

    # ── 处理入口 ──────────────────────────────────────────────
    def process_events(self, events, quarantine_ids=None):
        """批量处理；单条失败不中断。返回汇总 dict。"""
        state = self._load_state()
        results = self._load_results()
        cache = self._load_cache()

        summary = {"eligible": 0, "skipped": 0, "succeeded": 0,
                   "failed_retryable": 0, "failed_terminal": 0,
                   "invalid_model_output": 0, "cache_hit": 0, "cache_miss": 0}

        for event in events:
            eid = event.get("event_id", "")
            status, reason = eligibility_status(
                event, quarantine_ids=quarantine_ids, min_word_count=self.min_word_count)
            rec = state["records"].setdefault(eid, {})
            if status == "skipped_ineligible":
                rec.update({"status": SKIPPED_INELIGIBLE, "reason": reason})
                summary["skipped"] += 1
                continue

            summary["eligible"] += 1
            input_hash = compute_input_hash(event)
            key = self.cache_key(event, input_hash)

            # 缓存命中：相同输入+Prompt+模型
            if key in cache["entries"]:
                summary["cache_hit"] += 1
                rec.update({"status": cache["entries"][key].get("processing_status", SUCCEEDED),
                            "cache_hit": True, "input_hash": input_hash})
                continue
            summary["cache_miss"] += 1

            # 处理前记录：相同 key 是否已有成功缓存（失败不得覆盖）
            had_success_cache = (key in cache["entries"]
                                 and cache["entries"][key].get("processing_status") == SUCCEEDED)

            outcome = self._process_one(event, input_hash, key, rec, cache)
            results.setdefault("items", [])
            if outcome.get("status") == SUCCEEDED:
                # 存入结果集（幂等：按 event_id 替换）
                items = [r for r in results["items"] if r.get("event_id") != eid]
                items.append(outcome["record"])
                results["items"] = items
                cache["entries"][key] = outcome["record"]
                summary["succeeded"] += 1
            else:
                # 失败：不覆盖已有成功结果（相同 key 的缓存保持原样）
                if had_success_cache:
                    rec.update({"status": SUCCEEDED, "cache_hit": True,
                                "error_code": None})
                elif outcome["status"] == INVALID_MODEL_OUTPUT:
                    summary["invalid_model_output"] += 1
                elif outcome["status"] == FAILED_TERMINAL:
                    summary["failed_terminal"] += 1
                elif outcome["status"] == FAILED_RETRYABLE:
                    summary["failed_retryable"] += 1

        self._save_state(state)
        self._save_results(results)
        self._save_cache(cache)
        return summary

    def _process_one(self, event, input_hash, key, rec, cache):
        """处理单条；返回 outcome dict（status 等）。"""
        rec.update({"status": PROCESSING, "input_hash": input_hash,
                    "cache_key": key, "prompt_version": self.prompt_version,
                    "ai_provider": self.provider.provider_name,
                    "ai_model": self.provider.model_name})

        prompt_text = self._render_prompt(event)
        try:
            resp = self.provider.generate_structured(prompt_text)
        except ProviderTimeout:
            rec.update({"status": FAILED_RETRYABLE, "error_code": "PROVIDER_TIMEOUT"})
            return {"status": FAILED_RETRYABLE}
        except ProviderAPIError:
            rec.update({"status": FAILED_RETRYABLE, "error_code": "PROVIDER_API_ERROR"})
            return {"status": FAILED_RETRYABLE}
        except ProviderTerminalError:
            rec.update({"status": FAILED_TERMINAL, "error_code": "PROVIDER_TERMINAL_ERROR"})
            return {"status": FAILED_TERMINAL}
        except Exception as e:  # pragma: no cover
            rec.update({"status": FAILED_TERMINAL, "error_code": "UNEXPECTED:" + type(e).__name__})
            return {"status": FAILED_TERMINAL}

        parsed, warn, parse_err = parse_json_response(resp.get("raw_text", ""))
        if parse_err or parsed is None:
            rec.update({"status": INVALID_MODEL_OUTPUT, "error_code": "JSON:" + (parse_err or "parse"),
                        "warnings": warn})
            return {"status": INVALID_MODEL_OUTPUT}

        # Schema 校验（如提供）
        if self.schema_validator is not None:
            ok, schema_errors = self.schema_validator(parsed)
            if not ok:
                rec.update({"status": INVALID_MODEL_OUTPUT,
                            "error_code": "SCHEMA:" + ";".join(schema_errors[:5]),
                            "warnings": warn})
                return {"status": INVALID_MODEL_OUTPUT}

        # 语义校验
        ok, errors, warnings = validate_enrichment(
            parsed, event, expected_run_id=self.run_id)
        if not ok:
            rec.update({"status": INVALID_MODEL_OUTPUT,
                        "error_code": "SEMANTIC:" + ";".join(errors[:5]),
                        "warnings": warnings + warn})
            return {"status": INVALID_MODEL_OUTPUT}

        # 成功：补全元数据
        rec.update({"status": SUCCEEDED, "error_code": None, "warnings": warnings + warn,
                    "raw_response_hash": resp.get("raw_response_hash", "")})
        record = dict(parsed)
        record["processed_at"] = record.get("processed_at") or ""
        record["processing_status"] = SUCCEEDED
        record["error_code"] = None
        return {"status": SUCCEEDED, "record": record}

    def _render_prompt(self, event):
        """渲染 prompt 文本（简化渲染，字段插入 JSON 安全转义）。"""
        def esc(v):
            if v is None:
                return ""
            return str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

        return json.dumps({
            "event_id": event.get("event_id", ""),
            "canonical_run_id": self.run_id or "",
            "primary_country": event.get("primary_country", ""),
            "country_iso3": event.get("country_iso3", ""),
            "original_title": event.get("original_title", ""),
            "source_language": event.get("source_language", "unknown"),
            "event_time": event.get("event_time", ""),
            "canonical_url": event.get("canonical_url", ""),
            "body_extracted": event.get("body_extracted", ""),
        }, ensure_ascii=False)
