# MD to DOCX MCP Server

This MCP (Model Context Protocol) server converts Markdown to DOCX format and returns the result as base64-encoded content using the powerful Pandoc engine.

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

### As an MCP Server

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