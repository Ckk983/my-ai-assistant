"""入口层：程序从这里开始运行。

数据流（一次带知识库的提问）：

    网页 ──HTTP请求(JSON)──► main.py
                              │ ① 校验参数（models/schemas.py）
                              │ ② 业务处理（services/llm.py）
                              │      ├─► retriever.py 检索资料 ← RAG 新增
                              │      ├─► storage.py 读最近 6 轮历史
                              │      ├─► 调用大模型 API（资料 + 历史 + 问题）
                              │      └─► storage.py 写回这轮问答
                              │ ③ 返回 HTTP响应(JSON)
    网页 ◄────────────────────┘

额外提供了两个"观察检索过程"的接口（/knowledge、/search），
用来理解 RAG 到底检索到了什么，面试演示时很好用。
"""
from fastapi import FastAPI, HTTPException

from app.config import settings
from app.models.schemas import ChatRequest, ChatResponse, MessageOut, SearchHit
from app.services import llm, retriever, storage

app = FastAPI(
    title="我的 AI 助手",
    description="边做边学用的 AI 应用：对话 + 多轮记忆 + 本地存储 + RAG 知识库检索",
    version="0.2.0",
)


@app.get("/")
def health():
    """健康检查：确认服务活着、密钥配好没、知识库加载了没。"""
    chunks = retriever.load_chunks()
    return {
        "status": "ok",
        "model": settings.LLM_MODEL,
        "llm_ready": settings.llm_ready,
        "knowledge_chunks": len(chunks),
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """核心接口：问一句，答一句。use_rag=true 时先检索知识库。"""
    if not settings.llm_ready:
        raise HTTPException(
            status_code=500,
            detail=(
                "还没有配置密钥。请打开项目根目录的 .env 文件，"
                "把 LLM_API_KEY 换成你在模型平台申请到的真实 Key。"
            ),
        )

    try:
        answer, used_tokens, sources = llm.ask(req.question, req.session_id, use_rag=req.use_rag)
    except Exception as exc:  # noqa: BLE001 - 这里就是要兜住所有外部异常
        raise HTTPException(
            status_code=502,
            detail=f"调用大模型失败（{type(exc).__name__}）：{exc}",
        ) from exc

    return ChatResponse(
        answer=answer,
        session_id=req.session_id,
        used_tokens=used_tokens,
        sources=sources,
    )


@app.get("/history/{session_id}", response_model=list[MessageOut])
def get_history(session_id: str, limit: int = 50):
    """查某个会话的历史记录。"""
    return storage.get_history(session_id, limit=limit)


@app.get("/sessions", response_model=list[str])
def sessions():
    """列出所有会话ID。"""
    return storage.list_sessions()


# ---------------- 下面是"观察 RAG"用的辅助接口 ----------------

@app.get("/knowledge")
def knowledge_info():
    """看看知识库里有哪些文件、一共切成了多少块。"""
    chunks = retriever.load_chunks()
    files = sorted({c["source"] for c in chunks})
    return {"files": files, "file_count": len(files), "chunk_count": len(chunks)}


@app.post("/knowledge/reload")
def knowledge_reload():
    """改了 data/knowledge 里的文档后，调用它重建索引。"""
    return {"chunk_count": retriever.reload_index()}


@app.get("/search", response_model=list[SearchHit])
def search_knowledge(q: str, top_k: int = 3):
    """只做检索、不调模型 —— 用来单独观察"检索"这一步干了什么。"""
    hits = retriever.search(q, top_k)
    return [
        SearchHit(
            source=h["source"],
            chunk_id=h["chunk_id"],
            score=h["score"],
            preview=h["text"][:80].replace("\n", " ") + ("…" if len(h["text"]) > 80 else ""),
        )
        for h in hits
    ]