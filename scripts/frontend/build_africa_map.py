#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP V1.1 — Africa Risk Map generator.

数据源：Natural Earth 110m admin_0 countries（nvkelso/natural-earth-vector 官方 geojson，
含 ISO_A3 / NAME 属性）。等距圆柱（equirectangular）投影 → SVG path。
输出 assets/geo/africa-countries.js：真实国家边界，非手工绘制、非 AI 生成。
"""
import json
import math
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / ".workbuddy_tmp" / "ne110m.geo.json"
OUT = Path(__file__).resolve().parents[2] / "assets" / "geo" / "africa-countries.js"

# 非洲 54 国 ISO3（UN 地理方案）
AFRICA_ISO3 = {
    "DZA","AGO","BEN","BWA","BFA","BDI","CPV","CMR","CAF","TCD","COM","COG","COD",
    "CIV","DJI","EGY","GNQ","ERI","SWZ","ETH","GAB","GMB","GHA","GIN","GNB","KEN",
    "LSO","LBR","LBY","MDG","MWI","MLI","MRT","MUS","MAR","MOZ","NAM","NER","NGA",
    "RWA","STP","SEN","SYC","SLE","SOM","ZAF","SSD","SDN","TZA","TGO","TUN","UGA",
    "ESH","ZMB","ZWE",
}

# 等距圆柱投影参数（中心经度 20E；非洲纬度 -40..40；scale 视觉适度）
CENTER_LON = 17.5
SCALE = 7.2
X0 = 290.0
Y0 = 20.0

# 小岛国简化可见 marker（真实首都/主岛坐标；110m 数据无独立边界）
ISLAND_MARKERS = {
    "CPV": (-23.51, 14.93, "Cape Verde"),
    "COM": (43.25, -11.70, "Comoros"),
    "STP": (6.61, 0.34, "São Tomé & Príncipe"),
    "SYC": (55.45, -4.62, "Seychelles"),
    "MUS": (57.50, -20.17, "Mauritius"),
}

# 大国/重点国家常驻标签（ISO3 → 显示名），按地图尺寸自动控制（CSS 层）
LABELS = ["DZA", "LBY", "EGY", "SDN", "TCD", "NER", "NGA", "COD", "ETH", "KEN", "ZAF"]


def proj(lon, lat):
    x = (lon - CENTER_LON) * SCALE + X0
    y = (40.0 - lat) * SCALE * 0.98 + Y0
    return round(x, 1), round(y, 1)


def ring_to_path(ring, first=True):
    pts = []
    for p in ring:
        x, y = proj(p[0], p[1])
        pts.append("%s%s %.1f %.1f" % ("M" if (first and not pts) else "L", "", x, y))
    d = " ".join(pts)
    if first:
        return d + " Z"
    return d + " Z"  # 洞：fill-rule=evenodd 处理


def polygon_to_path(coords):
    """Polygon 坐标 → SVG path（外环 + 洞，evenodd）。"""
    d = ""
    for i, ring in enumerate(coords):
        d += ring_to_path(ring, first=(i == 0)) + " "
    return d.strip()


def multi_to_path(coords):
    return " ".join(polygon_to_path(c) for c in coords)


def main():
    doc = json.loads(SRC.read_text(encoding="utf-8"))
    out = {}
    centroids = {}
    matched = []
    for f in doc.get("features", []):
        iso = f.get("properties", {}).get("ISO_A3")
        if iso not in AFRICA_ISO3:
            continue
        name = f.get("properties", {}).get("NAME") or iso
        geom = f.get("geometry") or {}
        t = geom.get("type")
        if t == "Polygon":
            d = polygon_to_path(geom.get("coordinates", []))
        elif t == "MultiPolygon":
            d = multi_to_path(geom.get("coordinates", []))
        else:
            continue
        out[iso] = {"d": d, "name": name}
        matched.append(iso)
        # label 质心：用几何 bbox 中心（真实坐标投影）
        xs, ys = [], []
        coords = geom.get("coordinates", [])
        polys = coords if t == "MultiPolygon" else [coords]
        for poly in polys:
            for ring in poly[:1]:
                for p in ring:
                    xs.append(p[0]); ys.append(p[1])
        if xs:
            cx, cy = proj(sum(xs) / len(xs), sum(ys) / len(ys))
            centroids[iso] = (cx, cy)

    # 小岛 marker（真实坐标投影）
    markers = {}
    for iso, (lon, lat, nm) in ISLAND_MARKERS.items():
        x, y = proj(lon, lat)
        markers[iso] = {"x": x, "y": y, "name": nm}

    js = "// ASIP V1.1 Africa Risk Map — 真实国家边界（Natural Earth 110m, equirectangular）\n"
    js += "// 数据源：nvkelso/natural-earth-vector ne_110m_admin_0_countries.geojson (ISO_A3)\n"
    js += "window.AFRICA_GEO = {\n"
    for iso in sorted(out):
        js += '  "%s": {d: "%s", name: "%s"},\n' % (iso, out[iso]["d"], out[iso]["name"])
    js += "};\n"
    js += "window.AFRICA_LABELS = {\n"
    for iso in LABELS:
        if iso in centroids:
            js += '  "%s": [%.1f, %.1f],\n' % (iso, centroids[iso][0], centroids[iso][1])
    js += "};\n"
    js += "window.AFRICA_MARKERS = {\n"
    for iso in sorted(markers):
        m = markers[iso]
        js += '  "%s": {x: %.1f, y: %.1f, name: "%s"},\n' % (iso, m["x"], m["y"], m["name"])
    js += "};\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(js, encoding="utf-8")
    print("AFRICA_COUNTRIES=%d | labels=%d | markers=%d" % (
        len(out), len([i for i in LABELS if i in centroids]), len(markers)))
    print("SIZE=%d bytes -> %s" % (OUT.stat().st_size, OUT))


if __name__ == "__main__":
    main()
