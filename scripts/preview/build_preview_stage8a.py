#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8A — Frontend Product Integration 只读预览构建器。

dist/（已含 7 个公开安全前端视图 + __DB__）原样镜像到 preview/stage8a/：
  - 每页 <meta name="robots" content="noindex,nofollow"> + Development Preview
    banner（Not Production，返回正式站）
  - report-mock/：sanitized mock 报告样例（daily + TCD/SSD weekly，
    与 report_index.json 的 path 对齐；删除 generation_metadata）
  - status/index.html：能力状态清单
  - public/ 运行时兜底副本（API.get("public/*") 相对解析路径）
  - 密钥 / data/runtime 扫描（失败即退出）

绝不复制 data/runtime/、.env、密钥、review packs、provider telemetry。
生产根零修改（部署时仅新增 preview/stage8a/**）。

用法：
  python scripts/preview/build_preview_stage8a.py [--out DIR]
"""
import re
import sys
import json
import shutil
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
    '<strong>ASIP Development Preview</strong> · Stage 8A · Frontend Integration'
    '<span class="badge">Not Production</span>'
    '<a href="{prod}" target="_blank" rel="noopener">← 返回正式站</a>'
    '<a href="{status}">开发状态</a>'
    '<a href="{mock}">报告样例 (MOCK)</a>'
    '</div>'
)

STATUS_CAP = {
    "VISIBLE_NOW": ("#15803d", "前端已可见"),
    "BACKEND_READY_NOT_EXPOSED": ("#b45309", "后端就绪 · 前端未暴露"),
    "STAGE8_PENDING": ("#7c3aed", "Stage8 待办"),
}
CAPABILITIES = [
    ("Existing Frontend", "VISIBLE_NOW", "首页 / 态势事件 / 国家 / 疾病 / 报告 已统一导航。"),
    ("Country Pages", "VISIBLE_NOW", "countries + country（风险分组 + Priority Quick View + A-I 结构）。"),
    ("Entity Database", "VISIBLE_NOW", "intelligence/africa 实体档案页。"),
    ("Relationship Database", "VISIBLE_NOW", "intelligence/africa 关系档案页。"),
    ("Source Expansion", "BACKEND_READY_NOT_EXPOSED", "信源扩展引擎已建设，前端仅基础列表。"),
    ("Verification", "VISIBLE_NOW", "事件卡展示 已核实/较可信/单一来源/信息存在冲突 徽标。"),
    ("Disease Risk", "VISIBLE_NOW", "disease-risk.html 真 Dashboard（Outbreak-centric + 筛选 + 详情）。"),
    ("Master Event Clustering", "VISIBLE_NOW", "态势事件页 master-event 去重展示（Stage8A 已接入）。"),
    ("Event Timeline", "VISIBLE_NOW", "事件详情页时间线（update_count>1 显示）。"),
    ("Disease Timeline", "BACKEND_READY_NOT_EXPOSED", "outbreak 时间线已生成，详情面板展示确定性计数。"),
    ("Africa Daily Engine", "BACKEND_READY_NOT_EXPOSED", "引擎就绪；报告中心展示 MOCK 样例（非正式）。"),
    ("Country Weekly Engine", "BACKEND_READY_NOT_EXPOSED", "TCD/SSD weekly MOCK 样例可查看。"),
    ("Major Event Brief Engine", "BACKEND_READY_NOT_EXPOSED", "触发引擎就绪，当前无简报。"),
    ("Production AI", "STAGE8_PENDING", "AI 调用冻结（browser_direct_api_call=false）。"),
    ("Cloud Scheduling", "STAGE8_PENDING", "schedule / 6h 采集 / cron 全部冻结。"),
    ("Monitoring", "STAGE8_PENDING", "监控面板 Stage8 规划。"),
    ("Production Cutover", "STAGE8_PENDING", "production root 保持线上版本。"),
]


def rel_prefix(depth):
    return "../" * depth


def inject(html, depth):
    html = re.sub(r'(<meta name="viewport"[^>]*>)',
                  lambda m: m.group(1) + "\n" + NOINDEX, html, count=1)
    if NOINDEX not in html:
        html = re.sub(r'(<head[^>]*>)', lambda m: m.group(1) + "\n" + NOINDEX,
                      html, count=1)
    rp = rel_prefix(depth)
    banner = BANNER_TMPL.format(prod=PROD_URL, status=rp + "status/",
                                mock=rp + "report-mock/")
    if "asip-preview-banner" not in html:
        html = re.sub(r'(</head>)',
                      lambda m: "<style>%s</style>\n%s" % (BANNER_CSS, m.group(1)),
                      html, count=1)
    html = re.sub(r'(<body[^>]*>)', lambda m: m.group(1) + "\n" + banner,
                  html, count=1)
    return html


def sanitize_report(r):
    r = dict(r)
    r.pop("generation_metadata", None)
    for k in list(r.keys()):
        if any(x in k.lower() for x in ("debug", "trace", "prompt", "input_audit",
                                        "provider_telemetry")):
            r.pop(k)
    return r


def gen_report_mock(out):
    """report-mock/ 样例：与 report_index.json 的 path 对齐。"""
    src = ROOT / "data" / "runtime" / "report_preview"
    dst = out / "report-mock"
    dst.mkdir(parents=True, exist_ok=True)
    mapping = [
        ("africa_daily/DAILY_*.json", "sample-daily.json"),
        ("country_weekly/WEEKLY_TCD_*.json", "sample-weekly-tcd.json"),
        ("country_weekly/WEEKLY_SSD_*.json", "sample-weekly-ssd.json"),
    ]
    made = []
    for pat, name in mapping:
        hits = sorted((src / pat.split("/")[0]).glob(pat.split("/")[1]))
        if not hits:
            continue
        r = sanitize_report(json.loads(hits[0].read_text(encoding="utf-8")))
        (dst / name).write_text(json.dumps(r, ensure_ascii=False, indent=2),
                                encoding="utf-8")
        made.append(name)
    # 简单的 index.html 列表
    links = "".join("<li><a href='%s'>%s</a></li>" % (n, n) for n in made)
    (dst / "index.html").write_text(
        "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        + NOINDEX +
        "<title>MOCK 报告样例 · Stage 8A Preview</title></head><body>"
        + BANNER_TMPL.format(prod=PROD_URL, status="../status/", mock="") +
        "<h1>MOCK / DEVELOPMENT SAMPLE — NOT REAL INTELLIGENCE REPORT</h1>"
        "<ul>" + links + "</ul></body></html>", encoding="utf-8")
    return made


def gen_status(out, depth):
    rp = rel_prefix(depth)
    rows = []
    for name, cap, note in CAPABILITIES:
        color, _ = STATUS_CAP[cap]
        rows.append("<tr><td><code>%s</code></td>"
                    "<td><span style='background:%s;color:#fff;border-radius:4px;"
                    "padding:2px 8px;font-size:12px'>%s</span></td><td>%s</td></tr>"
                    % (name, color, cap, note))
    legend = "".join("<span style='background:%s;color:#fff;border-radius:4px;"
                     "padding:2px 8px;margin-right:8px'>%s</span>" % (c, k)
                     for k, (c, _) in STATUS_CAP.items())
    doc = ("<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
           "<meta name='viewport' content='width=device-width, initial-scale=1'>"
           + NOINDEX +
           "<title>ASIP Development Status · Stage 8A</title>"
           "<style>body{max-width:920px;margin:0 auto;padding:0 20px 60px;"
           "font-family:'Microsoft YaHei',sans-serif;color:#1f2937;background:#f8fafc}"
           "h1{color:#1e3a8a;border-bottom:2px solid #2563eb;padding-bottom:8px}"
           "table{width:100%%;border-collapse:collapse;margin-top:12px}"
           "td,th{border:1px solid #cbd5e1;padding:8px 10px;text-align:left;vertical-align:top}"
           "th{background:#e2e8f0}</style></head><body>"
           + BANNER_TMPL.format(prod=PROD_URL, status=rp + "status/",
                                mock=rp + "report-mock/") +
           "<h1>ASIP 开发状态清单（Stage 8A Preview）</h1>"
           "<p>" + legend + "</p>"
           "<p>仅说明后台能力与前端暴露情况，供 Frontend Gap Audit 参考；不暴露 internal runtime。</p>"
           "<table><tr><th>能力</th><th>状态</th><th>说明</th></tr>" +
           "".join(rows) + "</table></body></html>")
    (out / "status" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (out / "status" / "index.html").write_text(doc, encoding="utf-8")


def scan_secrets(root):
    problems = []
    pats = re.compile(
        r"ASIP_GLM_API_KEY|ASIP_DEEPSEEK_API_KEY|sk-[A-Za-z0-9]{16,}|"
        r"Bearer\s+[A-Za-z0-9._-]{16,}|GITHUB_TOKEN|GH_TOKEN|client_secret|"
        r"AIza[0-9A-Za-z_-]{20,}", re.I)
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in (".html", ".json", ".js", ".css", ".md", ".txt"):
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for m in pats.finditer(txt):
                problems.append("%s : %s" % (p.relative_to(root), m.group(0)[:50]))
    if (root / "data" / "runtime").exists():
        problems.append("data/runtime 进入预览（禁止）")
    if (root / ".env").exists():
        problems.append(".env 进入预览（禁止）")
    for bad in ("review_packs", "clustering", "source_health",
                "provider_telemetry", "ai_cache", "candidate_pool"):
        hits = [str(p.relative_to(root)) for p in root.rglob(bad + "*")]
        if hits:
            problems.append("内部路径 %s* 进入预览: %s" % (bad, hits[:3]))
    return problems


def main():
    out_root = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv \
        else ROOT / "preview_build_8a"
    out = out_root / "preview" / "stage8a"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(DIST, out)
    print("[1] mirrored dist ->", out)

    n = 0
    for p in sorted(out.rglob("*.html")):
        rel = p.relative_to(out)
        depth = len(rel.parent.parts)
        txt = p.read_text(encoding="utf-8")
        txt = inject(txt, depth)
        p.write_text(txt, encoding="utf-8")
        n += 1
    print("[2] banner+noindex injected:", n)

    made = gen_report_mock(out)
    print("[3] report-mock samples:", made)

    gen_status(out, depth=1)
    print("[4] status page generated")

    # public/ 兜底副本（API.get("public/*") 相对解析路径，__DB__ 为主）
    pub = out / "public"
    pub.mkdir(parents=True, exist_ok=True)
    pn = 0
    for f in sorted((DIST / "data" / "public").glob("*.json")):
        shutil.copy(f, pub / f.name)
        pn += 1
    print("[5] public/ fallback:", pn)

    problems = scan_secrets(out)
    if problems:
        print("[!] SECRET/RUNTIME SCAN FAILED:")
        for pr in problems:
            print("    -", pr)
        sys.exit(2)
    print("[6] secret/runtime scan clean")
    print("BUILD OK ->", out)


if __name__ == "__main__":
    main()
