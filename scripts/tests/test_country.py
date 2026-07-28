#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二轮整改单元测试（需求第十七节）。运行：python scripts/tests/test_country.py"""
import os
import sys
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COL = os.path.join(SCRIPT_DIR, "..", "collectors")
sys.path.insert(0, os.path.abspath(COL))
ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from country_runner import (load_country_cfg, identify_country, relevance_stage1,
                            classify_type)  # noqa

CHAD = load_country_cfg("chad")
NIGER = load_country_cfg("niger")

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  PASS  %s" % name)
    else:
        FAIL += 1
        print("  FAIL  %s" % name)


def idc(text, cfg):
    return identify_country(text, cfg)


print("== 国家识别：单词边界 ==")
# Lac 不得匹配 place/replace/displacement/marketplace
check("Lac 不误匹配 displacement/marketplace",
      idc("displaced persons in a marketplace near the border", CHAD)["decision"] != "chad")
check("Lac 作为独立词且配乍得可归乍得",
      idc("attaque armée dans la province du Lac au Tchad", CHAD)["decision"] == "chad")
# riot 不误匹配 patriot/priorité/authority
check("riot 不误匹配 patriot/patriote/priorité",
      idc("patriote nigérian priorité", NIGER)["decision"] != "niger")
check("riot 作为独立词可识别",
      idc("manifestation pacifique sans riot", NIGER)["decision"] in ("niger", "unclear"))
# mine 仅在爆炸物/地雷语境
check("mine 普通片段(examine/determine)不计安全",
      relevance_stage1("the committee will examine and determine the report")[
          0] is not True)

print("== 尼日尔/尼日利亚防误判 ==")
check("Niger Delta 不归尼日尔", idc("attack in Niger Delta Nigeria", NIGER)["decision"] == "exclude")
check("Niger State 不归尼日尔", idc("banditry in Niger State Nigeria", NIGER)["decision"] == "exclude")
check("Nigerian Army 不归尼日尔", idc("Nigerian Army raid in Kaduna", NIGER)["decision"] == "exclude")
check("Benin City 不归尼日尔", idc("clash in Benin City Nigeria", NIGER)["decision"] == "exclude")
check("Nigeria 不归尼日尔", idc("Nigeria army airstrike", NIGER)["decision"] == "exclude")
check("Republic of Niger + Niamey 归尼日尔",
      idc("coup in Niamey Republic of Niger", NIGER)["decision"] == "niger")
check("仅国名 Niger 无地点不盲目归尼日尔",
      idc("Niger discusses regional policy", NIGER)["decision"] == "unclear")

print("== 乍得湖跨国防误判 ==")
check("Lake Chad 尼日利亚博尔诺不归乍得",
      idc("Boko Haram attack in Borno Lake Chad Basin Nigeria", CHAD)["decision"] in ("regional", "unclear"))
check("Lake Chad 尼日尔迪法不归乍得",
      idc("attaque dans la région de Diffa bassin du lac Tchad", CHAD)["decision"] in ("regional", "unclear"))
check("Lake Chad + 乍得 Lac 省可归乍得",
      idc("affrontement à Baga Sola Lac Tchad", CHAD)["decision"] == "chad")

print("== 相关性筛选 ==")
check("体育(足球/非洲杯)不进安全事件", relevance_stage1("match de football CAN 2025")[
      0] is not True)
check("化肥交付不进武装冲突", relevance_stage1("livraison d'engrais aux agriculteurs")[
      0] is not True)
check("银行行长会见不进武装冲突", relevance_stage1("rencontre avec le gouverneur de la banque centrale")[
      0] is not True)
check("真实袭击可识别", relevance_stage1("attaque armée a fait 10 morts à N'Djamena")[
      0] is True)

print("== 事件类型分类（不再默认武装冲突） ==")
check("恐袭→terrorist_attack", classify_type("attentat suicide Boko Haram", "terrorist attack")[0] == "terrorist_attack")
check("农牧民冲突→communal_conflict", classify_type("conflit agriculteurs-éleveurs", "farmers herders clash")[0] == "communal_conflict")
check("政变→political_crisis", classify_type("coup d'Etat crise politique", "coup")[0] == "political_crisis")
check("绑架→kidnapping", classify_type("enlèvement de civils", "kidnapping")[0] == "kidnapping")
check("纯边境关闭→border_security", classify_type("fermeture de frontière", "border closure")[0] == "border_security")

print("\n结果：PASS=%d  FAIL=%d" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
