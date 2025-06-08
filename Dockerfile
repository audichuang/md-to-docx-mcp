# 使用 Python 3.12 官方基礎映像
FROM python:3.12-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴（Pandoc 需要）
RUN apt-get update && apt-get install -y \
    pandoc \
    && rm -rf /var/lib/apt/lists/*

# 複製專案檔案
COPY pyproject.toml README.md ./
COPY md_to_docx_mcp ./md_to_docx_mcp

# 安裝 Python 依賴
RUN pip install --no-cache-dir -e .

# 建立非 root 使用者
RUN useradd -m -s /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8000

# 啟動指令
CMD ["python", "-m", "md_to_docx_mcp.remote_server"]