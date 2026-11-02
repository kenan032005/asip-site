#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP-5 P0-R1 — quarantine 双格式存储（单体 ↔ 分片）与迁移。

背景：`data/canonical/quarantine.json` 达 99.97 MB（20,461 条），越过 GitHub 单文件
100 MB 硬上限，导致 Commit state 全部失败、状态永久冻结。

设计约束（P0-R1 第三部分）：
  * **不删除任何历史记录**：全部条目原样搬入分片；
  * 分片上限 20 MiB，自动 partN 滚动；
  * 支持跨月晚到条目（按条目自身 detected_at 归月，必要时新建 part）；
  * 重复 quarantine_id 幂等（不重复写入）；
  * 写入中断安全：临时文件 + 原子替换；孤儿 .tmp 在读取时清理；
  * 双格式兼容：旧单体（`quarantine.json` 含 items）与新分片（manifest+index+shards）都可读；
  * 迁移与回滚：迁移只新增分片与清单，回滚 = 恢复上一个提交（git 历史保留单体）。

目录布局（root = 仓库根）：
  data/canonical/quarantine.json           旧单体（迁移后由 manifest 取代其位置）
  data/canonical/quarantine_manifest.json  清单（迁移后的权威入口）
  data/canonical/quarantine/index.json     分片索引（count/bytes/sha256）
  data/canonical/quarantine/ids.json       quarantine_id → month（去重索引）
  data/canonical/quarantine/YYYY-MM[-partN].json
"""
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MAX_SHARD_BYTES = 20 * 1024 * 1024        # 20 MiB
SCHEMA_INDEX = "asip-quarantine-index-v1"
SCHEMA_MANIFEST = "asip-quarantine-manifest-v1"


class QuarantineCorrupt(RuntimeError):
    """分片校验失败（sha256 不匹配/JSON 非法）—— fail-closed，禁止静默跳过。"""


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _month_of(item):
    ts = str(item.get("detected_at") or "")
    if len(ts) >= 7 and ts[4] == "-":
        return ts[:7]
    return "unknown"


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _atomic_write(path, data_bytes):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data_bytes)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


HEADER = "{\n \"items\": [\n"
FOOTER = "\n ]\n}\n"


def _render_item(it):
    """按数组内实际缩进渲染单条（与 json.dumps(indent=1) 的嵌套结果逐字节一致）。"""
    return "  " + json.dumps(it, ensure_ascii=False, indent=1).replace("\n", "\n  ")


def _item_cost(it):
    """单条在分片中的净增量（含分隔符），用于精确滚动判定。"""
    return len(_render_item(it).encode("utf-8")) + 2


def _dump_items(items):
    """分片文件体：{"items":[...]}（与旧单体同构，便于复用解析逻辑）。"""
    body = HEADER + ",\n".join(_render_item(i) for i in items) + FOOTER
    return body.encode("utf-8")


class QuarantineStore:
    def __init__(self, root=None, max_shard_bytes=None):
        self.root = Path(root) if root else Path(__file__).resolve().parents[2]
        self.legacy = self.root / "data" / "canonical" / "quarantine.json"
        self.manifest_path = self.root / "data" / "canonical" / "quarantine_manifest.json"
        self.shard_dir = self.root / "data" / "canonical" / "quarantine"
        self.index_path = self.shard_dir / "index.json"
        self.ids_path = self.shard_dir / "ids.json"
        self.max_shard_bytes = int(max_shard_bytes or DEFAULT_MAX_SHARD_BYTES)

    # ── 状态 ────────────────────────────────────────────────
    def mode(self):
        """存储形态：legacy / sharded。任何不一致都 fail-closed，绝不静默回退。

        * manifest + index             → sharded（并校验 manifest schema）
        * manifest 无 index            → corrupt
        * 无 manifest 但 index/分片遗留 → corrupt（孤儿分片，说明迁移不完整/被误删）
        * 都没有                        → legacy
        """
        has_manifest = self.manifest_path.exists()
        has_index = self.index_path.exists()
        orphan_shards = (self.shard_dir.exists()
                         and (self.index_path.exists() or any(self.shard_dir.glob("*.json"))))
        if has_manifest:
            try:
                m = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                raise QuarantineCorrupt("manifest invalid json: %s" % e)
            if not isinstance(m, dict) or m.get("schema") != SCHEMA_MANIFEST:
                raise QuarantineCorrupt("manifest schema invalid: %r"
                                        % (m.get("schema") if isinstance(m, dict) else None))
            if not has_index:
                raise QuarantineCorrupt("manifest present but index.json missing "
                                        "(migrated-but-broken; refusing to fall back to legacy)")
            self.read_index()      # 校验 index JSON 可解析 + schema/结构合法（损坏即抛）
            return "sharded"
        if orphan_shards:
            raise QuarantineCorrupt("shards/index exist without manifest (incomplete migration)")
        return "legacy"

    def is_sharded(self):
        return self.mode() == "sharded"

    def read_index(self, strict=True):
        """读索引。strict：JSON 损坏/schema 错误/结构非法 → QuarantineCorrupt（不得静默空）。"""
        try:
            raw = self.index_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            if strict and self.shard_dir.exists() and any(self.shard_dir.glob("*.json")):
                raise QuarantineCorrupt("index.json missing while shard files exist")
            return {"schema": SCHEMA_INDEX, "total_items": 0, "shards": []}
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError as e:
            raise QuarantineCorrupt("index.json invalid json: %s" % e)
        if strict:
            if not isinstance(doc, dict) or doc.get("schema") != SCHEMA_INDEX:
                raise QuarantineCorrupt("index.json schema invalid: %r" % (doc.get("schema")
                                                                           if isinstance(doc, dict) else None))
            if not isinstance(doc.get("shards"), list):
                raise QuarantineCorrupt("index.json shards not a list")
            for s_ in doc["shards"]:
                for k in ("shard", "month", "part", "count", "bytes"):
                    if k not in s_:
                        raise QuarantineCorrupt("index shard entry missing %s: %r" % (k, s_))
        return doc

    def read_ids(self, strict=True):
        """读 id 索引。strict：损坏/类型错误 → QuarantineCorrupt。"""
        try:
            raw = self.ids_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            if strict and self.manifest_path.exists():
                raise QuarantineCorrupt("ids.json missing while manifest exists")
            return {}
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError as e:
            raise QuarantineCorrupt("ids.json invalid json: %s" % e)
        if strict and not isinstance(doc, dict):
            raise QuarantineCorrupt("ids.json must be an object")
        return doc

    def _cleanup_temp(self, directory=None):
        d = Path(directory) if directory else self.shard_dir
        if not d.exists():
            return 0
        n = 0
        for f in d.glob("*.tmp"):
            try:
                f.unlink()
                n += 1
            except OSError:
                pass
        return n

    # ── 读 ──────────────────────────────────────────────────
    def load_items(self, verify_checksums=True):
        """读取全部条目：有分片走分片，否则回退旧单体。"""
        if self.is_sharded():
            idx = self.read_index()
            self._cleanup_temp()
            out = []
            for s in idx.get("shards", []):
                path = self.shard_dir / s["shard"]
                if not path.exists():
                    raise QuarantineCorrupt("missing shard: %s" % s["shard"])
                if verify_checksums and s.get("sha256") and _sha256(path) != s["sha256"]:
                    raise QuarantineCorrupt("sha256 mismatch: %s" % s["shard"])
                try:
                    doc = json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as e:
                    raise QuarantineCorrupt("invalid json %s: %s" % (s["shard"], e))
                out.extend(doc.get("items") or [])
            return out
        return self._load_legacy()

    def _load_legacy(self):
        try:
            doc = json.loads(self.legacy.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return []
        return doc.get("items") or []

    def iter_items(self, verify_checksums=True):
        """流式读取（逐片 yield，避免一次 100MB 峰值）；默认校验每片 sha256。"""
        if self.is_sharded():
            idx = self.read_index()
            self._cleanup_temp()
            for s in idx.get("shards", []):
                path = self.shard_dir / s["shard"]
                if not path.exists():
                    raise QuarantineCorrupt("missing shard: %s" % s["shard"])
                if verify_checksums and s.get("sha256") and _sha256(path) != s["sha256"]:
                    raise QuarantineCorrupt("sha256 mismatch: %s" % s["shard"])
                try:
                    doc = json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as e:
                    raise QuarantineCorrupt("invalid json %s: %s" % (s["shard"], e))
                for it in (doc.get("items") or []):
                    yield it
            return
        for it in self._load_legacy():
            yield it

    def url_map(self, exclude_reasons=("", "not_security_relevant",
                                       "weak_signal_needs_review", "wrong_country")):
        """framework 用的 {normalized_url: quarantine_id}（保持旧语义）。"""
        try:
            from registry import norm_url  # 与 framework 同源
        except Exception:  # 独立调用（测试/离线）时退化为本地规范化
            def norm_url(u):
                u = str(u or "").strip()
                if not u:
                    return ""
                return u.split("#")[0].rstrip("/")
        out = {}
        for item in self.iter_items():
            oid = norm_url(item.get("original_id", ""))
            if oid and item.get("reason_code") not in exclude_reasons:
                out[oid] = item.get("quarantine_id", "")
        return out

    # ── 写 ──────────────────────────────────────────────────
    def append(self, items, run_id=""):
        """追加条目（按 detected_at 归月 + 20MiB 滚动 + id 去重 + 原子写）。

        返回 {"added": n, "duplicates": k, "shards_touched": [...], "mode": "sharded"|"legacy"}。
        """
        items = [it for it in (items or []) if isinstance(it, dict)]
        if not self.is_sharded():
            return self._append_legacy(items, run_id)

        self._cleanup_temp()
        idx = self.read_index()
        ids = self.read_ids()
        by_shard = {s["shard"]: s for s in idx.get("shards", [])}
        added, dups, touched = 0, 0, []
        per_month_new = {}
        for it in items:
            qid = str(it.get("quarantine_id") or "")
            if not qid:
                continue
            if qid in ids:
                dups += 1
                continue
            month = _month_of(it)
            per_month_new.setdefault(month, []).append(it)
            ids[qid] = month

        for month, new_items in sorted(per_month_new.items()):
            existing = [s for s in idx["shards"] if s.get("month") == month]
            existing.sort(key=lambda s: int(s.get("part") or 1))
            part = int(existing[-1]["part"]) if existing else 0
            if part == 0:
                part = 1
                cur_items, cur_name = [], self._shard_name(month, 1)
            else:
                cur_name = existing[-1]["shard"]
                cur_items = json.loads((self.shard_dir / cur_name).read_text(encoding="utf-8")).get("items") or []
            cur_bytes = len(_dump_items(cur_items)) if cur_items else 0
            for it in new_items:
                one = _item_cost(it)
                if cur_items and cur_bytes + one > self.max_shard_bytes:
                    self._write_shard(cur_name, cur_items)
                    self._upsert_index(idx, by_shard, cur_name, month, part, cur_items)
                    touched.append(cur_name)
                    added += 0  # 计数在最后统一
                    part += 1
                    cur_name = self._shard_name(month, part)
                    cur_items, cur_bytes = [], 0
                cur_items.append(it)
                cur_bytes += one
            if cur_items:
                self._write_shard(cur_name, cur_items)
                self._upsert_index(idx, by_shard, cur_name, month, part, cur_items)
                touched.append(cur_name)
        added = sum(len(v) for v in per_month_new.values())
        if added:
            idx["total_items"] = sum(int(s.get("count") or 0) for s in idx["shards"])
            _atomic_write(self.index_path, (json.dumps(idx, ensure_ascii=False, indent=1) + "\n").encode())
            _atomic_write(self.ids_path, (json.dumps(ids, ensure_ascii=False) + "\n").encode())
            self._write_manifest(idx, run_id)
        return {"added": added, "duplicates": dups, "shards_touched": sorted(set(touched)),
                "mode": "sharded", "total_items": idx.get("total_items")}

    def upsert(self, items, run_id=""):
        """新增 + 更新（quarantine_id 已存在且内容变化 → 就地重写所属分片）。

        与旧 `_save_dedup` 语义对齐：added / skipped(内容一致) / modified(内容变化)。
        仅重写受影响分片（≤20 MiB），历史分片除被修改记录外字节不变。
        """
        items = [it for it in (items or []) if isinstance(it, dict)]
        if not self.is_sharded():
            return self._append_legacy(items, run_id)
        self._cleanup_temp()
        idx = self.read_index()
        ids = self.read_ids()
        by_shard = {s_["shard"]: s_ for s_ in idx.get("shards", [])}
        shard_cache, dirty = {}, {}

        def _load_shard(name):
            if name not in shard_cache:
                shard_cache[name] = json.loads((self.shard_dir / name).read_text(encoding="utf-8")).get("items") or []
            return shard_cache[name]

        added = modified = skipped = 0
        new_by_month = {}
        for it in items:
            qid = str(it.get("quarantine_id") or "")
            if not qid:
                continue
            month = ids.get(qid)
            if month is None:
                new_by_month.setdefault(_month_of(it), []).append(it)
                ids[qid] = _month_of(it)
                continue
            target = None
            for s_ in idx.get("shards", []):
                if s_.get("month") != month:
                    continue
                cur = _load_shard(s_["shard"])
                for i2, old in enumerate(cur):
                    if str(old.get("quarantine_id")) == qid:
                        target = (s_["shard"], i2, old)
                        break
                if target:
                    break
            if target is None:
                # id 索引存在但分片缺失：按新增处理（自愈，不丢记录）
                new_by_month.setdefault(month, []).append(it)
                added += 1
                continue
            name, pos, old = target
            if json.dumps(old, ensure_ascii=False, sort_keys=True) == json.dumps(it, ensure_ascii=False, sort_keys=True):
                skipped += 1
            else:
                _load_shard(name)[pos] = it
                dirty[name] = True
                modified += 1

        # 应用修改：重写受影响分片
        for name in dirty:
            cur = shard_cache[name]
            meta = by_shard.get(name) or next(s_ for s_ in idx["shards"] if s_["shard"] == name)
            self._write_shard(name, cur)
            self._upsert_index(idx, by_shard, name, meta["month"], int(meta["part"]), cur)

        # 应用新增：按月份追加（含 partN 滚动）
        for month, rows in sorted(new_by_month.items()):
            existing = sorted([s_ for s_ in idx["shards"] if s_.get("month") == month],
                              key=lambda s_: int(s_.get("part") or 1))
            if existing:
                part = int(existing[-1]["part"])
                name = existing[-1]["shard"]
                cur = _load_shard(name)
            else:
                part, name, cur = 1, self._shard_name(month, 1), shard_cache.setdefault(self._shard_name(month, 1), [])
            size = len(_dump_items(cur)) if cur else 0
            for it in rows:
                one = _item_cost(it)
                if cur and size + one > self.max_shard_bytes:
                    self._write_shard(name, cur)
                    self._upsert_index(idx, by_shard, name, month, part, cur)
                    part += 1
                    name = self._shard_name(month, part)
                    cur = shard_cache.setdefault(name, [])
                    size = 0
                cur.append(it)
                size += one
                added += 1
            self._write_shard(name, cur)
            self._upsert_index(idx, by_shard, name, month, part, cur)

        if added or modified:
            idx["total_items"] = sum(int(s_.get("count") or 0) for s_ in idx["shards"])
            _atomic_write(self.index_path, (json.dumps(idx, ensure_ascii=False, indent=1) + "\n").encode())
            _atomic_write(self.ids_path, (json.dumps(ids, ensure_ascii=False) + "\n").encode())
            self._write_manifest(idx, run_id)
        return {"added": added, "modified": modified, "skipped": skipped, "failed": 0,
                "mode": "sharded", "total_items": idx.get("total_items")}

    def _append_legacy(self, items, run_id):
        doc = {"schema_version": "2.0", "pipeline_version": 2, "run_id": run_id,
               "updated_at": _now_iso(), "items": self._load_legacy()}
        have = {str(i.get("quarantine_id")) for i in doc["items"]}
        added = 0
        for it in items:
            qid = str(it.get("quarantine_id") or "")
            if not qid or qid in have:
                continue
            doc["items"].append(it)
            have.add(qid)
            added += 1
        if added:
            _atomic_write(self.legacy, (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode())
        return {"added": added, "duplicates": len(items) - added, "shards_touched": [],
                "mode": "legacy", "total_items": len(doc["items"])}

    def _shard_name(self, month, part):
        return "%s.json" % month if part == 1 else "%s-part%d.json" % (month, part)

    def _write_shard(self, name, items):
        _atomic_write(self.shard_dir / name, _dump_items(items))

    def _upsert_index(self, idx, by_shard, name, month, part, items):
        raw = _dump_items(items)
        entry = {"shard": name, "month": month, "part": part, "count": len(items),
                 "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        idx["shards"] = [s for s in idx.get("shards", []) if s.get("shard") != name] + [entry]
        idx["shards"].sort(key=lambda s: (str(s.get("month")), int(s.get("part") or 1)))
        idx["schema"] = SCHEMA_INDEX

    def _write_manifest(self, idx, run_id=""):
        manifest = {"schema": SCHEMA_MANIFEST, "replaces": "data/canonical/quarantine.json",
                    "total_items": idx.get("total_items"),
                    "shard_dir": "data/canonical/quarantine/",
                    "index": "data/canonical/quarantine/index.json",
                    "updated_at": _now_iso(), "run_id": run_id,
                    "note": "读取端必须 merge(index.shards)；写入端只追加到当月分片"}
        _atomic_write(self.manifest_path, (json.dumps(manifest, ensure_ascii=False, indent=1) + "\n").encode())

    # ── 迁移 / 校验 / 回滚 ──────────────────────────────────
    def migrate(self, dry_run=True, source_items=None, max_shard_bytes=None,
                allow_remigrate=False, expect_items=None):
        """单体 → 分片。dry_run 只计算不落盘。

        防呆：已经处于分片状态时**拒绝再次迁移**（否则会用旧单体覆盖迁移后新增的记录）。
        需要重跑时显式 `allow_remigrate=True`，且仍会先校验现有分片自洽。
        """
        if not dry_run:
            try:
                state = self.mode()
            except QuarantineCorrupt:
                raise
            if state == "sharded":
                rep = self.verify_consistency()
                if not allow_remigrate:
                    return {"dry_run": False, "refused": True, "reason": "already_migrated",
                            "consistent": True, "total_items": rep["on_disk"],
                            "note": "拒绝用旧单体覆盖分片（会丢失迁移后新增）；"
                                    "如需重建请显式 allow_remigrate=True 并先备份"}
        items = source_items if source_items is not None else self._load_legacy()
        # 防丢增量：源端条目数少于现有分片条目数时，任何"迁移"都会丢数据 → 拒绝
        if not dry_run and self.is_sharded():
            cur = len(self.load_items())
            if len(items) < cur:
                raise QuarantineCorrupt(
                    "refusing to overwrite %d sharded records with %d source records "
                    "(would lose increments)" % (cur, len(items)))
        if expect_items is not None and len(items) != int(expect_items):
            raise QuarantineCorrupt("source item count %d != expected %d"
                                    % (len(items), int(expect_items)))
        limit = int(max_shard_bytes or self.max_shard_bytes)
        by_month = {}
        for it in items:
            by_month.setdefault(_month_of(it), []).append(it)
        plan, ids = [], {}
        for month in sorted(by_month):
            rows = sorted(by_month[month], key=lambda x: str(x.get("quarantine_id") or ""))
            part, buf, size = 1, [], 0
            for it in rows:
                one = _item_cost(it)
                if buf and size + one > limit:
                    plan.append({"month": month, "part": part, "items": buf, "bytes": size})
                    part, buf, size = part + 1, [], 0
                buf.append(it)
                ids[str(it.get("quarantine_id"))] = month
                size += one
            if buf:
                plan.append({"month": month, "part": part, "items": buf, "bytes": size})
        report = {
            "dry_run": bool(dry_run),
            "source_items": len(items),
            "planned_shards": len(plan),
            "max_shard_bytes": max((p["bytes"] for p in plan), default=0),
            "limit_bytes": limit,
            "months": sorted(by_month.keys()),
            "destructive": False,
        }
        if dry_run:
            return report
        idx = {"schema": SCHEMA_INDEX, "total_items": 0, "shards": []}
        for p in plan:
            name = self._shard_name(p["month"], p["part"])
            self._write_shard(name, p["items"])
            raw = _dump_items(p["items"])
            idx["shards"].append({"shard": name, "month": p["month"], "part": p["part"],
                                  "count": len(p["items"]), "bytes": len(raw),
                                  "sha256": hashlib.sha256(raw).hexdigest()})
        idx["total_items"] = sum(s["count"] for s in idx["shards"])
        _atomic_write(self.index_path, (json.dumps(idx, ensure_ascii=False, indent=1) + "\n").encode())
        _atomic_write(self.ids_path, (json.dumps(ids, ensure_ascii=False) + "\n").encode())
        self._write_manifest(idx, run_id="")
        report.update({"written_shards": len(idx["shards"]), "total_items": idx["total_items"],
                       "index_bytes": self.index_path.stat().st_size,
                       "ids_bytes": self.ids_path.stat().st_size})
        return report

    def verify(self, expect_items=None):
        """校验：条目数、逐条身份哈希、分片 sha256、id 唯一性。"""
        idx = self.read_index()
        items = self.load_items(verify_checksums=True)
        ids = [str(i.get("quarantine_id")) for i in items]
        dups = len(ids) - len(set(ids))
        rep = {
            "sharded": self.is_sharded(),
            "index_total_items": idx.get("total_items"),
            "loaded_items": len(items),
            "duplicate_ids": dups,
            "shard_count": len(idx.get("shards", [])),
            "max_shard_bytes": max([s.get("bytes") or 0 for s in idx.get("shards", [])] or [0]),
            "checksums_ok": True,
        }
        if expect_items is not None:
            rep["expected_items"] = expect_items
            rep["count_match"] = len(items) == expect_items
        return rep

    def _read_manifest_strict(self):
        try:
            m = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise QuarantineCorrupt("manifest missing")
        except json.JSONDecodeError as e:
            raise QuarantineCorrupt("manifest invalid json: %s" % e)
        if not isinstance(m, dict) or m.get("schema") != SCHEMA_MANIFEST:
            raise QuarantineCorrupt("manifest schema invalid")
        return m

    def verify_consistency(self, verify_checksums=True):
        """内容级一致性：逐条 id 集合 / 归属月份 / ids 映射 / index / manifest / 分片字节。

        只比较计数是不够的：必须证明"哪些记录"与"记录在哪个分片/哪个月"也一致。
        """
        if self.mode() != "sharded":
            raise QuarantineCorrupt("not sharded")
        idx = self.read_index()
        ids = self.read_ids()
        manifest = self._read_manifest_strict()
        if manifest.get("index") and manifest["index"] != "data/canonical/quarantine/index.json":
            raise QuarantineCorrupt("manifest.index pointer unexpected: %r" % manifest["index"])
        if manifest.get("shard_dir") and manifest["shard_dir"] != "data/canonical/quarantine/":
            raise QuarantineCorrupt("manifest.shard_dir unexpected: %r" % manifest["shard_dir"])

        items, seen_ids, dup_ids = [], {}, []
        for s_ in idx["shards"]:
            path = self.shard_dir / s_["shard"]
            if not path.exists():
                raise QuarantineCorrupt("missing shard: %s" % s_["shard"])
            raw = path.read_bytes()
            if int(s_.get("bytes") or -1) != len(raw):
                raise QuarantineCorrupt("bytes mismatch %s: index=%s file=%d"
                                        % (s_["shard"], s_.get("bytes"), len(raw)))
            if verify_checksums and s_.get("sha256") and hashlib.sha256(raw).hexdigest() != s_["sha256"]:
                raise QuarantineCorrupt("sha256 mismatch: %s" % s_["shard"])
            try:
                rows = json.loads(raw.decode("utf-8")).get("items") or []
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                raise QuarantineCorrupt("invalid json %s: %s" % (s_["shard"], e))
            if len(rows) != int(s_.get("count") or 0):
                raise QuarantineCorrupt("count mismatch %s: index=%s file=%d"
                                        % (s_["shard"], s_.get("count"), len(rows)))
            for it in rows:
                qid = str(it.get("quarantine_id") or "")
                if not qid:
                    raise QuarantineCorrupt("record without quarantine_id in %s" % s_["shard"])
                month = _month_of(it)
                if month != s_["month"]:
                    raise QuarantineCorrupt("month attribution mismatch: %s in %s (record month=%s)"
                                            % (qid, s_["shard"], month))
                if qid in seen_ids:
                    dup_ids.append(qid)
                seen_ids[qid] = month
                items.append(it)
        if dup_ids:
            raise QuarantineCorrupt("duplicate quarantine_id: %s%s"
                                    % (dup_ids[:5], "..." if len(dup_ids) > 5 else ""))

        # ids 映射必须与真实记录集合、归属月份完全一致
        missing_in_ids = sorted(set(seen_ids) - set(ids))
        extra_in_ids = sorted(set(ids) - set(seen_ids))
        if missing_in_ids or extra_in_ids:
            raise QuarantineCorrupt("ids mapping mismatch: missing=%d%s extra=%d%s"
                                    % (len(missing_in_ids), missing_in_ids[:3],
                                       len(extra_in_ids), extra_in_ids[:3]))
        bad_month = [k for k, v in ids.items() if seen_ids.get(k) != v]
        if bad_month:
            raise QuarantineCorrupt("ids month mismatch: %s" % bad_month[:5])

        total = len(items)
        sum_counts = sum(int(x.get("count") or 0) for x in idx["shards"])
        if not (total == sum_counts == int(idx.get("total_items") or -1)
                == int(manifest.get("total_items") or -1)):
            raise QuarantineCorrupt("totals inconsistent: disk=%d sum=%d index=%s manifest=%s"
                                    % (total, sum_counts, idx.get("total_items"),
                                       manifest.get("total_items")))
        return {"consistent": True, "on_disk": total, "ids": len(ids),
                "index_total": int(idx["total_items"]), "sum_counts": sum_counts,
                "manifest_total": int(manifest["total_items"]),
                "shards": len(idx["shards"]), "months": sorted({v for v in seen_ids.values()})}

    def backup_legacy(self, dest, expect_items=None):
        """把迁移前单体复制到**离线**位置并校验 sha256（不进入生产分支）。"""
        src = self.legacy
        if not src.exists():
            return {"ok": False, "error": "legacy monolith not found"}
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        src_sha, dst_sha = _sha256(src), _sha256(dest)
        if src_sha != dst_sha:
            raise QuarantineCorrupt("backup sha mismatch: %s != %s" % (src_sha, dst_sha))
        n = len(json.loads(dest.read_text(encoding="utf-8")).get("items") or [])
        if expect_items is not None and n != expect_items:
            raise QuarantineCorrupt("backup item count %d != expected %d" % (n, expect_items))
        return {"ok": True, "path": str(dest), "bytes": dest.stat().st_size,
                "sha256": dst_sha, "items": n,
                "note": "离线备份：>100MB，禁止推回生产分支；仅用于离线恢复"}

    def write_backup_manifest(self, dest_dir, expect_items=None, path=None):
        """在离线备份目录写清单（sha256/bytes/items），供迁移前核对。"""
        src = self.legacy
        if not src.exists():
            raise QuarantineCorrupt("legacy monolith not found for backup")
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        payload = Path(dest_dir) / "quarantine.pre_migration.json"
        rep = self.backup_legacy(payload, expect_items=expect_items)
        manifest = {
            "schema": "asip-quarantine-backup-v1",
            "created_at": _now_iso(),
            "source_path": "data/canonical/quarantine.json",
            "backup_path": str(payload),
            "bytes": rep["bytes"], "sha256": rep["sha256"], "items": rep["items"],
            "note": "离线备份：>100MB，禁止推回生产分支；仅用于离线恢复",
        }
        mp = Path(path) if path else (dest_dir / "quarantine.backup.json")
        _atomic_write(mp, (json.dumps(manifest, ensure_ascii=False, indent=1) + "\n").encode())
        return dict(manifest, manifest_path=str(mp))

    def assert_backup_matches(self, manifest_path):
        """迁移前校验：清单的 sha256/bytes 必须与**当前**单体一致（防备份过期）。"""
        try:
            m = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            raise QuarantineCorrupt("backup manifest missing/invalid: %s" % manifest_path)
        if m.get("schema") != "asip-quarantine-backup-v1":
            raise QuarantineCorrupt("backup manifest schema invalid")
        if not self.legacy.exists():
            raise QuarantineCorrupt("legacy monolith missing")
        cur_bytes = self.legacy.stat().st_size
        cur_sha = _sha256(self.legacy)
        if cur_bytes != int(m.get("bytes") or -1) or cur_sha != m.get("sha256"):
            raise QuarantineCorrupt(
                "backup does not match current monolith (bytes %s/%s sha %s/%s)"
                % (cur_bytes, m.get("bytes"), cur_sha[:12], str(m.get("sha256"))[:12]))
        if not Path(m.get("backup_path") or "").exists():
            raise QuarantineCorrupt("backup file missing on disk: %s" % m.get("backup_path"))
        return {"ok": True, "bytes": cur_bytes, "sha256": cur_sha, "items": m.get("items"),
                "backup_path": m.get("backup_path")}

    def retire_monolith(self, backup_dir=None, expect_items=None):
        """分片迁移后**安全退役**旧单体：替换为小型墓碑清单（不含任何记录）。

        动机：迁移完成后若 104,825,716 B 的旧单体仍留在 `data/canonical/quarantine.json`，
        下一次 Commit state 会再次触发 GitHub 100MB 单文件限制（本次故障的根因）。
        墓碑文件 < 4KB，声明 retired 与迁移前体积/哈希/条目数，旧读者读到 0 条（这是
        退役的预期语义：数据在分片中，旧代码不得再直接读单体）。
        """
        if self.mode() != "sharded":
            raise QuarantineCorrupt("retire requires sharded mode")
        rep = self.verify_consistency()
        if expect_items is not None and rep["on_disk"] != expect_items:
            raise QuarantineCorrupt("shard item count %d != expected %d"
                                    % (rep["on_disk"], expect_items))
        backup = None
        if self.legacy.exists():
            pre_bytes = self.legacy.stat().st_size
            pre_sha = _sha256(self.legacy)
            if backup_dir:
                backup = self.backup_legacy(Path(backup_dir) / "quarantine.pre_shard.json",
                                            expect_items=expect_items)
            else:
                backup = {"ok": False, "note": "no backup_dir given (offline copy skipped)",
                          "bytes": pre_bytes, "sha256": pre_sha}
            # 保留离线备份的哈希（用于再次校验）；单体 >100MB 不得留在仓库路径
            pre = {"bytes": pre_bytes, "sha256": pre_sha, "items": rep["on_disk"]}
        else:
            pre = {"bytes": 0, "sha256": "", "items": 0}
        tombstone = {
            "schema_version": "2.0",
            "retired": True,
            "items": [],
            "note": "单体已退役：quarantine 数据改为分片存储，读取请用 QuarantineStore",
            "manifest": "data/canonical/quarantine_manifest.json",
            "total_items": rep["on_disk"],
            "pre_migration": pre,
        }
        _atomic_write(self.legacy, (json.dumps(tombstone, ensure_ascii=False, indent=1) + "\n").encode())
        size = self.legacy.stat().st_size
        if size >= 4096:
            raise QuarantineCorrupt("tombstone unexpectedly large: %d" % size)
        if self.mode() != "sharded" or len(self.load_items()) != rep["on_disk"]:
            raise QuarantineCorrupt("post-retire verification failed")
        return {"ok": True, "tombstone_bytes": size, "items_in_shards": rep["on_disk"],
                "backup": backup, "committable": True,
                "warning": "旧代码直接读 quarantine.json 将得到 0 条；必须先部署新 pin"}

    def expected_tree(self):
        """迁移+退役后的预期 Git 树（path → bytes），用于远端/本地 tree 校验。"""
        tree = {}
        if self.mode() == "sharded":
            idx = self.read_index()
            for s_ in idx["shards"]:
                tree["data/canonical/quarantine/%s" % s_["shard"]] = int(s_["bytes"])
            tree["data/canonical/quarantine/index.json"] = self.index_path.stat().st_size
            tree["data/canonical/quarantine/ids.json"] = self.ids_path.stat().st_size
            tree["data/canonical/quarantine_manifest.json"] = self.manifest_path.stat().st_size
        if self.legacy.exists():
            tree["data/canonical/quarantine.json"] = self.legacy.stat().st_size
        return {"paths": tree, "files": len(tree), "max_bytes": max(tree.values() or [0]),
                "github_hard_limit": 100 * 1024 * 1024,
                "all_below_hard_limit": all(v < 100 * 1024 * 1024 for v in tree.values())}

    def rollback_to_monolith(self, expect_items=None):
        """回滚：把**当前全部分片（含迁移后新增记录）**合并回旧单体，再移除分片。

        与 git revert 的区别：revert 会丢掉迁移后新增的记录；本方法先落单体再清理，
        保证增量不丢失（可重放）。返回回滚报告。
        """
        if self.mode() != "sharded":
            return {"ok": True, "noop": True, "reason": "not sharded"}
        self.verify_consistency()
        items = self.load_items(verify_checksums=True)
        if expect_items is not None and len(items) != expect_items:
            raise QuarantineCorrupt("rollback count mismatch: %d != %d" % (len(items), expect_items))
        doc = {"schema_version": "2.0", "pipeline_version": 2,
               "run_id": "rollback", "updated_at": _now_iso(), "items": items}
        _atomic_write(self.legacy, (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode())
        # 校验单体可读且条目一致后再清理分片
        back = json.loads(self.legacy.read_text(encoding="utf-8")).get("items") or []
        if len(back) != len(items):
            raise QuarantineCorrupt("monolith verification failed: %d != %d" % (len(back), len(items)))
        import shutil
        shutil.rmtree(self.shard_dir, ignore_errors=True)
        if self.manifest_path.exists():
            self.manifest_path.unlink()
        return {"ok": True, "restored_items": len(items), "shards_removed": True}

    def rollback_hint(self):
        """回滚说明（不执行）：迁移是单一提交，回滚 = git revert 该提交，
        旧单体恢复后 `load_items()` 自动回退到 legacy 分支。"""
        return {
            "method": "git_revert_migration_commit",
            "legacy_path": str(self.legacy.relative_to(self.root)).replace("\\", "/"),
            "sharded_detection": "manifest+index 存在即走分片，否则走旧单体",
            "data_loss": "none（迁移不删除记录；revert 恢复旧单体）",
        }
