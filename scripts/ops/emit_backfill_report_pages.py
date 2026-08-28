# -*- coding: utf-8 -*-
"""为 backfill preview 生成历史日报 HTML 页面 + 并入 report_index（仅 preview dist）。"""
import json
import shutil
from pathlib import Path

ROOT = Path("C:/Users/kenan/WorkBuddy/clean/asip-v11-homepage")
DIST = ROOT / "preview_dist_backfill"
REPORTS = ROOT / "data/runtime/backfill_preview/reports"

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · ASIP</title>
<link rel="stylesheet" href="../../../assets/css/style.css">
<style>
  body {{ font-family: "Microsoft YaHei", sans-serif; background: #f4f7fb; margin: 0; padding: 0; }}
  .wrap {{ max-width: 860px; margin: 0 auto; padding: 24px 18px 60px; }}
  .badge {{ display: inline-block; background: #dbeafe; color: #1d4ed8; border-radius: 4px;
            padding: 2px 10px; font-size: 12px; margin-left: 8px; vertical-align: middle; }}
  .card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 18px; margin: 12px 0; }}
  h1 {{ font-size: 20px; color: #0f2440; }}
  .meta {{ color: #64748b; font-size: 13px; }}
  .gates {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 10px 0; }}
  .gate {{ padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
  .pass {{ background: #dcfce7; color: #166534; }}
  .fact {{ border-top: 1px solid #eef2f7; padding: 10px 0; }}
  .fact h3 {{ font-size: 15px; margin: 0 0 4px; color: #0f2440; }}
  .fact .sum {{ color: #334155; font-size: 13px; line-height: 1.6; }}
  .fact .meta {{ font-size: 12px; }}
  .analysis {{ background: #f1f5f9; border-left: 3px solid #2563eb; padding: 10px 14px;
               border-radius: 0 6px 6px 0; color: #475569; font-size: 13px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{title} <span class="badge">历史回溯生成 · Historical Reconstruction</span></h1>
  <div class="meta">报告日期：{date} ｜ 生成模式：historical_backfill ｜ 批次：asip-backfill-20260818-20260827</div>
  <div class="card">
    <div class="meta">报告状态：{status_cn}（{status}）｜ 事实数：{fact_count}</div>
    <div class="gates">{gates_html}</div>
  </div>
  <div class="card">
    <h2 style="font-size:16px;color:#0f2440;">今日事实（Verified Facts）</h2>
    {facts_html}
  </div>
  <div class="card">
    <h2 style="font-size:16px;color:#0f2440;">综合研判（AI Analysis）</h2>
    <div class="analysis">{analysis_html}</div>
  </div>
  <p class="meta">本报告为历史回溯（Historical Backfill）预览产物，未进入 Production。前端状态映射：FALLBACK → 事实版。</p>
</div>
</body>
</html>"""


def esc(s):
    if s is None:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    entries = []
    for f in sorted(REPORTS.glob("daily_*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        day = doc["report_date"]
        out = DIST / "reports" / "africa_daily" / day / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        gates_html = "".join(
            '<span class="gate %s">%s: %s</span>' % ("pass" if v == "PASS" else "fail", k, v)
            for k, v in doc["gates"].items())
        facts_html = "".join(
            '<div class="fact"><h3>%s</h3><div class="sum">%s</div>'
            '<div class="meta">%s · %s · %d source(s) · %s%s</div></div>'
            % (esc(fa.get("title_cn") or fa.get("title_en")), esc(fa.get("summary_cn")),
               esc(fa.get("country_cn")), esc(fa.get("event_type")), fa.get("source_count") or 0,
               esc(fa.get("verification_label_cn")),
               (" · 不确定性: " + "；".join(fa.get("uncertainties") or [])) if fa.get("uncertainties") else "")
            for fa in doc["facts"])
        analysis_html = "历史回溯报告为确定性事实版（本地无 DeepSeek key，未调用 AI 分析）。" \
                        "综合研判区域留待正式 AI 契约接入后填充。" \
                        if doc.get("analysis") is None else esc(json.dumps(doc["analysis"], ensure_ascii=False))
        out.write_text(TEMPLATE.format(
            title="非洲地区社会安全与综合形势日报（历史回溯）",
            date=day, status_cn="事实版" if doc["status"] == "FALLBACK" else doc["status"],
            status=doc["status"], fact_count=doc["fact_count"],
            gates_html=gates_html, facts_html=facts_html, analysis_html=analysis_html),
            encoding="utf-8")
        entries.append({
            "report_id": doc["report_id"], "title": "非洲地区社会安全与综合形势日报（历史回溯）",
            "type": "daily", "type_cn": "日报",
            "status": doc["status"], "status_cn": "事实版 · 历史回溯",
            "period_start": day, "period_end": day, "published_at": day,
            "path": "reports/africa_daily/%s/" % day,
            "country_iso3": None, "is_mock": False,
            "generation_mode": "historical_backfill", "historical_reconstruction": True,
            "backfill_batch_id": "asip-backfill-20260818-20260827",
        })
        print("page:", day)

    # 并入 report_index（历史报告置顶，带标记）
    rip = DIST / "data" / "report_index.json"
    ri = json.loads(rip.read_text(encoding="utf-8"))
    existing = {r["report_id"] for r in ri.get("reports", [])}
    added = [e for e in entries if e["report_id"] not in existing]
    ri["reports"] = added + ri.get("reports", [])
    ri["count"] = len(ri["reports"])
    ri["generated_at"] = ri.get("generated_at")
    ri["note"] = "backfill preview: +%d historical dailies (asip-backfill-20260818-20260827)" % len(added)
    rip.write_text(json.dumps(ri, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("report_index merged: +%d (total %d)" % (len(added), ri["count"]))


if __name__ == "__main__":
    main()
