"""Physics-only PowerSim MPM session; graphics are drawn by the browser."""

from pathlib import Path


class InteractivePhysics:
    def __init__(self, candidate="balanced", configuration=None):
        import torch
        import warp as wp
        from powersim.foam_evolve.mpm.solver import build_mpm_solver
        from backend.geometry import build_geometry

        cache = Path("/data/warp-cache/interactive")
        cache.mkdir(parents=True, exist_ok=True)
        wp.config.kernel_cache_dir = str(cache)
        wp.init()
        geometry = build_geometry(configuration or {"candidate_id": candidate})
        self.reference = torch.from_numpy(geometry.positions.copy())
        self.mesh = geometry.mesh
        self.configuration = self.mesh["configuration"]
        self.groups = {"lower": geometry.support_ids.tolist()}
        self.max_drag = min(.25, self.configuration["thickness"]*.4)
        self.dt = .001
        self.substeps = 10
        material = {"material": "jelly", "n_grid": 100, "grid_lim": 2.,
            "E": 10000*self.configuration["stiffness_multiplier"], "nu": .3, "density": 2000,
            "g": [0,0,0], "grid_v_damping_scale": .9990004498800211}
        support_z = self.mesh["support_z_max"]
        support = {"point": [1.,1.,support_z/2], "size": [1.,1.,support_z/2+1e-6],
            "velocity": [0,0,0], "start_time": 0., "end_time": 1000.}
        boundaries = [{"type": "bounding_box"}, {"type": "cuboid", **support},
            {"type": "enforce_particle_translation", **support}]
        timing = {"substep_dt": self.dt, "frame_dt": .033, "frame_num": 3000}
        points = self.reference.to("cuda:0")
        volume = torch.from_numpy(geometry.volumes.copy()).to("cuda:0")
        self.solver = build_mpm_solver(points, volume, material, boundaries, timing)
        self.solver.enforce_particle_velocity_translation([1, 1, 1], [2, 2, 2], [0, 0, 0], 0., 1000.)
        self.grab = self.solver.particle_velocity_modifier_params[-1]
        self.grab_mask = torch.zeros(len(points), dtype=torch.int32, device="cuda:0")
        self.grab.mask = wp.from_torch(self.grab_mask, dtype=wp.int32)
        self.grab_ids = None
        self.target = None
        self.vertex_ids = geometry.surface_ids
        self.vertex_ids_gpu = torch.from_numpy(self.vertex_ids.copy()).to("cuda:0")
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
            delta *= torch.clamp(self.max_drag / torch.linalg.vector_norm(delta).clamp_min(1e-9), max=1.)
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
    import json
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
    (out / "gripper-pad-mesh.json").write_text(json.dumps(model.mesh))
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
