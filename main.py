from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from scheduler import start_scheduler, stop_scheduler, check_due_extinguishers
from auth_routes import router as auth_router
from customer_routes import router as customer_router
from auth_dependencies import get_current_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run immediate check on startup
    try:
        check_due_extinguishers()
    except Exception as e:
        print(f"[STARTUP] Initial due check error: {e}")

    # Start recurring background scheduler
    start_scheduler()
    yield
    # Clean shutdown on server exit
    stop_scheduler()


app = FastAPI(title="Fire Safety Management API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "https://fire-guard-app-lovat.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(customer_router, dependencies=[Depends(get_current_user)])