#!/usr/bin/env python3
"""ASIP Stage 2.5C-3 — AI Result Cache

Deterministic caching of validated AI results by cache_key.
Cache-hit tasks skip batch/lease/model invocation entirely.
"""

import os
import json
import hashlib
import tempfile
import shutil

from .schema_validation import validate_against_schema

HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(HERE))
_CACHE_DEFAULT_DIR = os.path.join(_REPO, "data", "ai", "cache")
_CACHE_SCHEMA_PATH = os.path.join(_REPO, "schemas", "ai_cache_entry.schema.json")
_SCHEMA_VERSION = "1.0"

_CACHE_SCHEMA = None
_AI_ROOT_OVERRIDE = None


def set_ai_root(root):
    """Set AI root for cache operations (default: data/ai/cache/)."""
    global _AI_ROOT_OVERRIDE
    _AI_ROOT_OVERRIDE = root


def _get_cache_dir():
    if _AI_ROOT_OVERRIDE:
        return os.path.join(_AI_ROOT_OVERRIDE, "cache")
    return _CACHE_DEFAULT_DIR


def _load_cache_schema():
    global _CACHE_SCHEMA
    if _CACHE_SCHEMA is None:
        with open(_CACHE_SCHEMA_PATH, "r", encoding="utf-8") as f:
            _CACHE_SCHEMA = json.load(f)
    return _CACHE_SCHEMA


def _cache_path(cache_key):
    """SHA-256 hashed path for cache key (not raw key)."""
    h = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
    return os.path.join(_get_cache_dir(), h + ".json")


def _validate_cache_entry(entry):
    """Validate cache entry against schema."""
    schema = _load_cache_schema()
    errors = validate_against_schema(entry, schema)
    return (len(errors) == 0), errors


def write_cache_entry(task, result_obj, provenance, ingest_ts):
    """Atomically write a validated cache entry.

    Returns True on success, raises on failure.
    """
    cache_key = task.get("cache_key") or task["task_id"]
    entry = {
        "schema_version": _SCHEMA_VERSION,
        "cache_key": cache_key,
        "cache_key_sha256": hashlib.sha256(
            cache_key.encode("utf-8")).hexdigest(),
        "task_type": task.get("task_type", ""),
        "content_hash": task.get("content_hash", ""),
        "prompt_version": task.get("prompt_version", ""),
        "output_schema_version": task.get("output_schema_version", "1.1"),
        "prompt_checksum": provenance.get("prompt_checksum", ""),
        "render_hash": provenance.get("render_hash", ""),
        "prompt_variables_digest": provenance.get(
            "prompt_variables_digest", ""),
        "result": result_obj,
        "provenance": provenance,
        "source_task_id": task["task_id"],
        "created_at": ingest_ts,
        "synthetic": task.get("synthetic", False),
    }

    ok, errs = _validate_cache_entry(entry)
    if not ok:
        raise ValueError("cache entry validation failed: %s" % "; ".join(errs[:3]))

    path = _cache_path(cache_key)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
        shutil.move(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return True


def get_cache_entry(cache_key):
    """Return cache entry dict if valid, or None on miss."""
    path = _cache_path(cache_key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            entry = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None  # corrupted → miss

    ok, _ = _validate_cache_entry(entry)
    if not ok:
        return None  # tampered/wrong version → miss

    return entry


def check_cache_hit(task):
    """Check if a valid cache entry exists for this task.

    Returns (hit: bool, entry: dict|None, reason: str).
    """
    cache_key = task.get("cache_key") or task["task_id"]
    entry = get_cache_entry(cache_key)
    if entry is None:
        return False, None, "no_valid_cache"

    # Cross-check identity fields
    if entry.get("task_type") != task.get("task_type"):
        return False, None, "task_type_mismatch"
    if entry.get("prompt_version") != task.get("prompt_version", ""):
        return False, None, "prompt_version_changed"
    if entry.get("output_schema_version") != task.get(
            "output_schema_version", "1.1"):
        return False, None, "output_schema_version_changed"
    if entry.get("content_hash") != task.get("content_hash", ""):
        return False, None, "content_hash_changed"

    # Re-validate business output
    from .output_contracts import validate_business_output
    b_ok, _ = validate_business_output(
        task["task_type"], entry["result"],
        prompt_version=entry["prompt_version"],
        output_schema_version=entry["output_schema_version"])
    if not b_ok:
        return False, None, "cached_result_schema_validation_failed"

    return True, entry, "ok"
