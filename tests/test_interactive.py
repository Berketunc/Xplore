import unittest
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.interactive import validate_command
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
        for _ in range(20):
            response = self.client.post("/v1/interactive/sessions", json={"candidate_id": "balanced"})
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["max_live_seconds"], 90)
        self.assertEqual(self.client.post("/v1/interactive/sessions", json={"candidate_id": "balanced"}).status_code, 429)

    def test_active_worker_does_not_consume_a_new_slot(self):
        self.claims.values["interactive-active"] = {"id": "active", "expires": time.time()+90}
        self.assertEqual(self.client.post("/v1/interactive/sessions", json={"candidate_id": "balanced"}).status_code, 409)
        self.assertEqual(len(self.claims.values), 1)

    def test_unknown_stiffness_is_rejected_before_reservation(self):
        self.assertEqual(self.client.post("/v1/interactive/sessions", json={"candidate_id": "unregistered"}).status_code, 422)
        self.assertEqual(self.claims.values, {})
