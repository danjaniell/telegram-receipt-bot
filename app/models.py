import datetime
from pydantic import BaseModel


class ReceiptResponse(BaseModel):
    merchant: str
    category: str
    date: str
    time: str
    total: float
