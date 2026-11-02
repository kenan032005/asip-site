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
    def is_sharded(self):
        return self.manifest_path.exists() and self.index_path.exists()

    def read_index(self):
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {"schema": SCHEMA_INDEX, "total_items": 0, "shards": []}

    def read_ids(self):
        try:
            return json.loads(self.ids_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

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
    def load_items(self, verify_checksums=False):
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

    def iter_items(self):
        """流式读取（分片模式下逐片 yield，避免一次性 100MB 内存峰值）。"""
        if self.is_sharded():
            idx = self.read_index()
            for s in idx.get("shards", []):
                path = self.shard_dir / s["shard"]
                if not path.exists():
                    raise QuarantineCorrupt("missing shard: %s" % s["shard"])
                doc = json.loads(path.read_text(encoding="utf-8"))
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
    def migrate(self, dry_run=True, source_items=None, max_shard_bytes=None):
        """单体 → 分片。dry_run 只计算不落盘。返回报告（含逐条哈希等价性）。"""
        items = source_items if source_items is not None else self._load_legacy()
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

    def rollback_hint(self):
        """回滚说明（不执行）：迁移是单一提交，回滚 = git revert 该提交，
        旧单体恢复后 `load_items()` 自动回退到 legacy 分支。"""
        return {
            "method": "git_revert_migration_commit",
            "legacy_path": str(self.legacy.relative_to(self.root)).replace("\\", "/"),
            "sharded_detection": "manifest+index 存在即走分片，否则走旧单体",
            "data_loss": "none（迁移不删除记录；revert 恢复旧单体）",
        }
