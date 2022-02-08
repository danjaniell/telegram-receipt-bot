import os
import requests
import json
from . import models
from typing import Optional
from urllib.request import urlopen
from fastapi import Request, FastAPI, Header
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from telebot import TeleBot, types
from dotenv import load_dotenv

load_dotenv("../.env")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bot_token = os.getenv("BOT_API_TOKEN")
mindee_token = os.getenv("MINDEE_API_TOKEN")
bot_mode = os.getenv("BOT_MODE")
secret = os.getenv("SECRET")
WEBHOOK_URL_BASE = os.getenv("WEBHOOK_HOST")
WEBHOOK_URL_PATH = "/%s/" % (secret)

bot_instance = TeleBot(
    token=bot_token,
    parse_mode="MARKDOWN",
    threaded=False,
)


@app.middleware("http")
async def add_no_cache_header(request: Request, call_next):
    """
    Disables caching in vercel
    """
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache"
    return response


@bot_instance.message_handler(content_types=["photo"])
def received_photo(message: types.Message):
    url = "https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}".format(
        bot_token=bot_token, file_id=message.photo[-1].file_id
    )
    response = requests.get(url).json()
    file_path = response["result"]["file_path"]
    url = "https://api.telegram.org/file/bot{bot_token}/{file_path}".format(
        bot_token=bot_token, file_path=file_path
    )
    photo = urlopen(url)
    data = parse_receipt(photo)
    bot_instance.reply_to(message, text=format_response(data))
    bot_instance.send_message(
        message.chat.id, text=f"AddExp {data.total} {data.merchant}-{data.category}"
    )


@bot_instance.message_handler(
    func=lambda message: is_image_file(message), content_types=["document"]
)
def received_image_document(message: types.Message):
    url = "https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}".format(
        bot_token=bot_token, file_id=message.document.file_id
    )
    response = requests.get(url).json()
    file_path = response["result"]["file_path"]
    url = "https://api.telegram.org/file/bot{bot_token}/{file_path}".format(
        bot_token=bot_token, file_path=file_path
    )
    photo = urlopen(url)
    data = parse_receipt(photo)
    bot_instance.reply_to(message, text=format_response(data))
    bot_instance.send_message(
        message.chat.id, text=f"AddExp {data.total} {data.merchant}-{data.category}"
    )


def is_image_file(message: types.Message) -> bool:
    return (
        message.document.mime_type == "image/jpg"
        or message.document.mime_type == "image/jpeg"
        or message.document.mime_type == "image/png"
    )


def parse_receipt(photo):
    receipt_data = read_receipt(photo)

    merchant = receipt_data["supplier"]["value"]
    category = receipt_data["category"]["value"]
    date = receipt_data["date"]["value"]
    time = receipt_data["time"]["value"]
    total = receipt_data["total_incl"]["value"]

    response = models.ReceiptResponse(
        merchant=merchant if merchant else "",
        category=category if category else "",
        date=date if date else "",
        time=time if time else "",
        total=total if total else "",
    )

    return response


def read_receipt(photo):
    url = "https://api.mindee.net/v1/products/mindee/expense_receipts/v3/predict"
    files = {"document": photo}
    headers = {"Authorization": f"Token {mindee_token}"}
    json_response = json.loads(requests.post(url, files=files, headers=headers).text)
    return json_response["document"]["inference"]["prediction"]


def format_response(response):
    return "Merchant: {a}\nCategory: {b}\nDate: {c}\nTime: {d}\nTotal: {e}".format(
        a=response.merchant,
        b=response.category,
        c=response.date,
        d=response.time,
        e=response.total,
    )


@app.post(WEBHOOK_URL_PATH)
async def receive_updates(request: Request, content_type: Optional[str] = Header(None)):
    if content_type == "application/json":
        json_string = await request.json()
        update = types.Update.de_json(json_string)
        bot_instance.process_new_updates([update])
        return "Message received"
    else:
        raise HTTPException(
            status_code=402, detail="Unrecognized data received. Try again."
        )


bot_instance.delete_webhook(drop_pending_updates=True)

if bot_mode == "webhook":
    bot_instance.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)
elif bot_mode == "polling":
    bot_instance.infinity_polling(skip_pending=True)
