#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 4 — Hy3 ↔ Stage 4 桥接 Provider（C 包交付）。

设计目标（对应阻断报告「阻断 3」与本包 §四）：
- 实现 Stage4Provider 同步接口（generate_structured），使 EnrichmentProcessor
  无需改动即可接入真实 Hy3 调用；
- 复用 Stage 2.5B「会话交接协议」：produce 阶段把任务入队到 data/ai/queue，
  并写入可被消费者会话（WorkBuddy 内置模型 = 本智能体）消费的 Prompt 文件；
  collect 阶段从 data/ai/completed 读取消费者写回的真实结果；
- 本 Provider 自身**绝不调用任何网络 / 绝不伪造模型输出**；真实 AI 由消费者会话
  生成并写回 completed（符合 workbuddy_worker.py「控制器不调用 AI」约定）；
- external_api_calls = 0（ASIP Python 不直接调用外部 API；内置模型使用由消费者负责）。

两个阶段：
  produce（生产端）：enqueue_event(event, prompt_contract) 入队 + 写 Prompt 文件 + 维护索引；
  collect（收集端）：generate_structured(prompt_text) 从 completed 取真实结果返回。

强制约束：
  - collect 模式下若消费者尚未写回结果 → 抛 ProviderTerminalError
    （HANDOFF_RESULT_MISSING），使 EnrichmentProcessor 记为 failed_terminal，
    绝不回退到 Mock / 绝不伪造；
  - 仅当 result_id 索引命中且 completed 文件存在时才返回 ok=True；
  - token_usage 一律为 0/0/0（与 2.5B 约定一致，不得伪造用量）。
"""

import os
import re
import json
import hashlib
import tempfile
from pathlib import Path

from .stage4_provider import (
    Stage4Provider, ProviderTimeout, ProviderAPIError, ProviderTerminalError,
)
from .provider import BaseAIProvider
from .workbuddy_queue_provider import WorkbuddyQueueProvider
from .contracts import new_ai_task
from .config import load_runtime_config

DEFAULT_AI_ROOT = Path(__file__).resolve().parents[2] / "data" / "ai"

# 单一参数来源：Provider 名称 / 任务类型 / 交接层 provider
PROVIDER_NAME = "hy3"
HANDOFF_PROVIDER = "workbuddy_queue"   # 2.5B 交接层永远是 workbuddy_queue
TASK_TYPE = "article_analysis"
OUTPUT_SCHEMA_VERSION = "1.0"

_EVENT_ID_RE = re.compile(r'"event_id"\s*:\s*"(EVT_[0-9a-f]{16})"')


def _sha256(text):
    if isinstance(text, str):
        text = text.encode("utf-8")
    return hashlib.sha256(text).hexdigest()


class Hy3Stage4Provider(Stage4Provider, BaseAIProvider):
    """Hy3 ↔ Stage 4 桥接 Provider（同步接口 + 2.5B 交接协议）。

    同时继承 Stage4Provider（供 EnrichmentProcessor 使用）与 BaseAIProvider
    （供 registry 注册 / 兼容 2.5A 接口），与 MockProvider 的双继承模式一致。
    """

    provider_name = PROVIDER_NAME

    def __init__(self, config=None, name=PROVIDER_NAME, ai_root=None,
                 expected_model=None, task_type=TASK_TYPE,
                 output_schema_version=OUTPUT_SCHEMA_VERSION,
                 max_retries=2, timeout=30, mode="collect", index_path=None):
        # BaseAIProvider.__init__ 需要 (config, name)
        BaseAIProvider.__init__(self, config or {}, name)
        Stage4Provider.__init__(self, timeout=timeout, max_retries=max_retries)

        cfg = config or load_runtime_config()
        # expected_model 默认取自运行时配置 ai_model（仓库默认 "hy3"）
        self.expected_model = expected_model or cfg.get("ai_model") or "hy3"
        self.model_name = self.expected_model

        self.ai_root = Path(ai_root) if ai_root else DEFAULT_AI_ROOT
        self.task_type = task_type
        self.output_schema_version = output_schema_version
        self.mode = mode

        self.queue_provider = WorkbuddyQueueProvider(cfg, ai_root=str(self.ai_root))
        self._prompts_dir = self.ai_root / "hy3_prompts"
        self._index_path = Path(index_path) if index_path \
            else self.ai_root / "hy3_bridge_index.json"
        self._index = self._load_index()

    # ── 索引（event_id -> 交接条目）────────────────────────────
    def _load_index(self):
        if self._index_path.exists():
            try:
                return json.loads(self._index_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_index(self):
        self.ai_root.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.ai_root), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._index, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self._index_path)
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass

    @staticmethod
    def _extract_event_id(prompt_text):
        m = _EVENT_ID_RE.search(prompt_text or "")
        return m.group(1) if m else None

    # ── produce（生产端）─────────────────────────────────────
    def enqueue_event(self, event, prompt_contract):
        """把一个合格事件渲染 Prompt 并入队，返回 task_id。

        仅做：渲染 Prompt -> 构造合规 AI 任务 -> 入队 data/ai/queue ->
        写 Prompt 文件 -> 更新索引。不调用任何模型、不生成结果。
        """
        if prompt_contract is None:
            raise ProviderTerminalError("hy3_bridge: prompt_contract required for enqueue")
        event_id = event.get("event_id")
        if not event_id:
            raise ProviderTerminalError("hy3_bridge: event missing event_id")

        prompt_text = prompt_contract.render(event)
        iso3 = event.get("country_iso3")
        input_ref = {
            "event_id": event_id,
            "country_iso3": iso3,
            "task_kind": "stage4_enrichment",
        }
        content_hash = _sha256(prompt_text)
        pv = prompt_contract.version
        task = new_ai_task(
            self.task_type, input_ref, content_hash, pv,
            self.output_schema_version,
            provider_requested=HANDOFF_PROVIDER,
            priority="high", max_retries=self.max_retries,
        )
        submitted = self.queue_provider.submit_task(task)
        task_id = submitted["task_id"]

        # 写可被消费者会话消费的 Prompt 文件
        self._prompts_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = self._prompts_dir / ("%s.json" % task_id)
        prompt_record = {
            "task_id": task_id,
            "event_id": event_id,
            "country_iso3": iso3,
            "prompt_version": pv,
            "output_schema_version": self.output_schema_version,
            "expected_model": self.expected_model,
            "handoff_provider": HANDOFF_PROVIDER,
            "prompt_text": prompt_text,
        }
        prompt_path.write_text(
            json.dumps(prompt_record, ensure_ascii=False, indent=2),
            encoding="utf-8")

        # 更新索引
        self._index[event_id] = {
            "task_id": task_id,
            "content_hash": content_hash,
            "prompt_version": pv,
            "output_schema_version": self.output_schema_version,
            "expected_model": self.expected_model,
            "prompt_file": "hy3_prompts/%s.json" % task_id,
        }
        self._save_index()
        return task_id

    def enqueue_events(self, events, prompt_contract):
        """批量入队，返回 (task_ids, entries)。"""
        task_ids = []
        entries = []
        for ev in events:
            tid = self.enqueue_event(ev, prompt_contract)
            task_ids.append(tid)
            entries.append(self._index[ev.get("event_id")])
        return task_ids, entries

    def write_handoff(self, entries, producer_session_id="hy3_bridge_producer"):
        """给消费者会话（本智能体）写交接说明，列出待处理的 Prompt 清单与规则。"""
        from datetime import datetime, timezone
        md_path = self.ai_root / "HY3_STAGE4_HANDOFF.md"
        lines = [
            "# ASIP Stage 4 — Hy3 真实试跑交接（生产端已完成，等待消费者会话）",
            "",
            "- producer_session_id: `%s`" % producer_session_id,
            "- created_at: %s" % datetime.now(timezone.utc).isoformat(),
            "- ai_root: `%s`" % str(self.ai_root),
            "- expected_model: `%s`（WorkBuddy 内置模型标识，须与 ai_result.model 一致）"
            % self.expected_model,
            "- handoff_provider: `%s`" % HANDOFF_PROVIDER,
            "- task_count: %d" % len(entries),
            "",
            "## 消费者会话必须执行的步骤（使用本会话内置模型处理，禁止伪造/禁止改事实）",
            "",
            "1. 逐一读取 `hy3_prompts/<task_id>.json` 中的 `prompt_text`；",
            "2. 使用本会话内置模型（标识 `%s`）生成中文增强分析；" % self.expected_model,
            "3. 仅输出 10 个语义字段（source_language/title_zh/summary_zh/event_type/"
            "country_iso3/location/key_facts/uncertainties/security_relevance/"
            "classification_confidence），不得输出 event_id/ai_provider 等元数据；",
            "4. 不编造原文不存在的数字/地名/人名；不修改输入事实；",
            "5. 将结果写入 `data/ai/completed/<task_id>.json`，结构遵循 ai_result 契约："
            "provider=`%s`、model=`%s`、usage 全 0、result 为上述 10 字段对象；"
            % (HANDOFF_PROVIDER, self.expected_model),
            "6. 全部写回后，由收集端（EnrichmentProcessor + 本 Provider collect 模式）装配 enrichment_results.json。",
            "",
            "## 任务清单",
            "",
        ]
        for e in entries:
            tid = e["task_id"]
            lines.append("- `%s` event=%s country=%s model=%s"
                         % (tid, e.get("event_id"), e.get("country_iso3"),
                            e.get("expected_model")))
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return md_path

    # ── collect（收集端 / generate_structured）──────────────────
    def generate_structured(self, prompt_text):
        """collect 模式：从 data/ai/completed 读取消费者写回的真实结果。

        返回统一结构：{ok, raw_text, parsed, error, token_usage, raw_response_hash}。
        若消费者尚未写回结果 → 抛 ProviderTerminalError（HANDOFF_RESULT_MISSING），
        绝不伪造、绝不回退 Mock。
        """
        event_id = self._extract_event_id(prompt_text)
        if not event_id:
            raise ProviderTerminalError(
                "hy3_bridge: cannot extract event_id from prompt_text")
        # 重新载入索引：produce 阶段可能在当前实例构造之后写入
        self._index = self._load_index()
        entry = self._index.get(event_id)
        if entry is None:
            raise ProviderTerminalError(
                "hy3_bridge: no handoff index entry for event_id=%s; "
                "run producer (enqueue_event) first" % event_id)

        task_id = entry["task_id"]
        completed_path = self.ai_root / "completed" / ("%s.json" % task_id)
        if not completed_path.exists():
            raise ProviderTerminalError(
                "HANDOFF_RESULT_MISSING: task_id=%s not found in completed; "
                "consumer session has not produced the result yet" % task_id)

        try:
            obj = json.loads(completed_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise ProviderTerminalError(
                "hy3_bridge: failed to read completed result: %s" % e)

        ai_result = obj.get("ai_result")
        if not isinstance(ai_result, dict) or "result" not in ai_result:
            raise ProviderTerminalError(
                "hy3_bridge: completed result missing ai_result.result for %s" % task_id)

        result = ai_result["result"]
        raw_text = json.dumps(result, ensure_ascii=False)
        raw_hash = _sha256(raw_text)
        return {
            "ok": True,
            "raw_text": raw_text,
            "parsed": result,
            "error": None,
            "token_usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "estimated_cost_usd": 0.0,
            },
            "raw_response_hash": raw_hash,
        }

    # ── BaseAIProvider 兼容接口（委托队列层）────────────────────
    def validate_config(self):
        return []

    def submit_task(self, task):
        return self.queue_provider.submit_task(task)

    def get_task_status(self, task_id):
        return self.queue_provider.get_task_status(task_id)

    def load_result(self, task_id):
        return self.queue_provider.load_result(task_id)

    def health_check(self):
        self.ai_root.mkdir(parents=True, exist_ok=True)
        return {
            "status": "ok",
            "provider": self.name,
            "mode": self.mode,
            "external_network": False,        # 本 Provider 不发起任何网络请求
            "ai_processing_enabled": False,   # 真实 AI 由消费者会话执行
            "expected_model": self.expected_model,
        }


# ── CLI（生产端入队 + 状态）────────────────────────────────────
def _load_canonical_eligible(min_word_count=30):
    from .enrichment_eligibility import eligibility_status
    here = Path(__file__).resolve().parents[2]
    d = json.loads((here / "data" / "canonical" / "event_clusters.json").read_text(encoding="utf-8"))
    items = d.get("items", [])
    qids = set()
    qp = here / "data" / "quarantine" / "quarantine.json"
    if qp.exists():
        q = json.loads(qp.read_text(encoding="utf-8"))
        qids = set(q.get("quarantine_ids", []) or [])
    out = []
    for ev in items:
        st, _ = eligibility_status(ev, qids, min_word_count)
        if st == "eligible":
            out.append(ev)
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="ASIP Stage 4 Hy3 桥接 Provider（生产端）")
    ap.add_argument("--ai-root", default=str(DEFAULT_AI_ROOT))
    ap.add_argument("--expected-model", default=None,
                    help="消费者会话内置模型标识（默认取配置 ai_model）")
    ap.add_argument("--limit", type=int, default=0,
                    help="最多入队条数（0=全部合格）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("produce")
    p.add_argument("--prompt", default=None,
                   help="PromptContract 文件路径（默认 config/prompts/stage4_event_enrichment_v1.md）")

    s = sub.add_parser("status")

    try:
        args = ap.parse_args(argv)
        root = Path(args.ai_root)
        prov = Hy3Stage4Provider(ai_root=str(root), expected_model=args.expected_model,
                                 mode="produce")

        if args.cmd == "produce":
            from .prompt_contract import load_prompt_contract
            prompt_path = args.prompt
            if not prompt_path:
                prompt_path = str(Path(__file__).resolve().parents[2]
                                  / "config" / "prompts" / "stage4_event_enrichment_v1.md")
            pc = load_prompt_contract(prompt_path)
            eligible = _load_canonical_eligible()
            if args.limit:
                eligible = eligible[:args.limit]
            tids, entries = prov.enqueue_events(eligible, pc)
            md = prov.write_handoff(entries)
            print(json.dumps({
                "enqueued": len(tids),
                "queue": sum(1 for f in os.listdir(root / "queue") if f.endswith(".json")),
                "handoff_md": str(md),
                "task_ids": tids,
            }, ensure_ascii=False, indent=2))
            return 0
        elif args.cmd == "status":
            q = root / "queue"
            c = root / "completed"
            print(json.dumps({
                "indexed_events": len(prov._index),
                "queue": sum(1 for f in os.listdir(q) if f.endswith(".json")) if q.is_dir() else 0,
                "completed": sum(1 for f in os.listdir(c) if f.endswith(".json")) if c.is_dir() else 0,
            }, ensure_ascii=False, indent=2))
            return 0
        return 0
    except SystemExit:
        raise
    except Exception as e:
        import sys
        sys.stderr.write("error: %s\n" % e)
        return 2


if __name__ == "__main__":
    import sys
    sys.exit(main())
