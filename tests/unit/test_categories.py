"""二级分类与标题前缀纯函数测试。"""
from zentray.core.categories import (
    CategorySettings,
    PrimaryCategory,
    SecondaryCategory,
    default_category_settings,
    format_category_prefix,
    format_display_title_with_category,
)


def test_default_has_three_primaries():
    s = default_category_settings()
    assert len(s.primary_list) >= 3
    names = {p.name for p in s.primary_list}
    assert "工作" in names


def test_format_primary_only():
    primary = PrimaryCategory(id="p1", name="工作")
    s = CategorySettings(
        primary_list=[primary],
        enabled_secondary=True,
        wrap_left="[",
        wrap_right="]",
    )
    assert format_category_prefix(s, primary_id="p1") == "[工作]"


def test_format_primary_secondary_joined():
    """目标格式: [一级-二级]"""
    sec = SecondaryCategory(id="s1", name="需求")
    primary = PrimaryCategory(id="p1", name="工作", secondaries=[sec])
    s = CategorySettings(
        enabled_secondary=True,
        level_separator="-",
        wrap_left="[",
        wrap_right="]",
        primary_list=[primary],
    )
    assert format_category_prefix(s, primary_id="p1", secondary_id="s1") == "[工作-需求]"


def test_secondary_disabled_shows_primary_only():
    sec = SecondaryCategory(id="s1", name="需求")
    primary = PrimaryCategory(id="p1", name="工作", secondaries=[sec])
    s = CategorySettings(
        enabled_secondary=False,
        primary_list=[primary],
        wrap_left="【",
        wrap_right="】",
    )
    assert format_category_prefix(s, primary_id="p1", secondary_id="s1") == "【工作】"


def test_display_title_with_overdue():
    primary = PrimaryCategory(id="p1", name="生活")
    s = CategorySettings(primary_list=[primary], wrap_left="[", wrap_right="]")
    out = format_display_title_with_category(
        "买菜",
        s,
        primary_id="p1",
        overdue_prefix="【已逾期】",
    )
    assert out.startswith("[生活] ")
    assert "买菜" in out
    assert "【已逾期】" in out


def test_from_dict_roundtrip():
    s = default_category_settings()
    d = s.to_dict()
    s2 = CategorySettings.from_dict(d)
    assert len(s2.primary_list) == len(s.primary_list)
