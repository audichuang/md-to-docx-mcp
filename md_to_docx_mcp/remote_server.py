import asyncio
import os
import json
import logging
import time
import secrets
import urllib.parse
import base64
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP
import pypandoc

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv()

# OAuth 設定
OAUTH_USERNAME = os.getenv("OAUTH_USERNAME", "admin")
OAUTH_PASSWORD = os.getenv("OAUTH_PASSWORD", "md-to-docx-mcp-password")

# 如果使用預設密碼，記錄警告
if OAUTH_PASSWORD == "md-to-docx-mcp-password":
    logger.warning("⚠️  使用預設密碼！請設定 OAUTH_PASSWORD 環境變數以增強安全性。")

# 記憶體中儲存 OAuth 資料
auth_codes = {}  # code -> {client_id, redirect_uri, expires_at, username}
access_tokens = {}  # token -> {username, expires_at, scope}

# 儲存生成的檔案（暫時存在記憶體中，生產環境應使用資料庫或物件儲存）
generated_files = {}  # file_id -> {filename, content, created_at, expires_at}

# 建立 FastMCP 伺服器
mcp = FastMCP("md-to-docx-remote")

def convert_md_to_docx_pandoc(markdown_text: str, filename: str = "document.docx") -> dict:
    """使用 pypandoc (Pandoc Python 包裝器) 將 Markdown 轉換為 DOCX"""
    
    # 建立暫存檔案
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp_md:
        tmp_md.write(markdown_text)
        tmp_md_path = tmp_md.name
    
    tmp_docx_path = tempfile.mktemp(suffix='.docx')
    
    try:
        # 使用 pypandoc 進行轉換，附加增強選項
        pypandoc.convert_file(
            tmp_md_path,
            'docx',
            outputfile=tmp_docx_path,
            extra_args=[
                '--standalone',
                '--highlight-style', 'tango',  # 程式碼高亮
                '--wrap', 'preserve',  # 保留換行
                '--resource-path', '.',  # 處理相對路徑
            ]
        )
        
        # 讀取生成的 docx 檔案
        with open(tmp_docx_path, 'rb') as f:
            docx_content = f.read()
        
        # 編碼為 base64
        base64_content = base64.b64encode(docx_content).decode('utf-8')
        
        return {
            "filename": filename,
            "base64_content": base64_content,
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }
        
    finally:
        # 清理暫存檔案
        if os.path.exists(tmp_md_path):
            os.unlink(tmp_md_path)
        if os.path.exists(tmp_docx_path):
            os.unlink(tmp_docx_path)

# MCP 工具定義
@mcp.tool()
async def convert_md_to_docx(
    markdown_text: str,
    filename: str = "document.docx",
    title: str = None,
    author: str = None,
    include_toc: bool = False
) -> str:
    """
    將 Markdown 文字轉換為 DOCX 格式並返回 base64 編碼。
    
    Args:
        markdown_text: 要轉換的 Markdown 文字
        filename: 期望的檔案名稱（預設：document.docx）
        title: 文件標題（選用）
        author: 文件作者（選用）
        include_toc: 是否包含目錄（預設：false）
    
    Returns:
        包含檔案名稱、MIME 類型和 base64 內容的格式化字串
    """
    if not filename.endswith('.docx'):
        filename += '.docx'
    
    # 如果提供了元數據，則添加到 markdown
    if title or author:
        metadata = "---\n"
        if title:
            metadata += f"title: {title}\n"
        if author:
            metadata += f"author: {author}\n"
        metadata += "---\n\n"
        markdown_text = metadata + markdown_text
    
    try:
        # 建立暫存檔案進行增強轉換
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp_md:
            tmp_md.write(markdown_text)
            tmp_md_path = tmp_md.name
        
        tmp_docx_path = tempfile.mktemp(suffix='.docx')
        
        # 建立額外參數
        extra_args = [
            '--standalone',
            '--highlight-style', 'tango',
            '--wrap', 'preserve',
            '--resource-path', '.',
        ]
        
        if include_toc:
            extra_args.append('--toc')
        
        # 使用 pypandoc 進行轉換
        pypandoc.convert_file(
            tmp_md_path,
            'docx',
            outputfile=tmp_docx_path,
            extra_args=extra_args
        )
        
        # 讀取檔案內容
        with open(tmp_docx_path, 'rb') as f:
            docx_content = f.read()
        
        # 生成唯一檔案 ID
        file_id = str(uuid.uuid4())
        
        # 儲存檔案資訊（30分鐘後過期）
        generated_files[file_id] = {
            'filename': filename,
            'content': docx_content,
            'created_at': time.time(),
            'expires_at': time.time() + 1800,  # 30 分鐘
            'size': len(docx_content)
        }
        
        # 清理暫存檔案
        os.unlink(tmp_md_path)
        os.unlink(tmp_docx_path)
        
        # 清理過期檔案
        cleanup_expired_files()
        
        # 取得伺服器 URL（從環境變數或使用預設值）
        server_url = os.getenv('SERVER_URL', 'http://localhost:8000')
        
        # 計算檔案大小（KB）
        file_size_kb = len(docx_content) / 1024
        
        # 簡潔的輸出格式，直接提供下載連結
        return f"""✅ 成功將 Markdown 轉換為 DOCX！

📄 檔案資訊：
- 檔案名稱：{filename}
- 檔案大小：{file_size_kb:.1f} KB
- 功能：{'目錄、' if include_toc else ''}程式碼高亮、增強格式

🔗 下載連結：
{server_url}/download/{file_id}

⏰ 有效期限：30 分鐘

💡 使用方式：點擊上方連結直接下載 .docx 檔案"""
    
    except Exception as e:
        logger.error(f"轉換 Markdown 到 DOCX 時發生錯誤：{e}")
        return f"轉換 Markdown 到 DOCX 時發生錯誤：{str(e)}"

@mcp.tool()
async def get_server_info() -> str:
    """
    取得伺服器資訊。
    
    Returns:
        伺服器名稱、版本和支援功能的資訊
    """
    return """MD to DOCX MCP Remote Server
版本：1.0.0

支援功能：
- Markdown 轉 DOCX（使用 Pandoc）
- 語法高亮
- 數學公式
- 目錄生成
- 元數據支援（標題、作者）
- Base64 編碼輸出

使用 pypandoc（Pandoc 的 Python 包裝器）進行高品質文件轉換。"""

# HTML 登入頁面模板
LOGIN_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MD to DOCX MCP - 授權</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f5f5f5;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08);
            max-width: 400px;
            width: 100%;
            padding: 40px;
        }}
        
        .logo {{
            text-align: center;
            margin-bottom: 30px;
        }}
        
        .logo h1 {{
            color: #333;
            font-size: 24px;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }}
        
        .logo .icon {{
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 18px;
        }}
        
        .auth-info {{
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 24px;
        }}
        
        .auth-info h2 {{
            font-size: 16px;
            color: #333;
            margin-bottom: 8px;
            font-weight: 500;
        }}
        
        .auth-info .client-name {{
            font-weight: 600;
            color: #007bff;
        }}
        
        .auth-info .redirect-url {{
            font-size: 12px;
            color: #6c757d;
            word-break: break-all;
            margin-top: 4px;
        }}
        
        .form-group {{
            margin-bottom: 20px;
        }}
        
        label {{
            display: block;
            margin-bottom: 8px;
            color: #495057;
            font-size: 14px;
            font-weight: 500;
        }}
        
        input[type="text"],
        input[type="password"] {{
            width: 100%;
            padding: 10px 14px;
            border: 1px solid #ced4da;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
        }}
        
        input[type="text"]:focus,
        input[type="password"]:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        
        .button-group {{
            display: flex;
            gap: 12px;
            margin-top: 24px;
        }}
        
        button {{
            flex: 1;
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.15s ease-in-out;
        }}
        
        .btn-cancel {{
            background-color: #e9ecef;
            color: #495057;
        }}
        
        .btn-cancel:hover {{
            background-color: #dee2e6;
        }}
        
        .btn-approve {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        .btn-approve:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }}
        
        .error-message {{
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        
        .hidden {{
            display: none;
        }}
        
        @media (max-width: 480px) {{
            .container {{
                padding: 30px 20px;
            }}
            
            .logo h1 {{
                font-size: 20px;
            }}
            
            .button-group {{
                flex-direction: column;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <h1>
                <span class="icon">📄</span>
                MD to DOCX MCP
            </h1>
        </div>
        
        <div class="auth-info">
            <h2><span class="client-name">{client_name}</span> 正在請求存取權限</h2>
            <div class="redirect-url">重新導向：{redirect_url}</div>
        </div>
        
        <div id="error-message" class="error-message {error_class}">
            {error_message}
        </div>
        
        <form method="POST" action="{form_action}">
            <div class="form-group">
                <label for="username">使用者名稱</label>
                <input type="text" id="username" name="username" required autofocus>
            </div>
            
            <div class="form-group">
                <label for="password">密碼</label>
                <input type="password" id="password" name="password" required>
            </div>
            
            <input type="hidden" name="client_id" value="{client_id}">
            <input type="hidden" name="redirect_uri" value="{redirect_uri}">
            <input type="hidden" name="response_type" value="{response_type}">
            <input type="hidden" name="state" value="{state}">
            <input type="hidden" name="scope" value="{scope}">
            
            <div class="button-group">
                <button type="button" class="btn-cancel" onclick="handleCancel()">取消</button>
                <button type="submit" class="btn-approve">核准</button>
            </div>
        </form>
    </div>
    
    <script>
        function handleCancel() {{
            // 重新導向並帶錯誤訊息
            const params = new URLSearchParams(window.location.search);
            const redirectUri = params.get('redirect_uri');
            const state = params.get('state');
            
            if (redirectUri) {{
                const separator = redirectUri.includes('?') ? '&' : '?';
                window.location.href = redirectUri + separator + 'error=access_denied' + (state ? '&state=' + state : '');
            }}
        }}
    </script>
</body>
</html>
"""

def cleanup_expired_files():
    """清理過期的檔案"""
    current_time = time.time()
    expired_ids = [file_id for file_id, data in generated_files.items() if data['expires_at'] < current_time]
    for file_id in expired_ids:
        del generated_files[file_id]
        logger.info(f"清理過期檔案：{file_id}")

def cleanup_expired_tokens():
    """移除過期的授權碼和存取權杖。"""
    current_time = time.time()
    
    # 清理授權碼
    expired_codes = [code for code, data in auth_codes.items() if data['expires_at'] < current_time]
    for code in expired_codes:
        del auth_codes[code]
    
    # 清理存取權杖
    expired_tokens = [token for token, data in access_tokens.items() if data['expires_at'] < current_time]
    for token in expired_tokens:
        del access_tokens[token]

def run_remote_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    log_level: str = "info"
):
    """執行支援 SSE 和 OAuth 認證的遠端伺服器。"""
    logger.info(f"啟動 MD to DOCX MCP Remote Server（含 OAuth）於 {host}:{port}")
    logger.info("=" * 60)
    logger.info("🔐 OAuth 認證資訊：")
    logger.info(f"   使用者名稱：{OAUTH_USERNAME}")
    logger.info(f"   密碼：{OAUTH_PASSWORD}")
    logger.info("=" * 60)
    
    # 使用 FastMCP 內建方法執行伺服器與 SSE 傳輸
    # 設定 uvicorn 的環境變數
    import os
    os.environ["HOST"] = host
    os.environ["PORT"] = str(port)
    
    # 使用 sse_app 方法取得 ASGI 應用程式
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route
    from starlette.responses import PlainTextResponse
    from starlette.middleware import Middleware
    
    # 建立含 OAuth 認證的自訂 ASGI 應用程式
    mcp_app = mcp.sse_app()
    base_url = f"http://{host}:{port}"
    
    async def oauth_app(scope, receive, send):
        """處理 OAuth 認證的 ASGI 應用程式"""
        if scope["type"] == "http":
            path = scope["path"]
            headers = dict(scope.get("headers", []))
            
            # 解析查詢參數
            query_string = scope.get("query_string", b"").decode("utf-8")
            query_params = urllib.parse.parse_qs(query_string)
            
            # 處理檔案下載
            if path.startswith("/download/"):
                file_id = path.split("/download/")[1]
                
                # 清理過期檔案
                cleanup_expired_files()
                
                # 檢查檔案是否存在
                if file_id in generated_files:
                    file_data = generated_files[file_id]
                    
                    # 準備回應
                    await send({
                        'type': 'http.response.start',
                        'status': 200,
                        'headers': [
                            (b'content-type', b'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
                            (b'content-disposition', f'attachment; filename="{file_data["filename"]}"'.encode()),
                            (b'cache-control', b'no-cache'),
                            (b'content-length', str(file_data['size']).encode()),
                        ],
                    })
                    await send({
                        'type': 'http.response.body',
                        'body': file_data['content'],
                    })
                else:
                    # 檔案不存在或已過期
                    error_html = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>檔案不存在</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background-color: #f5f5f5;
        }
        .error-container {
            text-align: center;
            padding: 40px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        h1 { color: #dc3545; }
        p { color: #6c757d; }
    </style>
</head>
<body>
    <div class="error-container">
        <h1>❌ 檔案不存在</h1>
        <p>檔案可能已過期或不存在。</p>
        <p>檔案有效期限為 30 分鐘。</p>
    </div>
</body>
</html>"""
                    await send({
                        'type': 'http.response.start',
                        'status': 404,
                        'headers': [
                            (b'content-type', b'text/html; charset=utf-8'),
                        ],
                    })
                    await send({
                        'type': 'http.response.body',
                        'body': error_html.encode('utf-8'),
                    })
                return
            
            # 處理 OAuth 發現端點
            if path == "/.well-known/oauth-authorization-server":
                # 從請求標頭中提取實際主機
                host_header = headers.get(b'host', b'').decode('utf-8')
                
                # 檢查 X-Forwarded-Proto 標頭（用於反向代理情況）
                proto_header = headers.get(b'x-forwarded-proto', b'').decode('utf-8')
                protocol = proto_header if proto_header else 'https' if host_header and ':443' in host_header else 'http'
                
                # 根據請求建構實際的發行者 URL
                if host_header:
                    issuer_url = f"{protocol}://{host_header}"
                else:
                    # 如果沒有主機標頭，則回退到 base_url
                    issuer_url = base_url
                
                discovery = {
                    "issuer": issuer_url,
                    "authorization_endpoint": f"{issuer_url}/oauth/authorize",
                    "token_endpoint": f"{issuer_url}/oauth/token",
                    "registration_endpoint": f"{issuer_url}/oauth/register",
                    "scopes_supported": ["mcp"],
                    "response_types_supported": ["code"],
                    "response_modes_supported": ["query"],
                    "grant_types_supported": ["authorization_code", "refresh_token"],
                    "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post", "none"],
                    "revocation_endpoint": f"{issuer_url}/oauth/token",
                    "code_challenge_methods_supported": ["plain", "S256"]
                }
                
                response_body = json.dumps(discovery).encode()
                await send({
                    'type': 'http.response.start',
                    'status': 200,
                    'headers': [
                        (b'content-type', b'application/json'),
                        (b'access-control-allow-origin', b'*'),
                        (b'cache-control', b'max-age=3600'),
                    ],
                })
                await send({
                    'type': 'http.response.body',
                    'body': response_body,
                })
                return
            
            # 處理 OAuth 授權端點 (GET)
            if path == "/oauth/authorize" and scope["method"] == "GET":
                # 提取參數
                client_id = query_params.get('client_id', [''])[0]
                redirect_uri = query_params.get('redirect_uri', [''])[0]
                response_type = query_params.get('response_type', [''])[0]
                state = query_params.get('state', [''])[0]
                scope_param = query_params.get('scope', [''])[0]
                
                # 驗證必要參數
                if not client_id or not redirect_uri or response_type != 'code':
                    await send({
                        'type': 'http.response.start',
                        'status': 400,
                        'headers': [(b'content-type', b'text/plain; charset=utf-8')],
                    })
                    await send({
                        'type': 'http.response.body',
                        'body': '無效的請求參數'.encode('utf-8'),
                    })
                    return
                
                # 準備模板變數
                template_vars = {
                    'client_name': 'claude.ai' if 'claude.ai' in redirect_uri else client_id,
                    'client_id': client_id,
                    'redirect_uri': redirect_uri,
                    'redirect_url': redirect_uri,
                    'response_type': response_type,
                    'state': state,
                    'scope': scope_param,
                    'form_action': '/oauth/authorize',
                    'error_message': '',
                    'error_class': 'hidden'
                }
                
                # 渲染登入頁面
                html = LOGIN_PAGE_TEMPLATE.format(**template_vars)
                
                await send({
                    'type': 'http.response.start',
                    'status': 200,
                    'headers': [
                        (b'content-type', b'text/html; charset=utf-8'),
                        (b'cache-control', b'no-store'),
                    ],
                })
                await send({
                    'type': 'http.response.body',
                    'body': html.encode('utf-8'),
                })
                return
            
            # 處理 OAuth 授權端點 (POST)
            if path == "/oauth/authorize" and scope["method"] == "POST":
                # 讀取表單資料
                body = b""
                while True:
                    message = await receive()
                    if message["type"] == "http.request":
                        body += message.get("body", b"")
                        if not message.get("more_body", False):
                            break
                
                # 解析表單資料
                form_data = urllib.parse.parse_qs(body.decode('utf-8'))
                
                # 提取表單欄位
                username = form_data.get('username', [''])[0]
                password = form_data.get('password', [''])[0]
                client_id = form_data.get('client_id', [''])[0]
                redirect_uri = form_data.get('redirect_uri', [''])[0]
                response_type = form_data.get('response_type', [''])[0]
                state = form_data.get('state', [''])[0]
                scope_param = form_data.get('scope', [''])[0]
                
                # 驗證認證資訊
                if username == OAUTH_USERNAME and password == OAUTH_PASSWORD:
                    # 生成授權碼
                    auth_code = secrets.token_urlsafe(32)
                    
                    # 儲存授權碼與元數據（10 分鐘後過期）
                    auth_codes[auth_code] = {
                        'client_id': client_id,
                        'redirect_uri': redirect_uri,
                        'expires_at': time.time() + 600,
                        'username': username,
                        'scope': scope_param
                    }
                    
                    # 重新導向回客戶端並附上授權碼
                    redirect_params = {'code': auth_code}
                    if state:
                        redirect_params['state'] = state
                    
                    redirect_url = redirect_uri + ('&' if '?' in redirect_uri else '?') + urllib.parse.urlencode(redirect_params)
                    
                    await send({
                        'type': 'http.response.start',
                        'status': 302,
                        'headers': [
                            (b'location', redirect_url.encode()),
                            (b'cache-control', b'no-store'),
                        ],
                    })
                    await send({
                        'type': 'http.response.body',
                        'body': b'',
                    })
                else:
                    # 無效的認證資訊 - 顯示錯誤
                    template_vars = {
                        'client_name': 'claude.ai' if 'claude.ai' in redirect_uri else client_id,
                        'client_id': client_id,
                        'redirect_uri': redirect_uri,
                        'redirect_url': redirect_uri,
                        'response_type': response_type,
                        'state': state,
                        'scope': scope_param,
                        'form_action': '/oauth/authorize',
                        'error_message': '無效的使用者名稱或密碼',
                        'error_class': ''
                    }
                    
                    html = LOGIN_PAGE_TEMPLATE.format(**template_vars)
                    
                    await send({
                        'type': 'http.response.start',
                        'status': 401,
                        'headers': [
                            (b'content-type', b'text/html; charset=utf-8'),
                            (b'cache-control', b'no-store'),
                        ],
                    })
                    await send({
                        'type': 'http.response.body',
                        'body': html.encode('utf-8'),
                    })
                return
            
            # 處理 OAuth 權杖端點
            if path == "/oauth/token" and scope["method"] == "POST":
                # 讀取內容
                body = b""
                while True:
                    message = await receive()
                    if message["type"] == "http.request":
                        body += message.get("body", b"")
                        if not message.get("more_body", False):
                            break
                
                # 解析表單資料
                form_data = urllib.parse.parse_qs(body.decode('utf-8'))
                
                grant_type = form_data.get('grant_type', [''])[0]
                code = form_data.get('code', [''])[0]
                redirect_uri = form_data.get('redirect_uri', [''])[0]
                
                # 從 Authorization 標頭提取客戶端認證
                auth_header = headers.get(b'authorization', b'').decode('utf-8')
                client_id = None
                client_secret = None
                
                if auth_header.startswith('Basic '):
                    try:
                        credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
                        client_id, client_secret = credentials.split(':', 1)
                    except:
                        pass
                
                if grant_type != 'authorization_code' or not code:
                    error_response = json.dumps({'error': 'invalid_request'}).encode()
                    await send({
                        'type': 'http.response.start',
                        'status': 400,
                        'headers': [
                            (b'content-type', b'application/json'),
                            (b'cache-control', b'no-store'),
                        ],
                    })
                    await send({
                        'type': 'http.response.body',
                        'body': error_response,
                    })
                    return
                
                # 驗證授權碼
                auth_data = auth_codes.get(code)
                if not auth_data or auth_data['expires_at'] < time.time():
                    error_response = json.dumps({'error': 'invalid_grant'}).encode()
                    await send({
                        'type': 'http.response.start',
                        'status': 400,
                        'headers': [
                            (b'content-type', b'application/json'),
                            (b'cache-control', b'no-store'),
                        ],
                    })
                    await send({
                        'type': 'http.response.body',
                        'body': error_response,
                    })
                    return
                
                # 移除已使用的授權碼
                del auth_codes[code]
                
                # 生成存取權杖
                access_token = secrets.token_urlsafe(64)
                
                # 儲存存取權杖
                access_tokens[access_token] = {
                    'username': auth_data['username'],
                    'expires_at': time.time() + 3600,  # 1 小時
                    'scope': auth_data.get('scope', '')
                }
                
                # 建立權杖回應
                token_response = {
                    'access_token': access_token,
                    'token_type': 'Bearer',
                    'expires_in': 3600,
                    'scope': auth_data.get('scope', '')
                }
                
                response_body = json.dumps(token_response).encode()
                await send({
                    'type': 'http.response.start',
                    'status': 200,
                    'headers': [
                        (b'content-type', b'application/json'),
                        (b'cache-control', b'no-store'),
                    ],
                })
                await send({
                    'type': 'http.response.body',
                    'body': response_body,
                })
                return
            
            # 處理客戶端註冊端點
            if path == "/oauth/register" and scope["method"] == "POST":
                # 目前我們接受任何客戶端註冊
                # 在生產環境中，您可能想要驗證並儲存客戶端認證
                
                # 讀取請求內容
                body = b""
                while True:
                    message = await receive()
                    if message["type"] == "http.request":
                        body += message.get("body", b"")
                        if not message.get("more_body", False):
                            break
                
                try:
                    registration_data = json.loads(body.decode('utf-8')) if body else {}
                except json.JSONDecodeError:
                    registration_data = {}
                
                # 生成客戶端 ID
                client_id = secrets.token_urlsafe(16)
                
                # 建立註冊回應
                registration_response = {
                    "client_id": client_id,
                    "client_id_issued_at": int(time.time()),
                    "grant_types": ["authorization_code", "refresh_token"],
                    "response_types": ["code"],
                    "redirect_uris": registration_data.get("redirect_uris", []),
                    "token_endpoint_auth_method": "none"
                }
                
                response_body = json.dumps(registration_response).encode()
                await send({
                    'type': 'http.response.start',
                    'status': 201,
                    'headers': [
                        (b'content-type', b'application/json'),
                        (b'cache-control', b'no-store'),
                    ],
                })
                await send({
                    'type': 'http.response.body',
                    'body': response_body,
                })
                return
            
            # 檢查 API 端點的 Bearer 權杖
            auth_header = headers.get(b'authorization', b'').decode('utf-8')
            token = None
            
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
            
            # 定期清理過期的權杖
            cleanup_expired_tokens()
            
            # 驗證受保護端點的權杖
            if path in ['/sse', '/messages']:
                if not token or token not in access_tokens:
                    # 返回 401 未授權
                    await send({
                        'type': 'http.response.start',
                        'status': 401,
                        'headers': [
                            (b'content-type', b'text/plain; charset=utf-8'),
                            (b'www-authenticate', b'Bearer'),
                        ],
                    })
                    await send({
                        'type': 'http.response.body',
                        'body': '未授權'.encode('utf-8'),
                    })
                    return
                
                # 檢查權杖是否已過期
                token_data = access_tokens[token]
                if token_data['expires_at'] < time.time():
                    del access_tokens[token]
                    await send({
                        'type': 'http.response.start',
                        'status': 401,
                        'headers': [
                            (b'content-type', b'text/plain; charset=utf-8'),
                            (b'www-authenticate', b'Bearer'),
                        ],
                    })
                    await send({
                        'type': 'http.response.body',
                        'body': '權杖已過期'.encode('utf-8'),
                    })
                    return
            
            # 處理根路徑的伺服器資訊
            if path == '/':
                server_info = {
                    "mcp": "1.0",
                    "name": "md-to-docx-mcp",
                    "description": "MD to DOCX MCP Server with OAuth authentication"
                }
                response_body = json.dumps(server_info).encode()
                await send({
                    'type': 'http.response.start',
                    'status': 200,
                    'headers': [
                        (b'content-type', b'application/json'),
                        (b'access-control-allow-origin', b'*'),
                    ],
                })
                await send({
                    'type': 'http.response.body',
                    'body': response_body,
                })
                return
            
            # 將其他路徑傳遞給 MCP 應用程式
            await mcp_app(scope, receive, send)
        else:
            # 對於非 HTTP（如 WebSocket），直接傳遞
            await mcp_app(scope, receive, send)
    
    # 使用我們的自訂 OAuth ASGI 應用程式建立 Starlette 應用程式
    app = Starlette(
        routes=[
            Mount('/', app=oauth_app),
        ]
    )
    
    # 更新日誌訊息
    logger.info(f"OAuth 發現：http://{host}:{port}/.well-known/oauth-authorization-server")
    logger.info(f"OAuth 授權：http://{host}:{port}/oauth/authorize")
    logger.info(f"OAuth 權杖：http://{host}:{port}/oauth/token")
    logger.info(f"SSE 端點：http://{host}:{port}/sse (需要 Bearer 權杖)")
    logger.info("\n與 Claude.ai Integrations 使用：")
    logger.info(f"  整合 URL：https://your-domain.com/sse")
    logger.info("  Claude.ai 將自動處理 OAuth 流程")
    logger.info("\n" + "=" * 60)
    logger.info("🔑 使用這些認證登入：")
    logger.info(f"   使用者名稱：{OAUTH_USERNAME}")
    logger.info(f"   密碼：{OAUTH_PASSWORD}")
    logger.info("=" * 60 + "\n")
    
    # 使用 uvicorn 執行
    uvicorn.run(app, host=host, port=port, log_level=log_level)

if __name__ == "__main__":
    run_remote_server()