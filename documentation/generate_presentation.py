"""
Presentation Generator - Convert Markdown slides to HTML/PDF.

This script converts the PRESENTATION_SLIDES.md to a beautiful HTML presentation
that can be opened in a browser and printed/exported to PDF.

Requirements:
    pip install markdown weasyprint

Usage:
    python generate_presentation.py

Output:
    - presentation.html (viewable in browser)
    - presentation.pdf (for sharing)
"""

import os
import re
from pathlib import Path

# HTML template with styling
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Incremental ML Pipeline - Presentation</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Fira+Code&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.6;
            color: #1a1a2e;
            background: #f0f2f5;
        }}
        
        .slide {{
            width: 100%;
            min-height: 100vh;
            padding: 60px 80px;
            background: white;
            page-break-after: always;
            display: flex;
            flex-direction: column;
        }}
        
        .slide:last-child {{
            page-break-after: avoid;
        }}
        
        .title-slide {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            justify-content: center;
            align-items: center;
            text-align: center;
        }}
        
        .title-slide h1 {{
            font-size: 3.5rem;
            margin-bottom: 20px;
        }}
        
        .title-slide h2 {{
            font-size: 1.8rem;
            font-weight: 400;
            opacity: 0.9;
            margin-bottom: 40px;
        }}
        
        .title-slide p {{
            font-size: 1.2rem;
            opacity: 0.8;
        }}
        
        h1 {{
            font-size: 2.5rem;
            color: #667eea;
            margin-bottom: 40px;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
        }}
        
        h2 {{
            font-size: 1.5rem;
            color: #4a4a6a;
            margin: 25px 0 15px 0;
        }}
        
        p {{
            font-size: 1.1rem;
            margin-bottom: 15px;
        }}
        
        ul, ol {{
            margin: 15px 0 15px 30px;
            font-size: 1.1rem;
        }}
        
        li {{
            margin-bottom: 10px;
        }}
        
        pre {{
            background: #1e1e3f;
            color: #e0e0e0;
            padding: 25px;
            border-radius: 10px;
            overflow-x: auto;
            margin: 20px 0;
            font-family: 'Fira Code', monospace;
            font-size: 0.9rem;
            line-height: 1.5;
        }}
        
        code {{
            font-family: 'Fira Code', monospace;
            background: #e8e8f0;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.95em;
        }}
        
        pre code {{
            background: transparent;
            padding: 0;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 1rem;
        }}
        
        th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        
        tr:hover {{
            background: #e8e8f0;
        }}
        
        blockquote {{
            border-left: 4px solid #667eea;
            padding-left: 20px;
            margin: 20px 0;
            color: #666;
            font-style: italic;
        }}
        
        strong {{
            color: #667eea;
        }}
        
        .emoji {{
            font-size: 1.2em;
        }}
        
        .highlight {{
            background: linear-gradient(120deg, #f6d365 0%, #fda085 100%);
            padding: 2px 8px;
            border-radius: 4px;
        }}
        
        .content {{
            flex: 1;
        }}
        
        .footer {{
            margin-top: auto;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            color: #888;
            font-size: 0.9rem;
            display: flex;
            justify-content: space-between;
        }}
        
        @media print {{
            .slide {{
                min-height: 100vh;
                padding: 40px 60px;
            }}
            
            body {{
                background: white;
            }}
        }}
        
        /* Diagram styling */
        .diagram {{
            background: #f8f9fa;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            font-family: 'Fira Code', monospace;
            font-size: 0.85rem;
            white-space: pre;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
{slides}
</body>
</html>
"""


def parse_markdown_slides(content: str) -> list:
    """Parse markdown content into individual slides."""
    # Remove YAML frontmatter
    content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)
    
    # Split by horizontal rules (---)
    slides = re.split(r'\n---\n', content)
    
    return [s.strip() for s in slides if s.strip()]


def markdown_to_html(md: str) -> str:
    """Convert markdown to HTML with basic formatting."""
    html = md
    
    # Headers
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    
    # Code blocks
    def replace_code_block(match):
        lang = match.group(1) or ''
        code = match.group(2)
        code = code.replace('<', '&lt;').replace('>', '&gt;')
        return f'<pre><code class="{lang}">{code}</code></pre>'
    
    html = re.sub(r'```(\w*)\n(.*?)```', replace_code_block, html, flags=re.DOTALL)
    
    # Inline code
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    
    # Bold
    html = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html)
    
    # Italic
    html = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', html)
    
    # Tables
    def replace_table(match):
        lines = match.group(0).strip().split('\n')
        if len(lines) < 2:
            return match.group(0)
        
        headers = [h.strip() for h in lines[0].split('|') if h.strip()]
        rows = []
        
        for line in lines[2:]:  # Skip header separator
            if line.strip():
                cells = [c.strip() for c in line.split('|') if c.strip()]
                rows.append(cells)
        
        table_html = '<table>\n<thead><tr>'
        for h in headers:
            table_html += f'<th>{h}</th>'
        table_html += '</tr></thead>\n<tbody>'
        
        for row in rows:
            table_html += '<tr>'
            for cell in row:
                table_html += f'<td>{cell}</td>'
            table_html += '</tr>\n'
        
        table_html += '</tbody></table>'
        return table_html
    
    html = re.sub(r'\|.+\|\n\|[-:\s|]+\|\n(\|.+\|\n?)+', replace_table, html)
    
    # Unordered lists
    def replace_ul(match):
        items = match.group(0).strip().split('\n')
        list_html = '<ul>'
        for item in items:
            text = re.sub(r'^[\s]*[-*]\s*', '', item)
            if text:
                list_html += f'<li>{text}</li>'
        list_html += '</ul>'
        return list_html
    
    html = re.sub(r'(^[\s]*[-*]\s+.+$\n?)+', replace_ul, html, flags=re.MULTILINE)
    
    # Ordered lists
    def replace_ol(match):
        items = match.group(0).strip().split('\n')
        list_html = '<ol>'
        for item in items:
            text = re.sub(r'^[\s]*\d+\.\s*', '', item)
            if text:
                list_html += f'<li>{text}</li>'
        list_html += '</ol>'
        return list_html
    
    html = re.sub(r'(^[\s]*\d+\.\s+.+$\n?)+', replace_ol, html, flags=re.MULTILINE)
    
    # Blockquotes
    html = re.sub(r'^>\s*(.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
    
    # Paragraphs (remaining text)
    lines = html.split('\n')
    result = []
    for line in lines:
        if line.strip() and not line.strip().startswith('<'):
            result.append(f'<p>{line}</p>')
        else:
            result.append(line)
    html = '\n'.join(result)
    
    # Math expressions (basic support)
    html = re.sub(r'\$\$(.+?)\$\$', r'<div class="math">\1</div>', html, flags=re.DOTALL)
    html = re.sub(r'\$(.+?)\$', r'<span class="math">\1</span>', html)
    
    return html


def create_slide_html(content: str, index: int, total: int) -> str:
    """Create HTML for a single slide."""
    html_content = markdown_to_html(content)
    
    # Check if it's a title slide
    is_title = index == 0 or 'Thank You' in content or 'Questions?' in content
    slide_class = 'slide title-slide' if is_title else 'slide'
    
    footer = '' if is_title else f'''
    <div class="footer">
        <span>Incremental ML Pipeline - DaST Research</span>
        <span>Slide {index + 1} / {total}</span>
    </div>
    '''
    
    return f'''
    <div class="{slide_class}">
        <div class="content">
            {html_content}
        </div>
        {footer}
    </div>
    '''


def generate_presentation(input_file: str, output_dir: str):
    """Generate HTML presentation from markdown."""
    # Read markdown
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse slides
    slides = parse_markdown_slides(content)
    print(f"📊 Found {len(slides)} slides")
    
    # Generate HTML for each slide
    slides_html = ''
    for i, slide_content in enumerate(slides):
        slides_html += create_slide_html(slide_content, i, len(slides))
    
    # Create final HTML
    html = HTML_TEMPLATE.format(slides=slides_html)
    
    # Write output
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'presentation.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML presentation saved to: {output_path}")
    print(f"📖 Open in browser and print to PDF (Ctrl+P)")
    
    return output_path


def main():
    """Main entry point."""
    print("=" * 60)
    print("🎯 Presentation Generator")
    print("=" * 60)
    
    # Find input file
    script_dir = Path(__file__).parent
    input_file = script_dir / 'PRESENTATION_SLIDES.md'
    
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        return
    
    # Generate presentation
    output_dir = script_dir / 'presentation_output'
    generate_presentation(str(input_file), str(output_dir))
    
    print("\n" + "=" * 60)
    print("🎉 Done! To create PDF:")
    print("   1. Open presentation.html in Chrome/Edge")
    print("   2. Press Ctrl+P (or Cmd+P on Mac)")
    print("   3. Select 'Save as PDF'")
    print("   4. Check 'Background graphics' in More settings")
    print("=" * 60)


if __name__ == "__main__":
    main()
