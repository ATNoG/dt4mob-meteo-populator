from enum import Enum
from typing import List, Union

from pydantic import AliasChoices, BaseModel, Field

from models.geo import Point


class Attributes(BaseModel):
    location: Union[Point, List[Point], None] = Field(
        None, validation_alias=AliasChoices("geometry", "location", "coordinates")
    )


class Thing(BaseModel):
    thingId: str
    attributes: Attributes


class PopulateResult(str, Enum):
    SUCCESS = "success"
    NO_STATIONS = "no_stations"
    NO_LOCATION = "no_locations"
    ERR = "error"
