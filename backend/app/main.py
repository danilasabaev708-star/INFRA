from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, health, public
from app.services.metrics import metrics_loop


@asynccontextmanager
async def lifespan(_: FastAPI):
    stop_event = asyncio.Event()
    metrics_task = asyncio.create_task(metrics_loop(stop_event))
    yield
    stop_event.set()
    await metrics_task


app = FastAPI(title="INFRA", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(public.router, prefix="/api/public", tags=["public"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


@app.get("/")
async def root() -> dict:
    return {"message": "INFRA backend работает."}
