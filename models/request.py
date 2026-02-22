from pydantic import BaseModel
from typing import List, Optional
from models.thing import Thing


class SearchResponse(BaseModel):
    items: List[Thing]
    cursor: Optional[str]
