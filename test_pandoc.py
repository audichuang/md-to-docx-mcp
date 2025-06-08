#!/usr/bin/env python3
"""
Test script for MD to DOCX MCP Server
"""
import base64
from md_to_docx_mcp.server import convert_md_to_docx_pandoc

# Test markdown with advanced features
test_md = """# Test Document

This is a test document with various **Markdown** elements.

## Features

1. **Syntax highlighting** for code blocks
2. **Math formulas** support
3. **Tables** with proper formatting
4. Professional document structure

### Code Example

```python
def fibonacci(n):
    '''Calculate Fibonacci sequence'''
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)

# Test
print(fibonacci(10))
```

### Math Formulas

Inline formula: $E = mc^2$

Block formula:

$$\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}$$

### Table Example

| Feature | Supported | Notes |
|---------|-----------|-------|
| Syntax Highlighting | ✓ | Using Pandoc's built-in highlighters |
| Math Formulas | ✓ | LaTeX syntax |
| Tables | ✓ | Full table support |
| Metadata | ✓ | Title, author, etc. |

---

*Generated using MD to DOCX MCP Server with Pandoc*
"""

def test():
    print("Testing MD to DOCX conversion with Pandoc...")
    print("=" * 50)
    
    # Test basic conversion
    result = convert_md_to_docx_pandoc(test_md, "test_output.docx")
    
    print(f"Filename: {result['filename']}")
    print(f"MIME Type: {result['mime_type']}")
    print(f"Base64 content length: {len(result['base64_content'])} characters")
    
    # Save the file
    with open(result['filename'], 'wb') as f:
        f.write(base64.b64decode(result['base64_content']))
    
    print(f"\nFile saved as: {result['filename']}")
    print("You can open this file in Microsoft Word to verify the conversion.")
    
    # Show first 200 chars of base64
    print(f"\nFirst 200 chars of base64 content:")
    print(result['base64_content'][:200] + "...")
    
    return result

if __name__ == "__main__":
    test()