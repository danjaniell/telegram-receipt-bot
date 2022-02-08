from . import models
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_no_cache_header(request: Request, call_next):
    """
    Disables caching in vercel
    """
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/say-hello")
def say_hello():
    return "Hello!"
