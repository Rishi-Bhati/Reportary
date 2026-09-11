"""
public_portal/css_sanitizer.py

Sanitises owner-supplied CSS before it is served on a public reporting portal,
and scopes it to the portal form container so it cannot restyle the page around
it.

This is a parse-and-allowlist implementation. The previous version was a regex
blocklist, which is not a defensible way to filter CSS — it was bypassable by
token splitting (``javasjavascript:cript:`` reassembles into ``javascript:``
after a single-pass removal), by CSS character escapes (``url(\\68 ttps://…)``
walked past the external-URL filter), and by at-rules, which were appended
verbatim and therefore unscoped. Its brace-splitting also dropped a closing
brace on any nested block, corrupting the remainder of the stylesheet.

Rules enforced here:
  * only declarations whose property is on ALLOWED_PROPERTIES survive;
  * ``url()`` may only reference a relative path — no external hosts, no data:,
    and escapes are resolved by the tokenizer before the check;
  * every at-rule is dropped except ``@media``, whose contents are recursively
    sanitised and scoped;
  * every selector is prefixed with the scope selector, so the declaration
    cannot reach outside the portal form.
"""
import logging

import tinycss2

logger = logging.getLogger(__name__)

# Hard cap on the input we will even attempt to parse.
MAX_CSS_LENGTH = 20_000

# Properties an owner may set. Deliberately presentational: no `position`,
# `content`, `behavior`, `-moz-binding`, or anything that can overlay the page.
ALLOWED_PROPERTIES = frozenset({
    'align-items', 'background', 'background-color', 'background-image',
    'background-position', 'background-repeat', 'background-size',
    'border', 'border-bottom', 'border-bottom-color', 'border-bottom-left-radius',
    'border-bottom-right-radius', 'border-bottom-style', 'border-bottom-width',
    'border-color', 'border-left', 'border-left-color', 'border-left-style',
    'border-left-width', 'border-radius', 'border-right', 'border-right-color',
    'border-right-style', 'border-right-width', 'border-style', 'border-top',
    'border-top-color', 'border-top-left-radius', 'border-top-right-radius',
    'border-top-style', 'border-top-width', 'border-width',
    'box-shadow', 'box-sizing', 'color', 'column-gap', 'display', 'flex',
    'flex-basis', 'flex-direction', 'flex-grow', 'flex-shrink', 'flex-wrap',
    'font', 'font-family', 'font-size', 'font-style', 'font-variant',
    'font-weight', 'gap', 'grid-template-columns', 'grid-template-rows',
    'height', 'justify-content', 'letter-spacing', 'line-height',
    'list-style', 'list-style-type', 'margin', 'margin-bottom', 'margin-left',
    'margin-right', 'margin-top', 'max-height', 'max-width', 'min-height',
    'min-width', 'opacity', 'outline', 'outline-color', 'outline-offset',
    'outline-style', 'outline-width', 'padding', 'padding-bottom',
    'padding-left', 'padding-right', 'padding-top', 'row-gap',
    'text-align', 'text-decoration', 'text-shadow', 'text-transform',
    'transition', 'vertical-align', 'white-space', 'width', 'word-break',
})

# At-rules that may survive. Everything else — @import, @font-face, @supports,
# @charset, @namespace — is dropped.
ALLOWED_AT_RULES = frozenset({'media'})

# Selectors that mean "the whole page"; they are rewritten to the scope itself
# rather than being nested underneath it.
ROOT_SELECTORS = frozenset({'html', 'body', ':root', '*'})

# Functions permitted inside a declaration value. This is an allowlist for the
# same reason the property list is: blocklisting `expression(` merely moves the
# bypass one token along (`expresexpression(sion(` survives a substring filter).
ALLOWED_VALUE_FUNCTIONS = frozenset({
    'calc', 'clamp', 'conic-gradient', 'cubic-bezier', 'hsl', 'hsla',
    'linear-gradient', 'max', 'min', 'radial-gradient',
    'repeating-linear-gradient', 'repeating-radial-gradient', 'rgb', 'rgba',
    'steps', 'url', 'var',
})

# Token types that may never appear in a value we keep. tinycss2 reports a
# malformed url() as a ParseError token whose .type is 'error', so that is the
# type to reject — not the 'bad-url' kind name.
FORBIDDEN_TOKEN_TYPES = frozenset({
    'error', 'bad-url', 'bad-string', 'at-keyword', '[] block', '{} block',
})


def _url_is_safe(value: str) -> bool:
    """
    Only same-origin relative paths are allowed.

    tinycss2 has already resolved CSS escapes by the time we see this value, so
    ``url(\\68 ttps://evil/x)`` arrives here as ``https://evil/x`` and is caught.
    """
    value = value.strip()
    if not value:
        return False
    lowered = value.lower()
    if '//' in lowered or ':' in lowered:
        # Covers scheme-relative (//host), absolute (https:), data:, javascript:.
        return False
    return not lowered.startswith('\\')


def _tokens_are_safe(tokens) -> bool:
    """Recursively check a value's tokens against the allowlists."""
    for token in tokens:
        if token.type in FORBIDDEN_TOKEN_TYPES:
            return False

        if token.type == 'url':
            if not _url_is_safe(token.value):
                return False

        elif token.type == 'function':
            if token.lower_name not in ALLOWED_VALUE_FUNCTIONS:
                return False
            if token.lower_name == 'url':
                serialised = tinycss2.serialize(token.arguments).strip().strip('"\'')
                if not _url_is_safe(serialised):
                    return False
            elif not _tokens_are_safe(token.arguments):
                return False

    return True


def _declaration_is_safe(declaration) -> bool:
    if declaration.lower_name not in ALLOWED_PROPERTIES:
        return False
    return _tokens_are_safe(declaration.value)


def _sanitise_declarations(content) -> str:
    """Filter a declaration list down to allowed, safe declarations."""
    kept = []
    for declaration in tinycss2.parse_blocks_contents(content):
        if declaration.type != 'declaration':
            continue
        if not _declaration_is_safe(declaration):
            continue
        value = tinycss2.serialize(declaration.value).strip()
        if not value:
            continue
        important = ' !important' if declaration.important else ''
        kept.append(f"{declaration.lower_name}: {value}{important};")
    return ' '.join(kept)


def _scope_selector(raw_selector: str, scope_selector: str) -> str:
    """Prefix each comma-separated selector with the scope container."""
    scoped = []
    for part in raw_selector.split(','):
        part = ' '.join(part.split())
        if not part:
            continue
        if part in ROOT_SELECTORS:
            scoped.append(scope_selector)
        elif part.startswith(scope_selector):
            scoped.append(part)
        else:
            scoped.append(f"{scope_selector} {part}")
    return ', '.join(scoped)


def _sanitise_rules(rules, scope_selector: str) -> list:
    """Sanitise a list of parsed rules, returning serialised CSS blocks."""
    out = []
    for rule in rules:
        if rule.type == 'qualified-rule':
            selector = _scope_selector(tinycss2.serialize(rule.prelude), scope_selector)
            body = _sanitise_declarations(rule.content)
            if selector and body:
                out.append(f"{selector} {{ {body} }}")

        elif rule.type == 'at-rule':
            if rule.lower_at_keyword not in ALLOWED_AT_RULES:
                continue
            if rule.content is None:
                # A statement at-rule such as `@import url(...);` — never allowed.
                continue
            prelude = tinycss2.serialize(rule.prelude).strip()
            inner = _sanitise_rules(
                tinycss2.parse_rule_list(rule.content, skip_comments=True, skip_whitespace=True),
                scope_selector,
            )
            if inner:
                out.append(f"@{rule.lower_at_keyword} {prelude} {{ " + ' '.join(inner) + " }")

        # 'error' and 'comment' rules are dropped.
    return out


def sanitize_and_scope_css(raw_css: str, scope_selector: str = "#portal-form-wrapper") -> str:
    """
    Sanitise and scope raw CSS. Returns CSS text, or "" if nothing survived.

    Never raises — a portal must still render if its custom CSS is unparseable.
    """
    if not raw_css:
        return ""

    if len(raw_css) > MAX_CSS_LENGTH:
        raw_css = raw_css[:MAX_CSS_LENGTH]

    try:
        rules = tinycss2.parse_stylesheet(raw_css, skip_comments=True, skip_whitespace=True)
        blocks = _sanitise_rules(rules, scope_selector)
    except Exception:
        logger.exception("Failed to sanitise portal CSS; serving none.")
        return ""

    return ("\n".join(blocks) + "\n") if blocks else ""
