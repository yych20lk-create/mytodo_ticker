# tests/unit/test_logging_import.py
def test_main_package_importable():
    """入口模块应可通过包路径导入（非裸 logging_config）。"""
    from zentray.main import main
    from zentray.logging_config import setup_logging

    assert callable(main)
    assert callable(setup_logging)
