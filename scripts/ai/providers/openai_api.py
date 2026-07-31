#!/usr/bin/env python3
"""ASIP Stage 2.5D/E — OpenAI API Provider

Explicit entry for api.openai.com. Uses GenericAPIProvider under the hood
with platform OpenAI's standard endpoint.
"""

import os
from .generic_api import GenericAPIProvider
from .base import ProviderConfig


class OpenAIAPIProvider(GenericAPIProvider):
    """OpenAI 官方 API Provider。"""

    def __init__(self, config=None):
        super().__init__(config or ProviderConfig("openai_api"))
        # Override defaults for OpenAI
        if not self.base_url:
            self.base_url = "https://api.openai.com/v1"
        if not self.api_key:
            self.api_key = os.environ.get("OPENAI_API_KEY", "")
        if not self.model:
            self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def __repr__(self):
        return "OpenAIAPIProvider(model=%s)" % self.model
