"""动态 JSON 边界；固定业务结果使用专用 dataclass。"""

from dataclasses import dataclass

type JsonValue = (
    str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
)


@dataclass(frozen=True)
class JsonObjectResult:
    payload: dict[str, JsonValue]
