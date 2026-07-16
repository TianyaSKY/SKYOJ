"""业务异常定义。"""


class BusinessError(Exception):
    """业务异常基类。"""


class ResourceNotFoundError(BusinessError):
    """业务资源不存在。"""


class PermissionDeniedError(BusinessError):
    """当前用户无权执行该操作。"""


class InvalidStateError(BusinessError):
    """业务对象状态不允许当前操作。"""


class ExternalServiceError(BusinessError):
    """外部服务调用失败。"""


class LlmConfigError(BusinessError):
    """LLM 环境变量未完整配置。"""
