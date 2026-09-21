"""配置层：负责从 .env（本地文件）读取密钥和参数。

数据流位置：整个项目的"起点"，所有模块都从这里拿配置。

为什么密钥不直接写在代码里？
    因为代码要上传到 GitHub。Key 写进代码 = 全世界都能看到 = 被盗刷。
    所以密钥放在 .env（不上传），代码只从环境变量里读。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# .env 里还是这个值，说明用户还没换成自己真实的 Key
PLACEHOLDER_KEY = "在这里粘贴你的key"


class Settings:
    # ---- 大模型相关（从 .env 读）----
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-chat")

    # ---- 目录（本地文件存储）----
    DATA_DIR: Path = BASE_DIR / "data"
    LOG_DIR: Path = BASE_DIR / "logs"

    @property
    def llm_ready(self) -> bool:
        """密钥是否真的配好了。

        注意：这里要同时判"空值"和"还是占位符"两种情况。
        （踩过的坑：只判空值的话，占位符会被当成有效Key，
          程序会带着假Key去调API，用户看到的是难懂的 Internal Server Error。）
        """
        key = self.LLM_API_KEY.strip()
        return bool(key) and key != PLACEHOLDER_KEY


settings = Settings()