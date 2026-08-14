from __future__ import annotations

import math
from itertools import pairwise

import pytest

from makeover_render.domain.model.camera_path import known_moves, positions_for

TARGET = (1.0, 2.0, 3.0)
DISTANCE = 5.0


class TestPositionsFor:
    def test_rejects_unknown_move(self):
        with pytest.raises(ValueError, match="unknown camera move"):
            positions_for("zoom", TARGET, DISTANCE, 10)

    def test_rejects_zero_frames(self):
        with pytest.raises(ValueError, match="frame_count"):
            positions_for("orbit", TARGET, DISTANCE, 0)

    def test_returns_one_position_per_frame(self):
        positions = positions_for("orbit", TARGET, DISTANCE, 12)
        assert len(positions) == 12

    def test_a_single_frame_does_not_divide_by_zero(self):
        # _progress guards frame_count == 1 explicitly; every move must
        # survive it without a ZeroDivisionError.
        for move in known_moves():
            positions = positions_for(move, TARGET, DISTANCE, 1)
            assert len(positions) == 1


class TestOrbit:
    def test_every_position_is_distance_from_target(self):
        positions = positions_for("orbit", TARGET, DISTANCE, 16)
        for x, y, z in positions:
            radius = math.hypot(x - TARGET[0], y - TARGET[1])
            assert radius == pytest.approx(DISTANCE)
            assert z == pytest.approx(TARGET[2])

    def test_closes_the_loop_back_near_the_start(self):
        # The last sample is one step short of a full revolution, not equal
        # to the first - a full circle sampled at N points never repeats.
        positions = positions_for("orbit", TARGET, DISTANCE, 8)
        first, last = positions[0], positions[-1]
        assert first != last


class TestDollyIn:
    def test_moves_monotonically_closer_to_the_target(self):
        positions = positions_for("dolly_in", TARGET, DISTANCE, 10)
        distances = [math.dist(p, TARGET) for p in positions]
        assert all(a >= b for a, b in pairwise(distances))
        assert distances[0] > distances[-1]

    def test_ends_at_half_the_starting_distance(self):
        positions = positions_for("dolly_in", TARGET, DISTANCE, 10)
        assert math.dist(positions[-1], TARGET) == pytest.approx(DISTANCE * 0.5)


class TestCraneDown:
    def test_descends_monotonically_to_the_targets_elevation(self):
        positions = positions_for("crane_down", TARGET, DISTANCE, 10)
        elevations = [p[2] for p in positions]
        assert all(a >= b for a, b in pairwise(elevations))
        assert elevations[-1] == pytest.approx(TARGET[2])


class TestPan:
    def test_sweeps_symmetrically_around_the_start(self):
        positions = positions_for("pan", TARGET, DISTANCE, 11)
        first, middle, last = positions[0], positions[5], positions[-1]
        assert first[0] == pytest.approx(-last[0] + 2 * TARGET[0], abs=1e-9)
        assert middle[0] == pytest.approx(TARGET[0], abs=1e-9)


def test_known_moves_matches_every_registered_builder():
    assert set(known_moves()) == {"orbit", "dolly_in", "crane_down", "pan"}
