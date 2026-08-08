#!/usr/bin/env python3
"""
最简启动方式：不需要Docker、不需要单独装数据库。

用法：
    python run.py

启动后浏览器打开 http://127.0.0.1:8000 即可看到Dashboard。
数据默认存在项目目录下的 b2b_leads.db 文件里（SQLite），删掉这个文件就等于清空所有数据重新开始。

首次运行前记得先：
    1. pip install -r requirements.txt
    2. cp .env.example .env   然后编辑 .env 填入 SERPAPI_KEY 和 ANTHROPIC_API_KEY
"""
import os
import sys
import webbrowser
from threading import Timer

import uvicorn


def check_env_file():
    if not os.path.exists(".env"):
        print("⚠️  没有找到 .env 文件。")
        print("   请先执行: cp .env.example .env")
        print("   然后编辑 .env，填入 SERPAPI_KEY 和 ANTHROPIC_API_KEY，否则搜索/AI分析功能无法使用。")
        print("   （现在会继续启动，你可以先看看Dashboard界面，功能测试需要先配置好密钥）\n")


def open_browser():
    webbrowser.open("http://127.0.0.1:8000")


if __name__ == "__main__":
    check_env_file()

    # 延迟1.5秒自动打开浏览器，给服务器一点启动时间
    Timer(1.5, open_browser).start()

    print("=" * 50)
    print("跨境B2B客户增长系统 启动中...")
    print("Dashboard: http://127.0.0.1:8000")
    print("按 Ctrl+C 停止服务")
    print("=" * 50)

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
