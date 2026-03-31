from typing import List, Union

from pydantic import AliasChoices, BaseModel, Field

from models.geo import Point


class Attributes(BaseModel):
    location: Union[Point, List[Point], None] = Field(
        None, validation_alias=AliasChoices("geometry", "location")
    )


class Thing(BaseModel):
    thingId: str
    attributes: Attributes
