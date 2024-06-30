import pathlib
from typing import Optional

from pydantic import BaseModel


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
