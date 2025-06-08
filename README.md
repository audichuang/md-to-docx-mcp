# MD to DOCX MCP Server

This MCP (Model Context Protocol) server converts Markdown to DOCX format and returns the result as base64-encoded content using the powerful Pandoc engine.

## 🚀 Now with Remote MCP Support!

This server now supports the [Claude.ai Integrations](https://www.anthropic.com/news/integrations) feature, allowing you to use it directly from Claude.ai without local installation.

## Features

- **Syntax highlighting** for code blocks
- **Math formulas** support (LaTeX)
- **Table of contents** generation
- **Metadata support** (title, author)
- **Enhanced formatting** with Pandoc's superior conversion quality
- **Multiple Markdown extensions** support
- **Professional document structure**

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -e .
```

## Usage

### Option 1: Remote Server (for Claude.ai Integrations)

Run the server with OAuth authentication:

```bash
# 1. Set up environment variables (copy and edit .env.example)
cp .env.example .env
# Edit .env to set your OAuth credentials

# 2. Run the remote server
python -m md_to_docx_mcp.remote_server

# Or use the installed script
md-to-docx-mcp-remote
```

The server will start with:
- OAuth discovery: `http://localhost:8000/.well-known/oauth-authorization-server`
- OAuth authorize: `http://localhost:8000/oauth/authorize`
- SSE endpoint: `http://localhost:8000/sse`

To use with Claude.ai:
1. Deploy the server to a public URL (e.g., using ngrok, Railway, or your preferred hosting)
2. Add the integration in Claude.ai using your public SSE endpoint URL
3. Claude will automatically handle the OAuth flow

### Option 2: Local MCP Server

Add this server to your MCP configuration:

```json
{
  "mcpServers": {
    "md-to-docx": {
      "command": "python",
      "args": ["-m", "md_to_docx_mcp.server"]
    }
  }
}
```

### Available Tool

The server provides one tool:

#### `convert_md_to_docx`

Converts Markdown text to DOCX format using Pandoc and returns as base64.

**Parameters:**
- `markdown_text` (required): The Markdown text to convert
- `filename` (optional): The desired filename (default: "document.docx")
- `title` (optional): Document title
- `author` (optional): Document author
- `include_toc` (optional): Include table of contents (default: false)

**Returns:**
- `filename`: The filename of the document
- `mime_type`: The MIME type of the DOCX file
- `base64_content`: The base64-encoded DOCX file content

### Converting Base64 to File

To save the base64 content as a file, you can use:

#### Python:
```python
import base64

# base64_content is the string returned by the MCP server
with open("output.docx", "wb") as f:
    f.write(base64.b64decode(base64_content))
```

#### JavaScript:
```javascript
const fs = require('fs');

// base64Content is the string returned by the MCP server
const buffer = Buffer.from(base64Content, 'base64');
fs.writeFileSync('output.docx', buffer);
```

#### Command Line (Linux/Mac):
```bash
echo "BASE64_CONTENT" | base64 -d > output.docx
```

## Example

When you send Markdown like:

```markdown
---
title: My Document
author: John Doe
---

# My Document

This is a **bold** text and this is *italic*.

## Features
- Item 1
- Item 2

### Code Example
```python
print("Hello World")
```

## Math Formula

$E = mc^2$

$$\sum_{i=1}^{n} i = \frac{n(n+1)}{2}$$
```

The server will return a base64-encoded DOCX file with:
- Professional formatting
- Syntax-highlighted code blocks
- Rendered math formulas
- Optional table of contents
- Document metadata

## Why Pandoc?

This MCP server uses pypandoc (Python wrapper for Pandoc) because:
- **Best conversion quality** - Pandoc is the gold standard for document conversion
- **Rich feature set** - Supports advanced Markdown features like math, citations, and more
- **Active development** - Regularly updated and maintained
- **Wide format support** - Can be extended to support other formats in the future

## Dependencies

- `mcp` - Model Context Protocol implementation
- `pypandoc_binary` - Pandoc with Python bindings (includes Pandoc binary)
- `fastmcp` - FastMCP for remote server support
- `uvicorn` - ASGI server for remote deployment
- `python-dotenv` - Environment variable management

## Environment Variables (for Remote Server)

Create a `.env` file based on `.env.example`:

```env
# OAuth Authentication
OAUTH_USERNAME=admin
OAUTH_PASSWORD=your-secure-password-here

# Server Settings (optional)
# HOST=0.0.0.0
# PORT=8000

# Public URL (required for production)
# SERVER_URL=https://your-domain.com
```

**Security Note**: Always use strong passwords and HTTPS in production!

## 🎯 Key Features of Remote Server

1. **Direct Download Links** - No base64 conversion needed!
2. **30-minute File Storage** - Files are automatically cleaned up
3. **OAuth 2.0 Security** - Secure authentication flow
4. **Beautiful Chinese UI** - User-friendly login page