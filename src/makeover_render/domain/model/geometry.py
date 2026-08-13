"""Primitive geometry types shared by the template registry and the resolver.

Plain tuples and dataclasses, no ``bpy`` and no third-party dependency, so the
same module imports cleanly in this service's own venv *and* inside Blender's
bundled interpreter once the build script adds ``src`` to its path.
"""

from __future__ import annotations

from dataclasses import dataclass

Vec3 = tuple[float, float, float]
"""(x, y, z) in metres, or as a 0..1 fraction of a dimension - callers know
which from context, the same way ``UnitInterval`` elsewhere is unitless."""


@dataclass(frozen=True)
class Dimensions:
    """A stand-in for ``makeover_contracts.scene.StorefrontDimensions``.

    Deliberately not that type: this module is imported from inside Blender's
    bundled interpreter, which has neither this service's virtualenv nor
    ``pydantic`` on its path, and importing ``makeover_contracts.scene`` pulls
    in ``pydantic`` as a side effect of the module load, not of any one name
    used from it.
    """

    width_m: float
    height_m: float
    depth_m: float
