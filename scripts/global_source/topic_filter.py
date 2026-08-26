#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Country Source Layer — 确定性 Topic Filter 与 Opinion 标记（§十一/§十二）。

社安/疾病关键词第一轮筛选，不用 AI。
opinion/analysis/chronique/editorial 栏目标记 content_type，
不默认作为 primary factual evidence。
"""

# §十一 社安关键词
SECURITY_KEYWORDS = [
    "security", "sécurité", "securite", "defense", "défense", "defence",
    "conflict", "violence", "attack", "attaque", "attentat", "border",
    "frontière", "frontiere", "crime", "kidnap", "hostage", "otage",
    "protest", "manifestation", "strike", "grève", "greve",
    "displacement", "refugee", "réfugié", "refugie", "humanitarian",
    "humanitaire", "disaster", "catastrophe", "explosion", "military",
    "armée", "armee", "enlèvement", "enlevement", "assassinat",
    "tuerie", "attaque", "déplacé", "deplace", "aide humanitaire",
]

# 疾病关键词（健康源单独识别）
DISEASE_KEYWORDS = [
    "outbreak", "épidémie", "epidemie", "epidemic", "cholera",
    "mpox", "monkeypox", "measles", "rougeole", "yellow fever",
    "fièvre jaune", "fievre jaune", "meningitis", "méningite",
    "meningite", "ebola", "marburg", "lassa", "polio", "poliomyelitis",
    "cas de", "vaccination", "cas confirmés", "cas confirmes",
    "flambée", "flambee", "santé publique", "sante publique",
]

# §十二 opinion/analysis 标记
OPINION_MARKERS = [
    "opinion", "editorial", "chronique", "analyse", "analysis",
    "commentary", "tribune libre", "point de vue", "débat",
    "debate", "blog",
]


def classify_chain(role, topic_scope):
    """按 registry 判定进入 Social 或 Disease candidate chain。"""
    if role == "authoritative_disease_evidence" or "disease" in (topic_scope or []):
        return "disease"
    return "social"


def match_topic(text, chain):
    """确定性主题匹配。chain: social | disease。命中返回 (matched, keyword)。"""
    t = (text or "").lower()
    kws = DISEASE_KEYWORDS if chain == "disease" else SECURITY_KEYWORDS
    for kw in kws:
        if kw in t:
            return True, kw
    return False, None


def detect_opinion(title, url="", section=""):
    """根据标题/URL/栏目名检测 opinion/analysis 内容。返回 None 或 'opinion'/'analysis'。"""
    blob = " ".join([str(title or ""), str(url or ""), str(section or "")]).lower()
    for m in OPINION_MARKERS:
        if m in blob:
            if m in ("chronique", "tribune libre", "point de vue", "débat", "debate", "commentary"):
                return "opinion"
            if m in ("analyse", "analysis", "blog"):
                return "analysis"
            return "opinion"
    return None


def classify_candidate(cand):
    """为 candidate 补 chain/content_type 字段。"""
    chain = classify_chain(cand.get("role"), cand.get("topic_scope"))
    cand["chain"] = chain
    if chain == "social":
        matched, kw = match_topic(
            " ".join([str(cand.get("title") or ""), str(cand.get("url") or "")]), "social")
        cand["topic_match"] = kw if matched else None
    else:
        cand["topic_match"] = None
    opinion = detect_opinion(cand.get("title"), cand.get("url"), cand.get("section"))
    if opinion:
        cand["content_type"] = opinion
    return cand
