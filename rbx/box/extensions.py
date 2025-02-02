from typing import Optional

from pydantic import BaseModel, Field

from rbx.box.packaging.boca.extension import BocaExtension, BocaLanguageExtension


# List of extensions defined in-place.
class MacExtension(BaseModel):
    gpp_alternative: Optional[str] = None


# Extension abstractions.
class Extensions(BaseModel):
    mac: Optional[MacExtension] = Field(
        None, description='Extension for setting mac-only configuration.'
    )
    boca: Optional[BocaExtension] = Field(
        None, description='Environment-level extensions for BOCA packaging.'
    )


class LanguageExtensions(BaseModel):
    boca: Optional[BocaLanguageExtension] = Field(
        None, description='Language-level extensions for BOCA packaging.'
    )
