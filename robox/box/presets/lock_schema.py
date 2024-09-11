from typing import List

from pydantic import BaseModel

from robox.box.presets.schema import TrackedAsset


class LockedAsset(TrackedAsset):
    hash: str


class PresetLock(BaseModel):
    preset_name: str

    assets: List[LockedAsset] = []
