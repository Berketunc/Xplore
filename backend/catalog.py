"""Catalog for the registered, bounded single-pillow compression experiment."""

from copy import deepcopy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def get_catalog(*, available=False, numerical_quality=None):
    catalog = json.loads((ROOT / "shared/catalog.fixture.json").read_text())
    catalog["fixture"] = False
    test = catalog["tests"][0]
    test["availability"] = "available" if available else "proposed"
    test["title"] = "Exploratory pillow compression pulse"
    test["scene"].update({
        "display_name": "Prepared pillow",
        "description": "One isolated pillow. Its lower 15% is supported and its upper 15% receives a downward load pulse for 0.1 simulation seconds. Gravity is off.",
        "preview_url": "/v1/examples/reference.png" if available else None,
    })
    test["metric"].update({
        "definition": "100 × reduction in the vertical separation of fixed upper/lower particle-group centroids, divided by their unloaded separation. Groups are the upper/lower 15% by initial height.",
        "window_description": "Peak positive compression over 0–2.0 simulation seconds. The reference is captured before stepping; IDs and regions remain fixed.",
    })
    test["load"].update({"min": 1., "max": 1., "step": 1., "default": 1.})
    test["target"]["default"] = 15.
    test["assumptions"] = [
        "Only Young's modulus differs between Flexible (0.5×), Balanced (1×), and Firm (2×). Density, Poisson's ratio, geometry, supports, load, timestep, duration and camera are identical.",
        "A uniform downward force per particle acts on the fixed upper 15% for 0.1 simulation seconds, followed by free response until 2.0 seconds. The lower 15% is held by particle/grid velocity constraints; gravity is off and there is no rigid plate.",
        "Only the tested reference load multiplier 1.0 is currently enabled.",
        "The released scene is not dimensionally calibrated. Load and stiffness values are simulator parameters; no prediction in newtons or millimetres is implied.",
        "These are hypothetical stiffness scenarios, not named or validated commercial materials.",
        "Compression screens geometric deformation. Transmitted force, energy absorption, recovery, fatigue and physical agreement have not been validated.",
    ]
    if numerical_quality:
        test["numerical_quality"] = deepcopy(numerical_quality)
        if numerical_quality["status"] == "timestep_sensitive":
            test["assumptions"].insert(0, numerical_quality["note"])
            test["scene"]["description"] += f" Exploratory result: the timestep check changed Balanced's peak by {numerical_quality['timestep_relative_change']:.1%}; shortlists are provisional."
    return deepcopy(catalog)
