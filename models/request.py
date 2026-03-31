from typing import List, Optional

from pydantic import BaseModel

from models.thing import Thing


class SearchResponse(BaseModel):
    items: List[Thing]
    cursor: Optional[str] = None
