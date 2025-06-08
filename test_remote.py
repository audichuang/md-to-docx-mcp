#!/usr/bin/env python3
"""
測試 MD to DOCX Remote MCP Server
"""
import asyncio
import sys
from md_to_docx_mcp.remote_server import run_remote_server

def test_remote():
    print("測試 MD to DOCX Remote MCP Server...")
    print("=" * 60)
    print("🔐 OAuth 設定：")
    print("   使用者名稱：admin")
    print("   密碼：test123456")
    print("=" * 60)
    print("\n按下 Ctrl+C 停止伺服器\n")
    
    try:
        # 啟動伺服器
        run_remote_server(host="127.0.0.1", port=8001)
    except KeyboardInterrupt:
        print("\n\n伺服器已停止")
        sys.exit(0)

if __name__ == "__main__":
    test_remote()