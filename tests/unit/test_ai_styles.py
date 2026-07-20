"""AI 风格 merge / resolve 测试。"""
from zentray.services.ai_styles import (
    STYLE_GENTLE,
    STYLE_TOXIC,
    builtin_styles,
    merge_styles,
    resolve_active_style,
)


def test_builtin_three():
    styles = builtin_styles()
    ids = {s.id for s in styles}
    assert STYLE_TOXIC in ids
    assert STYLE_GENTLE in ids
    assert all(s.is_builtin and s.system_prompt for s in styles)


def test_merge_preserves_user_edit():
    stored = [
        {
            "id": STYLE_TOXIC,
            "name": "毒舌改",
            "system_prompt": "自定义毒舌",
            "is_builtin": True,
        }
    ]
    merged = merge_styles(stored)
    toxic = next(s for s in merged if s.id == STYLE_TOXIC)
    assert toxic.system_prompt == "自定义毒舌"
    assert toxic.name == "毒舌改"
    # 其他内置仍在
    assert any(s.id == STYLE_GENTLE for s in merged)


def test_merge_adds_custom():
    stored = [
        {
            "id": "custom-1",
            "name": "赛博禅师",
            "system_prompt": "保持冷静",
            "is_builtin": False,
        }
    ]
    merged = merge_styles(stored)
    assert any(s.id == "custom-1" for s in merged)
    assert any(s.id == STYLE_TOXIC for s in merged)


def test_resolve_active():
    styles = merge_styles(None)
    s = resolve_active_style(styles, STYLE_GENTLE)
    assert s.id == STYLE_GENTLE
