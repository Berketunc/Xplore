import unittest
import time
from collections import Counter

import numpy as np

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.interactive import validate_command
from backend.geometry import build_geometry
from backend.live_api import install_interactive_routes


class InteractionCommandTests(unittest.TestCase):
    def test_grab_and_move_accept_bounded_coordinates(self):
        grab = {"type": "grab", "point": [1, 1, 1.3], "target": [1, 1, 1.3]}
        self.assertEqual(validate_command(grab), grab)
        self.assertEqual(validate_command({"type": "move", "target": [1., 1., 1.2]}), {"type": "move", "target": [1., 1., 1.2]})

    def test_invalid_grab_targets_are_rejected(self):
        for target in [[float("nan"),1,1], [True,1,1], [0,1,1], [1,1], "1,1,1"]:
            with self.assertRaises(ValueError):
                validate_command({"type": "grab", "point": [1,1,1], "target": target})

    def test_unsupported_commands_are_rejected(self):
        for command in [{"type": "set_timestep"}, {"type": "grab", "target": [1,1,1]}, None]:
            with self.assertRaises(ValueError):
                validate_command(command)

    def test_release_reset_and_stop_need_no_coordinates(self):
        for kind in ["release", "reset", "stop"]:
            self.assertEqual(validate_command({"type": kind}), {"type": kind})


class SessionAllowanceTests(unittest.TestCase):
    def setUp(self):
        class Claims:
            def __init__(self):
                self.values = {}
            def get(self, key):
                return self.values.get(key)
            def put(self, key, value, skip_if_exists=False):
                if skip_if_exists and key in self.values:
                    return False
                self.values[key] = value
                return True
        self.claims = Claims()
        app = FastAPI()
        install_interactive_routes(app, claims=self.claims, volume=None, stream_function=None)
        self.client = TestClient(app)

    def test_session_allowance_is_bounded_without_starting_gpu(self):
        for _ in range(25):
            response = self.client.post("/v1/interactive/sessions", json={"candidate_id": "balanced"})
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["max_live_seconds"], 90)
        self.assertEqual(self.client.post("/v1/interactive/sessions", json={"candidate_id": "balanced"}).status_code, 429)

    def test_presentation_allowance_preserves_used_slots_and_adds_only_five(self):
        for slot in range(20):
            self.claims.values[f"interactive-credit-v1-{slot}"] = "already-used"
        for remaining in range(4, -1, -1):
            response = self.client.post("/v1/interactive/sessions", json={"candidate_id":"balanced"})
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["remaining_starts"], remaining)
        self.assertEqual(self.client.post("/v1/interactive/sessions", json={}).status_code, 429)
        for slot in range(20):
            self.assertEqual(self.claims.values[f"interactive-credit-v1-{slot}"], "already-used")

    def test_active_worker_does_not_consume_a_new_slot(self):
        self.claims.values["interactive-active"] = {"id": "active", "expires": time.time()+90}
        self.assertEqual(self.client.post("/v1/interactive/sessions", json={"candidate_id": "balanced"}).status_code, 409)
        self.assertEqual(len(self.claims.values), 1)

    def test_unknown_stiffness_is_rejected_before_reservation(self):
        self.assertEqual(self.client.post("/v1/interactive/sessions", json={"candidate_id": "unregistered"}).status_code, 422)
        self.assertEqual(self.claims.values, {})

    def test_preview_does_not_reserve_a_session(self):
        response = self.client.post("/v1/interactive/preview", json={"object_type":"gripper_pad", "thickness":.4, "stiffness_multiplier":1.3})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["configuration"]["thickness"], .4)
        self.assertEqual(self.claims.values, {})

    def test_geometry_and_material_are_preserved_for_worker(self):
        config = {"object_type":"material_block", "width":.8, "depth":.5, "thickness":.4, "stiffness_multiplier":1.3}
        response = self.client.post("/v1/interactive/sessions", json=config)
        self.assertEqual(response.status_code, 201)
        saved = self.claims.values["interactive-session:"+response.json()["session_id"]]["configuration"]
        for key, value in config.items():
            self.assertEqual(saved[key], value)

    def test_invalid_custom_tests_are_rejected_before_reservation(self):
        for config in [{"width": 100}, {"thickness":0}, {"stiffness_multiplier":10}, {"object_type":"unsupported"}, {"width":True}]:
            self.assertEqual(self.client.post("/v1/interactive/sessions", json=config).status_code, 422)
        self.assertEqual(self.claims.values, {})


class GeometryTests(unittest.TestCase):
    def test_dimensions_volume_support_and_closed_surface(self):
        geometry = build_geometry()
        np.testing.assert_allclose(np.ptp(geometry.positions, axis=0), [1,.6,.25], atol=1e-6)
        self.assertAlmostEqual(float(geometry.volumes.sum()), 1*.6*.25, places=6)
        self.assertTrue(np.all(geometry.volumes > 0))
        self.assertTrue(np.all(geometry.positions[geometry.support_ids,2] <= geometry.mesh["support_z_max"]+1e-7))
        self.assertLess(len(geometry.support_ids), len(geometry.positions)//3)
        faces = np.array(geometry.mesh["triangles"]).reshape(-1,3)
        edges = Counter(tuple(sorted((int(face[i]), int(face[(i+1)%3])))) for face in faces for i in range(3))
        self.assertTrue(all(count == 2 for count in edges.values()))
        xyz = geometry.positions[geometry.surface_ids]
        normals = np.cross(xyz[faces[:,1]]-xyz[faces[:,0]],xyz[faces[:,2]]-xyz[faces[:,0]])
        self.assertTrue(np.all(np.einsum("ij,ij->i", normals, xyz[faces].mean(axis=1)-1) > 0))

    def test_new_specimen_changes_particle_geometry(self):
        pad = build_geometry()
        block = build_geometry({"object_type":"material_block", "width":.8, "stiffness_multiplier":1.4})
        self.assertNotEqual(len(pad.positions),len(block.positions))
        np.testing.assert_allclose(np.ptp(block.positions,axis=0), [.8,.6,.6], atol=1e-6)
        self.assertEqual(block.mesh["configuration"]["stiffness_multiplier"],1.4)
