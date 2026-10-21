import uuid
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.database.session import Base, engine, SessionLocal
from backend.app.database.seed import seed_initial_data
from backend.app.routers import (
    auth, cases, evidence, validation, decisions, audit, analytics, team, billing, system, integrations, gold_loan
)
from backend.app.routers.gold_loan import _public_router as gold_loan_public_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="AURA development API for evidence intake, validation, decision traceability, and gold-loan workflow simulations.",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Correlation ID & Performance Middleware
@app.middleware("http")
async def add_correlation_and_timing(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Response-Time-Ms"] = str(duration_ms)
    return response

# Startup Event: Initialize DB Schema & Seed Baseline Data
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()

# Include Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(cases.router, prefix=settings.API_V1_STR)
app.include_router(evidence.router, prefix=settings.API_V1_STR)
app.include_router(validation.router, prefix=settings.API_V1_STR)
app.include_router(decisions.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)
app.include_router(team.router, prefix=settings.API_V1_STR)
app.include_router(billing.router, prefix=settings.API_V1_STR)
app.include_router(system.router, prefix=settings.API_V1_STR)
app.include_router(integrations.router, prefix=settings.API_V1_STR)
app.include_router(gold_loan.router, prefix=settings.API_V1_STR)
app.include_router(gold_loan_public_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "service": "AURA Enterprise SaaS API",
        "version": "1.0.0",
        "docs": f"{settings.API_V1_STR}/docs",
        "status": "online"
    }
