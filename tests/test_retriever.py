"""检索层测试：验证"切块不丢内容"和"能检索到相关内容"。

为什么这些测试能单独跑、不用启动服务、不用调模型？
    因为检索层不依赖网络也不依赖数据库 —— 这正是分层的收益。
"""
import pytest

from app.services import retriever


@pytest.fixture(autouse=True)
def temp_knowledge(tmp_path, monkeypatch):
    """每个测试用一个临时空知识库，避免受真实 data/knowledge 内容影响。"""
    kb = tmp_path / "knowledge"
    kb.mkdir()
    monkeypatch.setattr(retriever, "KNOWLEDGE_DIR", kb)
    retriever.reset_index()
    yield kb
    retriever.reset_index()


def test_split_short_text_returns_single_chunk():
    assert retriever.split_text("很短的一句话") == ["很短的一句话"]


def test_split_empty_text_returns_nothing():
    assert retriever.split_text("   ") == []


def test_split_long_text_keeps_head_tail_and_overlaps():
    text = "".join(chr(ord("a") + i % 26) for i in range(1000))
    pieces = retriever.split_text(text, size=300, overlap=50)

    assert len(pieces) > 1
    assert all(len(p) <= 300 for p in pieces)
    # 开头和结尾的内容都不能丢
    assert pieces[0].startswith(text[:20])
    assert pieces[-1].endswith(text[-20:])
    # 相邻块必须有重叠，否则边界上的一句话会被切断导致漏检
    assert pieces[1][:20] in pieces[0]


def test_ngrams_of_chinese_text():
    grams = retriever._ngrams("周三有什么课")
    assert "周三" in grams
    assert "什么" in grams
    assert "么课" in grams


def test_search_finds_the_relevant_file(temp_knowledge):
    (temp_knowledge / "a.md").write_text("密钥写在项目根目录的 .env 文件里", encoding="utf-8")
    (temp_knowledge / "b.md").write_text("今天天气很好，适合出门散步", encoding="utf-8")
    retriever.reload_index()

    hits = retriever.search("密钥写在哪个文件", top_k=2)
    assert hits, "应该能检索到内容"
    assert hits[0]["source"] == "a.md"


def test_search_on_empty_knowledge_returns_nothing(temp_knowledge):
    retriever.reload_index()
    assert retriever.search("随便问一句") == []


def test_retrieve_context_returns_text_and_sources(temp_knowledge):
    (temp_knowledge / "c.md").write_text("服务默认端口是 8000", encoding="utf-8")
    retriever.reload_index()

    context, sources = retriever.retrieve_context("服务默认端口是多少")
    assert "8000" in context
    assert "c.md" in context          # 资料里要标出来源，便于追溯
    assert sources == ["c.md"]