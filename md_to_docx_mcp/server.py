import asyncio
import base64
import tempfile
import os
from typing import Any

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent
import pypandoc


app = Server("md-to-docx-mcp")


def convert_md_to_docx_pandoc(markdown_text: str, filename: str = "document.docx") -> dict:
    """Convert Markdown to DOCX using pypandoc (Pandoc Python wrapper)"""
    
    # Create temporary files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp_md:
        tmp_md.write(markdown_text)
        tmp_md_path = tmp_md.name
    
    tmp_docx_path = tempfile.mktemp(suffix='.docx')
    
    try:
        # Use pypandoc to convert with enhanced options
        pypandoc.convert_file(
            tmp_md_path,
            'docx',
            outputfile=tmp_docx_path,
            extra_args=[
                '--standalone',
                '--highlight-style', 'tango',  # Code highlighting
                '--wrap', 'preserve',  # Preserve line breaks
                '--resource-path', '.',  # For handling relative paths
            ]
        )
        
        # Read the generated docx file
        with open(tmp_docx_path, 'rb') as f:
            docx_content = f.read()
        
        # Encode to base64
        base64_content = base64.b64encode(docx_content).decode('utf-8')
        
        return {
            "filename": filename,
            "base64_content": base64_content,
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }
        
    finally:
        # Clean up temporary files
        if os.path.exists(tmp_md_path):
            os.unlink(tmp_md_path)
        if os.path.exists(tmp_docx_path):
            os.unlink(tmp_docx_path)


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="convert_md_to_docx",
            description="Convert Markdown text to DOCX format using Pandoc and return as base64",
            inputSchema={
                "type": "object",
                "properties": {
                    "markdown_text": {
                        "type": "string",
                        "description": "The Markdown text to convert"
                    },
                    "filename": {
                        "type": "string",
                        "description": "The desired filename for the DOCX (default: document.docx)",
                        "default": "document.docx"
                    },
                    "title": {
                        "type": "string",
                        "description": "Document title (optional)"
                    },
                    "author": {
                        "type": "string",
                        "description": "Document author (optional)"
                    },
                    "include_toc": {
                        "type": "boolean",
                        "description": "Include table of contents (default: false)",
                        "default": False
                    }
                },
                "required": ["markdown_text"]
            }
        )
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    if name == "convert_md_to_docx":
        markdown_text = arguments.get("markdown_text", "")
        filename = arguments.get("filename", "document.docx")
        title = arguments.get("title")
        author = arguments.get("author")
        include_toc = arguments.get("include_toc", False)
        
        if not filename.endswith('.docx'):
            filename += '.docx'
        
        # Add metadata to markdown if provided
        if title or author:
            metadata = "---\n"
            if title:
                metadata += f"title: {title}\n"
            if author:
                metadata += f"author: {author}\n"
            metadata += "---\n\n"
            markdown_text = metadata + markdown_text
        
        try:
            # Create temporary files for enhanced conversion
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp_md:
                tmp_md.write(markdown_text)
                tmp_md_path = tmp_md.name
            
            tmp_docx_path = tempfile.mktemp(suffix='.docx')
            
            # Build extra arguments
            extra_args = [
                '--standalone',
                '--highlight-style', 'tango',
                '--wrap', 'preserve',
                '--resource-path', '.',
            ]
            
            if include_toc:
                extra_args.append('--toc')
            
            # Convert using pypandoc
            pypandoc.convert_file(
                tmp_md_path,
                'docx',
                outputfile=tmp_docx_path,
                extra_args=extra_args
            )
            
            # Read and encode
            with open(tmp_docx_path, 'rb') as f:
                docx_content = f.read()
            
            base64_content = base64.b64encode(docx_content).decode('utf-8')
            
            # Clean up
            os.unlink(tmp_md_path)
            os.unlink(tmp_docx_path)
            
            return [
                TextContent(
                    type="text",
                    text=f"Successfully converted Markdown to DOCX using Pandoc.\n\n"
                         f"Filename: {filename}\n"
                         f"MIME Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\n"
                         f"Features: {'Table of Contents, ' if include_toc else ''}Code Highlighting, Enhanced Formatting\n\n"
                         f"Base64 Content:\n{base64_content}"
                )
            ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"Error converting Markdown to DOCX: {str(e)}"
                )
            ]
    else:
        return [
            TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )
        ]


async def main():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="md-to-docx-mcp",
                server_version="1.0.0"
            )
        )


if __name__ == "__main__":
    asyncio.run(main())