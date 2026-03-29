import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
from routers import auth, inventory, recipes, chat_sessions
from rating.router import router as rating_router
from rating import ensure_collection
from configs import settings
from configs.database import connect_to_mongo, close_mongo_connection

# Align cookie session with long JWTs (OAuth state); override via env if needed.
_SESSION_MAX_AGE = int(os.getenv("SESSION_MAX_AGE_SECONDS", str(7 * 24 * 3600)))
_SESSION_HTTPS_ONLY = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
_SESSION_SAME_SITE = os.getenv("SESSION_COOKIE_SAMESITE", "lax").lower()
if _SESSION_SAME_SITE not in ("lax", "strict", "none"):
    _SESSION_SAME_SITE = "lax"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown"""
    # Startup
    await connect_to_mongo()
    ensure_collection()
    recipes.initialize_recipe_retrieval()
    yield
    # Shutdown
    await close_mongo_connection()


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

# Configure Session Middleware (required for OAuth)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=_SESSION_MAX_AGE,
    same_site=_SESSION_SAME_SITE,
    https_only=_SESSION_HTTPS_ONLY,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(inventory.router)
app.include_router(rating_router)
app.include_router(recipes.router)
app.include_router(chat_sessions.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to FastAPI!",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "database": "connected"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", reload=True, port=8000)
