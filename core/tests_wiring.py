"""
Static wiring checks.

Two whole classes of 500 in this codebase came from references that are only
resolved at request time: URL names that do not exist, and templates that were
never created. Both are cheap to verify statically, and both bugs lived
exclusively on error/permission-denied branches that no functional test reaches.

These tests read the source tree; they touch no database and run in about a
second.
"""
import re
from pathlib import Path

from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.test import SimpleTestCase
from django.urls import get_resolver

BASE_DIR = Path(__file__).resolve().parent.parent

SKIP_DIRS = {'venv', 'node_modules', '.git', '__pycache__', 'staticfiles', 'media'}


def _source_files():
    for path in BASE_DIR.rglob('*'):
        if path.suffix not in ('.py', '.html'):
            continue
        if SKIP_DIRS & set(path.relative_to(BASE_DIR).parts):
            continue
        yield path


def _registered_url_names():
    """Every reversible name, including namespaced ones."""

    def walk(resolver, prefix=''):
        names = {prefix + key for key in resolver.reverse_dict if isinstance(key, str)}
        for namespace, (_, sub_resolver) in resolver.namespace_dict.items():
            names |= walk(sub_resolver, f'{prefix}{namespace}:')
        return names

    return walk(get_resolver())


URL_REF = re.compile(
    r"""(?:redirect|reverse|reverse_lazy)\(\s*['"]([a-zA-Z0-9_:\-]+)['"]"""
    r"""|\{%\s*url\s+['"]([a-zA-Z0-9_:\-]+)['"]"""
)

TEMPLATE_REF = re.compile(
    r"""render\(\s*request\s*,\s*['"]([^'"]+\.html)['"]"""
    r"""|render_to_string\(\s*['"]([^'"]+\.html)['"]"""
    r"""|template_name\s*=\s*['"]([^'"]+\.html)['"]"""
    r"""|\{%\s*(?:extends|include)\s+['"]([^'"]+\.html)['"]"""
)


class UrlNameResolutionTests(SimpleTestCase):
    def test_every_referenced_url_name_resolves(self):
        known = _registered_url_names()
        unresolved = {}

        for path in _source_files():
            try:
                text = path.read_text(encoding='utf-8')
            except (UnicodeDecodeError, OSError):
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                for match in URL_REF.finditer(line):
                    name = match.group(1) or match.group(2)
                    if not name or '/' in name or name.startswith('http'):
                        continue
                    if name not in known:
                        location = f'{path.relative_to(BASE_DIR)}:{lineno}'
                        unresolved.setdefault(name, []).append(location)

        self.assertEqual(
            unresolved, {},
            'Unresolvable URL names (these raise NoReverseMatch at request time):\n'
            + '\n'.join(f'  {name} <- {", ".join(locs)}' for name, locs in sorted(unresolved.items()))
        )


class TemplateResolutionTests(SimpleTestCase):
    def test_every_referenced_template_exists(self):
        missing = {}
        checked = set()

        for path in _source_files():
            try:
                text = path.read_text(encoding='utf-8')
            except (UnicodeDecodeError, OSError):
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                for match in TEMPLATE_REF.finditer(line):
                    name = next(g for g in match.groups() if g)
                    if name in checked or name in missing:
                        continue
                    try:
                        get_template(name)
                    except TemplateDoesNotExist:
                        location = f'{path.relative_to(BASE_DIR)}:{lineno}'
                        missing.setdefault(name, []).append(location)
                    except Exception:
                        # A template that exists but fails to compile is a
                        # different problem; this test only checks existence.
                        checked.add(name)
                    else:
                        checked.add(name)

        self.assertEqual(
            missing, {},
            'Missing templates (these raise TemplateDoesNotExist at request time):\n'
            + '\n'.join(f'  {name} <- {", ".join(locs)}' for name, locs in sorted(missing.items()))
        )
