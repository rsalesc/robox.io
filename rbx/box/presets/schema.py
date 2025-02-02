import pathlib
from typing import List, Optional

from pydantic import BaseModel, Field

from rbx.box.presets.fetch import PresetFetchInfo, get_preset_fetch_info


def NameField(**kwargs):
    return Field(
        pattern=r'^[a-zA-Z0-9][a-zA-Z0-9\-]*$', min_length=3, max_length=32, **kwargs
    )


class TrackedAsset(BaseModel):
    # Path of the asset relative to the root of the problem/contest that should
    # be tracked. Can also be a glob, when specified in the preset config.
    path: pathlib.Path


class Tracking(BaseModel):
    # Problem assets that should be tracked and updated by rbx
    # when the preset has an update.
    problem: List[TrackedAsset] = []

    # Contest assets that should be tracked and updated by rbx
    # when the preset has an update.
    contest: List[TrackedAsset] = []


class Preset(BaseModel):
    # Name of the preset, or a GitHub repository containing it.
    name: str = NameField()

    # URI of the preset to be fetched.
    uri: Optional[str] = None

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

    @property
    def fetch_info(self) -> PresetFetchInfo:
        if self.uri is None:
            return PresetFetchInfo(name=self.name)
        res = get_preset_fetch_info(self.uri)
        assert res is not None
        return res
