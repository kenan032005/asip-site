#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 2.5B-2B-P — 跨会话交接准备端（Producer）。

由当前 WorkBuddy 任务准备一个隔离的合成 AI 批次并生成交接文件，
但不领取、不处理、不生成结果；随后由一个新的 WorkBuddy 任务接手。

职责边界（对应 2.5B-2B-P 规范一/四/五/六/七）：
- 只做 prepare / inspect / verify / cleanup 四个动作；
- 不 claim、不创建 lease、不生成 AI 结果、不 ingest；
- 仅使用合成任务（synthetic=true），不处理真实新闻 / 真实 API / 真实数据；
- 不使用生产 data/ai，全部状态落在 .workbuddy_runtime/stage25b2b/（已 gitignore）；
- 本模块不做任何网络调用：external_api_calls=0（ASIP Python 程序未直接调用外部 API；
  WorkBuddy 内置模型的使用由接收端会话负责，不计入 ASIP 代码 API 调用）。

模型说明（对应 2.5B-2B-P 模型调整）：
- provider 固定为 workbuddy_queue；
- expected_model 使用 WorkBuddy 内置 DeepSeek V4 Flash 的模型标识
  （deepseek-v4-flash），不得将 DeepSeek V4 Flash 伪装成 hy3；
- 模型标识只在本文件顶部单一参数 EXPECTED_MODEL 定义一次，
  HANDOFF_READY / manifest / results.template / AI Result 均以其为唯一来源；
- 接收端处理时 AI Result 的 model 字段必须与 manifest.expected_model 完全一致。

用法：
  python scripts/ai/cross_session_handoff_demo.py prepare
  python scripts/ai/cross_session_handoff_demo.py inspect
  python scripts/ai/cross_session_handoff_demo.py verify --consumer-session-id <id>
  python scripts/ai/cross_session_handoff_demo.py cleanup
"""

import os
import re
import sys
import json
import shutil
import secrets
import hashlib
import subprocess
import argparse
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.dirname(_HERE)
ROOT = os.path.dirname(_SCRIPTS)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from ai.contracts import new_ai_task  # noqa: E402
from ai.contracts import validate_ai_result  # noqa: E402
from ai.workbuddy_queue_provider import WorkbuddyQueueProvider  # noqa: E402
from ai.workbuddy_worker import status_summary  # noqa: E402

# 运行时目录（与生产 data/ai 完全隔离；.gitignore 已覆盖 .workbuddy_runtime/）
DEFAULT_AI_ROOT = os.path.join(ROOT, ".workbuddy_runtime", "stage25b2b")

# ── 单一参数：provider / model（所有文件只从这里读取，不分散写死） ──
EXPECTED_PROVIDER = "workbuddy_queue"
# WorkBuddy 内置 DeepSeek V4 Flash 的模型标识（与 UI 显示名一一对应）。
# 严禁改成 hy3 或任何伪装值；接收端 AI Result.model 必须与此完全一致。
EXPECTED_MODEL = "deepseek-v4-flash"

HANDOFF_VERSION = "1.0"
STAGE = "2.5B-2B"
AI_ROOT_REL = ".workbuddy_runtime/stage25b2b"  # 契约声明的默认交接位置

# 安全语义分类（与 2.5B-2A 保持一致；verify 复用）
SECURITY_EVENT_TYPES = {
    "armed_incident", "security_incident", "shooting_incident",
    "violent_incident", "explosion_incident",
}
TRANSPORT_EVENT_TYPES = {
    "transport_disruption", "road_closure", "traffic_disruption",
    "infrastructure_disruption",
}

# ── 新的虚构场景（不复用 2.5B-2A 原文；明确标注 FICTIF / SYNTHETIC） ──
TCD_SOURCE_TEXT = (
    "[SCÉNARIO FICTIF]\n"
    "De brèves émeutes ont été signalées dans la ville fictive de Moundjara, au "
    "Tchad. Les autorités locales ont imposé un couvre-feu nocturne temporaire et "
    "mis en place des points de contrôle sur les routes principales. Aucun bilan "
    "de victimes n'a été officiellement confirmé à ce stade."
)

NER_SOURCE_TEXT = (
    "[SYNTHETIC SCENARIO]\n"
    "A road blockage was reported in a fictional area of Niger near the town of "
    "Guidan-Roumdji. Security forces guided vehicles onto alternative routes. "
    "The road reopening time has not yet been announced. No casualties have "
    "been officially reported."
)

# (country_iso3, source_language, source_text, scenario_id, priority)
SCENARIOS = [
    ("TCD", "fr", TCD_SOURCE_TEXT, "stage25b2b-tcd-curfew", "critical"),
    ("NER", "en", NER_SOURCE_TEXT, "stage25b2b-ner-roadblock", "high"),
]

_HANDOFF_JSON_KEYS = {
    "handoff_version", "stage", "producer_session_id", "created_at",
    "repo_commit", "ai_root_relative", "expected_task_count", "task_ids",
    "task_content_hashes", "expected_provider", "expected_model",
    "consumer_must_claim", "producer_processed_results",
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _content_hash(text):
    """content_hash 必须基于 source_text 计算（稳定且可复现）。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _repo_commit():
    try:
        p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, timeout=15)
        if p.returncode == 0:
            return p.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _find_results_files(ai_root):
    """遍历查找 results*.json（接收端写入的结果文件，生产阶段不应存在）。"""
    found = []
    for base, _dirs, fns in os.walk(ai_root):
        for fn in fns:
            if fn.startswith("results") and fn.endswith(".json"):
                found.append(os.path.join(base, fn))
    return found


def _queue_tasks(ai_root):
    q = os.path.join(ai_root, "queue")
    out = []
    if os.path.isdir(q):
        for fn in sorted(os.listdir(q)):
            if fn.endswith(".json"):
                out.append(_read_json(os.path.join(q, fn)))
    return out


def _handoff_path(ai_root, ext=".json"):
    return os.path.join(ai_root, "HANDOFF_READY%s" % ext)


def prepare(ai_root=DEFAULT_AI_ROOT):
    """清理旧目录 → 建独立模拟 AI Root → 写 2 个合成任务到 queue。

    不 claim、不建 lease、不生成结果、不 ingest；
    仅生成 HANDOFF_READY.json / HANDOFF_READY.md 交接文件。
    """
    # 1) 清理旧的 stage25b2b 演示目录
    if os.path.isdir(ai_root):
        shutil.rmtree(ai_root, ignore_errors=True)
    os.makedirs(ai_root, exist_ok=True)

    # 2) 建立独立模拟 AI Root
    provider = WorkbuddyQueueProvider({}, ai_root=ai_root)

    # 3) 创建 2 个 synthetic=true 的虚构 article_analysis 任务并写入 queue
    for iso3, lang, src, scid, prio in SCENARIOS:
        input_ref = {
            "country_iso3": iso3,
            "source_language": lang,
            "source_text": src,
            "synthetic": True,
            "scenario_id": scid,
        }
        ch = _content_hash(src)
        task = new_ai_task("article_analysis", input_ref, ch, "ai_v1", "1.0",
                           provider_requested=EXPECTED_PROVIDER,
                           priority=prio, max_retries=1)
        task["synthetic"] = True  # 标记合成，绝不进入生产数据
        provider.submit_task(task)

    # 4) 生成跨会话交接文件
    tasks = _queue_tasks(ai_root)
    task_ids = sorted(t["task_id"] for t in tasks)
    handoff = {
        "handoff_version": HANDOFF_VERSION,
        "stage": STAGE,
        "producer_session_id": "producer_%s" % secrets.token_hex(4),
        "created_at": _now_iso(),
        "repo_commit": _repo_commit(),
        "ai_root_relative": AI_ROOT_REL,
        "expected_task_count": len(task_ids),
        "task_ids": task_ids,
        "task_content_hashes": {
            t["task_id"]: t["content_hash"] for t in tasks
        },
        "expected_provider": EXPECTED_PROVIDER,
        "expected_model": EXPECTED_MODEL,
        "consumer_must_claim": True,
        "producer_processed_results": False,
    }
    with open(_handoff_path(ai_root, ".json"), "w", encoding="utf-8") as f:
        json.dump(handoff, f, ensure_ascii=False, indent=2)

    _write_handoff_md(ai_root, handoff, tasks)

    return {
        "ai_root": ai_root,
        "handoff_path": _handoff_path(ai_root, ".json"),
        "handoff_md_path": _handoff_path(ai_root, ".md"),
        "producer_session_id": handoff["producer_session_id"],
        "repo_commit": handoff["repo_commit"],
        "ai_root_relative": handoff["ai_root_relative"],
        "expected_provider": EXPECTED_PROVIDER,
        "expected_model": EXPECTED_MODEL,
        "tasks": [
            {
                "task_id": t["task_id"],
                "task_type": t["task_type"],
                "country_iso3": (t.get("input_ref") or {}).get("country_iso3"),
                "source_language": (t.get("input_ref") or {}).get("source_language"),
                "scenario_id": (t.get("input_ref") or {}).get("scenario_id"),
                "source_text": (t.get("input_ref") or {}).get("source_text"),
                "content_hash": t.get("content_hash"),
                "synthetic": t.get("synthetic"),
            }
            for t in tasks
        ],
        "queue": status_summary(ai_root).get("queue", 0),
    }


def _write_handoff_md(ai_root, handoff, tasks):
    """HANDOFF_READY.md：给接收端（全新 WorkBuddy 任务）的 10 条指引。

    不得在此文件中预置中文摘要或 AI 结果。
    """
    lines = [
        "# ASIP Stage 2.5B-2B 跨会话交接（准备端已完成，等待接收端）",
        "",
        "本文件由准备端 WorkBuddy 任务生成，指示一个**全新的 WorkBuddy 任务**"
        "接手本批次的领取与处理。",
        "",
        "## 交接摘要",
        "",
        "- handoff_version: %s" % handoff["handoff_version"],
        "- stage: %s" % handoff["stage"],
        "- producer_session_id: `%s`" % handoff["producer_session_id"],
        "- created_at: %s" % handoff["created_at"],
        "- repo_commit: `%s`" % handoff["repo_commit"],
        "- ai_root_relative: `%s`" % handoff["ai_root_relative"],
        "- expected_task_count: %s" % handoff["expected_task_count"],
        "- expected_provider: `%s`" % handoff["expected_provider"],
        "- expected_model: `%s`（WorkBuddy 内置 DeepSeek V4 Flash 的模型标识）"
        % handoff["expected_model"],
        "",
        "## 任务清单（queue 中待领取）",
        "",
    ]
    for t in sorted(tasks, key=lambda x: x["task_id"]):
        ir = t.get("input_ref") or {}
        lines.append("- `%s` country=%s lang=%s scenario=%s hash=%s" % (
            t["task_id"], ir.get("country_iso3"), ir.get("source_language"),
            ir.get("scenario_id"), t.get("content_hash")))
    lines += [
        "",
        "## 接收端必须执行的步骤",
        "",
        "1. 先阅读仓库根目录的 WORKBUDDY_AI_WORKER.md（AI 任务领取与交接协议），"
        "再按本文件执行。",
        "2. 不要依赖准备端 WorkBuddy 对话的任何上下文：以本文件与 "
        "HANDOFF_READY.json 为唯一事实来源。",
        "3. 校验交接契约：核对 `repo_commit` 与当前仓库 HEAD 一致；"
        "用 `sha256(source_text)` 核对 `task_content_hashes`（见 "
        "HANDOFF_READY.json）。",
        "4. 由接收端**自行 claim**：以 HANDOFF_READY.json 的 "
        "`expected_provider` / `expected_model` 为准调用 claim_batch，"
        "不得使用默认值。",
        "5. 使用接收端新任务内置的 **DeepSeek V4 Flash** 处理 2 个任务："
        "AI Result 的 `model` 字段必须与 `manifest.expected_model` 完全一致"
        "（即 `%s`），不得写成 hy3。" % handoff["expected_model"],
        "6. 将结果写入标准 results.json（批次目录内），字段遵循 "
        "results.template.json 与 AI Result Schema。",
        "7. 调用 ingest 摄取结果，然后**再次 ingest**（幂等验证："
        "第二次 accepted=0 且全部 idempotent_success）。",
        "8. 调用 verify（--consumer-session-id <你的会话标识>）："
        "queue=0 / processing=0 / completed=2 / leases=0，且 "
        "consumer_session_id 必须与 producer_session_id 不同。",
        "9. 不修改生产 data/ai；本批次所有状态只存在于 "
        "`.workbuddy_runtime/stage25b2b/`（已 gitignore）。",
        "10. 不使用任何外部 API（DeepSeek 开放平台 / ChatGPT / 新闻 API 等）；"
        "external_api_calls=0，仅使用 WorkBuddy 内置模型。",
        "",
        "## 边界",
        "",
        "- 本批次为 synthetic=true 的虚构场景（SCÉNARIO FICTIF / SYNTHETIC "
        "SCENARIO 已标注），不指向任何真实事件、人物或新闻。",
        "- 准备端未领取、未处理、未生成任何 AI 结果（producer_processed_results"
        "=false）。",
        "- 处理完成后，接收端应在验收记录中如实注明使用 WorkBuddy 内置 "
        "DeepSeek V4 Flash（模型标识 `%s`）。" % handoff["expected_model"],
    ]
    with open(_handoff_path(ai_root, ".md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def validate_result_event(result):
    """对单条 AI 结果做业务语义校验（安全事件 / 交通中断 / 伤亡未确认）。

    与 2.5B-2A 逻辑一致；verify 与测试均复用。
    返回错误字符串列表；空列表表示通过。
    """
    errs = []
    if not isinstance(result, dict):
        return ["result is not an object"]
    r = result.get("result") or {}
    iso3 = r.get("country_iso3")
    et = r.get("event_type")
    summary = r.get("summary_zh") or ""
    uncertainties = r.get("uncertainties") or []
    blob = (summary + " " + " ".join(uncertainties)).lower()

    def _asserts_confirmed(text):
        return any(p in text for p in (
            "已造成伤亡", "已造成死伤", "确认有死伤", "确认造成",
            "造成死亡", "造成伤亡", "造成死伤",
        ))

    def _mentions_unconfirmed(text):
        casualty = ("死伤", "伤亡", "死亡", "受伤", "morts", "bless",
                    "casualt", "deaths", "injured", "victim")
        unconf = ("尚未", "未确认", "未证实", "没有确认", "暂未", "待确认",
                  "not confirmed", "unconfirmed", "have not confirmed",
                  "officially", "no casualties reported")
        return any(c in text for c in casualty) and any(u in text for u in unconf)

    def _fabricates(text):
        return any(p in text for p in (
            "造成伤亡", "造成死伤", "人死亡", "人受伤", "导致死亡",
            "confirmed deaths", "fatalities",
        ))

    if _asserts_confirmed(blob):
        errs.append("casualties written as confirmed")
    if iso3 == "TCD":
        if et not in SECURITY_EVENT_TYPES:
            errs.append("TCD task must be a security event, got %r" % et)
        if not _mentions_unconfirmed(blob):
            errs.append("TCD result must retain unconfirmed casualties")
    if iso3 == "NER":
        if et not in TRANSPORT_EVENT_TYPES:
            errs.append("NER task must be transport/road disruption, got %r" % et)
        if _fabricates(blob):
            errs.append("NER result must not fabricate casualties")
    return errs


def inspect(ai_root=DEFAULT_AI_ROOT):
    """检查准备端初始状态（交接文件 + 队列 + 无结果 + 哈希一致）。"""
    checks = {}
    errors = []

    def add(cond, name, val=None):
        checks[name] = (val if val is not None else cond)
        if not cond:
            errors.append(name)

    hj = _handoff_path(ai_root, ".json")
    add(os.path.exists(hj), "handoff_present")

    st = status_summary(ai_root)
    add(st.get("queue", 0) == 2, "queue", st.get("queue"))
    add(st.get("processing", 0) == 0, "processing", st.get("processing"))
    add(st.get("completed", 0) == 0, "completed", st.get("completed"))
    add(st.get("leases", 0) == 0, "leases", st.get("leases"))

    rf = _find_results_files(ai_root)
    add(len(rf) == 0, "results_files", len(rf))

    if os.path.exists(hj):
        h = _read_json(hj)
        add(h.get("producer_processed_results") is False,
            "producer_processed_results", h.get("producer_processed_results"))
        add(h.get("expected_provider") == EXPECTED_PROVIDER,
            "expected_provider", h.get("expected_provider"))
        add(h.get("expected_model") == EXPECTED_MODEL,
            "expected_model", h.get("expected_model"))
        queue_tasks = _queue_tasks(ai_root)
        hh = h.get("task_content_hashes") or {}
        ok_hashes = (len(queue_tasks) == 2
                     and all(hh.get(t["task_id"]) == t.get("content_hash")
                             and t.get("content_hash") == _content_hash(
                                 (t.get("input_ref") or {}).get("source_text") or "")
                             for t in queue_tasks))
        add(ok_hashes, "hashes_match")
        ok_ids = sorted(t["task_id"] for t in queue_tasks) == sorted(
            h.get("task_ids", []))
        add(ok_ids, "task_ids_match", sorted(t["task_id"] for t in queue_tasks))
    else:
        add(False, "producer_processed_results")
        add(False, "hashes_match")
        add(False, "task_ids_match")

    return {"ok": len(errors) == 0, "checks": checks, "errors": errors}


def verify(ai_root=DEFAULT_AI_ROOT, consumer_session_id=None):
    """接收端完成后校验最终状态（queue=0/completed=2/语义/model/session）。"""
    checks = {}
    errors = []

    def add(cond, name, val=None):
        checks[name] = (val if val is not None else cond)
        if not cond:
            errors.append(name)

    hj = _handoff_path(ai_root, ".json")
    if not os.path.exists(hj):
        return {"ok": False, "checks": {"handoff_present": False},
                "errors": ["HANDOFF_READY.json missing"]}
    add(True, "handoff_present")
    h = _read_json(hj)
    expected_ids = sorted(h.get("task_ids", []))

    st = status_summary(ai_root)
    add(st.get("queue", 0) == 0, "queue", st.get("queue"))
    add(st.get("processing", 0) == 0, "processing", st.get("processing"))
    add(st.get("completed", 0) == 2, "completed", st.get("completed"))
    add(st.get("leases", 0) == 0, "leases", st.get("leases"))

    # task_id 不变 + 无重复
    comp_dir = os.path.join(ai_root, "completed")
    completed_ids = []
    if os.path.isdir(comp_dir):
        completed_ids = sorted(
            f[:-5] for f in os.listdir(comp_dir) if f.endswith(".json"))
    add(completed_ids == expected_ids, "completed_task_ids",
        completed_ids)
    add(len(completed_ids) == 2, "no_duplicate_completed", len(completed_ids))

    # provider / model / synthetic / 中文摘要 / 安全语义（逐结果）
    for tid in expected_ids:
        cpath = os.path.join(comp_dir, "%s.json" % tid)
        if not os.path.exists(cpath):
            errors.append("completed missing: %s" % tid)
            checks["completed_present_%s" % tid] = False
            continue
        obj = _read_json(cpath)
        res = obj.get("ai_result")
        if not isinstance(res, dict):
            errors.append("no ai_result for %s" % tid)
            checks["ai_result_present_%s" % tid] = False
            continue
        schema_errs = validate_ai_result(res)
        add(schema_errs == [], "schema_%s" % tid, schema_errs == [])
        add(res.get("provider") == h.get("expected_provider"),
            "provider_%s" % tid, res.get("provider"))
        add(res.get("model") == h.get("expected_model"),
            "model_%s" % tid, res.get("model"))
        r = res.get("result") or {}
        add(r.get("synthetic") is True, "synthetic_%s" % tid,
            r.get("synthetic"))
        add(r.get("country_iso3") in ("TCD", "NER"),
            "country_%s" % tid, r.get("country_iso3"))
        add(bool(r.get("summary_zh")), "summary_zh_%s" % tid,
            bool(r.get("summary_zh")))
        sem_errs = validate_result_event(res)
        add(sem_errs == [], "semantics_%s" % tid, sem_errs == [])
        checks.setdefault("event_type_%s" % tid, r.get("event_type"))

    # consumer_session_id 与 producer_session_id 不同
    add(bool(consumer_session_id), "consumer_session_id_present",
        bool(consumer_session_id))
    add(consumer_session_id != h.get("producer_session_id"),
        "consumer_differs_from_producer",
        consumer_session_id)

    return {"ok": len(errors) == 0, "checks": checks, "errors": errors}


def cleanup(ai_root=DEFAULT_AI_ROOT):
    """删除整个隔离运行时目录（best-effort，失败返回 False）。"""
    if os.path.isdir(ai_root):
        shutil.rmtree(ai_root, ignore_errors=True)
    return not os.path.isdir(ai_root)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="ASIP 2.5B-2B-P 跨会话交接准备端（不领取/不处理/不生成结果）")
    ap.add_argument("--ai-root", default=DEFAULT_AI_ROOT)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare")
    sub.add_parser("inspect")
    v = sub.add_parser("verify")
    v.add_argument("--consumer-session-id", default=None)
    sub.add_parser("cleanup")
    try:
        args = ap.parse_args(argv)
        root = args.ai_root

        if args.cmd == "prepare":
            info = prepare(ai_root=root)
            print(json.dumps(info, ensure_ascii=False, indent=2))
            return 0
        elif args.cmd == "inspect":
            out = inspect(ai_root=root)
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 0 if out.get("ok") else 1
        elif args.cmd == "verify":
            out = verify(ai_root=root, consumer_session_id=args.consumer_session_id)
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 0 if out.get("ok") else 1
        elif args.cmd == "cleanup":
            ok = cleanup(ai_root=root)
            print(json.dumps({"cleaned": ok}, ensure_ascii=False, indent=2))
            return 0 if ok else 1
        return 0
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write("error: %s\n" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
