"""入口层：程序从这里开始运行。

数据流（从上到下就是一次请求的完整旅程）：

    网页  ──HTTP请求(JSON)──►  main.py
                                │ ① 校验参数（schemas.py 负责）
                                │ ② 交给 services/llm.py 处理
                                │       └─► storage.py 读历史
                                │       └─► 调大模型 API
                                │       └─► storage.py 写回记录
                                │ ③ 返回 HTTP响应(JSON)
    网页  ◄────────────────────┘

职责划分（面试会问"你的代码怎么分层"）：
    main.py         只管"接收请求、返回结果"，不写业务逻辑
    services/       业务逻辑：调模型、存取数据
    models/         数据结构定义
    config.py       读配置
这样换数据库或换模型时，只改一个文件，其他都不用动。
"""
from fastapi import FastAPI, HTTPException

from app.config import settings
from app.models.schemas import ChatRequest, ChatResponse, MessageOut
from app.services import llm, storage

app = FastAPI(
    title="我的 AI 助手",
    description="一个边做边学用的最小可运行项目：对话 + 多轮记忆 + 本地存储",
    version="0.1.1",
)


@app.get("/")
def health():
    """健康检查：确认服务活着。部署到服务器后，第一件事就是访问这个接口。"""
    return {
        "status": "ok",
        "model": settings.LLM_MODEL,
        "llm_ready": settings.llm_ready,  # 一眼看出密钥配好了没
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """核心接口：问一句，答一句。"""
    # ① 配置检查：给出明确提示，而不是抛一堆看不懂的异常
    if not settings.llm_ready:
        raise HTTPException(
            status_code=500,
            detail=(
                "还没有配置密钥。请打开项目根目录的 .env 文件，"
                "把 LLM_API_KEY 换成你在模型平台申请到的真实 Key。"
            ),
        )

    # ② 调用外部服务要包异常：网络抖动、Key 失效、余额不足都可能发生。
    #    把技术异常翻译成人话，方便自己排查，也避免把调用栈暴露给用户。
    try:
        answer, used_tokens = llm.ask(req.question, req.session_id)
    except Exception as exc:  # noqa: BLE001 - 这里就是要兜住所有外部异常
        raise HTTPException(
            status_code=502,
            detail=f"调用大模型失败（{type(exc).__name__}）：{exc}",
        ) from exc

    return ChatResponse(answer=answer, session_id=req.session_id, used_tokens=used_tokens)


@app.get("/history/{session_id}", response_model=list[MessageOut])
def get_history(session_id: str, limit: int = 50):
    """查某个会话的历史记录。"""
    return storage.get_history(session_id, limit=limit)


@app.get("/sessions", response_model=list[str])
def sessions():
    """列出所有会话ID。"""
    return storage.list_sessions()