"""模型层：负责"借用别人的 AI 能力"。

数据流位置（这是 RAG 之前的版本，先跑通最简单的对话）：
    1. 从 storage 拿最近几轮对话（让 AI 记得前面说了什么）
    2. 拼成 messages 数组
    3. 通过 HTTP 发给大模型 API
    4. 拿到回答
    5. 把这一轮问答交给 storage 存起来

注意：我们不是自己造 AI，只是"按约定格式发请求、收结果"。
      这个约定就是 API。
"""
from openai import OpenAI

from app.config import settings
from app.services import storage

client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

# 系统提示词：告诉 AI 它是谁、要怎么回答。
# 以后做 RAG 时，会在这里插入"检索到的资料"。
SYSTEM_PROMPT = (
    "你是一个严谨的助手。回答简洁、准确，用中文回答。"
    "如果不确定，就直说不确定，不要编造。"
)


def ask(question: str, session_id: str) -> tuple[str, int]:
    """问 AI 一个问题，返回 (回答, 消耗的token数)。"""
    history = storage.get_history(session_id)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += history                                  # 把前几轮对话带上 → 多轮对话
    messages.append({"role": "user", "content": question})

    # ---- 真正的"生成"发生在这里，程序向外部发出一次 HTTP 请求 ----
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=messages,
    )
    answer = response.choices[0].message.content or ""
    used_tokens = response.usage.total_tokens if response.usage else 0

    # ---- 写回存储：一问一答都存下来 ----
    storage.save_message(session_id, "user", question)
    storage.save_message(session_id, "assistant", answer)

    return answer, used_tokens