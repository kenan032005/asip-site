#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 7B Read-only Preview Deployment —— 预览构建脚本（v2）。

将现有 development 前端（dist/，已脱敏公开子集）原样镜像到
preview/stage7b/，仅新增/调整：
  - 每页 <meta name="robots" content="noindex,nofollow">
  - 顶部 Development Preview banner（明确 Not Production + 返回正式站）
  - common.js NAV 预览专用改写："/asip-site/intelligence/africa/" →
    "intelligence/africa/"（避免预览内点击跳生产根；不改生产源码）
  - public/ 运行时兜底副本：preview/stage7b/public/*.json（与
    API.get("public/xxx") 相对解析路径一致；__DB__ 为主，此为次保险）
  - status/index.html（能力状态清单：VISIBLE_NOW / BACKEND_READY_NOT_EXPOSED /
    STAGE8_PENDING，§十二 17 项）
  - report-mock/index.html（复用 Stage7B renderer 渲染 MOCK 日报样例，
    明确标注 MOCK / NOT REAL INTELLIGENCE REPORT；FACT/ASSESSMENT/OUTLOOK
    视觉分层）
  - data/preview_reports/：sanitized 报告产物（mock daily + TCD/SSD weekly，
    删除 generation_metadata 等内部字段；来源为 data/runtime/report_preview/
    生成的 mock artifact，非 data/runtime 目录复制）

绝不复制 data/runtime/、.env、密钥、review packs、provider telemetry。
生成物用于只读开发预览，不进生产根。

用法：
  python scripts/preview/build_preview.py [--out DIR]
"""
import os
import re
import sys
import json
import shutil
import html as _html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"
PROD_URL = "https://kenan032005.github.io/asip-site/"

NOINDEX = '  <meta name="robots" content="noindex,nofollow">'

BANNER_CSS = """
    .asip-preview-banner{position:relative;background:#1e293b;color:#e2e8f0;
      padding:8px 14px;font-size:13px;line-height:1.5;border-bottom:3px solid #f59e0b;
      font-family:"Microsoft YaHei",sans-serif;z-index:999}
    .asip-preview-banner strong{color:#fbbf24}
    .asip-preview-banner .badge{display:inline-block;background:#b91c1c;color:#fff;
      border-radius:4px;padding:1px 8px;margin:0 6px;font-weight:700}
    .asip-preview-banner a{color:#93c5fd;text-decoration:none;margin-left:10px}
    .asip-preview-banner a:hover{text-decoration:underline}
  """

BANNER_TMPL = (
    '<div class="asip-preview-banner">'
    '<strong>ASIP Development Preview</strong> · Stage 7B Snapshot'
    '<span class="badge">Not Production</span>'
    '<a href="{prod}" target="_blank" rel="noopener">← 返回正式站</a>'
    '<a href="{status}">开发状态</a>'
    '<a href="{mock}">报告样例 (MOCK)</a>'
    '</div>'
)

STATUS_CAP = {
    "VISIBLE_NOW": ("#15803d", "前端已可见",
                    "该能力在当前前端有对应页面 / 数据展示。"),
    "BACKEND_READY_NOT_EXPOSED": ("#b45309", "后端就绪 · 前端未暴露",
                                  "引擎 / 数据已在后台就绪，但当前前端尚未接入展示。"),
    "STAGE8_PENDING": ("#7c3aed", "Stage8 待办",
                       "需在 Stage8 规划 / 实现，当前冻结未启用。"),
}

# §十二：17 项能力状态（只反映真实现状，供 Frontend Gap Audit 参考）
CAPABILITIES = [
    ("Existing Frontend", "VISIBLE_NOW",
     "首页 / 事件 / 国家 / 日报 / 疾病风险 页面均已上线（本次预览原样镜像）。"),
    ("Country Pages", "VISIBLE_NOW",
     "countries.html + country.html（国家风险等级 / 事件过滤）。"),
    ("Entity Database", "VISIBLE_NOW",
     "intelligence/africa/entities + entity 档案页（公开知识库）。"),
    ("Relationship Database", "VISIBLE_NOW",
     "intelligence/africa/relations + relation 档案页。"),
    ("Source Expansion", "BACKEND_READY_NOT_EXPOSED",
     "信源注册 / 扩展引擎已建设（Stage Expansion A/B），前端仅基础 sources 列表。"),
    ("Verification", "VISIBLE_NOW",
     "事件页展示 verification_status（verified / probable / single_source / conflicting）。"),
    ("Disease Risk", "VISIBLE_NOW",
     "disease-risk.html 与 data/public/disease_events.json 已公开展示。"),
    ("Master Event Clustering", "BACKEND_READY_NOT_EXPOSED",
     "Stage6 主事件聚类引擎已就绪，前端事件页尚未显式聚合 master event 时间线。"),
    ("Event Timeline", "BACKEND_READY_NOT_EXPOSED",
     "Stage6B social timeline 已生成，前端未接入时间线视图。"),
    ("Disease Timeline", "BACKEND_READY_NOT_EXPOSED",
     "Stage6B disease outbreak timeline 已生成，前端未接入。"),
    ("Africa Daily Engine", "BACKEND_READY_NOT_EXPOSED",
     "Stage7A 选材 + Stage7B 生成 / 质量门已就绪；本预览 report-mock 为 MOCK 样例。"),
    ("Country Weekly Engine", "BACKEND_READY_NOT_EXPOSED",
     "Stage7A 周报引擎已就绪；report-mock 含 TCD/SSD 样例，前端未接入。"),
    ("Major Event Brief Engine", "BACKEND_READY_NOT_EXPOSED",
     "Stage7A brief 触发引擎已就绪，前端未接入。"),
    ("Production AI", "STAGE8_PENDING",
     "AI 调用冻结（browser_direct_api_call=false、AI calls=0）。"),
    ("Cloud Scheduling", "STAGE8_PENDING",
     "schedule / 6h 采集 / 日报 cron 全部冻结（production_auto_update=false）。"),
    ("Monitoring", "STAGE8_PENDING",
     "Stage8 监控能力待规划，当前未启用。"),
    ("Production Cutover", "STAGE8_PENDING",
     "production root 保持线上版本，未做任何 cutover。"),
]


def rel_prefix(depth):
    return "../" * depth


def inject(html, depth):
    """注入 noindex + banner。"""
    html = re.sub(r'(<meta name="viewport"[^>]*>)',
                  lambda m: m.group(1) + "\n" + NOINDEX, html, count=1)
    if NOINDEX not in html:
        html = re.sub(r'(<head[^>]*>)', lambda m: m.group(1) + "\n" + NOINDEX,
                      html, count=1)
    rp = rel_prefix(depth)
    banner = (BANNER_TMPL.format(prod=PROD_URL, status=rp + "status/",
                                 mock=rp + "report-mock/"))
    if "asip-preview-banner" not in html:
        html = re.sub(r'(</head>)',
                      lambda m: "<style>%s</style>\n%s" % (BANNER_CSS, m.group(1)),
                      html, count=1)
    html = re.sub(r'(<body[^>]*>)', lambda m: m.group(1) + "\n" + banner,
                  html, count=1)
    return html


def preview_transform_common_js(path):
    """预览专用改写：NAV 安全情报库链接不跳生产根（§十一）。"""
    txt = path.read_text(encoding="utf-8")
    new = txt.replace('"/asip-site/intelligence/africa/"',
                      '"intelligence/africa/"')
    if new != txt:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def add_public_fallback(out):
    """preview/stage7b/public/*.json —— 运行时兜底副本（§二 数据隔离）。

    API.get("public/published_events") 相对页面根解析为 public/*.json；
    __DB__ 内联为主、此副本为次保险，二者都只落在 preview/stage7b/** 内。
    """
    src = DIST / "data" / "public"
    dst = out / "public"
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in sorted(src.glob("*.json")):
        shutil.copy(f, dst / f.name)
        n += 1
    return n


def sanitize_report(r):
    """§四：删除 generation_metadata 等内部字段，保留报告正文。"""
    r = dict(r)
    r.pop("generation_metadata", None)
    for k in list(r.keys()):
        if any(x in k.lower() for x in ("debug", "trace", "prompt", "input_audit",
                                        "provider_telemetry")):
            r.pop(k)
    return r


def gen_preview_reports(out):
    """data/preview_reports/：sanitized mock 报告产物。"""
    dst = out / "data" / "preview_reports"
    dst.mkdir(parents=True, exist_ok=True)
    daily_src = sorted((ROOT / "data" / "runtime" / "report_preview" /
                        "africa_daily").glob("DAILY_*.json"))
    weekly_src = sorted((ROOT / "data" / "runtime" / "report_preview" /
                         "country_weekly").glob("WEEKLY_*.json"))
    out_files = []
    if daily_src:
        r = sanitize_report(json.loads(daily_src[0].read_text(encoding="utf-8")))
        f = dst / "mock-daily.json"
        f.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        out_files.append(f)
    wk_map = [("TCD", "mock-weekly-tcd.json"), ("SSD", "mock-weekly-ssd.json")]
    for tag, name in wk_map:
        src = next((w for w in weekly_src if tag in w.stem), None)
        if src:
            r = sanitize_report(json.loads(src.read_text(encoding="utf-8")))
            f = dst / name
            f.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
            out_files.append(f)
    return out_files


def gen_status_page(out_html, depth):
    rp = rel_prefix(depth)
    rows = []
    for name, cap, note in CAPABILITIES:
        color, _, _ = STATUS_CAP[cap]
        rows.append(
            "<tr><td><code>%s</code></td>"
            "<td><span class='cap' style='background:%s'>%s</span></td>"
            "<td>%s</td></tr>" % (_html.escape(name), color, cap,
                                  _html.escape(note)))
    cap_legend = "".join(
        "<span class='cap' style='background:%s'>%s</span> %s &nbsp; " %
        (c, k, d) for k, (c, d, _) in STATUS_CAP.items())
    doc = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
%s
<title>ASIP Development Status · Stage 7B Preview</title>
<style>
body{max-width:920px;margin:0 auto;padding:0 20px 60px;
  font-family:"Microsoft YaHei",sans-serif;color:#1f2937;background:#f8fafc}
h1{color:#1e3a8a;border-bottom:2px solid #2563eb;padding-bottom:8px}
.cap{display:inline-block;color:#fff;border-radius:4px;padding:2px 8px;
  font-size:12px;font-weight:700}
table{width:100%%;border-collapse:collapse;margin-top:12px}
td,th{border:1px solid #cbd5e1;padding:8px 10px;vertical-align:top;text-align:left}
th{background:#e2e8f0}
.legend{margin:10px 0;font-size:13px}
code{background:#eef2ff;padding:1px 5px;border-radius:3px}
</style></head>
<body>
<div class="asip-preview-banner"><strong>ASIP Development Preview</strong> ·
Stage 7B Snapshot<span class="badge">Not Production</span>
<a href="%s" target="_blank" rel="noopener">← 返回正式站</a>
<a href="%sstatus/">开发状态</a><a href="%sreport-mock/">报告样例 (MOCK)</a></div>
<h1>ASIP 开发状态清单（Stage 7B Preview）</h1>
<p class="legend">能力状态图例：%s</p>
<p>本页仅说明当前后台能力与前端暴露情况，供 Frontend Gap Audit 参考。
不暴露任何 internal runtime 数据。</p>
<table><tr><th>能力</th><th>状态</th><th>说明</th></tr>
%s</table>
</body></html>""" % (NOINDEX, PROD_URL, rp, rp, cap_legend, "\n".join(rows))
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(doc, encoding="utf-8")


def gen_report_mock_page(out_html, daily_dict, weekly_samples, depth):
    rp = rel_prefix(depth)
    body = render_daily_html(daily_dict)
    weekly_links = "".join(
        "<li><a href='%s' target='_blank'>%s</a>（MOCK 周报样例 JSON）</li>" %
        (_html.escape(w.name), _html.escape(w.stem)) for w in weekly_samples)
    doc = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
%s
<title>ASIP Report UI Preview (MOCK) · Stage 7B</title>
<style>
body{max-width:920px;margin:0 auto;padding:0 20px 60px;
  font-family:"Microsoft YaHei",sans-serif;color:#1f2937;background:#fff}
.preview-warn{background:#fef2f2;border:2px solid #dc2626;color:#991b1b;
  padding:10px 14px;border-radius:6px;margin:14px 0;font-weight:700}
h1{color:#1e3a8a;border-bottom:2px solid #2563eb;padding-bottom:8px}
.sec{border:1px solid #e2e8f0;border-radius:6px;padding:10px 14px;margin:14px 0}
.sec h2{margin:0 0 8px;color:#1e3a8a;font-size:17px}
.item{border-top:1px dashed #cbd5e1;padding:10px 0}
.item h3{margin:0 0 6px;color:#374151}
.fact,.assess,.outlook{margin:4px 0;padding:6px 10px;border-radius:4px}
.fact{background:#eff6ff;border-left:4px solid #2563eb}
.assess{background:#fffbeb;border-left:4px solid #f59e0b}
.outlook{background:#ecfdf5;border-left:4px solid #10b981}
.fact b,.assess b,.outlook b{margin-right:6px}
.tags span{display:inline-block;background:#fef3c7;color:#92400e;border-radius:4px;
  padding:1px 7px;margin-right:6px;font-size:12px}
.unc{color:#92400e;font-size:13px}
.refs{color:#475569;font-size:13px}
</style></head>
<body>
<div class="asip-preview-banner"><strong>ASIP Development Preview</strong> ·
Stage 7B Snapshot<span class="badge">Not Production</span>
<a href="%s" target="_blank" rel="noopener">← 返回正式站</a>
<a href="%sstatus/">开发状态</a><a href="%sreport-mock/">报告样例 (MOCK)</a></div>
<div class="preview-warn">⚠ MOCK / DEVELOPMENT SAMPLE — NOT REAL INTELLIGENCE REPORT
本页仅为报告 UI 排版预览，内容由 mock 生成器占位，<b>非真实情报</b>。</div>
<h1>%s</h1>
<p>报告期：%s ～ %s ｜ 生成：%s ｜ 时区：%s</p>
%s
<p class="refs">sanitized MOCK 样例（均为生成器占位，非真实数据）：</p>
<ul class="refs">%s</ul>
</body></html>""" % (NOINDEX, PROD_URL, rp, rp,
        _html.escape(daily_dict.get("title", "非洲地区社会安全与综合形势日报")),
        _html.escape(str(daily_dict.get("period_start"))),
        _html.escape(str(daily_dict.get("period_end"))),
        _html.escape(str(daily_dict.get("generated_at"))),
        _html.escape(str(daily_dict.get("report_timezone"))),
        body, weekly_links)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(doc, encoding="utf-8")


def render_daily_html(report):
    titles = [
        ("executive_summary", "一、核心摘要"),
        ("major_security_developments", "二、主要安全动态"),
        ("political_social_stability", "三、政治与社会稳定"),
        ("terrorism_armed_violence", "四、恐怖主义与武装暴力"),
        ("cross_border_regional_risks", "五、跨境与地区风险"),
        ("public_health_disease_risks", "六、公共卫生与疾病风险"),
        ("key_changes", "七、较上期主要变化"),
        ("watch_items", "八、关注事项"),
    ]
    out = []
    for sec, title in titles:
        items = report.get(sec, []) or []
        if not items:
            continue
        out.append("<div class='sec'><h2>%s</h2>" % title)
        for it in items:
            out.append("<div class='item'>")
            out.append("<h3>%s</h3>" % _html.escape(
                it.get("headline_zh") or it.get("item_id") or ""))
            tags = []
            if it.get("single_source_warning"):
                tags.append("<span>⚠ 单一来源</span>")
            if it.get("conflicting"):
                tags.append("<span>⚠ 来源冲突</span>")
            if tags:
                out.append("<div class='tags'>%s</div>" % "".join(tags))
            out.append("<div class='fact'><b>事实 FACT</b>%s</div>" %
                       _html.escape(it.get("fact_summary") or ""))
            if it.get("assessment"):
                out.append("<div class='assess'><b>判断 ASSESSMENT</b>%s</div>" %
                           _html.escape(it["assessment"]))
            if it.get("outlook"):
                out.append("<div class='outlook'><b>展望 OUTLOOK</b>%s</div>" %
                           _html.escape(it["outlook"]))
            if it.get("uncertainties"):
                out.append("<div class='unc'>不确定：%s</div>" % _html.escape(
                    "；".join(it["uncertainties"])))
            refs = it.get("source_refs") or []
            if refs:
                out.append("<div class='refs'>来源：%s</div>" % _html.escape(
                    ", ".join(r.get("source_name") or r.get("source_id")
                              for r in refs)))
            out.append("</div>")
        out.append("</div>")
    if report.get("overall_assessment"):
        out.append("<div class='sec'><h2>整体评估</h2><p>%s</p></div>" %
                   _html.escape(report["overall_assessment"]))
    if report.get("source_notes"):
        out.append("<div class='sec'><h2>来源说明</h2><ul class='refs'>")
        for sn in report["source_notes"]:
            url = (" (%s)" % sn["url"]) if sn.get("url") else ""
            out.append("<li>%s%s</li>" % _html.escape(
                sn.get("source_name") or sn.get("source_id")), url)
        out.append("</ul></div>")
    return "\n".join(out)


def scan_secrets(root):
    """§九/§十四：扫描预览产物中是否含密钥 / internal runtime。"""
    problems = []
    pats = [
        r"ASIP_GLM_API_KEY", r"ASIP_DEEPSEEK_API_KEY", r"sk-[A-Za-z0-9]{16,}",
        r"Bearer\s+[A-Za-z0-9._-]{16,}", r"Authorization\s*[:=]\s*['\"]?[A-Za-z0-9._-]{16,}",
        r"GITHUB_TOKEN", r"GH_TOKEN", r"client_secret", r"api[_-]?key['\"]?\s*[:=]\s*['\"][A-Za-z0-9]{16,}",
        r"AIza[0-9A-Za-z_-]{20,}",
    ]
    rx = re.compile("|".join(pats))
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in (".html", ".json", ".js", ".css", ".md", ".txt"):
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for m in rx.finditer(txt):
                problems.append("%s : %s" % (p.relative_to(root), m.group(0)[:60]))
    if (root / "data" / "runtime").exists():
        problems.append("data/runtime 进入了预览（禁止）")
    if (root / ".env").exists():
        problems.append(".env 进入了预览（禁止）")
    # 禁止 review packs / clustering audit / source_health / provider telemetry
    for bad in ("review_packs", "clustering", "source_health", "provider_telemetry",
                "ai_cache", "candidate_pool"):
        hits = [str(p.relative_to(root)) for p in root.rglob(bad + "*")]
        if hits:
            problems.append("内部路径 %s* 进入预览: %s" % (bad, hits[:3]))
    return problems


def main():
    out_root = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv \
        else ROOT / "preview_build"
    out = out_root / "preview" / "stage7b"
    if out.exists():
        shutil.rmtree(out)

    # 1. 镜像 dist/
    shutil.copytree(DIST, out)
    print("[1] mirrored dist ->", out)

    # 1b. common.js NAV 预览改写
    js = out / "assets" / "js" / "common.js"
    if preview_transform_common_js(js):
        print("[1b] common.js NAV rewritten (preview-only)")

    # 1c. public/ 运行时兜底
    n = add_public_fallback(out)
    print("[1c] public/ fallback copies:", n)

    # 2. 注入 banner + noindex
    n = 0
    for p in sorted(out.rglob("*.html")):
        rel = p.relative_to(out)
        depth = len(rel.parent.parts)
        txt = p.read_text(encoding="utf-8")
        txt = inject(txt, depth)
        p.write_text(txt, encoding="utf-8")
        n += 1
    print("[2] injected banner+noindex into %d html files" % n)

    # 3. status 页
    gen_status_page(out / "status" / "index.html", depth=1)
    print("[3] status page generated")

    # 4. report-mock 页 + sanitized 样本（data/preview_reports/）
    samples = gen_preview_reports(out)
    mock_dir = out / "report-mock"
    mock_dir.mkdir(parents=True, exist_ok=True)
    daily_sample = next((s for s in samples if s.stem == "mock-daily"), None)
    if daily_sample:
        daily_dict = json.loads(daily_sample.read_text(encoding="utf-8"))
        gen_report_mock_page(mock_dir / "index.html", daily_dict,
                             [s for s in samples if s.stem != "mock-daily"],
                             depth=1)
        print("[4] report-mock page + %d sanitized samples generated" % len(samples))
    else:
        print("[!] 未找到 mock daily 报告，跳过 report-mock")

    # 5. 密钥 / runtime 扫描
    problems = scan_secrets(out)
    if problems:
        print("[!] SECRET/RUNTIME SCAN FAILED:")
        for pr in problems:
            print("    -", pr)
        sys.exit(2)
    print("[5] secret/runtime scan clean")

    print("BUILD OK ->", out)


if __name__ == "__main__":
    main()
