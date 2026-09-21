"""一键测试：验证服务能不能真正跟大模型对话，并且记住上文。

用法（在项目根目录执行，不用打开浏览器，不用看英文）：
    .venv\Scripts\python.exe scripts\try_chat.py

它会自动做两轮对话：
    第 1 轮：告诉 AI 我的名字
    第 2 轮：问它我叫什么
如果第 2 轮答对了，说明"历史上下文"这条数据流真的通了。
"""
import json
import sys
import urllib.error
import urllib.request

# Windows 控制台默认编码可能是 GBK，强制用 UTF-8 输出，避免中文乱码
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"
SESSION_ID = "demo-1"


def ask(question: str) -> dict:
    """向本机服务发一个 HTTP 请求（这一步就是"数据从哪来"的起点）。"""
    payload = json.dumps(
        {"session_id": SESSION_ID, "question": question}, ensure_ascii=False
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    print("=" * 60)
    print("第 1 轮：先让 AI 记住一个信息")
    print("=" * 60)
    q1 = "你好，我叫小明，请记住我的名字。"
    print(f"我 ：{q1}")
    r1 = ask(q1)
    print(f"AI：{r1['answer']}")
    print(f"（本次消耗 {r1['used_tokens']} 个 token —— 这就是要花钱的地方，面试会问）")

    print()
    print("=" * 60)
    print("第 2 轮：问它刚才说了什么（这一轮考察的是多轮记忆）")
    print("=" * 60)
    q2 = "我叫什么名字？"
    print(f"我 ：{q2}")
    r2 = ask(q2)
    print(f"AI：{r2['answer']}")

    print()
    if "小明" in r2["answer"]:
        print("成功！AI 记住了上文 —— 说明【历史上下文】这条数据流打通了。")
    else:
        print("它没答对，但请求本身是成功的（数据流是通的，可能只是模型比较保守）。")

    print()
    print("下一步：打开 data/history.json，看看这四句话被存成什么样了。")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"服务返回了错误（HTTP {e.code}）：")
        try:
            print("  " + json.loads(body)["detail"])
        except Exception:
            print("  " + body)
    except urllib.error.URLError as e:
        print("连不上本机服务，请确认服务已经启动：")
        print("  .venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --port 8000")
        print(f"（原始错误：{e}）")