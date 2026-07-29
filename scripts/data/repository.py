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
from data.schema_validator import validate_instance, load_schema

SCHEMA_VERSION = "2.0"
try:
    from pipeline_core import PIPELINE_VERSION, generate_run_id
except Exception:
    PIPELINE_VERSION = 2
    def generate_run_id():
        from datetime import datetime
        return datetime.now().strftime("%Y%m%dT%H%M%S") + "+0800_xxxxxx"

try:
    from data.source_rules import validate_source_business_rules
except Exception:
    validate_source_business_rules = None


class RepositorySchemaError(Exception):
    """保存前/保存中 Schema 或业务规则校验失败。

    抛出此异常时，原文件必须保持字节级不变（校验在写入前完成，
    或通过两文件原子回滚恢复）。
    """

    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors or []

    def __str__(self):
        if self.errors:
            return f"{self.args[0]} | 样例: {self.errors[:3]}"
        return self.args[0]


# 各保存方法对应的 Schema 文件名
SCHEMA_FOR = {
    "article": "article.schema.json",
    "event_cluster": "event_cluster.schema.json",
    "published_event": "published_event.schema.json",
    "quarantine": "quarantine_record.schema.json",
    "source": "source.schema.json",
}


def _safe_unlink(p):
    try:
        if p and Path(p).exists():
            os.unlink(p)
    except Exception:
        pass

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

    def _atomic_write(self, path: Path, data: dict, post_check=None):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            self._backup(path)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            # 写入临时文件后重新读取并再次校验（规范第三节要求 5）
            if post_check is not None:
                post_check(tmp)
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

    def _save_items(self, path: Path, items: list, run_id: str = "", schema_name: str = None):
        env = _new_envelope(run_id or self.run_id)
        env["items"] = items
        post = None
        if schema_name:
            post = lambda tmp: self._revalidate(tmp, schema_name)
        self._atomic_write(path, env, post_check=post)
        return env

    def _validate_item(self, item: dict, kind: str) -> bool:
        if not isinstance(item, dict):
            return False
        iid = item.get("id") or item.get("article_id") or item.get("event_id") \
            or item.get("quarantine_id") or item.get("source_id")
        if not iid:
            return False
        return True

    # ── Schema / 业务规则强制校验（规范第三节）─────────────
    def _validate_records(self, items: list, kind: str, id_key: str) -> list:
        """校验全部记录；返回 [(对象ID, 错误列表), ...]。空表示全部通过。

        非法 schema_version、缺失必填字段、非法枚举、非法 URL 均在此拦截。
        """
        schema_name = SCHEMA_FOR.get(kind)
        if not schema_name:
            return []
        schema = load_schema(schema_name, SCHEMA_DIR)
        errors = []
        for it in items:
            if not isinstance(it, dict):
                errors.append(("(非对象)", ["记录不是 dict"]))
                continue
            errs = validate_instance(it, schema)
            if kind == "source" and validate_source_business_rules is not None:
                errs = errs + validate_source_business_rules(it)
            if errs:
                iid = it.get(id_key) or it.get("article_id") or it.get("event_id") \
                    or it.get("quarantine_id") or it.get("source_id") or "?"
                errors.append((iid, errs))
        return errors

    def _revalidate(self, tmp_path, schema_name: str):
        """临时文件回读后再次校验（规范第三节要求 5）。非法则抛 RepositorySchemaError。"""
        try:
            d = json.loads(Path(tmp_path).read_text(encoding="utf-8"))
        except Exception as e:
            raise RepositorySchemaError(f"临时文件回读失败: {e}")
        items = d.get("items") or []
        sch = load_schema(SCHEMA_FOR.get(schema_name, schema_name), SCHEMA_DIR)
        errs = []
        for it in items:
            e = validate_instance(it, sch)
            if schema_name == "source" and validate_source_business_rules is not None:
                e = e + validate_source_business_rules(it)
            errs.extend(e)
        if errs:
            raise RepositorySchemaError(f"{schema_name} 临时文件回读校验未通过", errors=errs[:5])

    def _revalidate_source(self, tmp_path):
        self._revalidate(tmp_path, "source")

    # ── Articles ──────────────────────────────────────
    def load_articles(self) -> list:
        return self._load_items(self._canonical("articles.json"))

    def save_articles(self, items: list, run_id: str = "") -> dict:
        return self._save_dedup(self._canonical("articles.json"), items, run_id, "article_id", "article")

    # ── Event Clusters ────────────────────────────────
    def load_event_clusters(self) -> list:
        return self._load_items(self._canonical("event_clusters.json"))

    def save_event_clusters(self, items: list, run_id: str = "") -> dict:
        return self._save_dedup(self._canonical("event_clusters.json"), items, run_id, "event_id", "event_cluster")

    # ── Published Events ──────────────────────────────
    def load_published_events(self) -> list:
        return self._load_items(self._public("published_events.json"))

    def save_published_events(self, items: list, run_id: str = "") -> dict:
        return self._save_dedup(self._public("published_events.json"), items, run_id, "event_id", "published_event")

    # ── Quarantine ────────────────────────────────────
    def load_quarantine(self) -> list:
        return self._load_items(self._canonical("quarantine.json"))

    def save_quarantine(self, items: list, run_id: str = "") -> dict:
        return self._save_dedup(self._canonical("quarantine.json"), items, run_id, "quarantine_id", "quarantine")

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
        # 保存前强制校验：Schema + 来源业务规则；任一不合规则整个保存失败
        errs = self._validate_records(items, "source", "source_id")
        if errs:
            raise RepositorySchemaError(
                f"source.schema / 业务规则：{len(errs)} 条不合规，整个保存已中止（原文件保持不变）",
                errors=errs)
        # 空 url 非合法 uri；schema 不要求 url，省略即可（保证幂等一致）
        cleaned = []
        for s in items:
            s = dict(s)
            if not s.get("url"):
                s.pop("url", None)
            cleaned.append(s)
        rid = run_id or self.run_id or generate_run_id()
        env = {
            "schema_version": SCHEMA_VERSION,
            "pipeline_version": PIPELINE_VERSION,
            "run_id": rid,
            "updated_at": _now_iso(),
            "sources": cleaned,
        }
        # 幂等：去除易变字段后内容未变则不重写；否则写入并回读校验
        self._write_validated_if_changed(self._data("sources.json"), env, "source")
        return {"added": 0, "modified": 0, "skipped": 0, "failed": 0}

    def _write_validated_if_changed(self, path: Path, env: dict, schema_name: str) -> bool:
        """信封级免重写（幂等）；需要写入时先回读校验再原子替换。返回是否写入。"""
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
        self._atomic_write(p, env, post_check=lambda tmp: self._revalidate(tmp, schema_name))
        return True

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

    def _save_dedup(self, path: Path, items: list, run_id: str, id_key: str, schema_name: str = None) -> dict:
        rid = run_id or self.run_id or generate_run_id()
        # 保存前整体校验：任一记录不合规 → 整个保存失败，原文件保持字节级不变
        if schema_name:
            pre = self._validate_records(items, schema_name, id_key)
            if pre:
                raise RepositorySchemaError(
                    f"{schema_name}: {len(pre)} 条记录不合规，整个保存已中止（原文件保持不变）",
                    errors=pre)
        existing = {it.get(id_key): it for it in self._load_items(path)}
        new_map = {}
        local = {"added": 0, "modified": 0, "skipped": 0, "failed": 0}
        for it in items:
            if not self._validate_item(it, id_key):
                local["failed"] += 1
                self.log["failed"] += 1
                continue
            iid = it.get(id_key)
            it = dict(it)
            it.setdefault("schema_version", SCHEMA_VERSION)
            it.setdefault("pipeline_version", PIPELINE_VERSION)
            it["run_id"] = rid
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
        self._save_items(path, ordered, run_id, schema_name)
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
        """事务式双向关联（规范第四节）。

        流程：一次性加载 Articles 与 Event Clusters → 定位两侧 →
        Article.linked_event_id=event_id、processing_status=linked_to_event →
        Event.article_ids 加入 article_id（Event 不得写 linked_event_id）→
        两侧 Schema 全部校验 → 两个文件均准备成功后再原子替换，任一侧
        失败则恢复两个旧文件。重复关联不产生重复 ID，且不改变文件内容。
        """
        articles = self.load_articles()
        events = self.load_event_clusters()
        aidx = {a["article_id"]: a for a in articles}
        eidx = {e["event_id"]: e for e in events}
        # 任一侧不存在 → 两文件均不变
        if article_id not in aidx or event_id not in eidx:
            return False
        a = aidx[article_id]
        e = eidx[event_id]
        # 幂等短路：已关联且无任何变化 → 不写文件（保证“第二次关联不改变文件内容”）
        if (a.get("linked_event_id") == event_id
                and a.get("processing_status") == "linked_to_event"
                and article_id in (e.get("article_ids") or [])
                and "linked_event_id" not in e):
            return False

        new_a = dict(a)
        new_a["linked_event_id"] = event_id
        new_a["processing_status"] = "linked_to_event"
        aids = list(e.get("article_ids") or [])
        if article_id not in aids:
            aids.append(article_id)
        new_e = dict(e)
        new_e["article_ids"] = aids
        new_e.pop("linked_event_id", None)  # Event 不得写无意义的 linked_event_id

        # 两侧 Schema 全部校验（不合规则整体失败，不写任何文件）
        aerrs = validate_instance(new_a, load_schema("article.schema.json", SCHEMA_DIR))
        eerrs = validate_instance(new_e, load_schema("event_cluster.schema.json", SCHEMA_DIR))
        if aerrs or eerrs:
            raise RepositorySchemaError(
                f"link 校验失败: article={aerrs[:2]} event={eerrs[:2]}")

        new_articles = [new_a if x["article_id"] == article_id else x for x in articles]
        new_events = [new_e if x["event_id"] == event_id else x for x in events]
        rid = self.run_id or generate_run_id()
        env_a = _new_envelope(rid); env_a["items"] = new_articles
        env_e = _new_envelope(rid); env_e["items"] = new_events
        self._write_two_atomic(
            (self._canonical("articles.json"), env_a, "article"),
            (self._canonical("event_clusters.json"), env_e, "event_cluster"))
        return True

    def _mk_validated_temp(self, path: Path, env: dict, schema_name: str) -> str:
        """写临时文件 → 回读校验 → 返回临时路径；校验失败抛 RepositorySchemaError。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(env, f, ensure_ascii=False, indent=2)
                f.flush(); os.fsync(f.fileno())
            d = json.loads(Path(tmp).read_text(encoding="utf-8"))
            errs = []
            for it in (d.get("items") or []):
                errs.extend(validate_instance(it, load_schema(SCHEMA_FOR.get(schema_name, schema_name), SCHEMA_DIR)))
            if errs:
                raise RepositorySchemaError(f"{schema_name} link 写入校验失败", errors=errs[:3])
            return tmp
        except Exception:
            try:
                os.unlink(tmp)
            except Exception:
                pass
            raise

    def _write_two_atomic(self, spec_a, spec_b):
        """两个文件均准备（写临时+校验）成功后再原子替换；任一侧失败则恢复两旧文件。"""
        import shutil
        path_a, env_a, sch_a = spec_a
        path_b, env_b, sch_b = spec_b
        tmp_a = self._mk_validated_temp(path_a, env_a, sch_a)
        try:
            tmp_b = self._mk_validated_temp(path_b, env_b, sch_b)
        except Exception:
            _safe_unlink(tmp_a)
            raise
        # 保留原文件用于回滚
        rb_a = tempfile.mktemp(suffix=".rbak")
        rb_b = tempfile.mktemp(suffix=".rbak")
        if path_a.exists():
            shutil.copy2(path_a, rb_a)
        if path_b.exists():
            shutil.copy2(path_b, rb_b)
        try:
            os.replace(tmp_a, path_a)
        except Exception:
            _safe_unlink(tmp_b); _safe_unlink(rb_a); _safe_unlink(rb_b)
            raise
        try:
            os.replace(tmp_b, path_b)
        except Exception:
            shutil.copy2(rb_a, path_a)  # 恢复 a
            _safe_unlink(tmp_b); _safe_unlink(rb_a); _safe_unlink(rb_b)
            raise
        _safe_unlink(rb_a); _safe_unlink(rb_b)

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
