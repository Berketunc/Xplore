"""Validate shared fixtures against experiment.schema.json.

Usage: python3 shared/validate.py            (needs: pip install jsonschema)
Backend can reuse check(obj, "Experiment") in contract tests.
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).parent
SCHEMA = json.loads((HERE / "experiment.schema.json").read_text())
Draft202012Validator.check_schema(SCHEMA)


def check(obj, ref):
    validator = Draft202012Validator({"$ref": f"#/$defs/{ref}", "$defs": SCHEMA["$defs"]})
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in validator.iter_errors(obj)]


FILES = {
    "catalog.fixture.json": "Catalog",
    "experiment.fixture.json": "Experiment",
    "experiment.partial.fixture.json": "Experiment",
}

if __name__ == "__main__":
    failed = False
    for name, ref in FILES.items():
        errors = check(json.loads((HERE / name).read_text()), ref)
        print(f"{name} ({ref}): {'OK' if not errors else 'FAIL'}")
        for err in errors:
            print("   ", err)
        failed |= bool(errors)
    sys.exit(1 if failed else 0)
