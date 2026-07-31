"""ASIP Stage 2.5A — 确定性 task_id 与 cache_key 生成。

设计要点（对应规范第十节）：
- 使用 SHA-256，截取稳定长度，不使用简单递增编号；
- 相同输入重复提交 -> task_id / cache_key 一致（幂等）；
- prompt_version 变化 -> 生成新 cache_key；
- Provider 变化不得篡改原始内容哈希（Provider 不进入哈希输入）。
"""

import hashlib
import json

_ID_LEN = 24
_CACHE_LEN = 32


def _stable_digest(*parts):
    h = hashlib.sha256()
    for part in parts:
        # 规范化序列化，保证 dict 顺序无关
        h.update(json.dumps(part, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    return h.hexdigest()


def generate_ai_task_id(
    task_type,
    input_ref,
    content_hash,
    prompt_version,
    output_schema_version,
    provider_requested=None,
):
    """基于内容确定性生成 task_id（不以 Provider 作为哈希输入）。"""
    digest = _stable_digest(
        task_type,
        input_ref,
        content_hash,
        prompt_version,
        output_schema_version,
    )
    return "AIT_" + digest[:_ID_LEN]


def generate_ai_cache_key(
    task_type,
    input_ref,
    content_hash,
    prompt_version,
    output_schema_version,
):
    """基于内容确定性生成 cache_key。与 task_id 同源，但更长。"""
    digest = _stable_digest(
        task_type,
        input_ref,
        content_hash,
        prompt_version,
        output_schema_version,
    )
    return "cache:" + digest[:_CACHE_LEN]
