import datetime
from pydantic import BaseModel


class ReceiptResponse(BaseModel):
    merchant: str
    category: str
    date: datetime.date
    time: datetime.time
    total: float
