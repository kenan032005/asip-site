#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASIP Stage 4 — 版本化 Prompt 合同加载与渲染。

约束：
- Prompt 文件不存在 → 失败关闭（raise）
- Prompt 版本与处理器配置不一致 → 失败关闭
- 不允许静默退回"仅发送 JSON"
- 正文通过 JSON 序列化安全嵌入，不破坏 Prompt 结构
"""

import hashlib
import json
import os
from datetime import datetime


class PromptContractError(Exception):
    """Prompt 合同配置或渲染错误。"""


class PromptContract:
    """版本化 Prompt 合同。"""

    def __init__(self, path, version=None):
        self.path = os.path.abspath(path)
        self.version = version
        self.content = None
        self.content_hash = None
        self.parsed_version = None
        self._load()

    def _load(self):
        """加载 Prompt 文件并校验。"""
        if not os.path.exists(self.path):
            raise PromptContractError(f"Prompt 文件不存在: {self.path}")
        with open(self.path, "r", encoding="utf-8") as f:
            self.content = f.read()
        if len(self.content.strip()) < 50:
            raise PromptContractError(f"Prompt 文件内容过短（<50 字符）: {self.path}")
        self.content_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        # 尝试从文件名或内容首行提取版本号
        self.parsed_version = self._extract_version()
        if self.version is not None and self.version != self.parsed_version:
            raise PromptContractError(
                f"Prompt 版本不一致: 配置要求 {self.version}, 文件声明 {self.parsed_version}")
        if self.version is None:
            self.version = self.parsed_version

    def _extract_version(self):
        """从文件名或内容提取版本号。"""
        import re
        # 文件名: stage4_event_enrichment_v1.md → 1.0.0
        basename = os.path.basename(self.path)
        m = re.search(r'v(\d+[._]\d+[._]\d+)', basename)
        if m:
            return m.group(1).replace("_", ".")
        m = re.search(r'v(\d+[._]\d+)', basename)
        if m:
            return m.group(1).replace("_", ".") + ".0"
        # 内容首行
        m = re.search(r'v(\d+\.\d+\.\d+)', self.content[:200])
        if m:
            return m.group(1)
        return "0.0.0"

    def render(self, event):
        """渲染完整 Prompt 文本（系统指令 + 事件 JSON 数据）。

        正文通过 JSON 序列化安全嵌入，不会被模板符号破坏。
        """
        if not self.content:
            raise PromptContractError("Prompt 内容未加载")
        data = {
            "event_id": event.get("event_id", ""),
            "canonical_run_id": event.get("canonical_run_id", ""),
            "primary_country": event.get("primary_country", ""),
            "country_iso3": event.get("country_iso3", ""),
            "original_title": event.get("original_title", ""),
            "source_language": event.get("source_language", "unknown"),
            "event_time": event.get("event_time", ""),
            "canonical_url": event.get("canonical_url", ""),
            "body_extracted": event.get("body_extracted", ""),
        }
        # 安全：正文通过 JSON 序列化嵌入，不会被文本内容破坏结构
        event_json = json.dumps(data, ensure_ascii=False, indent=2)
        # 渲染模板变量
        rendered = self.content
        if "{{" in rendered:
            rendered = rendered.replace("{{ event_id }}", event.get("event_id", ""))
            rendered = rendered.replace("{{ canonical_run_id }}", event.get("canonical_run_id", ""))
            rendered = rendered.replace("{{ primary_country }}", event.get("primary_country", ""))
            rendered = rendered.replace("{{ country_iso3 }}", event.get("country_iso3", ""))
            rendered = rendered.replace("{{ original_title }}", json.dumps(event.get("original_title", ""), ensure_ascii=False))
            rendered = rendered.replace("{{ source_language }}", event.get("source_language", "unknown"))
            rendered = rendered.replace("{{ event_time }}", event.get("event_time", ""))
            rendered = rendered.replace("{{ canonical_url }}", event.get("canonical_url", ""))
            body_safe = json.dumps(event.get("body_extracted", ""), ensure_ascii=False)
            rendered = rendered.replace("{{ body_extracted }}", body_safe)
        # 追加结构化数据（正文安全）
        rendered += "\n\n## 输入数据（结构化 JSON）\n```json\n" + event_json + "\n```"
        return rendered


def load_prompt_contract(path, version=None):
    """加载 PromptContract 实例。"""
    return PromptContract(path, version=version)


def compute_prompt_content_hash(contract):
    """返回已加载合同的 content_hash。"""
    return contract.content_hash if contract else ""


def bj_iso_now():
    """北京时间 ISO 8601 时间字符串。"""
    from datetime import timezone, timedelta
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat(timespec="seconds")
