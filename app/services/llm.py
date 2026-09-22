"""模型层：负责"借用别人的 AI 能力"。

数据流位置（现在多了 RAG 分支）：
    main.py
      └─► ask(question, session_id, use_rag)
            ├─ [use_rag=False] 直接把历史 + 问题发给模型
            └─ [use_rag=True ] ① 先让 retriever 检索出相关资料
                               ② 把资料拼进系统提示词（这叫"增强"）
                               ③ 再发给模型，让它照着资料回答
"""
from openai import OpenAI

from app.config import settings
from app.services import retriever, storage

client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

# 系统提示词：告诉 AI 它是谁、要怎么回答。
SYSTEM_PROMPT = (
    "你是一个严谨的助手。回答简洁、准确，用中文回答。"
    "如果不确定，就直说不确定，不要编造。"
)

# RAG 模式下的额外要求。★ 这段是 RAG 效果的关键 ★
# 如果不说清"只依据资料、没有就说没有"，模型会习惯性地用自己的通用知识补充，
# 那就白做检索了 —— 这个现象叫"不遵循上下文"。
RAG_INSTRUCTION = (
    "\n\n下面会给你若干段【参考资料】。请严格遵守：\n"
    "1. 只依据参考资料回答，不要使用你自己的其他知识；\n"
    "2. 如果参考资料里没有相关信息，就直接回答「资料中没有提到」，绝对不要编造；\n"
    "3. 不要照抄资料原文，用简洁的中文总结成通顺的回答。"
)


def ask(question: str, session_id: str, use_rag: bool = False) -> tuple[str, int, list[str]]:
    """问 AI 一个问题。

    返回 (回答, 消耗的token数, 引用的资料文件名)。
    """
    history = storage.get_history(session_id)
    sources: list[str] = []
    system_prompt = SYSTEM_PROMPT

    # ---- ① 检索 + ② 增强（这一步就是 RAG 的 R 和 A）----
    if use_rag:
        context, sources = retriever.retrieve_context(question)
        if context:
            system_prompt = SYSTEM_PROMPT + RAG_INSTRUCTION + "\n\n【参考资料开始】\n" + context + "\n【参考资料结束】"
        else:
            system_prompt = SYSTEM_PROMPT + "\n\n（知识库里没有检索到相关资料，请据实说明你无法从资料中找到答案。）"

    messages = [{"role": "system", "content": system_prompt}]
    messages += history                                  # 前几轮对话 → 多轮对话
    messages.append({"role": "user", "content": question})

    # ---- ③ 生成：真正的"调用大模型"发生在这里 ----
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=messages,
    )
    answer = response.choices[0].message.content or ""
    used_tokens = response.usage.total_tokens if response.usage else 0

    # ---- 写回存储：一问一答都存下来 ----
    storage.save_message(session_id, "user", question)
    storage.save_message(session_id, "assistant", answer)

    return answer, used_tokens, sources