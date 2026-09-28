"""C8-3 STEP 7：按新的 54 国 + 多国 + 区域规则重处理近期 `wrong_country` 隔离。

安全边界（严格遵守项目铁律）：
  · **绝不**直接写 Article Store / canonical —— 唯一入口是
    `article_persistence.persist_collected_articles()`；
  · 本工具只做两件事：
      1) 用确定性几何规则重判每条 `wrong_country` 隔离，产出分类统计与候选清单；
      2) `--apply` 时把**可恢复**的 URL 的处理状态从终态重置为可重试，
         使**下一次采集**按新规则重新发现并正常入库（等价于 quarantine_reeval 的释放语义）。
  · 不触碰其他隔离原因（TRUE SAFETY 永不释放；not_security_relevant 不在本任务范围）。

用法：
  python scripts/ops/quarantine_recovery.py            # 只统计（dry）
  python scripts/ops/quarantine_recovery.py --apply    # 重置可恢复 URL 的处理状态
"""
import argparse
import collections
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BJT = timezone(timedelta(hours=8))
QUAR = Path("data") / "canonical" / "quarantine.json"
OUT = Path("data") / "runtime" / "ops" / "quarantine_recovery_candidates.json"
REPORT = Path("reports") / "ops" / "C8_3_QUARANTINE_RECOVERY.md"


def load(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def parse_t(s):
    if not s:
        return None
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def is_terminal_state(status):
    """C8-3 FIX 1：终态判据**大小写不敏感**。

    生产 processing_state 实际使用小写（如 `quarantined_terminal`、
    `extraction_failed_terminal`），而原实现比较 `.endswith("TERMINAL")`（大写）
    → 永不匹配 → state_reset_count 恒为 0，355 条合法恢复候选全部无法重置。
    语义未变：仍只认"以 TERMINAL 结尾"的状态，不放宽任何其他状态。
    """
    return str(status or "").upper().endswith("TERMINAL")


def main(argv=None):
    ap = argparse.ArgumentParser(description="C8-3 STEP 7 隔离重处理（确定性）")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root)
    sys.path.insert(0, str(root / "scripts"))
    sys.path.insert(0, str(root / "scripts" / "collectors"))
    from geo_scope import detect_geo_scope, load_monitored_country_index  # noqa: E402
    from data import quarantine_reeval as R  # noqa: E402

    idx = load_monitored_country_index(root)
    doc = load(root / QUAR, {}) or {}
    items = doc.get("items") if isinstance(doc, dict) else doc
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=args.days)

    scanned = reprocessable = 0
    buckets = collections.Counter()
    candidates = []
    for it in (items or []):
        if str(it.get("reason_code")) != R.REPROCESSABLE_REASON:
            continue
        t = parse_t(it.get("detected_at"))
        if not t or t < since:
            continue
        scanned += 1
        ok, why = (True, "")
        try:
            ok, why = R.is_reprocessable(it) if hasattr(R, "is_reprocessable") else (True, "")
        except Exception:  # noqa: BLE001
            ok, why = True, ""
        if not ok:
            buckets["NOT_REPROCESSABLE:" + str(why)[:40]] += 1
            continue
        reprocessable += 1
        text = str(it.get("title") or "") + " " + str((it.get("legacy_payload") or {}).get("summary") or "")
        geo = detect_geo_scope(text, idx)
        scope = geo["scope"]
        if scope == "SINGLE_COUNTRY":
            buckets["RECOVERED_SINGLE_COUNTRY"] += 1
        elif scope == "MULTI_COUNTRY":
            buckets["RECOVERED_MULTI_COUNTRY"] += 1
        elif scope == "REGIONAL_AFRICA":
            buckets[(("RECOVERED_AFRICA_WIDE" if geo.get("region") == "AFRICA_WIDE"
                      else "RECOVERED_REGIONAL_AFRICA"))] += 1
        elif scope == "OUTSIDE_AFRICA":
            buckets["OUTSIDE_AFRICA"] += 1
        else:
            buckets["STILL_COUNTRY_UNRESOLVED"] += 1
        if scope != "COUNTRY_UNRESOLVED" and scope != "OUTSIDE_AFRICA":
            candidates.append({
                "quarantine_id": it.get("quarantine_id"), "url": it.get("original_id") or it.get("url"),
                "title": it.get("title"), "detected_at": it.get("detected_at"),
                "scope": scope, "countries": geo.get("countries"), "region": geo.get("region"),
                "within_24h": bool(t and t >= now - timedelta(hours=24)),
            })

    recovered = [c for c in candidates]
    out = {
        "schema": "c8-3-quarantine-recovery-v1",
        "generated_at": now.isoformat(timespec="seconds"),
        "window_days": args.days,
        "WRONG_COUNTRY_SCANNED": scanned,
        "WRONG_COUNTRY_REPROCESSED": reprocessable,
        "RECOVERED_TOTAL": len(recovered),
        "RECOVERED_ITEMS_WITHIN_24H": len([c for c in recovered if c["within_24h"]]),
        "RECOVERED_ITEMS_24H_TO_7D": len([c for c in recovered if not c["within_24h"]]),
        "BY_CLASS": dict(buckets),
        "candidates": recovered,
        "apply": bool(args.apply),
    }
    print(json.dumps({k: v for k, v in out.items() if k != "candidates"},
                     ensure_ascii=False, indent=1))
    if args.apply:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        # 重置可恢复 URL 的**处理状态**（不写 canonical；由下次采集重新发现并入库）
        try:
            sys.path.insert(0, str(root / "scripts" / "collectors"))
            from framework import load_processing_state, save_processing_state  # noqa: E402
            st = load_processing_state() or {}
            arts = st.get("articles") or {}
            matched = reset = not_found = 0
            for c in recovered:
                u = c.get("url")
                if u and u in arts:
                    matched += 1
                    rec = arts[u]
                    # FIX 1：大小写不敏感（生产为小写 quarantined_terminal）
                    if is_terminal_state(rec.get("state")):
                        rec["state"] = "PENDING_RECOVERY"
                        rec["recovery_note"] = "C8-3 geo scope recovery"
                        reset += 1
                else:
                    # FIX 2：不在 processing_state 中的候选**只报告、不伪造**
                    # （下次正常采集会把它当新 URL 处理，届时观察是否自然重回处理链）
                    not_found += 1
            if reset:
                save_processing_state(st)
            out["state_reset_count"] = reset
            out["RECOVERY_CANDIDATES_TOTAL"] = len(recovered)
            out["RECOVERY_STATE_MATCHED"] = matched
            out["RECOVERY_STATE_RESET"] = reset
            out["RECOVERY_STATE_NOT_FOUND"] = not_found
            OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
            print("state_reset_count =", reset, "| matched =", matched, "| not_found =", not_found)
        except Exception as e:  # noqa: BLE001
            print("state reset skipped:", str(e)[:120])
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# C8-3 · 近期 wrong_country 重处理", "",
                 "生成：%s ｜ 窗口：%s 天" % (out["generated_at"], args.days), "",
                 "| 指标 | 数值 |", "|---|---|"]
        for k in ("WRONG_COUNTRY_SCANNED", "WRONG_COUNTRY_REPROCESSED", "RECOVERED_TOTAL",
                  "RECOVERED_ITEMS_WITHIN_24H", "RECOVERED_ITEMS_24H_TO_7D"):
            lines.append("| %s | %s |" % (k, out[k]))
        lines += ["", "## 分类", "", "| 类别 | 数量 |", "|---|---|"]
        for k, v in sorted(buckets.items(), key=lambda kv: -kv[1]):
            lines.append("| %s | %d |" % (k, v))
        REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("written:", OUT, "/", REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
