import unittest

import numpy as np

from backend.metrics import deformation_series


class MetricTests(unittest.TestCase):
    def test_compression_is_invariant_to_rigid_translation(self):
        reference = np.array([[0., 0., 0.], [0., 0., 1.]])
        compressed = np.array([[0., 0., 0.], [0., 0., .8]]) + [4., 7., 3.]
        result = deformation_series(reference, [compressed], [.1], upper=[1], lower=[0], axis=[0, 0, 1], metric="compression")
        self.assertAlmostEqual(result["deformation_pct"], 20)

    def test_deflection_removes_support_motion(self):
        reference = np.array([[0., 0., 0.], [0., 0., 1.]])
        frame = reference + [3., 0., 0.]
        frame[1, 0] += .25
        result = deformation_series(reference, [frame], [.1], upper=[1], lower=[0], axis=[1, 0, 0], metric="deflection", reference_length=1)
        self.assertAlmostEqual(result["deformation_pct"], 25)

    def test_invalid_state_is_rejected(self):
        with self.assertRaises(ValueError):
            deformation_series([[0, 0, 0], [0, 0, 1]], [[[0, 0, 0], [0, 0, float("inf")]]], [.1], upper=[1], lower=[0], axis=[0, 0, 1], metric="compression")

    def test_zero_reference_length_is_rejected(self):
        with self.assertRaises(ValueError):
            deformation_series([[0, 0, 0], [1, 0, 0]], [[[0, 0, 0], [1, 0, 0]]], [.1], upper=[1], lower=[0], axis=[0, 0, 1], metric="compression")
