"""冒烟测试（smoke test）：最小的"程序能不能启动"检查。

为什么需要它？
    踩过的坑：11 个业务测试全过，但服务起不来 —— 因为那些测试只导入了 storage 和
    retriever，没有导入 main.py / llm.py。Python 的语法错误只在"导入那一刻"才暴露。
    所以必须有一个测试，把整个应用导入一遍。
"""
from fastapi import FastAPI


def test_app_can_be_imported():
    """整个应用能被导入起来（能抓出语法错误、循环导入、配置读取失败）。"""
    from app.main import app

    assert isinstance(app, FastAPI)
    assert app.title


def test_all_routes_registered():
    """接口都注册上了，没有因为写错装饰器而丢失。"""
    from app.main import app

    paths = {r.path for r in app.routes if hasattr(r, "methods")}
    for expected in ("/", "/chat", "/history/{session_id}", "/sessions", "/knowledge", "/search"):
        assert expected in paths, f"缺少接口: {expected}"


def test_llm_module_imports_and_has_rag_instruction():
    """业务模块能导入（这一条在当时就能抓出那个嵌套引号的语法错误）。"""
    from app.services import llm

    assert llm.SYSTEM_PROMPT
    assert "参考资料" in llm.RAG_INSTRUCTION