"""Loads the editable data tables in app/data/."""
from __future__ import annotations

import json
import os
from functools import lru_cache

DATA = os.path.join(os.path.dirname(__file__), "..", "data")


@lru_cache(maxsize=None)
def load(name: str) -> dict:
    with open(os.path.join(DATA, f"{name}.json"), encoding="utf-8") as f:
        return json.load(f)


def reload():
    load.cache_clear()
