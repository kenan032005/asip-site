"""C8-3 STEP 3/4/5：文章级**地理范围分类**（确定性，无 AI、无猜测）。

用途：
  1) STEP 3 —— 对剩余 `wrong_country` 隔离做分类（single/multi/regional/outside/…）；
  2) STEP 4/5 —— 为 `MULTI_COUNTRY` / `REGIONAL_AFRICA` 提供判定依据。

铁律（与用户 C8-3 要求一致）：
  · **不得**把"单国未解析"提升为 REGIONAL_AFRICA（STEP 5）；那必须保持 COUNTRY_UNRESOLVED；
  · REGIONAL_AFRICA 只在文本**明确**命中区域/次区域表述时成立；
  · MULTI_COUNTRY 需要文本**明确**提到 ≥2 个非洲国家（国名/首都/主要城市/别名）；
  · 不猜、不靠源默认国家兜底。

输出 schema：
  {"scope": "SINGLE_COUNTRY|MULTI_COUNTRY|REGIONAL_AFRICA|COUNTRY_UNRESOLVED|OUTSIDE_AFRICA",
   "countries": ["尼日利亚", ...],   # scope=SINGLE/MULTI 时
   "region": "SAHEL|WEST_AFRICA|...", # scope=REGIONAL_AFRICA 时
   "evidence": {"countries": [...], "regions": [...], "outside": [...]}}
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: 区域/次区域词族（仅有明确地域表述才可命中 REGIONAL_AFRICA）
REGION_PATTERNS = [
    ("AFRICA_WIDE", r"\bafrica[- ]wide\b|\bcontinent[- ]wide\b|across africa|pan[- ]african|"
                    r"非洲大陆|全非洲|整个非洲|泛非"),
    ("SAHEL", r"\bsahel\b|sahelian|萨赫勒|萨赫勒地区"),
    ("WEST_AFRICA", r"\bwest africa\b|\bwest african\b|ecowas|西非|西非地区"),
    ("NORTH_AFRICA", r"\bnorth africa\b|\bnorth african\b|maghreb|北非|马格里布"),
    ("CENTRAL_AFRICA", r"\bcentral africa\b|\bcentral african region\b|中部非洲|中非地区"),
    ("GREAT_LAKES", r"\bgreat lakes\b|great lakes region|大湖区"),
    ("EAST_AFRICA", r"\beast africa\b|\beast african\b|东非|东非地区"),
    ("HORN_OF_AFRICA", r"\bhorn of africa\b|非洲之角"),
    ("SOUTHERN_AFRICA", r"\bsouthern africa\b|\bsadc\b|南部非洲"),
    ("LAKE_CHAD_BASIN", r"\blake chad basin\b|bassin du lac tchad|乍得湖流域"),
]

#: 明确属于非洲之外的地名（用于 OUTSIDE_AFRICA 判定，避免把非非洲内容当区域情报）
OUTSIDE_PATTERNS = (r"\bunited states\b|\bu\.s\.\b|\bwashington\b|\beurope\b|\beuropean union\b|\bchina\b|\bindia\b|\brussia\b|\bukraine\b|\bgaza\b|\bvenezuela\b|\bafghanistan\b|\bpakistan\b|\bsyria\b|\biraq\b")


def load_monitored_country_index(root=None):
    """从 config/countries/** 派生"国家 → 可识别别名"索引（单一事实源）。"""
    root = Path(root or ROOT)
    cfg_dir = root / "config" / "countries"
    index = {}
    if not cfg_dir.is_dir():
        return index
    for f in sorted(cfg_dir.glob("*.json")):
        try:
            c = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        cn = str(c.get("country") or "").strip()
        if not cn:
            continue
        aliases = {cn}
        for key in ("country_en", "aliases", "names"):
            v = c.get(key)
            if isinstance(v, str) and v.strip():
                aliases.add(v.strip())
            elif isinstance(v, list):
                aliases.update(str(x).strip() for x in v if str(x).strip())
        for key in ("keywords", "locations"):
            v = c.get(key)
            if isinstance(v, list):
                aliases.update(str(x).strip() for x in v if str(x).strip() and len(str(x).strip()) > 3)
        index[cn] = sorted(a for a in aliases if a)
    return index


def _hits(text, alias):
    """词边界优先；含空格/非 ASCII 的别名退化为大小写不敏感子串匹配。"""
    a = alias.strip()
    if not a:
        return False
    low = text.lower()
    if re.fullmatch(r"[a-zA-Z0-9 .'\-]+", a):
        return re.search(r"(?<![a-z0-9])" + re.escape(a.lower()) + r"(?![a-z0-9])", low) is not None
    return a.lower() in low


def detect_geo_scope(text, country_index=None, own_country=None):
    """返回确定性地理范围判定（见模块 docstring）。"""
    text = str(text or "")
    index = country_index if country_index is not None else load_monitored_country_index()
    matched = []
    for cn, aliases in index.items():
        if any(_hits(text, a) for a in aliases[:24]):
            matched.append(cn)
    regions = [code for code, pat in REGION_PATTERNS if re.search(pat, text, re.I)]
    outside = bool(re.search(OUTSIDE_PATTERNS, text, re.I)) and not matched and not regions

    if len(matched) >= 2:
        return {"scope": "MULTI_COUNTRY", "countries": matched[:8], "region": regions[0] if regions else None,
                "evidence": {"countries": matched[:8], "regions": regions, "outside": outside}}
    # C8-3 STEP 5：**明确的区域/次区域表述优先于单一国家**——用户语义即为
    #  "Security deteriorates across the Sahel" → REGIONAL_AFRICA / SAHEL；
    #  而命中单一国家且**同时**有区域词时，区域表述是文章的真实范围（如"萨赫勒某国"）。
    if regions:
        return {"scope": "REGIONAL_AFRICA", "countries": matched[:1], "region": regions[0],
                "evidence": {"countries": matched[:1], "regions": regions, "outside": outside}}
    if matched:
        return {"scope": "SINGLE_COUNTRY", "countries": matched[:1], "region": None,
                "evidence": {"countries": matched[:1], "regions": regions, "outside": outside}}
    return {"scope": "OUTSIDE_AFRICA" if outside else "COUNTRY_UNRESOLVED",
            "countries": [], "region": None,
            "evidence": {"countries": [], "regions": [], "outside": outside}}


def classify_wrong_country(title, summary="", own_country=None, country_index=None):
    """STEP 3：把一条 wrong_country 记录分类。"""
    scope = detect_geo_scope(str(title or "") + " " + str(summary or ""), country_index, own_country)
    if scope["scope"] == "MULTI_COUNTRY":
        return "MULTI_COUNTRY"
    if scope["scope"] == "REGIONAL_AFRICA":
        return "REGIONAL_AFRICA"
    if scope["scope"] == "OUTSIDE_AFRICA":
        return "OUTSIDE_AFRICA"
    if scope["scope"] == "SINGLE_COUNTRY":
        # 解析到了国家但不是本管线国家 → 属"该由别的国家管线接收"
        return "SINGLE_COUNTRY_RESOLUTION_FAIL" if scope["countries"][0] == own_country \
            else "SINGLE_COUNTRY_OTHER"
    return "COUNTRY_UNRESOLVED"


if __name__ == "__main__":  # 自检
    idx = load_monitored_country_index()
    print("监控国别名索引 =", len(idx), "国")
    cases = [
        ("Sahel: security deteriorates across the Sahel region", "REGIONAL_AFRICA"),
        ("Mali, Niger and Burkina Faso announce joint force", "MULTI_COUNTRY"),
        ("Cholera risk rising across East Africa", "REGIONAL_AFRICA"),
        ("Africa-wide instability trends in 2026", "REGIONAL_AFRICA"),
        ("Maiduguri attack kills soldiers in Borno", "SINGLE_COUNTRY"),
        ("Some unclear incident happened somewhere", "COUNTRY_UNRESOLVED"),
        ("US election results announced", "OUTSIDE_AFRICA"),
    ]
    for t, want in cases:
        got = detect_geo_scope(t, idx)
        flag = "OK " if got["scope"] == want else "!! "
        print("  %s%-40s -> %-18s %s" % (flag, t[:40], got["scope"], got.get("countries") or got.get("region")))
