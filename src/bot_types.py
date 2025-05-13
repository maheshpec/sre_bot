from typing import Optional

from pydantic import AnyHttpUrl
from pydantic import BaseModel


class State(BaseModel):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    comments: Optional[list[str]] = None

    messages: Optional[list] = None
    matched_runbooks: Optional[list[AnyHttpUrl]] = None


class IndexerState(BaseModel):
    docs: Optional[list] = None
    loaded_docs: Optional[list] = None
