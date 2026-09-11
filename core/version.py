"""
Single source of truth for the version string shown in the UI footer.

This lived inline in beta/context_processors.py as two hardcoded literals, which
meant every release had to remember to edit a context processor.
"""

# Bump on release. RELEASE_NOTES.md documents what changed.
STABLE_VERSION = 'v1.0.0 - stable'
BETA_VERSION = 'v1.1.0-beta.1'
