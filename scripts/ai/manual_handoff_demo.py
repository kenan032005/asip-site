#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 2.5B-2A 验收补正 — 单会话 Hy3（免费）手工交接演示。

演示「创建任务 → 领取 → 当前 WorkBuddy 内置 Hy3（免费）处理 → 写结果 →
ingest → 完成 → 幂等重ingest → 校验最终状态」整条链路。

边界（对应验收补正规范一/三/四/五/六）：
- 仅使用合成任务（synthetic=true），不处理真实新闻 / 真实 API / 真实数据；
- 仅允许当前 WorkBuddy 内置 Hy3（免费）：provider=workbuddy_queue、model=hy3；
- 禁用 DeepSeek / ChatGPT 等付费或外部模型；
- 用量 input_tokens / output_tokens / estimated_cost_usd 一律记 0，不得伪造；
- 演示状态全部落在 .workbuddy_runtime/stage25b2a/（已 gitignore，绝不入库）；
- 两个任务均为 ASIP 安全场景（虚构）：乍得（法语）安全事件 + 尼日尔（英语）交通中断，
  真实 source_text 进入 AI Task，content_hash 由 source_text 计算。
"""

import os
import sys
import json
import shutil
import argparse
import hashlib

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.dirname(_HERE)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from ai.contracts import new_ai_task  # noqa: E402
from ai.workbuddy_queue_provider import WorkbuddyQueueProvider  # noqa: E402
from ai.workbuddy_worker import (  # noqa: E402
    claim_batch, ingest_results, status_summary,
)

# 运行时目录（与 data/ai 完全隔离；gitignore，绝不入库）
DEFAULT_AI_ROOT = os.path.join(
    os.path.dirname(_SCRIPTS), ".workbuddy_runtime", "stage25b2a"
)

EXPECTED_PROVIDER = "workbuddy_queue"
EXPECTED_MODEL = "hy3"

# 分类枚举（用于结果语义校验）
SECURITY_EVENT_TYPES = {
    "armed_incident", "security_incident", "shooting_incident",
    "violent_incident", "explosion_incident",
}
TRANSPORT_EVENT_TYPES = {
    "transport_disruption", "road_closure", "traffic_disruption",
    "infrastructure_disruption",
}

# ── 真实虚构 source_text（明确标注 FICTIF / SYNTHETIC，不指向任何真实事件）──
TCD_SOURCE_TEXT = (
    "[SCÉNARIO FICTIF]\n"
    "Des tirs ont été signalés dans la soirée près d'un marché de la localité "
    "fictive de Dar-Salam, au Tchad. Les forces de sécurité ont temporairement "
    "bouclé le secteur. Les autorités n'ont pas encore confirmé s'il y a eu des "
    "morts ou des blessés."
)

NER_SOURCE_TEXT = (
    "[SYNTHETIC SCENARIO]\n"
    "Local authorities temporarily closed the main road near the fictional town "
    "of Kori in Niger after an unidentified object was found beside the roadway. "
    "Traffic was diverted while security personnel inspected the area. No "
    "casualties were officially reported."
)

# (country_iso3, source_language, source_text, scenario_id, priority)
SCENARIOS = [
    ("TCD", "fr", TCD_SOURCE_TEXT, "synthetic-tcd-darsalam-2026", "critical"),
    ("NER", "en", NER_SOURCE_TEXT, "synthetic-ner-kori-2026", "high"),
]


def _content_hash(text):
    """content_hash 必须基于 source_text 计算（稳定且可复现）。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def prepare(ai_root=DEFAULT_AI_ROOT, worker_id="workbuddy-hy3-demo"):
    """在 queue 放入 2 个合成 ASIP 安全任务（synthetic=true），并 claim 出批次。

    返回信息字典，含 batch_id、tasks（task_id / task_type / country_iso3 /
    source_language / scenario_id / source_text / content_hash）、各批次文件路径，
    供 Hy3 生成结果时引用 task_id 与原文。
    """
    os.makedirs(ai_root, exist_ok=True)
    provider = WorkbuddyQueueProvider({}, ai_root=ai_root)
    claimed_tasks = []
    for iso3, lang, src, scid, prio in SCENARIOS:
        input_ref = {
            "country_iso3": iso3,
            "source_language": lang,
            "source_text": src,
            "synthetic": True,
            "scenario_id": scid,
        }
        ch = _content_hash(src)
        t = new_ai_task("article_analysis", input_ref, ch, "ai_v1", "1.0",
                        provider_requested=EXPECTED_PROVIDER,
                        priority=prio, max_retries=1)
        t["synthetic"] = True  # 标记合成，绝不进入生产数据
        provider.submit_task(t)
        claimed_tasks.append(t)
    claimed = claim_batch(ai_root, worker_id=worker_id, batch_size=2,
                          lease_minutes=30,
                          expected_provider=EXPECTED_PROVIDER,
                          expected_model=EXPECTED_MODEL)
    bdir = os.path.join(ai_root, "batches", claimed["batch_id"])
    return {
        "ai_root": ai_root,
        "batch_id": claimed["batch_id"],
        "worker_id": claimed["worker_id"],
        "tasks": [
            {
                "task_id": t["task_id"],
                "task_type": t["task_type"],
                "country_iso3": (t.get("input_ref") or {}).get("country_iso3"),
                "source_language": (t.get("input_ref") or {}).get("source_language"),
                "scenario_id": (t.get("input_ref") or {}).get("scenario_id"),
                "source_text": (t.get("input_ref") or {}).get("source_text"),
                "content_hash": t.get("content_hash"),
            }
            for t in claimed["tasks"]
        ],
        "manifest_path": os.path.join(bdir, "manifest.json"),
        "request_md_path": os.path.join(bdir, "WORKBUDDY_REQUEST.md"),
        "template_path": os.path.join(bdir, "results.template.json"),
    }


def validate_result_event(result):
    """对单条 AI 结果做业务语义校验（安全事件 / 交通中断 / 伤亡未确认）。

    返回错误字符串列表；空列表表示通过。verify 与测试均复用此函数。
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


def verify(ai_root=DEFAULT_AI_ROOT, batch_id=None, info=None):
    """校验批次最终状态，返回 {ok, checks, errors}。

    硬性条件（任一失败 ok=false）：
      1. batch manifest 存在
      2. task_count=2
      3. expected_provider=workbuddy_queue
      4. expected_model=hy3
      5. queue=0
      6. processing=0
      7. completed=2
      8. leases=0
      9. 两个 completed task_id 与 manifest 一致
     10. 两个 AI Result 均通过 Schema
     11. country_iso3 分别为 TCD 与 NER
     12. synthetic 均为 true
     13. 两个结果均有非空 summary_zh
     14. 乍得结果保留“伤亡未确认”
     15. 尼日尔结果不虚构伤亡
     16. 不存在第二份重复 completed 结果
    """
    checks = {}
    errors = []

    def add(cond, name, val=None):
        checks[name] = (val if val is not None else cond)
        if not cond:
            errors.append(name)

    # 定位批次目录
    if info is not None and info.get("batch_id"):
        bdir = os.path.join(ai_root, "batches", info["batch_id"])
    else:
        bpat = os.path.join(ai_root, "batches")
        if not os.path.isdir(bpat):
            return {"ok": False, "checks": {"manifest_exists": False},
                    "errors": ["no batches dir"]}
        subs = [d for d in os.listdir(bpat)
                if os.path.isdir(os.path.join(bpat, d))
                and not d.startswith(".tmp_")]
        if not subs:
            return {"ok": False, "checks": {"manifest_exists": False},
                    "errors": ["no batch found"]}
        bdir = os.path.join(bpat, sorted(subs)[-1])

    manifest = os.path.join(bdir, "manifest.json")
    if not os.path.exists(manifest):
        return {"ok": False, "checks": {"manifest_exists": False},
                "errors": ["manifest missing"]}
    add(True, "manifest_exists")

    m = _read_json(manifest)
    add(m.get("task_count") == 2, "task_count", m.get("task_count"))
    add(m.get("expected_provider") == EXPECTED_PROVIDER,
        "expected_provider", m.get("expected_provider"))
    add(m.get("expected_model") == EXPECTED_MODEL,
        "expected_model", m.get("expected_model"))
    manifest_ids = {t["task_id"] for t in m.get("tasks", [])}

    # 队列状态
    st = status_summary(ai_root)
    add(st.get("queue", 0) == 0, "queue", st.get("queue"))
    add(st.get("processing", 0) == 0, "processing", st.get("processing"))
    add(st.get("completed", 0) == 2, "completed", st.get("completed"))
    add(st.get("leases", 0) == 0, "leases", st.get("leases"))

    # completed 与 manifest 一致性
    comp_dir = os.path.join(ai_root, "completed")
    completed_ids = set()
    if os.path.isdir(comp_dir):
        for fn in os.listdir(comp_dir):
            if fn.endswith(".json"):
                tid = fn[:-5]
                if tid in manifest_ids:
                    completed_ids.add(tid)
    add(completed_ids == manifest_ids, "completed_task_ids_match",
        sorted(completed_ids))
    add(len(completed_ids) == 2, "no_duplicate_completed", len(completed_ids) == 2)

    # 逐结果校验
    for tid in sorted(manifest_ids):
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
        from ai.contracts import validate_ai_result  # 延迟导入，避免循环依赖
        schema_errs = validate_ai_result(res)
        add(schema_errs == [], "schema_%s" % tid, schema_errs == [])
        r = res.get("result") or {}
        add(r.get("country_iso3") in ("TCD", "NER"),
            "country_%s" % tid, r.get("country_iso3"))
        add(r.get("synthetic") is True, "synthetic_%s" % tid, r.get("synthetic"))
        add(bool(r.get("summary_zh")), "summary_zh_%s" % tid, bool(r.get("summary_zh")))
        sem_errs = validate_result_event(res)
        add(sem_errs == [], "semantics_%s" % tid, sem_errs == [])
        checks.setdefault("event_type_%s" % tid, r.get("event_type"))

    ok = (len(errors) == 0)
    return {"ok": ok, "checks": checks, "errors": errors}


def cleanup(ai_root=DEFAULT_AI_ROOT):
    """删除整个运行时目录。"""
    if os.path.isdir(ai_root):
        shutil.rmtree(ai_root, ignore_errors=True)
    return not os.path.isdir(ai_root)


def run(ai_root=DEFAULT_AI_ROOT, result_file=None, worker_id="workbuddy-hy3-demo"):
    """完整演示：prepare → ingest(result_file) → 幂等重ingest → verify。

    假设 result_file 已由当前 Hy3 会话生成（含 2 个合法结果）。
    """
    info = prepare(ai_root=ai_root, worker_id=worker_id)
    if result_file is None:
        return {"ok": False, "stage": "prepare", "info": info,
                "note": "需先由 Hy3 生成结果文件"}
    rep1 = ingest_results(ai_root, info["batch_id"], result_file)
    rep2 = ingest_results(ai_root, info["batch_id"], result_file)  # 幂等
    v = verify(ai_root, info["batch_id"], info)
    ok = (rep1.get("accepted") == 2
          and rep1.get("batch_complete") is True
          and rep2.get("accepted") == 0
          and all(e.get("outcome") == "idempotent_success"
                  for e in rep2.get("tasks", []))
          and v.get("ok") is True)
    return {
        "ok": ok,
        "prepare": info,
        "ingest_first": rep1,
        "ingest_idempotent": rep2,
        "verify": v,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="ASIP 2.5B-2A 验收补正 单会话 Hy3（免费）手工交接演示")
    ap.add_argument("--ai-root", default=DEFAULT_AI_ROOT)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare")
    sub.add_parser("verify")
    sub.add_parser("cleanup")
    r = sub.add_parser("run")
    r.add_argument("--result-file", required=True)
    try:
        args = ap.parse_args(argv)
        root = args.ai_root

        if args.cmd == "prepare":
            info = prepare(ai_root=root)
            print(json.dumps(info, ensure_ascii=False, indent=2))
            return 0
        elif args.cmd == "verify":
            v = verify(ai_root=root)
            print(json.dumps(v, ensure_ascii=False, indent=2))
            return 0 if v.get("ok") else 1
        elif args.cmd == "cleanup":
            ok = cleanup(ai_root=root)
            print(json.dumps({"cleaned": ok}, ensure_ascii=False, indent=2))
            return 0 if ok else 1
        elif args.cmd == "run":
            out = run(ai_root=root, result_file=args.result_file)
            print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
            return 0 if out.get("ok") else 1
        return 0
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write("error: %s\n" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
