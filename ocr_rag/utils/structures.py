from typing import Any
from pydantic import BaseModel
from datetime import datetime


class UploadedFile(BaseModel):
    uuid: str
    name: str
    filetype: str
    path: str = None
    date: datetime = None


class QueryResponse(BaseModel):
    question: str
    output_text: str
    input_documents: list[dict[str, Any]] = None