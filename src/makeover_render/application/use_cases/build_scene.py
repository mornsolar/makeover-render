"""Turn a ``SceneSpec`` into a ``.glb``, failing before Blender launches if the
spec cannot possibly build."""

from __future__ import annotations

from pathlib import Path

from makeover_contracts.scene import SceneSpec

from makeover_render.application.ports.scene_builder import BuildArtifact, SceneBuilder
from makeover_render.domain.errors import BuildFailedError
from makeover_render.domain.model.template_geometry import geometry_for


class BuildScene:
    """Validates a spec against this renderer's own build recipes, then builds.

    Distinct from the ``CapabilityManifest`` check Repo A runs before it ever
    submits a job: that check asks "is this allowed"; this one asks "can this
    registry actually build it", which is the more specific question once a
    concrete ``SceneSpec`` is in hand.
    """

    def __init__(self, builder: SceneBuilder) -> None:
        self._builder = builder

    def execute(self, spec: SceneSpec, out_dir: Path) -> BuildArtifact:
        geometry = geometry_for(spec.template_id)
        # ``spec.materials[*].slot`` is the contracts enum; the domain registry
        # only knows plain strings (see template_geometry's module docstring),
        # so the comparison happens on the wire value both sides agree on.
        assigned_slots = {assignment.slot.value for assignment in spec.materials}
        missing = geometry.required_slots - assigned_slots
        if missing:
            names = ", ".join(sorted(missing))
            # Launching Blender for a spec that is already known to be
            # incomplete would waste a multi-second subprocess just to fail
            # with a less specific error inside it.
            raise BuildFailedError(f"template {spec.template_id!r} requires materials for: {names}")
        out_dir.mkdir(parents=True, exist_ok=True)
        return self._builder.build(spec, out_dir)
