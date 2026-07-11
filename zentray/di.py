# zentray/di.py
"""
轻量级依赖注入容器。

提供与 injector 库兼容的 API，在 injector 库不可用时使用。
当 pip 可用后，可替换为标准的 injector 库。
"""
import inspect
from typing import Any, Callable, Dict, Type, get_type_hints


class _Binding:
    """单个依赖绑定"""

    def __init__(self, provider_fn: Callable, is_singleton: bool = True):
        self.provider_fn = provider_fn
        self.is_singleton = is_singleton
        self._instance = None
        self._resolved = False

    def resolve(self, injector: "Injector") -> Any:
        if self.is_singleton and self._resolved:
            return self._instance

        # 自动注入 provider 函数的参数
        sig = inspect.signature(self.provider_fn)
        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else None
            if param_type and param_type in injector._bindings:
                kwargs[param_name] = injector.get(param_type)
            elif param_type:
                raise ValueError(
                    f"无法解析参数 '{param_name}' (类型: {param_type}) "
                    f"在 provider '{self.provider_fn.__name__}'"
                )

        instance = self.provider_fn(**kwargs)

        if self.is_singleton:
            self._instance = instance
            self._resolved = True

        return instance


class Module:
    """依赖注入模块基类"""
    pass


class Injector:
    """依赖注入容器"""

    def __init__(self, modules: list = None):
        self._bindings: Dict[Type, _Binding] = {}
        if modules:
            for module in modules:
                self._register_module(module)

    def _register_module(self, module: Module) -> None:
        """扫描模块中的 provider 方法并注册"""
        for name in dir(module):
            attr = getattr(module, name)
            if callable(attr) and hasattr(attr, "_is_provider"):
                return_type = attr._return_type
                is_singleton = getattr(attr, "_is_singleton", True)
                # 绑定 provider 方法到模块实例
                bound_fn = attr.__get__(module, type(module))
                self._bindings[return_type] = _Binding(bound_fn, is_singleton)

    def get(self, target_type: Type) -> Any:
        """获取指定类型的实例"""
        if target_type not in self._bindings:
            raise KeyError(f"未注册的类型: {target_type.__name__}")
        return self._bindings[target_type].resolve(self)

    def binder(self):
        """返回 binder 用于程序化绑定（兼容 injector API 的 configure 模式）"""
        return _Binder(self)


class _Binder:
    """程序化绑定器"""

    def __init__(self, injector: Injector):
        self._injector = injector

    def bind(self, interface: Type, to: Type = None) -> None:
        """绑定接口到实现"""
        if to:
            # 将实现类的构造函数作为 provider
            def _provider():
                return to()
            _provider._is_provider = True
            _provider._return_type = interface
            _provider._is_singleton = True
            self._injector._bindings[interface] = _Binding(_provider, is_singleton=True)


def provider(fn: Callable) -> Callable:
    """标记方法为 provider"""
    hints = get_type_hints(fn)
    return_type = hints.get("return")
    if return_type is None:
        raise ValueError(f"provider 方法必须标注返回类型: {fn.__name__}")
    fn._is_provider = True
    fn._return_type = return_type
    fn._is_singleton = getattr(fn, "_is_singleton", True)
    return fn


def singleton(cls_or_fn):
    """标记为单例（可以用作装饰器）"""
    if isinstance(cls_or_fn, type):
        # 用于类装饰器
        cls_or_fn._is_singleton = True
        return cls_or_fn
    else:
        # 用于方法装饰器
        cls_or_fn._is_singleton = True
        return cls_or_fn
