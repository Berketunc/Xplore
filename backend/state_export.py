"""Minimal additive export adapter for the pinned PowerSim simulate.py.

Apply only after the unmodified released example has been reproduced. No solver
equations, boundary conditions, timesteps, material assignment, or rendering are
changed. Each subprocess owns its patched source copy.
"""

from pathlib import Path


def patched_source(source):
    before_loop = '    for frame in tqdm(range(time_params["frame_num"]), desc="Simulating"):\n'
    reference_export = '''    if save_positions:
        xplore_state_dir = output_path / "xplore_state"
        xplore_state_dir.mkdir(exist_ok=True)
        save_uint8_rgb_png(backdrop, str(output_path / "reference.png"))
        torch.save({
            "particle_ids": indices.detach().to(torch.int64).cpu(),
            "positions_mpm": mpm_solver.export_particle_x_to_torch().detach().float().cpu(),
        }, xplore_state_dir / "reference.pt")
        (xplore_state_dir / "metadata.json").write_text(json.dumps({
            "format": "xplore.positions.v1",
            "coordinate_system": "mpm",
            "unit_system": "relative_dimensionless",
            "position_dtype": "float32",
            "reference_time": 0.0,
            "reference_is_before_stepping": True,
            "frame_dt": step_per_frame * substep_dt,
            "requested_frame_dt": time_params["frame_dt"],
            "substep_dt": substep_dt,
            "substeps_per_frame": step_per_frame,
            "frame_count": time_params["frame_num"],
            "scale_factor": float(scale_factor),
            "original_mean_pos": original_mean_pos.detach().float().cpu().tolist(),
            "rotation_degree": preprocessing_params["rotation_degree"],
            "rotation_axis": preprocessing_params["rotation_axis"],
        }, indent=2))

'''
    after_position = '        x = mpm_solver.export_particle_x_to_torch()\n'
    frame_export = '''        if not torch.isfinite(x).all():
            raise RuntimeError(f"Nonfinite simulated positions at frame {frame}")
        if save_positions:
            torch.save({
                "time": (frame + 1) * step_per_frame * substep_dt,
                "positions_mpm": x.detach().float().cpu(),
                "max_speed_mpm": float(torch.linalg.vector_norm(mpm_solver.export_particle_v_to_torch(), dim=1).max()),
            }, xplore_state_dir / f"frame_{frame:04d}.pt")
'''
    if source.count(before_loop) != 1 or source.count(after_position) != 1:
        raise ValueError("Export anchors do not match the pinned PowerSim source")
    updated = source.replace(before_loop, reference_export + before_loop).replace(after_position, after_position + frame_export)
    return updated.replace("import torch\n", "import torch\n\ntorch.manual_seed(0)\nnp.random.seed(0)\n", 1)


def apply_export_adapter(simulate_file):
    import hashlib

    path = Path(simulate_file)
    original = path.read_text()
    updated = patched_source(original)
    path.write_text(updated)
    return {
        "adapter": "xplore-state-export-v1",
        "original_sha256": hashlib.sha256(original.encode()).hexdigest(),
        "patched_sha256": hashlib.sha256(updated.encode()).hexdigest(),
    }
