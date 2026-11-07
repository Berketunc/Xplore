"""Bounded procedural specimens shared by CPU preview and the GPU solver."""

from dataclasses import dataclass
from typing import Annotated, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat


class InteractiveConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    object_type: Literal["gripper_pad", "material_block"] = "gripper_pad"
    candidate_id: Literal["flexible", "balanced", "firm"] = "balanced"
    width: Annotated[FiniteFloat, Field(ge=.5, le=1.1)] | None = None
    depth: Annotated[FiniteFloat, Field(ge=.3, le=.9)] | None = None
    thickness: Annotated[FiniteFloat, Field(ge=.16, le=.6)] | None = None
    stiffness_multiplier: Annotated[FiniteFloat, Field(ge=.5, le=2.)] | None = None

    def resolved(self):
        pad = self.object_type == "gripper_pad"
        return {"object_type": self.object_type, "candidate_id": self.candidate_id,
            "width": self.width if self.width is not None else (1. if pad else .6),
            "depth": self.depth if self.depth is not None else .6,
            "thickness": self.thickness if self.thickness is not None else (.25 if pad else .6),
            "stiffness_multiplier": self.stiffness_multiplier if self.stiffness_multiplier is not None else
                {"flexible": .5, "balanced": 1., "firm": 2.}[self.candidate_id]}


@dataclass
class Geometry:
    positions: np.ndarray
    volumes: np.ndarray
    surface_ids: np.ndarray
    support_ids: np.ndarray
    mesh: dict


def build_geometry(configuration=None):
    config = InteractiveConfig.model_validate(configuration or {}).resolved()
    dimensions = np.array([config["width"], config["depth"], config["thickness"]])
    counts = np.ceil(dimensions / .025).astype(int)+1
    axes = [np.linspace(1-d/2, 1+d/2, n) for d, n in zip(dimensions, counts)]
    positions = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3).astype(np.float32)
    # Tensor-product trapezoidal nodal volumes sum to the exact cuboid volume.
    weights = []
    for d, n in zip(dimensions, counts):
        w = np.full(n, d/(n-1))
        w[[0, -1]] *= .5
        weights.append(w)
    volumes = np.einsum("i,j,k->ijk", *weights).reshape(-1).astype(np.float32)
    support_z = float(axes[2][0]+dimensions[2]*.15)
    support_ids = np.flatnonzero(positions[:, 2] <= support_z+1e-7)
    nodes = np.arange(len(positions)).reshape(tuple(counts))
    samples = [sorted(set(range(0, int(n), 2)) | {int(n)-1}) for n in counts]
    particle_ids, triangles, remap = [], [], {}

    def vertex(index):
        if index not in remap:
            remap[index] = len(particle_ids)
            particle_ids.append(index)
        return remap[index]

    for normal_axis in range(3):
        a, b = [i for i in range(3) if i != normal_axis]
        for side in (0, int(counts[normal_axis])-1):
            for i, ni in zip(samples[a][:-1], samples[a][1:]):
                for j, nj in zip(samples[b][:-1], samples[b][1:]):
                    corners = []
                    for u, v in ((i,j), (ni,j), (ni,nj), (i,nj)):
                        index = [0,0,0]
                        index[normal_axis], index[a], index[b] = side, u, v
                        corners.append(int(nodes[tuple(index)]))
                    for face in ((0,1,2), (0,2,3)):
                        ids = [corners[k] for k in face]
                        normal = np.cross(positions[ids[1]]-positions[ids[0]], positions[ids[2]]-positions[ids[0]])
                        if normal[normal_axis]*(1 if side else -1) < 0:
                            ids.reverse()
                        triangles.extend(vertex(k) for k in ids)
    surface_ids = np.array(particle_ids, dtype=np.int64)
    supported = set(support_ids.tolist())
    mesh = {"schema_version": "1.0", "engine": "powersim_mpm", "representation": "structured_surface_proxy",
        "object_type": config["object_type"], "display_name": "Silicone-inspired gripper pad" if config["object_type"] == "gripper_pad" else "Elastic material test block",
        "configuration": config, "positions": positions[surface_ids].flatten().tolist(),
        "triangles": triangles, "particle_ids": particle_ids,
        "particle_count": len(positions), "supported_particle_ids": [i for i in particle_ids if i in supported],
        "support_z_max": support_z, "center": [1.,1.,1.], "unit_system": "dimensionless",
        "notice": "Generic elastic material inspired by silicone robotics. No commercial silicone is calibrated; physical agreement and numerical convergence are not established."}
    return Geometry(positions, volumes, surface_ids, support_ids, mesh)
