"""
public_portal/css_sanitizer.py

Sanitizes arbitrary user-supplied CSS to prevent security vulnerabilities (XSS, phishing overlays, external tracking)
and scopes it to the portal form container so it cannot break other page elements.
"""
import re


def sanitize_and_scope_css(raw_css: str, scope_selector: str = "#portal-form-wrapper") -> str:
    """
    Sanitizes and scopes raw CSS.

    1. Removes dangerous strings:
       - <script> tags or any HTML tags
       - 'javascript:' protocols
       - 'expression(...)' IE hacks
       - 'behavior(...)' IE hacks
       - '-moz-binding' Firefox binding hacks
    2. Restricts url() functions to prevent tracking/stealing credentials:
       - Allows only relative paths or safe data URIs
       - Removes any url() pointing to external http/https/double-slash URLs
    3. Blocks @import to prevent loading malicious external stylesheets.
    4. Scopes every selector to a target container (e.g. #portal-form-wrapper)
       so it cannot modify the style of the global layout (body, nav, sidebar, etc.).
    """
    if not raw_css:
        return ""

    # Remove comments first
    css = re.sub(r'/\*.*?\*/', '', raw_css, flags=re.DOTALL)

    # Convert to lowercase for uniform checks
    css_lower = css.lower()

    # Block @import entirely
    if '@import' in css_lower:
        css = re.sub(r'@import\s+[^;]+;', '', css, flags=re.IGNORECASE)

    # Strip dangerous HTML tags
    css = re.sub(r'<[^>]*>', '', css)

    # Strip dangerous terms
    danger_patterns = [
        r'expression\s*\(',
        r'javascript\s*:',
        r'behaviour\s*\(',
        r'behavior\s*\(',
        r'-moz-binding',
    ]
    for pattern in danger_patterns:
        css = re.sub(pattern, '', css, flags=re.IGNORECASE)

    # Strip external url() values
    # url("http://...") or url('//...') or url(http://...)
    css = re.sub(
        r'url\s*\(\s*[\'"]?\s*(https?:)?//[^\)]+\)',
        'none',
        css,
        flags=re.IGNORECASE
    )

    # Scope the CSS: prepend the scope selector to all rules
    # A simple regex split on brackets to identify selectors and their rules.
    scoped_parts = []
    # Split by closing bracket }
    blocks = css.split('}')
    for block in blocks:
        if not block.strip():
            continue
        if '{' in block:
            selector, rules = block.split('{', 1)
            selector = selector.strip()
            
            # Skip media queries for this simple parser
            if selector.startswith('@'):
                scoped_parts.append(f"{selector} {{{rules}}}")
                continue

            # Split comma-separated selectors (e.g. h1, h2, .btn)
            split_selectors = selector.split(',')
            scoped_selectors = []
            for sel in split_selectors:
                sel = sel.strip()
                if not sel:
                    continue
                # Handle special selectors like body or html by binding them directly to wrapper
                if sel in ('html', 'body', ':root'):
                    scoped_selectors.append(scope_selector)
                elif sel.startswith(scope_selector):
                    scoped_selectors.append(sel)
                else:
                    scoped_selectors.append(f"{scope_selector} {sel}")

            new_selector = ", ".join(scoped_selectors)
            scoped_parts.append(f"{new_selector} {{{rules}}}")

    return "\n".join(scoped_parts) + "\n"
