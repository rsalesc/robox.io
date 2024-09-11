import pathlib
from typing import List, Optional

from pydantic import BaseModel, Field


class TrackedAsset(BaseModel):
    # Path of the asset relative to the root of the problem/contest that should
    # be tracked.
    path: pathlib.Path


class Tracking(BaseModel):
    # Problem assets that should be tracked and updated by robox
    # when the preset has an update.
    problem: List[TrackedAsset] = []

    # Contest assets that should be tracked and updated by robox
    # when the preset has an update.
    contest: List[TrackedAsset] = []


class Preset(BaseModel):
    # Name of the preset.
    name: str

    # Path to the environment file that will be installed with this preset.
    # When copied to the box environment, the environment will be named `name`.
    env: Optional[pathlib.Path] = None

    # Path to the contest preset directory, relative to the preset directory.
    problem: Optional[pathlib.Path] = None

    # Path to the problem preset directory, relative to the preset directory.
    contest: Optional[pathlib.Path] = None

    # Configures how preset assets should be tracked and updated when the
    # preset has an update. Usually useful when a common library used by the
    # package changes in the preset, or when a latex template is changed.
    tracking: Tracking = Field(default_factory=Tracking)
