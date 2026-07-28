#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""niger 国家采集入口。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from country_runner import run_country, load_country_cfg  # noqa: E402

CFG = load_country_cfg("niger")


def run(sources):
    return run_country(CFG, sources)
