"""ASIP Stage 2.5A — AI Provider 契约异常。

所有异常均不携带任何密钥或本机绝对路径；失败信息仅描述语义。
"""


class AIContractError(Exception):
    """AI 契约层通用错误。"""


class ProviderError(AIContractError):
    """Provider 运行时错误。"""


class ProviderNotConfigured(ProviderError):
    """所选 Provider 未配置（如付费 Provider 缺少密钥），必须失败关闭。"""


class TaskValidationError(AIContractError):
    """AI 任务不满足契约。"""

    def __init__(self, errors):
        self.errors = list(errors) if errors else ["task validation failed"]
        super().__init__("; ".join(self.errors))


class SchemaNotFoundError(AIContractError):
    """契约 Schema 文件缺失（required=True 时抛出的硬性失败）。"""

    def __init__(self, name, path):
        self.schema_name = name
        self.schema_path = path
        super().__init__(f"schema not found: {name} (path={path})")


class TaskStateError(AIContractError):
    """任务状态移动 / 查找失败（原子性违反、源丢失、锁冲突等）。"""
