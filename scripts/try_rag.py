"""RAG 效果对比演示：同一个问题，问两次。

    第 1 次：不开启知识库 → 模型只能靠自己的通用知识，答不出你项目的细节
    第 2 次：开启知识库（RAG） → 模型照着资料回答，并给出引用来源

还会先展示"检索"这一步单独找到了什么。用法：
    .venv\Scripts\python.exe scripts\try_rag.py
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"
QUESTION = "这个项目的密钥写在哪个文件里？变量名叫什么？"


def ask(question: str, use_rag: bool) -> dict:
    payload = json.dumps(
        {"session_id": "rag-demo", "question": question, "use_rag": use_rag},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def search(q: str, top_k: int = 3) -> list:
    url = f"{BASE_URL}/search?q={urllib.parse.quote(q)}&top_k={top_k}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def line(ch="=", n=64):
    print(ch * n)


def main() -> None:
    line()
    print("问题：" + QUESTION)
    line()

    # ---- 第 0 步：只看检索，不调模型 ----
    print()
    print("【第 0 步】单独看「检索」找到了什么（这一步完全不调用大模型）")
    hits = search(QUESTION, top_k=3)
    if not hits:
        print("  没检索到任何内容 —— 检查 data/knowledge 里有没有文档")
    for i, h in enumerate(hits, 1):
        print(f"  {i}. 来源={h['source']}  分数={h['score']}")
        print(f"     {h['preview']}")

    # ---- 第 1 次：不用知识库 ----
    print()
    line("-")
    print("【第 1 次】不使用知识库（模型只能靠自己的通用知识）")
    line("-")
    r1 = ask(QUESTION, use_rag=False)
    print("AI：" + r1["answer"])
    print(f"（消耗 {r1['used_tokens']} tokens）")

    # ---- 第 2 次：使用知识库 ----
    print()
    line("-")
    print("【第 2 次】使用知识库检索（RAG）")
    line("-")
    r2 = ask(QUESTION, use_rag=True)
    print("AI：" + r2["answer"])
    print(f"（消耗 {r2['used_tokens']} tokens）")
    if r2.get("sources"):
        print("引用资料：" + "、".join(r2["sources"]))

    print()
    line()
    print("对比一下这两次回答：第 2 次的内容应该来自你的文档，而不是模型瞎猜。")
    print("这就是 RAG 的价值 —— 让模型回答「它原本不可能知道」的东西。")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"服务返回错误（HTTP {e.code}）：")
        try:
            print("  " + json.loads(body)["detail"])
        except Exception:
            print("  " + body)
    except urllib.error.URLError as e:
        print("连不上本机服务，请确认服务已经启动：")
        print("  .venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --port 8000")
        print(f"（原始错误：{e}）")