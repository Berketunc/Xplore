"""Modal Dict state with Volume backups for saved experiment records."""

from copy import deepcopy
import json
from pathlib import Path
import re
from threading import RLock


class RecordStore:
    def __init__(self, mapping, root=Path("/data/experiments"), volume=None):
        self.mapping = mapping
        self.root = Path(root)
        self.volume = volume
        self.lock = RLock()

    def put(self, key, value):
        if re.fullmatch(r"xplore-[0-9a-f]{32}", key):
            with self.lock:
                self.root.mkdir(parents=True, exist_ok=True)
                destination = self.root / f"{key}.json"
                temporary = destination.with_suffix(".tmp")
                temporary.write_text(json.dumps(value, allow_nan=False))
                temporary.replace(destination)
                if self.volume:
                    self.volume.commit()
        self.mapping[key] = deepcopy(value)

    def get(self, key):
        value = self.mapping.get(key)
        if value is not None:
            return deepcopy(value)
        if not re.fullmatch(r"xplore-[0-9a-f]{32}", key):
            return None
        with self.lock:
            if self.volume:
                self.volume.reload()
            path = self.root / f"{key}.json"
            return json.loads(path.read_text()) if path.is_file() else None
