"""最基础的测试：验证"存进去能读出来"。

为什么要有测试？
    面试常问"你项目有测试吗"。有 3 个用例也比一个没有强得多，
    而且它逼你把"存储层"设计成可以单独测的样子（这就是分层的收益）。
"""
from app.services import storage


def _use_temp_file(tmp_path, monkeypatch):
    """把存储文件指到临时目录，避免污染真实数据。"""
    monkeypatch.setattr(storage, "HISTORY_FILE", tmp_path / "history.json")


def test_save_and_get_history(tmp_path, monkeypatch):
    _use_temp_file(tmp_path, monkeypatch)
    storage.save_message("s1", "user", "你好")
    storage.save_message("s1", "assistant", "你好，有什么可以帮你？")

    msgs = storage.get_history("s1")
    assert len(msgs) == 2
    assert msgs[0]["content"] == "你好"
    assert msgs[1]["role"] == "assistant"


def test_history_limit_keeps_latest(tmp_path, monkeypatch):
    """只取最近 limit 条 —— 对应"不能把全部历史都给模型"的截断策略。"""
    _use_temp_file(tmp_path, monkeypatch)
    for i in range(10):
        storage.save_message("s2", "user", f"问题{i}")

    recent = storage.get_history("s2", limit=3)
    assert len(recent) == 3
    assert recent[-1]["content"] == "问题9"


def test_unknown_session_returns_empty(tmp_path, monkeypatch):
    _use_temp_file(tmp_path, monkeypatch)
    assert storage.get_history("不存在的会话") == []


def test_sessions_are_isolated(tmp_path, monkeypatch):
    """不同会话的数据不能串 —— 这就是 session_id 存在的意义。"""
    _use_temp_file(tmp_path, monkeypatch)
    storage.save_message("A", "user", "我是A")
    storage.save_message("B", "user", "我是B")

    assert [m["content"] for m in storage.get_history("A")] == ["我是A"]
    assert sorted(storage.list_sessions()) == ["A", "B"]