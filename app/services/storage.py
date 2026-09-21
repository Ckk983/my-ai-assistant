"""存储层：负责决定"数据存在哪"。

★★★★★ 这是你最该看懂的一个文件 ★★★★★

第一版为什么用本地文件（data/history.json）？
    1. 零配置，不用装 MySQL，能立刻跑起来 —— 先让它能跑，再加复杂度
    2. 数据量小，整份读进来也就几毫秒

什么时候必须换掉它？（这三条就是"为什么需要数据库"的答案，面试必问）
    1. 要多人同时写 —— 文件会被同时写坏（没有事务、没有锁）
    2. 要按条件查询、做统计 —— 文件只能全量读进来再自己筛，慢了就崩
    3. 数据大到内存放不下

换的时候，只需要改这一个文件。
上层的 llm.py / main.py 完全不用动 —— 这就是"分层"的价值。
"""
import json
from datetime import datetime
from pathlib import Path

from app.config import settings

HISTORY_FILE = settings.DATA_DIR / "history.json"


def _load_all() -> dict:
    """把整个文件读进内存。注意是"读全部"，数据大了就撑不住。"""
    if not HISTORY_FILE.exists():
        return {}
    with open(HISTORY_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_all(data: dict) -> None:
    """把整份数据写回去。注意是"写全部"，两个人同时写就会互相覆盖。"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_message(session_id: str, role: str, content: str) -> None:
    """存一条消息。role 只有两种：user（用户说的）或 assistant（AI 说的）。"""
    data = _load_all()
    data.setdefault(session_id, []).append(
        {
            "role": role,
            "content": content,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    _save_all(data)


def get_history(session_id: str, limit: int = 6) -> list[dict]:
    """只取最近 limit 条历史。

    为什么不能把全部历史都塞给模型？
        1. 模型一次能读的长度有限（叫"上下文长度"）
        2. 每多一个 token 都要花钱
    所以这里取最近 6 条 —— 这就是"截断策略"。
    """
    data = _load_all()
    messages = data.get(session_id, [])
    return [{"role": m["role"], "content": m["content"]} for m in messages[-limit:]]


def list_sessions() -> list[str]:
    """列出所有会话 ID。文件方案下只能全读进来，这也是将来要换数据库的原因之一。"""
    return list(_load_all().keys())