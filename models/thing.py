from typing import Union, List
from models.geo import Point
from pydantic import BaseModel, Field, AliasChoices


class Attributes(BaseModel):
    location: Union[Point, List[Point], None] = Field(
        None, validation_alias=AliasChoices("geometry", "location")
    )


class Thing(BaseModel):
    thingId: str
    attributes: Attributes
