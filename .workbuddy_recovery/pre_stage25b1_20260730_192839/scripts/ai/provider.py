"""ASIP Stage 2.5A — Provider 抽象接口。

统一业务代码必须通过 Registry 获取 Provider 实例，禁止直接调用：
- Hy3 / WorkBuddy 内部接口；
- OpenAI SDK / 任意中转 API；
- 任何外部网络请求。

所有 Provider 必须实现以下五个方法。
"""

from abc import ABC, abstractmethod


class BaseAIProvider(ABC):
    """AI Provider 统一接口。"""

    #: Provider 名称（workbuddy_queue / openai_api / generic_api / disabled）
    name = "base"

    def __init__(self, config, name="base"):
        self.config = config or {}
        self.name = name

    @abstractmethod
    def validate_config(self):
        """返回错误字符串列表；空列表表示配置可用。"""
        raise NotImplementedError

    @abstractmethod
    def submit_task(self, task):
        """提交一个 AI 任务，返回（可能被补充后的）任务 dict。"""
        raise NotImplementedError

    @abstractmethod
    def get_task_status(self, task_id):
        """返回任务状态字符串（见 contracts.TASK_STATUSES）。"""
        raise NotImplementedError

    @abstractmethod
    def load_result(self, task_id):
        """加载任务结果 dict；未产生结果返回 None。"""
        raise NotImplementedError

    @abstractmethod
    def health_check(self):
        """返回健康状态 dict（含是否涉及外部网络）。"""
        raise NotImplementedError
