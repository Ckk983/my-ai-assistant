"""数据库连接层（占位，第二版才用）。

现在数据存在 data/history.json（本地文件），还不涉及数据库。

什么时候要用到这个文件？
    1. 要多人同时写、要事务保证 → 换 MySQL
    2. 要按条件查询、做统计 → SQL 比"读整个文件再筛"高效得多
    3. 会话上下文要极快读写、且可以过期 → 加 Redis

换的时候怎么做？（面试必答的"分层"价值）
    只改 services/storage.py 里的函数实现，
    main.py 和 llm.py 一行都不用改。
"""
# 第二版示例（现在不要打开，装好 MySQL 再用）：
#
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
#
# DATABASE_URL = "mysql+pymysql://用户名:密码@localhost:3306/ai_assistant"
# engine = create_engine(DATABASE_URL, pool_pre_ping=True)
# SessionLocal = sessionmaker(bind=engine)