"""兼容 JSON 与表单接口的请求体解析，使用框架统一的校验错误响应。"""

from json import JSONDecodeError
from typing import TypeVar

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError

BodyModel = TypeVar('BodyModel', bound=BaseModel)


def is_json_content_type(content_type: str) -> bool:
    """支持标准 JSON 及 application/*+json 媒体类型。"""
    media_type = content_type.split(';', 1)[0].strip().lower()
    return media_type == 'application/json' or (
        media_type.startswith('application/') and media_type.endswith('+json')
    )


def validate_code_body(model: type[BodyModel], value: object) -> BodyModel:
    """将手动 Pydantic 校验错误转换为带 body 路径的请求校验错误。"""
    try:
        return model.model_validate(value)
    except ValidationError as exc:
        errors = [
            {**error, 'loc': ('body', *error['loc'])}
            for error in exc.errors(include_url=False)
        ]
        raise RequestValidationError(errors) from exc


async def parse_json_code_body(request: Request, model: type[BodyModel]) -> BodyModel:
    """非法 JSON 或编码错误均返回 422，不进入业务层。"""
    try:
        value = await request.json()
    except (JSONDecodeError, UnicodeDecodeError) as exc:
        location = ('body', exc.pos) if isinstance(exc, JSONDecodeError) else ('body',)
        raise RequestValidationError([{
            'type': 'json_invalid', 'loc': location, 'msg': 'JSON decode error',
            'input': {},
            'ctx': {'error': exc.msg if isinstance(exc, JSONDecodeError) else exc.reason},
        }]) from exc
    return validate_code_body(model, value)
