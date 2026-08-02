#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 4 — AI 增强处理器 v2（PromptContract + 可信元数据 + 多模型并存 + 严格 JSON）。

状态机：
  pending → processing → succeeded
                        → failed_retryable
                        → failed_terminal
                        → invalid_model_output
  未资格 → skipped_ineligible

关键约束：
- PromptContract 加载后渲染给 Provider；缺失或版本不一致 → 失败关闭。
- 模型只输出 semantic_payload（MODEL_OUTPUT_FIELDS），处理器注入可信元数据。
- result_id = SHA-256(event_id+input_hash+prompt_version+prompt_content_hash+provider+model)
- 按 result_id 保存，多模型/多版本结果并存（不互相覆盖）。
- strict_json 默认 True：围栏/解释/多对象/非 object → invalid_model_output。
- 单条失败不中断批次；原子写入；runtime 缓存不入库不进 dist。
"""

import hashlib
import json
import os
import tempfile
from pathlib import Path

from .stage4_provider import (
    ProviderTimeout, ProviderAPIError, ProviderTerminalError,
)
from .enrichment_eligibility import eligibility_status, compute_input_hash
from .enrichment_validator import (
    parse_json_response_strict,
    validate_enrichment_semantics,
    MODEL_OUTPUT_FIELDS, SYSTEM_METADATA_FIELDS, ALL_ENRICHMENT_FIELDS,
)
from .prompt_contract import PromptContract, bj_iso_now

# ── 状态常量 ──
PENDING = "pending"
PROCESSING = "processing"
SUCCEEDED = "succeeded"
FAILED_RETRYABLE = "failed_retryable"
FAILED_TERMINAL = "failed_terminal"
SKIPPED_INELIGIBLE = "skipped_ineligible"
INVALID_MODEL_OUTPUT = "invalid_model_output"

# 默认 AI 输出目录（runtime，gitignore 排除）
DEFAULT_AI_ROOT = Path(__file__).resolve().parents[2] / "data" / "ai"


def compute_result_id(event_id, input_hash, prompt_version,
                      prompt_content_hash, provider_name, model_name):
    """result_id = SHA-256 组合唯一键。"""
    raw = "|".join([
        event_id, input_hash, prompt_version, prompt_content_hash,
        provider_name, model_name,
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class EnrichmentProcessor:
    """事件增强处理器 v2。"""

    def __init__(self, provider, prompt_contract=None,
                 prompt_version=None, prompt_path=None,
                 ai_root=None, schema_validator=None, run_id=None,
                 min_word_count=None, strict_json=True):
        if prompt_contract is None and prompt_path is not None:
            prompt_contract = PromptContract(prompt_path, version=prompt_version)
        elif prompt_contract is None:
            raise ValueError("EnrichmentProcessor 必须提供 prompt_contract 或 prompt_path")

        self.provider = provider
        self.prompt_contract = prompt_contract
        self.prompt_version = prompt_contract.version
        self.prompt_content_hash = prompt_contract.content_hash
        self.ai_root = Path(ai_root) if ai_root else DEFAULT_AI_ROOT
        self.schema_validator = schema_validator
        self.run_id = run_id
        self.min_word_count = min_word_count
        self.strict_json = strict_json
        self._state_path = self.ai_root / "enrichment_state_v2.json"
        self._results_path = self.ai_root / "enrichment_results.json"

    # ── 持久化 ────────────────────────────────────────────────
    def _load_state(self):
        if self._state_path.exists():
            try:
                return json.loads(self._state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"records": {}}

    def _save_state(self, d):
        self._atomic_write(self._state_path, d)

    def _load_results(self):
        if self._results_path.exists():
            try:
                return json.loads(self._results_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"items": [], "active_result_by_event": {}}

    def _save_results(self, d):
        self._atomic_write(self._results_path, d)

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
                try: os.remove(tmp)
                except OSError: pass

    # ── 处理入口 ──────────────────────────────────────────────
    def process_events(self, events, quarantine_ids=None):
        state = self._load_state()
        results = self._load_results()

        summary = {"eligible": 0, "skipped": 0, "succeeded": 0,
                   "failed_retryable": 0, "failed_terminal": 0,
                   "invalid_model_output": 0, "cache_hit": 0, "cache_miss": 0}

        for event in events:
            eid = event.get("event_id", "")
            status, reason = eligibility_status(
                event, quarantine_ids=quarantine_ids,
                min_word_count=self.min_word_count)
            if status == "skipped_ineligible":
                summary["skipped"] += 1
                continue

            summary["eligible"] += 1
            input_hash = compute_input_hash(event)
            result_id = compute_result_id(
                eid, input_hash, self.prompt_version,
                self.prompt_content_hash,
                self.provider.provider_name,
                self.provider.model_name,
            )

            # 缓存：相同 result_id 已有成功结果 → 幂等命中
            existing = [r for r in results["items"] if r.get("result_id") == result_id]
            if existing and existing[0].get("processing_status") == SUCCEEDED:
                summary["cache_hit"] += 1
                continue
            summary["cache_miss"] += 1

            # 处理单条
            rec = state["records"].setdefault(result_id, {})
            outcome = self._process_one(event, input_hash, result_id, rec)

            if outcome.get("status") == SUCCEEDED:
                record = outcome["record"]
                # 按 result_id 幂等保存（不覆盖已有相同 result_id 的结果）
                items = [r for r in results["items"] if r.get("result_id") != result_id]
                items.append(record)
                results["items"] = items
                # active_result_by_event 只作为指针（指向最新成功），不自动选择发布
                results["active_result_by_event"][eid] = result_id
                summary["succeeded"] += 1
            elif outcome["status"] == INVALID_MODEL_OUTPUT:
                summary["invalid_model_output"] += 1
            elif outcome["status"] == FAILED_TERMINAL:
                summary["failed_terminal"] += 1
            elif outcome["status"] == FAILED_RETRYABLE:
                summary["failed_retryable"] += 1

        self._save_state(state)
        self._save_results(results)
        return summary

    def _process_one(self, event, input_hash, result_id, rec):
        """处理单条。返回 outcome dict。"""
        rec.update({"status": PROCESSING, "result_id": result_id,
                    "input_hash": input_hash,
                    "prompt_version": self.prompt_version,
                    "prompt_content_hash": self.prompt_content_hash,
                    "ai_provider": self.provider.provider_name,
                    "ai_model": self.provider.model_name})

        # 渲染 Prompt（PromptContract 负责，失败关闭）
        try:
            prompt_text = self.prompt_contract.render(event)
        except Exception as e:
            rec.update({"status": FAILED_TERMINAL,
                        "error_code": "PROMPT_RENDER:" + type(e).__name__})
            return {"status": FAILED_TERMINAL}

        # 调用 Provider
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
            rec.update({"status": FAILED_TERMINAL,
                        "error_code": "UNEXPECTED:" + type(e).__name__})
            return {"status": FAILED_TERMINAL}

        raw_text = resp.get("raw_text", "")
        raw_hash = resp.get("raw_response_hash", hashlib.sha256(
            raw_text.encode("utf-8")).hexdigest())

        # strict JSON 解析
        parsed, warn, parse_err = parse_json_response_strict(
            raw_text, strict=self.strict_json)
        if parse_err or parsed is None:
            rec.update({"status": INVALID_MODEL_OUTPUT,
                        "error_code": "JSON:" + (parse_err or "parse"),
                        "warnings": warn})
            return {"status": INVALID_MODEL_OUTPUT}

        # ── 拆分模型输出与可信元数据 ──
        semantic = {}
        for k in MODEL_OUTPUT_FIELDS:
            if k in parsed:
                semantic[k] = parsed[k]
        # 拒绝模型提供的元数据字段（模型不得决定 event_id/provider/status 等）
        injected_meta = [k for k in parsed if k in SYSTEM_METADATA_FIELDS
                         and k not in MODEL_OUTPUT_FIELDS]
        if injected_meta:
            warn = warn + ["injected_metadata:" + ",".join(injected_meta)]
        # 模型输出中的 event_id 与期望不一致 → 直接拒绝
        if "event_id" in parsed and parsed["event_id"] != event.get("event_id"):
            rec.update({"status": INVALID_MODEL_OUTPUT,
                        "error_code": "MODEL_INJECTED_WRONG_EVENT_ID",
                        "warnings": warn})
            return {"status": INVALID_MODEL_OUTPUT}

        # Schema 校验（仅 model output）
        if self.schema_validator is not None:
            ok, schema_errors = self.schema_validator(semantic)
            if not ok:
                rec.update({"status": INVALID_MODEL_OUTPUT,
                            "error_code": "SCHEMA:" + ";".join(schema_errors[:5]),
                            "warnings": warn})
                return {"status": INVALID_MODEL_OUTPUT}

        # 语义校验（model output）
        ok, errors, warnings = validate_enrichment_semantics(
            semantic, event, expected_run_id=self.run_id)
        if not ok:
            rec.update({"status": INVALID_MODEL_OUTPUT,
                        "error_code": "SEMANTIC:" + ";".join(errors[:5]),
                        "warnings": warnings + warn})
            return {"status": INVALID_MODEL_OUTPUT}

        # ── 组装完整记录（可信元数据由处理器注入，不信任模型）──
        record = {
            "result_id": result_id,
            "event_id": event.get("event_id", ""),
            "canonical_run_id": event.get("canonical_run_id", ""),
            "input_hash": input_hash,
            "cache_key": result_id,
            "prompt_version": self.prompt_version,
            "prompt_content_hash": self.prompt_content_hash,
            "ai_provider": self.provider.provider_name,
            "ai_model": self.provider.model_name,
            "processed_at": bj_iso_now(),
            "processing_status": SUCCEEDED,
            "error_code": None,
            "raw_response_hash": raw_hash,
        }
        record.update(semantic)
        # 强制覆盖模型可能返回的错误元数据
        record["event_id"] = event.get("event_id", "")
        record["canonical_run_id"] = event.get("canonical_run_id", "")
        record["input_hash"] = input_hash
        record["ai_provider"] = self.provider.provider_name
        record["ai_model"] = self.provider.model_name
        record["prompt_version"] = self.prompt_version
        record["prompt_content_hash"] = self.prompt_content_hash
        record["processing_status"] = SUCCEEDED
        record["error_code"] = None
        record["raw_response_hash"] = raw_hash

        rec["status"] = SUCCEEDED
        rec["raw_response_hash"] = raw_hash
        return {"status": SUCCEEDED, "record": record}
