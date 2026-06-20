from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.api.consignas import router as consignas_router
from app.api.submissions import router as submissions_router
from app.api.admin import router as admin_router
from app.models.database import engine, Base
from app.models import models  # noqa: F401 — registra las tablas en Base.metadata

app = FastAPI(title="Corrector Automático AED")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


app.include_router(router, prefix="/api")
app.include_router(consignas_router, prefix="/api")
app.include_router(submissions_router, prefix="/api")
app.include_router(admin_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
