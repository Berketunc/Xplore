"""Measure fixed particle groups against a genuine unloaded reference.

All calculations use float64, but source exports must retain at least float32
precision. Regions are fixed once at t=0 and reused by stable particle ID.
"""

import numpy as np


def _positions(value):
    result = np.asarray(value, dtype=np.float64)
    if result.ndim != 2 or result.shape[1] != 3 or not len(result):
        raise ValueError("Positions must be a nonempty N by 3 array")
    if not np.isfinite(result).all():
        raise ValueError("Positions contain NaN or Inf")
    return result


def _group(value, count):
    raw = np.asarray(value)
    if raw.ndim != 1 or not len(raw) or raw.dtype.kind not in "iu":
        raise ValueError("Particle groups must contain integer row indices")
    result = raw.astype(np.int64)
    if np.any(result < 0) or np.any(result >= count) or len(np.unique(result)) != len(result):
        raise ValueError("Particle group indices must be in range and unique")
    return result


def deformation_series(reference, frames, times, *, upper, lower, axis, metric, reference_length=None):
    """Return signed series and peak positive deformation over the given interval.

    compression: reduction of upper/lower centroid separation.
    deflection: upper/ROI centroid displacement relative to lower/support,
    projected onto the declared positive loading direction.
    """
    initial = _positions(reference)
    upper = _group(upper, len(initial))
    lower = _group(lower, len(initial))
    if np.intersect1d(upper, lower).size:
        raise ValueError("Measurement groups must not overlap")
    direction = np.asarray(axis, dtype=np.float64)
    if direction.shape != (3,) or not np.isfinite(direction).all() or np.linalg.norm(direction) == 0:
        raise ValueError("Loading axis must be a finite, nonzero 3-vector")
    direction = direction / np.linalg.norm(direction)
    initial_separation = float((initial[upper].mean(0) - initial[lower].mean(0)) @ direction)
    if metric == "compression":
        length = initial_separation
    elif metric == "deflection":
        if reference_length is None:
            raise ValueError("Deflection requires an explicit reference length")
        length = float(reference_length)
    else:
        raise ValueError("Unknown deformation metric")
    if not np.isfinite(length) or length <= 0:
        raise ValueError("Initial reference length must be positive and finite")
    samples = [{"time": 0.0, "deformation_pct": 0.0}]
    last_time = 0.0
    if len(frames) != len(times) or not len(frames):
        raise ValueError("Frames and times must be nonempty and equal in length")
    for frame, time in zip(frames, times):
        state = _positions(frame)
        if state.shape != initial.shape:
            raise ValueError("Particle count/order must match the unloaded reference")
        time = float(time)
        if not np.isfinite(time) or time <= last_time:
            raise ValueError("Sample times must be finite, positive, and strictly increasing")
        separation = float((state[upper].mean(0) - state[lower].mean(0)) @ direction)
        delta = initial_separation - separation if metric == "compression" else separation - initial_separation
        samples.append({"time": time, "deformation_pct": 100.0 * delta / length})
        last_time = time
    return {
        "metric_id": f"peak-normalized-{metric}-v1",
        "aggregation": "peak_positive_over_fixed_interval",
        "reference_length": length,
        "interval": [0.0, last_time],
        "deformation_pct": max(sample["deformation_pct"] for sample in samples),
        "time_series": samples,
    }
