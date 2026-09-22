"""检索层：RAG 里的"检索"这一步。

RAG = Retrieval Augmented Generation（检索增强生成）。人话：**考试开卷**。
    1. 把你的资料切成小块（chunking）存起来
    2. 用户提问时，先检索出最相关的几块
    3. 把这几块连同问题一起交给大模型，让它"照着资料回答"

数据流位置：
    main.py ──► llm.py ──► 【retriever.py 检索资料】
                       └─► 把资料拼进提示词 → 调大模型

★ 为什么第一版用关键词（n-gram）检索，而不是向量检索？★
    1. 零新增依赖、零额外 API Key，当天就能把整条链路跑通
    2. 先理解"检索 → 增强 → 生成"这条数据流，检索器只是可替换的零件
    3. 换向量检索时，只改这一个文件（和存储层一个道理），还能对比召回率
向量检索的区别：把文字变成"语义坐标"(embedding)，能匹配"意思相近但用词不同"的内容，
例如"密钥放哪" 和 "凭证文件位置" —— 关键词检索匹配不上，向量检索可以。
"""
import math
from pathlib import Path

from app.config import settings

KNOWLEDGE_DIR = settings.DATA_DIR / "knowledge"
SUPPORTED_SUFFIXES = (".md", ".txt")

CHUNK_SIZE = 300     # 每块多少字
CHUNK_OVERLAP = 50   # 相邻块重叠多少字
TOP_K = 3            # 每次检索取几块

# 索引缓存：文档没变就不用重复算（真实项目会把索引离线建好；这里数据小，先内存缓存）
_cache = {"chunks": None, "grams": None, "df": None, "total": 0}


# ---------------------------------------------------------------- 切块

def split_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """把长文本切成小块，相邻块留一点重叠。

    为什么要有重叠？
        否则一句关键的话可能刚好被切成两半，两边都不完整，检索时就漏掉了。
    说明：真实项目更常用"按标题/段落切"（语义切块），效果更好。
         这里先用最简单的定长切，等你理解了流程再升级。
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    pieces = []
    step = max(1, size - overlap)
    start = 0
    while start < len(text):
        pieces.append(text[start:start + size])
        if start + size >= len(text):
            break
        start += step
    return pieces


def load_chunks() -> list[dict]:
    """把 data/knowledge 下的所有文档读进来，切成块。

    返回形如：[{"source": "文件.md", "chunk_id": 0, "text": "..."}]
    """
    chunks: list[dict] = []
    if not KNOWLEDGE_DIR.exists():
        return chunks
    for path in sorted(KNOWLEDGE_DIR.iterdir()):
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue          # 先只支持 .md / .txt；PDF 要先做解析，属于下一步
        text = path.read_text(encoding="utf-8")
        for i, piece in enumerate(split_text(text)):
            chunks.append({"source": path.name, "chunk_id": i, "text": piece})
    return chunks


# ---------------------------------------------------------------- 打分

def _ngrams(text: str, n: int = 2) -> set[str]:
    """把文字切成 n-gram 集合（这里 n=2，即字符二元组）。

    为什么需要它？中文没有空格，检索前得先"切词"。
    例："周三有什么课" → {"周三","三有","有什","什么","么课"}
    好处：零依赖、对中文够用。
    坏处：只能匹配"字面相同"的内容 —— 这正是后面要换向量检索的原因。
    """
    cleaned = "".join(ch.lower() for ch in text if not ch.isspace())
    if not cleaned:
        return set()
    if len(cleaned) < n:
        return {cleaned}
    return {cleaned[i:i + n] for i in range(len(cleaned) - n + 1)}


def _build_index(chunks: list[dict]) -> tuple[list[set[str]], dict[str, int]]:
    """建立索引：记录每个 n-gram 出现在多少个块里（用于算 IDF）。"""
    df: dict[str, int] = {}
    chunk_grams: list[set[str]] = []
    for chunk in chunks:
        grams = _ngrams(chunk["text"])
        chunk_grams.append(grams)
        for g in grams:
            df[g] = df.get(g, 0) + 1
    return chunk_grams, df


def reload_index() -> int:
    """重新读取知识库并重建索引。改了 data/knowledge 里的文件后调用它。"""
    chunks = load_chunks()
    grams, df = _build_index(chunks)
    _cache.update(chunks=chunks, grams=grams, df=df, total=len(chunks))
    return len(chunks)


def reset_index() -> None:
    """清空索引缓存（测试用）。"""
    _cache.update(chunks=None, grams=None, df=None, total=0)


def _ensure_index() -> None:
    if _cache["chunks"] is None:
        reload_index()


def search(query: str, top_k: int = TOP_K) -> list[dict]:
    """检索：给一个问题，返回最相关的 top_k 块（带分数）。"""
    _ensure_index()
    chunks = _cache["chunks"] or []
    if not chunks:
        return []

    q_grams = _ngrams(query)
    if not q_grams:
        return []

    grams_list = _cache["grams"]
    df = _cache["df"]
    total = _cache["total"]

    scored = []
    for idx, chunk in enumerate(chunks):
        hit = q_grams & grams_list[idx]
        if not hit:
            continue
        # IDF（逆文档频率）：越少见的词越有区分度。
        # "的""了"这种到处都是的词权重会很低，专属名词权重高。
        score = sum(math.log((total + 1) / (df[g] + 1)) + 1 for g in hit)
        scored.append({**chunk, "score": round(score, 3)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def retrieve_context(query: str, top_k: int = TOP_K) -> tuple[str, list[str]]:
    """检索并拼成给大模型看的资料文本。

    返回 (资料文本, 引用的来源文件列表)。
    资料文本为空 = 知识库里没有相关内容 → 上层要告诉模型"据实说明，别编造"。
    """
    hits = search(query, top_k)
    if not hits:
        return "", []
    parts = [
        "【资料{0}｜来源：{1}】\n{2}".format(i, h["source"], h["text"])
        for i, h in enumerate(hits, 1)
    ]
    return "\n\n".join(parts), [h["source"] for h in hits]