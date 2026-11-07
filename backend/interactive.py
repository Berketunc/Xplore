"""Physics-only PowerSim MPM session; graphics are drawn by the browser."""

import json
from pathlib import Path


class InteractivePhysics:
    def __init__(self, candidate="balanced"):
        import numpy as np
        import torch
        import warp as wp
        from scipy.spatial import ConvexHull
        from powersim.core.primitive_state import compute_grid_occupancy_volume
        from powersim.core.thirdparty_paths import ensure_physgaussian_on_path, load_physgaussian_decode_param
        from powersim.foam_evolve.mpm.solver import build_mpm_solver

        cache = Path("/data/warp-cache/interactive")
        cache.mkdir(parents=True, exist_ok=True)
        wp.config.kernel_cache_dir = str(cache)
        wp.init()
        registry = json.loads(Path("/data/controlled/registry.json").read_text())
        directory = Path("/data/runs") / registry["runs"]["balanced"]
        reference = torch.load(directory / "xplore_state/reference.pt", map_location="cpu", weights_only=True)
        self.reference = reference["positions_mpm"].float()
        self.groups = json.loads((directory / "groups.json").read_text())
        self.dt = .001
        self.substeps = 10
        ensure_physgaussian_on_path()
        decoder = load_physgaussian_decode_param()
        material, boundaries, timing, _, _ = decoder.decode_param_json(str(directory / "config.json"))
        material["E"] = 10000 * {"flexible": .5, "balanced": 1., "firm": 2.}[candidate]
        timing["substep_dt"] = self.dt
        boundaries = [bc for bc in boundaries if bc["type"] != "particle_impulse"]
        points = self.reference.to("cuda:0")
        volume = compute_grid_occupancy_volume(points, material["n_grid"], material["grid_lim"] / material["n_grid"])
        self.solver = build_mpm_solver(points, volume, material, boundaries, timing)
        self.solver.enforce_particle_velocity_translation([1, 1, 1], [2, 2, 2], [0, 0, 0], 0., 1000.)
        self.grab = self.solver.particle_velocity_modifier_params[-1]
        self.grab_mask = torch.zeros(len(points), dtype=torch.int32, device="cuda:0")
        self.grab.mask = wp.from_torch(self.grab_mask, dtype=wp.int32)
        self.grab_ids = None
        self.target = None
        hull = ConvexHull(self.reference.numpy())
        self.vertex_ids = np.unique(hull.simplices).astype(np.int64)
        remap = np.full(len(points), -1, dtype=np.int64)
        remap[self.vertex_ids] = np.arange(len(self.vertex_ids))
        faces = hull.simplices.copy()
        xyz = self.reference.numpy()
        for i, face in enumerate(faces):
            normal = np.cross(xyz[face[1]]-xyz[face[0]], xyz[face[2]]-xyz[face[0]])
            if np.dot(normal, hull.equations[i, :3]) < 0:
                faces[i] = face[[0, 2, 1]]
        self.vertex_ids_gpu = torch.tensor(self.vertex_ids, device="cuda:0")
        supported = set(self.groups["lower"])
        self.mesh = {"schema_version": "1.0", "engine": "powersim_mpm", "representation": "convex_surface_proxy",
            "positions": self.reference[self.vertex_ids].flatten().tolist(),
            "triangles": remap[faces].flatten().tolist(), "particle_ids": self.vertex_ids.tolist(),
            "supported_particle_ids": [int(i) for i in self.vertex_ids if i in supported],
            "center": [1., 1., 1.], "unit_system": "dimensionless",
            "notice": "Exploratory PowerSim MPM physics with a browser-rendered surface proxy. Physical agreement and numerical convergence are not established."}
        self.frame = 0

    def grab_particle(self, particle_id, target):
        import torch
        if not 0 <= particle_id < len(self.reference) or particle_id in self.groups["lower"]:
            return False
        positions = self.solver.export_particle_x_to_torch()
        self.grab_ids = torch.linalg.vector_norm(positions-positions[particle_id], dim=1) < .08
        self.grab_ids[self.groups["lower"]] = False
        self.grab_mask.copy_(self.grab_ids.to(torch.int32))
        self.grab_origin = positions[self.grab_ids].mean(0).detach().clone()
        self.move(target)
        return True

    def grab_point(self, point, target):
        import torch
        positions = self.solver.export_particle_x_to_torch()
        point = torch.tensor(point, dtype=torch.float32, device="cuda:0")
        particle = int(torch.linalg.vector_norm(positions-point, dim=1).argmin())
        if particle in self.groups["lower"]:
            return False
        return self.grab_particle(particle, target)

    def move(self, target):
        import torch
        if self.grab_ids is not None:
            value = torch.tensor(target, dtype=torch.float32, device="cuda:0")
            delta = value-self.grab_origin
            delta *= torch.clamp(.25 / torch.linalg.vector_norm(delta).clamp_min(1e-9), max=1.)
            self.target = self.grab_origin+delta

    def release(self):
        self.grab_mask.zero_()
        self.grab_ids = None
        self.target = None

    def step(self):
        import torch
        import warp as wp
        from powersim.foam_evolve.mpm.solver import step_frame

        if self.grab_ids is not None and self.target is not None:
            positions = self.solver.export_particle_x_to_torch()
            velocity = (self.target - positions[self.grab_ids].mean(0)) * 8.
            velocity *= torch.clamp(.5 / torch.linalg.vector_norm(velocity).clamp_min(1e-9), max=1.)
            self.grab.velocity = wp.vec3(*velocity.tolist())
        step_frame(self.solver, self.substeps, self.dt, frame=self.frame)
        self.frame += 1
        positions = self.solver.export_particle_x_to_torch()
        if not torch.isfinite(positions).all():
            raise RuntimeError("The live simulation became nonfinite")
        return positions[self.vertex_ids_gpu].detach().float().cpu().flatten().tolist()


def benchmark():
    import time
    import warp as wp

    started = time.monotonic()
    model = InteractivePhysics()
    initialization = time.monotonic()-started
    for _ in range(3):
        model.step()
    # Pick an actual renderable upper vertex for the drag benchmark.
    node = max(model.mesh["particle_ids"], key=lambda i: float(model.reference[i,2]))
    target = model.reference[node].tolist()
    target[2] -= .12
    model.grab_particle(node, target)
    wp.synchronize()
    started = time.monotonic()
    for _ in range(60):
        frame = model.step()
    elapsed = time.monotonic()-started
    out = Path("/data/interactive")
    out.mkdir(exist_ok=True)
    (out / "pillow-mesh.json").write_text(json.dumps(model.mesh))
    return {"initialization_seconds": initialization, "updates": 60, "physics_wall_seconds": elapsed,
        "updates_per_second": 60/elapsed, "simulation_seconds": 60*model.dt*model.substeps,
        "particle_count": len(model.reference), "surface_vertices": len(model.vertex_ids),
        "frame_json_bytes": len(json.dumps(frame)),
        "finite": True, "surface_mesh_saved": True}


def validate_command(message):
    import math
    if not isinstance(message, dict) or message.get("type") not in ("grab", "move", "release", "reset", "stop"):
        raise ValueError("Unsupported interaction command")
    command = {"type": message["type"]}
    if command["type"] in ("grab", "move"):
        target = message.get("target")
        if not isinstance(target, list) or len(target) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) or not .15 <= v <= 1.85 for v in target):
            raise ValueError("Target must be a finite, bounded 3D position")
        command["target"] = target
    if command["type"] == "grab":
        point = message.get("point")
        if not isinstance(point, list) or len(point) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) or not .15 <= v <= 1.85 for v in point):
            raise ValueError("Grab point must be a finite, bounded 3D position")
        command["point"] = point
    return command
