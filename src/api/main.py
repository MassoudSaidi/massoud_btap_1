
from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.responses import HTMLResponse, RedirectResponse

from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.openapi.models import OAuthFlowAuthorizationCode
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request, Response, HTTPException, status, Depends, Form


from jose import jwt, jwk
from jose.utils import base64url_decode

from contextlib import asynccontextmanager
import os
# import asyncio
# import redis.asyncio as aioredis
import redis.asyncio as redis
import logging
import boto3
from config import settings
from typing import Optional, Dict, Any, List
from routes import auth, tests, maintenance
from auth.cognito import get_cognito_login_url
from auth.dependency_functions import get_current_user, get_current_token, get_api_user
from redis_client import redis_client


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



# Environment variables (from ECS Task Definition)
# REDIS_HOST = os.getenv("REDIS_ENDPOINT", "localhost")
# REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# REDIS_HOST = settings.REDIS_ENDPOINT
# REDIS_PORT = settings.REDIS_PORT

# # Define redis client globally
# redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        logger.info("Connecting to Redis...")
        await redis_client.ping()
        logger.info("Successfully connected to Redis!")
    except Exception as e:
        logger.error(f"Redis connection error: {e}")

    yield  # <-- App runs here

    # Shutdown
    # await redis_client.close()
    # await redis_client.connection_pool.disconnect()
    try:
        logger.info("Closing Redis connection...")
        await redis_client.close()
        logger.info("Redis connection closed.")
    except Exception as e:
        logger.error(f"Error while closing Redis: {e}")    

# app = FastAPI(lifespan=lifespan)
app = FastAPI(
    lifespan=lifespan,
    title="Surrogate Model API",
    swagger_ui_init_oauth={
        "clientId": settings.COGNITO_APP_PUBLIC_CLIENT_ID,
        "scopes": {"openid"},
        "usePkceWithAuthorizationCodeGrant": True,
    }
)


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

# Register routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(tests.router, prefix="/tests", tags=["Test"])
app.include_router(maintenance.router, prefix="/maintenance", tags=["Redis Maintenance"])




# 1. Health check endpoint
@app.get("/health")
async def health_check():
    return JSONResponse(status_code=200, content={
        "status": "ok",
        "message": "Server is healthy"
    })

# 2. Main application endpoint
@app.get("/api/v1/data", response_class=JSONResponse)
async def get_sample_data(user: Optional[Dict[str, Any]] = Depends(get_api_user)):
# async def get_sample_data(user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Returns sample data to authenticated users."""
    # if not user:
    #     raise HTTPException(status_code=401, detail="Unauthorized")

    sample_data = {
        "message": f"Hello, {user.get('email', 'user')}!",
        "data": {
            "items": [
                {"id": 1, "value": "foo"},
                {"id": 2, "value": "bar"},
                {"id": 3, "value": "baz"},
            ]
        }
    }
    return JSONResponse(content=sample_data)

# --- Template routes ---

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home(request: Request):
    """
    Displays the home page.
    """
    context = {
    "request": request,
    "user": {},
    "cognito_login_url": get_cognito_login_url()
    }
    return templates.TemplateResponse("index.html", context)

# Root endpoint
@app.get("/entry")
async def root():
    return PlainTextResponse("Welcome to the application (v1.2.0). Try the /app or /health endpoints.")

@app.get("/profile", response_class=HTMLResponse, include_in_schema=False)
async def home(request: Request, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """
    Displays the home page.
    """
    context = {
    "request": request,
    "user": user,
    "cognito_login_url": get_cognito_login_url()
    }
    return templates.TemplateResponse("profile.html", context)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
# if __name__ == "__main__":
#     import asyncio
#     import uvicorn

#     async def main():
#         config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 3000)))
#         server = uvicorn.Server(config)
#         await server.serve()

#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         logger.info("Shutting down via Ctrl+C")
#     finally:
#         # Manually restore prompt on Windows
#         import sys
#         sys.stdout.write('\n')
#         sys.stdout.flush()