"""
Server-side Markdown rendering.

Report bodies, steps and comments are attacker-controlled — the public portal
accepts them from unauthenticated submitters. They were previously rendered in
the browser with `marked.parse(el.textContent)` assigned to `innerHTML`, which
recovers the raw string past Django's escaping and hands it to a parser that
does not sanitise HTML. Rendering here instead keeps the sanitisation on the
server, where it cannot be bypassed.
"""
from django import template
from django.utils.safestring import mark_safe
from markdown_it import MarkdownIt

register = template.Library()


def _link_open(tokens, idx, options, env):
    """Neutralise tabnabbing and SEO abuse on user-supplied links."""
    token = tokens[idx]
    token.attrSet("rel", "nofollow noopener noreferrer")
    token.attrSet("target", "_blank")
    return _renderer.renderToken(tokens, idx, options, env)


# html=False makes the parser escape raw HTML instead of passing it through.
# markdown-it-py's built-in link validator already rejects javascript:,
# vbscript:, file: and non-image data: URLs.
_md = MarkdownIt("commonmark", {"html": False, "breaks": True, "linkify": False})
_renderer = _md.renderer
_renderer.rules["link_open"] = _link_open


@register.filter(name="markdown")
def markdown(value):
    """Render trusted-nowhere Markdown to sanitised HTML."""
    if not value:
        return ""
    return mark_safe(_md.render(str(value)))
