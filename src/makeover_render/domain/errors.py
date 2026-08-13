"""Domain-level error taxonomy.

Mirrors the discovery repo's shape on purpose - both repos map these onto their
own interface vocabulary (HTTP status, CLI exit code), so keeping the taxonomy
recognisable between them costs nothing and pays off whenever someone works on
both in the same sitting.
"""

from __future__ import annotations


class RenderError(Exception):
    """Base class for every error this service raises deliberately."""


class UnknownTemplateError(RenderError):
    """A ``SceneSpec`` names a template this renderer has no geometry for.

    Distinct from a manifest mismatch: the manifest lists template *metadata*
    for callers; this is the internal registry of *how to build* one, and the
    two must never silently drift apart.
    """


class BuildFailedError(RenderError):
    """Blender ran but did not produce a usable artifact."""
