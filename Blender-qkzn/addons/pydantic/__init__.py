"""简化版 pydantic 兼容层。

在离线或受限环境中无法安装官方 pydantic 时，本模块提供基础兼容能力，
仅覆盖本项目所需的 `BaseModel`、`Field`、`ValidationError` 与 `root_validator`。
真实部署建议安装官方 pydantic，以获得完整特性与类型校验能力。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional


class ValidationError(Exception):
    """与 pydantic 的 ValidationError 对齐的异常类型。"""


class _FieldInfo:
    def __init__(self, default: Any = ... , default_factory: Optional[Callable[[], Any]] = None):
        self.default = default
        self.default_factory = default_factory


def Field(*, default: Any = ..., default_factory: Optional[Callable[[], Any]] = None) -> _FieldInfo:
    """提供与 pydantic.Field 相同的接口。"""

    return _FieldInfo(default=default, default_factory=default_factory)


def root_validator(func: Optional[Callable[[Any, Dict[str, Any]], Dict[str, Any]]] = None, **_kwargs):
    """注册根验证器的装饰器。"""

    def decorator(method: Callable[[Any, Dict[str, Any]], Dict[str, Any]]) -> Callable[[Any, Dict[str, Any]], Dict[str, Any]]:
        setattr(method, "__is_root_validator__", True)
        return method

    if func is not None:
        return decorator(func)
    return decorator


class BaseModelMeta(type):
    """负责收集字段信息与根验证器的元类。"""

    def __new__(mcls, name: str, bases: tuple[type, ...], namespace: Dict[str, Any]):
        cls = super().__new__(mcls, name, bases, dict(namespace))
        annotations: Dict[str, Any] = namespace.get("__annotations__", {})
        fields: Dict[str, _FieldInfo] = {}
        for field_name in annotations:
            value = namespace.get(field_name, ...)
            if isinstance(value, _FieldInfo):
                fields[field_name] = value
            else:
                fields[field_name] = _FieldInfo(default=value)
        setattr(cls, "__fields__", fields)
        validators = []
        for attr in namespace.values():
            if getattr(attr, "__is_root_validator__", False):
                validators.append(attr)
        setattr(cls, "__root_validators__", validators)
        return cls


class BaseModel(metaclass=BaseModelMeta):
    """最小化的 BaseModel 实现，支持 parse_obj 与 root_validator。"""

    __fields__: Dict[str, _FieldInfo]
    __root_validators__: list[Callable[[Any, Dict[str, Any]], Dict[str, Any]]]

    def __init__(self, **data: Any) -> None:
        values: Dict[str, Any] = {}
        for name, info in self.__fields__.items():
            if name in data:
                values[name] = data[name]
            elif info.default is not ...:
                values[name] = info.default
            elif info.default_factory is not None:
                values[name] = info.default_factory()
            else:
                raise ValidationError(f"字段 {name} 缺失")
        for validator in self.__root_validators__:
            values = validator(self.__class__, values)
        for key, value in values.items():
            setattr(self, key, value)

    @classmethod
    def parse_obj(cls, obj: Any) -> "BaseModel":
        if isinstance(obj, cls):
            return obj
        if isinstance(obj, dict):
            return cls(**obj)
        raise ValidationError(f"无法解析对象 {obj!r}")

    def dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)
