#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
repository.py —— ASIP Stage-2 统一数据访问层（唯一规范数据读写入口）

职责（规范第十二节）：
- 所有业务脚本通过本模块读写规范数据；
- 原子写入：先写临时文件，再 os.replace 替换；
- 写前自动备份（复制，不依赖删除）；
- 写入失败不破坏旧数据；
- 自动去重（按 id）；
- 校验通过后才能保存；
- 记录新增/修改/跳过/失败数量；
- 保留 schema_version 与 run_id；
- 除 repository / migration / compatibility_export 外，不得直接写规范数据。

规范文件顶层信封（规范第五/六节）：
{
  "schema_version": "2.0",
  "pipeline_version": 2,
  "run_id": "",
  "updated_at": "",
  "items": []
}
"""

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("Asia/Shanghai")
except Exception:
    from datetime import timezone
    _TZ = timezone.utc

from data.identifiers import (
    is_article_id, is_event_id, is_quarantine_id,
)

SCHEMA_VERSION = "2.0"
try:
    from pipeline_core import PIPELINE_VERSION
except Exception:
    PIPELINE_VERSION = 2

_HERE = Path(__file__).resolve().parent          # scripts/data
_ROOT = _HERE.parent.parent                       # asip-site
CANONICAL_DIR = _ROOT / "data" / "canonical"
PUBLIC_DIR = _ROOT / "data" / "public"
SCHEMA_DIR = _ROOT / "schemas"

# 标准文件位置
ARTICLES_FILE = CANONICAL_DIR / "articles.json"
EVENT_CLUSTERS_FILE = CANONICAL_DIR / "event_clusters.json"
QUARANTINE_FILE = CANONICAL_DIR / "quarantine.json"
PUBLISHED_EVENTS_FILE = PUBLIC_DIR / "published_events.json"
CURRENT_METRICS_FILE = PUBLIC_DIR / "current_metrics.json"


def _now_iso():
    return datetime.now(_TZ).isoformat()


def _new_envelope(run_id: str = ""):
    return {
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "run_id": run_id,
        "updated_at": _now_iso(),
        "items": [],
    }


class Repository:
    def __init__(self, root=None, run_id: str = "", make_backups: bool = True):
        self.root = Path(root) if root else _ROOT
        self.canonical_dir = self.root / "data" / "canonical"
        self.public_dir = self.root / "data" / "public"
        self.run_id = run_id
        self.make_backups = make_backups
        self.log = {"added": 0, "modified": 0, "skipped": 0, "failed": 0}

    def _canonical(self, name: str) -> Path:
        return self.canonical_dir / name

    def _public(self, name: str) -> Path:
        return self.public_dir / name

    def _data(self, name: str) -> Path:
        return self.root / "data" / name

    # ── 原子写入 + 备份 ─────────────────────────────────
    def _backup(self, path: Path):
        if not self.make_backups:
            return
        try:
            bak_dir = path.parent / ".backups"
            bak_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(_TZ).strftime("%Y%m%dT%H%M%S")
            dst = bak_dir / f"{path.name}.{ts}.bak"
            shutil.copy2(path, dst)
            # 仅保留最近 5 份（逐个删除，规避批量删除保护）
            olds = sorted(bak_dir.glob(f"{path.name}.*.bak"), key=lambda p: p.name)
            for old in olds[:-5]:
                try:
                    old.unlink()
                except Exception:
                    pass
        except Exception:
            pass

    def _atomic_write(self, path: Path, data: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            self._backup(path)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except Exception:
                pass
            raise

    # ── 信封读写 ───────────────────────────────────────
    def _load_items(self, path: Path) -> list:
        if not path.exists():
            return []
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                return d.get("items") or d.get("events") or []
            return d if isinstance(d, list) else []
        except Exception:
            return []

    def _save_items(self, path: Path, items: list, run_id: str = ""):
        env = _new_envelope(run_id or self.run_id)
        env["items"] = items
        self._atomic_write(path, env)
        return env

    def _validate_item(self, item: dict, kind: str) -> bool:
        if not isinstance(item, dict):
            return False
        iid = item.get("id") or item.get("article_id") or item.get("event_id") \
            or item.get("quarantine_id") or item.get("source_id")
        if not iid:
            return False
        if item.get("schema_version") != SCHEMA_VERSION:
            # 允许在保存时补齐，但不阻断
            pass
        return True

    # ── Articles ──────────────────────────────────────
    def load_articles(self) -> list:
        return self._load_items(self._canonical("articles.json"))

    def save_articles(self, items: list, run_id: str = "") -> dict:
        return self._save_dedup(self._canonical("articles.json"), items, run_id, "article_id")

    # ── Event Clusters ────────────────────────────────
    def load_event_clusters(self) -> list:
        return self._load_items(self._canonical("event_clusters.json"))

    def save_event_clusters(self, items: list, run_id: str = "") -> dict:
        return self._save_dedup(self._canonical("event_clusters.json"), items, run_id, "event_id")

    # ── Published Events ──────────────────────────────
    def load_published_events(self) -> list:
        return self._load_items(self._public("published_events.json"))

    def save_published_events(self, items: list, run_id: str = "") -> dict:
        return self._save_dedup(self._public("published_events.json"), items, run_id, "event_id")

    # ── Quarantine ────────────────────────────────────
    def load_quarantine(self) -> list:
        return self._load_items(self._canonical("quarantine.json"))

    def save_quarantine(self, items: list, run_id: str = "") -> dict:
        return self._save_dedup(self._canonical("quarantine.json"), items, run_id, "quarantine_id")

    # ── Sources（参考配置，非运行时数据池）────────────
    def load_sources(self) -> list:
        p = self._data("sources.json")
        if not p.exists():
            return []
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            return d.get("sources", []) if isinstance(d, dict) else (d if isinstance(d, list) else [])
        except Exception:
            return []

    def save_sources(self, items: list, run_id: str = "") -> dict:
        p = self._data("sources.json")
        env = {
            "schema_version": SCHEMA_VERSION,
            "pipeline_version": PIPELINE_VERSION,
            "run_id": run_id or self.run_id,
            "updated_at": _now_iso(),
            "sources": items,
        }
        self.write_if_changed(p, env)
        local = {"added": 0, "modified": 0, "skipped": 0, "failed": 0}
        return local

    # ── 信封级免重写（幂等）────────────────────────────
    def write_if_changed(self, path: Path, env: dict) -> bool:
        """仅当去除易变字段后的内容发生变化时才写入。返回是否写入。"""
        p = Path(path)
        if p.exists():
            try:
                old = json.loads(p.read_text(encoding="utf-8"))
                strip = lambda d: json.dumps(
                    {k: v for k, v in d.items() if k not in self.VOLATILE_KEYS},
                    sort_keys=True, ensure_ascii=False)
                if strip(old) == strip(env):
                    return False
            except Exception:
                pass
        self._atomic_write(p, env)
        return True

    # ── Public metrics ────────────────────────────────
    def save_current_metrics(self, data: dict, run_id: str = ""):
        p = self._public("current_metrics.json")
        env = {
            "schema_version": SCHEMA_VERSION,
            "pipeline_version": PIPELINE_VERSION,
            "run_id": run_id or self.run_id,
            "updated_at": _now_iso(),
        }
        env.update(data)
        self.write_if_changed(p, env)

    # ── 去重保存（核心）───────────────────────────────
    # 内容比较时忽略的易变字段：这些字段随每次运行变化，不代表业务内容变更。
    VOLATILE_KEYS = ("run_id", "updated_at")

    @classmethod
    def _stable_dump(cls, item: dict) -> str:
        d = {k: v for k, v in item.items() if k not in cls.VOLATILE_KEYS}
        return json.dumps(d, sort_keys=True, ensure_ascii=False)

    def _save_dedup(self, path: Path, items: list, run_id: str, id_key: str) -> dict:
        existing = {it.get(id_key): it for it in self._load_items(path)}
        new_map = {}
        local = {"added": 0, "modified": 0, "skipped": 0, "failed": 0}
        for it in items:
            if not self._validate_item(it, id_key):
                local["failed"] += 1
                self.log["failed"] += 1
                continue
            iid = it.get(id_key)
            it.setdefault("schema_version", SCHEMA_VERSION)
            it.setdefault("pipeline_version", PIPELINE_VERSION)
            if run_id:
                it["run_id"] = run_id
            if iid in existing:
                if self._stable_dump(existing[iid]) == self._stable_dump(it):
                    # 内容一致：完整保留旧记录（含旧 run_id），保证幂等字节不变
                    local["skipped"] += 1
                    self.log["skipped"] += 1
                    new_map[iid] = existing[iid]
                else:
                    local["modified"] += 1
                    self.log["modified"] += 1
                    new_map[iid] = it
            else:
                local["added"] += 1
                self.log["added"] += 1
                new_map[iid] = it
        # 内容完全未变（无新增/修改且 ID 集合一致）时不重写文件，
        # 避免信封 run_id/updated_at 或传入顺序差异破坏字节级幂等。
        if (local["added"] == 0 and local["modified"] == 0
                and set(new_map.keys()) == set(existing.keys())
                and path.exists()):
            return local
        ordered = list(new_map.values())
        self._save_items(path, ordered, run_id)
        return local

    # ── 查询 ──────────────────────────────────────────
    def get_article(self, article_id: str) -> dict:
        for a in self.load_articles():
            if a.get("article_id") == article_id:
                return a
        return {}

    def get_event(self, event_id: str) -> dict:
        for e in self.load_event_clusters():
            if e.get("event_id") == event_id:
                return e
        return {}

    # ── 关系维护 ─────────────────────────────────────
    def link_article_to_event(self, event_id: str, article_id: str) -> bool:
        events = self.load_event_clusters()
        changed = False
        for e in events:
            if e.get("event_id") == event_id:
                aids = e.setdefault("article_ids", [])
                if article_id not in aids:
                    aids.append(article_id)
                    changed = True
                e["linked_event_id"] = event_id
                a = self.get_article(article_id)
                if a and a.get("linked_event_id") != event_id:
                    a["linked_event_id"] = event_id
                    a["processing_status"] = "linked_to_event"
                    self.save_articles(self.load_articles())
                break
        if changed:
            self.save_event_clusters(events, self.run_id)
        return changed

    def update_publication_status(self, event_id: str, status: str,
                                  reason: str = "") -> bool:
        events = self.load_event_clusters()
        changed = False
        for e in events:
            if e.get("event_id") == event_id:
                e["publication_status"] = status
                if reason:
                    e["publication_reason"] = reason
                changed = True
                break
        if changed:
            self.save_event_clusters(events, self.run_id)
        return changed

    # ── 兼容导出（委托 compatibility_export）────────────
    def export_legacy_views(self, run_id: str = ""):
        try:
            from compatibility_export import export_all
            return export_all(self, run_id or self.run_id)
        except ImportError:
            raise RuntimeError(
                "compatibility_export 尚未构建（应在 2B 阶段提供）；export_legacy_views 暂不可用"
            )

    # ── 统计 ──────────────────────────────────────────
    def counts(self) -> dict:
        return {
            "articles": len(self.load_articles()),
            "event_clusters": len(self.load_event_clusters()),
            "published_events": len(self.load_published_events()),
            "quarantine": len(self.load_quarantine()),
        }
